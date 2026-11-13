"""Single entry point for textbook text: every part of the app gets page text from here.

    from diagnostic.extraction import get_pages, split_sentences, normalize_query

    pages = get_pages('assets/textbooks/hi/fhgp101.pdf', 'hi')   # [{'page': 1, 'text': ...}, ...]
    sents = split_sentences(pages[0]['text'], 'hi')               # splits on । ? ! as well as .
    query = normalize_query(user_question, 'hi')                  # before embedding a question

How it decides:
  * Hindi  -> the frozen clean file assets/extracted/hi/hi_<stem>_clean.txt if it exists;
              otherwise (a new PDF) it runs the v4.5 pipeline (diagnostic/hindi_text.py),
              writes that file, and uses it from then on.
  * English -> the frozen file assets/extracted/en/en_<stem>_clean.txt if it exists;
              otherwise PyMuPDF blocks (English extraction was never broken), saved the same way.
To re-extract a chapter (e.g. after improving hindi_text.py), delete its file or pass force=True.

Export all chapters at once (creates the missing files, leaves frozen ones alone):
    python -m diagnostic.extraction --export
    python -m diagnostic.extraction --export --force      # re-extract everything
"""
import re
from functools import lru_cache
from pathlib import Path

EXTRACTION_VERSION = 'hi-v4.5 (pdfium+PyMuPDF merge, lexicon repair); en-pymupdf-blocks'
ROOT = Path(__file__).resolve().parents[1]
TEXTBOOKS = ROOT / 'assets' / 'textbooks'
EXTRACTED = ROOT / 'assets' / 'extracted'
_PAGE = re.compile(r'^===== PAGE (\d+) =====$', re.M)


def _fitz():
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    return pymupdf


def clean_path(pdf_path, lang):
    return EXTRACTED / lang / f'{lang}_{Path(pdf_path).stem}_clean.txt'


def read_clean_file(path):
    """Parse a '===== PAGE n =====' file into [{'page': n, 'text': ...}]."""
    text = Path(path).read_text(encoding='utf-8')
    parts = _PAGE.split(text)                       # ['', '1', 'text1', '2', 'text2', ...]
    return [{'page': int(n), 'text': body.strip()} for n, body in zip(parts[1::2], parts[2::2])]


def write_clean_file(path, pages):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(f'===== PAGE {p["page"]} =====\n{p["text"]}' for p in pages),
                    encoding='utf-8')


@lru_cache(maxsize=1)
def _hindi_lexicon():
    from diagnostic.hindi_text import make_is_word
    terms = []
    try:                                            # KG Hindi terms make the repairs better
        from diagnostic import engine
        nodes, _ = engine.load_graph()
        terms = [n.get('hi', '') for n in nodes.values()]
    except Exception:
        pass
    return make_is_word(terms)


def _extract_hindi(pdf_path):
    from diagnostic.hindi_text import extract_hindi_pdf
    return [{'page': p['page'], 'text': p['text']}
            for p in extract_hindi_pdf(pdf_path, _hindi_lexicon(), ocr=False)]


def _extract_english(pdf_path):
    """The same PyMuPDF blocks book_chat.page_content always used, one block per line
    (blank line between blocks), so English chunks stay exactly as before."""
    with _fitz().open(pdf_path) as doc:
        return [{'page': i, 'text': '\n\n'.join(' '.join(b[4].split()) for b in page.get_text('blocks')
                                                if b[4].strip())}
                for i, page in enumerate(doc, 1)]


def get_pages(pdf_path, lang, force=False):
    """Page texts for one textbook PDF; extracts and saves on first use."""
    path = clean_path(pdf_path, lang)
    if path.exists() and not force:
        return read_clean_file(path)
    pages = _extract_hindi(pdf_path) if lang == 'hi' else _extract_english(pdf_path)
    write_clean_file(path, pages)
    return pages


# ---------------------------------------------------------------------------
_SENT_HI = re.compile(r'(?<=[।॥?!])\s+')           # । ॥ ? !
_SENT_EN = re.compile(r'(?<=[.?!])\s+(?=[A-Z0-9(])')


def split_sentences(text, lang):
    """Sentence split that knows the Hindi full stop (।)."""
    text = ' '.join(text.split())
    parts = (_SENT_HI if lang == 'hi' else _SENT_EN).split(text)
    return [p.strip() for p in parts if p.strip()]


def normalize_query(text, lang):
    """Apply to user questions before embedding, so they match the cleaned book text."""
    if lang == 'hi':
        from diagnostic.hindi_text import normalize_query as nq
        return nq(text)
    return ' '.join(text.split())


def export_all(force=False):
    for lang in ('en', 'hi'):
        for pdf in sorted((TEXTBOOKS / lang).glob('*.pdf')):
            existed = clean_path(pdf, lang).exists()
            pages = get_pages(pdf, lang, force=force)
            state = 'kept (frozen)' if existed and not force else 'extracted'
            print(f'{lang}  {pdf.name:16} {len(pages):>3} pages  {state}  -> '
                  f'{clean_path(pdf, lang).relative_to(ROOT)}')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    if '--export' in sys.argv:
        export_all(force='--force' in sys.argv)
    else:
        print(__doc__)