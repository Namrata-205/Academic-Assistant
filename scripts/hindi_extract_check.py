"""Check Hindi extraction quality for one or more chapters (v4).

Run from the project root:
    python scripts/hindi_extract_check.py                      # fhgp101.pdf
    python scripts/hindi_extract_check.py fhgp102.pdf fhgp103.pdf
    python scripts/hindi_extract_check.py --all                # every fhgp*.pdf
    python scripts/hindi_extract_check.py --engine pymupdf     # v3 behaviour, for comparison
    python scripts/hindi_extract_check.py --ocr                # allow Tesseract fallback
    python scripts/hindi_extract_check.py --poppler            # agreement with pdftotext (if on PATH)
    python scripts/hindi_extract_check.py --audit 40           # sample 40 sentences to check by hand
    python scripts/hindi_extract_check.py --score-audit        # score the filled-in audit file

Sentence audit (quick manual check, ~15 min per chapter):
    --audit N writes tmp/hi_<chapter>_audit.tsv with N random sentences (fixed seed).
    Open the PDF next to it and put 1 (sentence exactly right) or 0 (any error) in the
    'ok' column; then --score-audit prints sentence accuracy with a 95% interval.

Gold pages (stopping rule: body OOV <= 2 %, CER <= 2-3 %):
    hand-type a page in reading order, without header/footer/page number, and save it as
        assets/gold/hi/<chapter>_p<page>.txt        e.g. assets/gold/hi/fhgp101_p3.txt
    the script finds these files automatically and prints CER / WER for
    raw PyMuPDF, the PyMuPDF-only path and the final output.

Columns: OOV raw = raw PyMuPDF text; mupdf = PyMuPDF engine + v4 repairs (no pdfium);
final = chosen output.  OOV cannot see 'repaired into the wrong real word', so judge
with gold CER (or --poppler) as well, not OOV alone.

Outputs (in tmp/, ignored by git):
    hi_<chapter>_raw.txt      raw PyMuPDF text
    hi_<chapter>_clean.txt    cleaned text
    hi_<chapter>_oov.txt      unknown words with counts      (review these!)
    hi_<chapter>_blocks.tsv   per block: chosen engine, scores, both candidates
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from diagnostic.hindi_text import (LEXICON_FILE, WORD_RE, cer, extract_hindi_page, have_pdfium,
                                   load_corrections, make_is_word, quality, wer)

HI_DIR = ROOT / 'assets' / 'textbooks' / 'hi'
GOLD_DIR = ROOT / 'assets' / 'gold' / 'hi'
OUT_DIR = ROOT / 'tmp'

# ---------- arguments ----------
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('pdfs', nargs='*', default=['fhgp101.pdf'])
ap.add_argument('--all', action='store_true', help='run every fhgp*.pdf in assets/textbooks/hi')
ap.add_argument('--engine', choices=['auto', 'pdfium', 'pymupdf'], default='auto')
ap.add_argument('--ocr', action='store_true', help='OCR fallback for bad pages (needs Tesseract hin)')
ap.add_argument('--no-compare', action='store_true', help='skip the v3 (pymupdf-only) column')
ap.add_argument('--poppler', action='store_true',
                help='letter-level agreement with poppler pdftotext (independent ActualText reader)')
ap.add_argument('--gold-dir', type=Path, default=GOLD_DIR)
ap.add_argument('--audit', type=int, metavar='N', help='write N random sentences for a manual check')
ap.add_argument('--score-audit', action='store_true', help='score tmp/hi_<chapter>_audit.tsv and exit')
args = ap.parse_args()

names = sorted(p.name for p in HI_DIR.glob('fhgp*.pdf')) if args.all else args.pdfs
if not names:
    sys.exit(f'No PDFs found in {HI_DIR}')


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return max(0.0, c - h), min(1.0, c + h)


if args.score_audit:
    for name in names:
        f = OUT_DIR / f'hi_{Path(name).stem}_audit.tsv'
        if not f.exists():
            print(f'{name}: no audit file (run with --audit N first)')
            continue
        marks = [l.split('\t')[2].strip() for l in f.read_text(encoding='utf-8').splitlines()[1:] if l.strip()]
        done = [m for m in marks if m in ('0', '1')]
        k = done.count('1')
        lo, hi = wilson(k, len(done))
        print(f'{name}: {k}/{len(done)} sentences correct = {k / max(len(done), 1):.0%} '
              f'(95% interval {lo:.0%} to {hi:.0%}); {len(marks) - len(done)} not marked')
    sys.exit(0)
compare = not args.no_compare and args.engine != 'pymupdf'
if args.engine != 'pymupdf' and not have_pdfium():
    print('NOTE: pypdfium2 not installed -> pymupdf only.  pip install pypdfium2')
poppler = shutil.which('pdftotext') if args.poppler else None
if args.poppler and not poppler:
    print('NOTE: --poppler given but pdftotext is not on PATH; skipping')

# ---------- lexicon ----------
if not LEXICON_FILE.exists():
    LEXICON_FILE.write_text('# One correct Hindi word per line '
                            '(domain terms the general word list misses)\n', encoding='utf-8')
terms = []
try:
    from diagnostic import engine as e
    nodes, _ = e.load_graph()
    terms = [n.get('hi', '') for n in nodes.values()]
    print(f'Loaded {len(terms)} Hindi KG terms')
except Exception as ex:
    print('Could not load KG terms:', ex)
is_word = make_is_word(terms)
corrections = load_corrections()
print(f'Lexicon: {len(is_word.domain)} domain words | corrections: {len(corrections)}')
OUT_DIR.mkdir(exist_ok=True)


def bigram_f1(hyp, ref):
    """Order-free agreement: F1 of Devanagari character bigrams (spaces removed).
    Doubled letters lower precision, lost letters lower recall; reading order and
    word splits do not matter, so it is fair against poppler's layout."""
    def grams(t):
        t = re.sub('[^\u0900-\u0963\u0966-\u097F]', '', t)
        return Counter(t[i:i + 2] for i in range(len(t) - 1))
    h, r = grams(hyp), grams(ref)
    ov = sum((h & r).values())
    p, rc = ov / max(sum(h.values()), 1), ov / max(sum(r.values()), 1)
    return 2 * p * rc / max(p + rc, 1e-9)


def poppler_page(pdf, i):
    r = subprocess.run([poppler, '-f', str(i), '-l', str(i), '-enc', 'UTF-8', str(pdf), '-'],
                       capture_output=True, text=True, encoding='utf-8')
    return r.stdout


summary = []
for name in names:
    pdf = HI_DIR / name
    if not pdf.exists():
        print(f'Not found: {pdf}')
        continue
    stem = pdf.stem
    raw_all, clean_all, block_rows, gold_rows = [], [], [], []
    engine_blocks = Counter()
    start = time.time()

    print(f'\n{name}  (engine {args.engine}, OCR {"on" if args.ocr else "off"})')
    head = f'{"page":>4} | {"words":>5} | {"OOV raw":>7} |'
    head += f' {"mupdf":>5} |' if compare else ''
    head += f' {"final":>5} | {"bad/100":>7} | blocks pdfium/merged/pymupdf | swaps | method'
    head += ' | poppler F1 raw -> final' if poppler else ''
    print(head)

    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc, 1):
            raw = page.get_text('text', sort=True)
            clean, method, _, records = extract_hindi_page(
                page, is_word, ocr=args.ocr, engine=args.engine,
                corrections=corrections, return_blocks=True)
            q_raw, q_clean = quality(raw, is_word), quality(clean, is_word)
            n = Counter(r['chosen'] for r in records)
            n_swaps = sum(r.get('swaps', 0) for r in records)
            engine_blocks.update(n)
            engine_blocks['swaps'] += n_swaps

            row = f'{i:>4} | {q_clean["words"]:>5} | {q_raw["oov_rate"]:>7.0%} |'
            v3 = None
            if compare:
                v3, _, _ = extract_hindi_page(page, is_word, ocr=False, engine='pymupdf',
                                              corrections=corrections)
                row += f' {quality(v3, is_word)["oov_rate"]:>5.0%} |'
            row += (f' {q_clean["oov_rate"]:>5.0%} | {q_clean["invalid_per_100"]:>7.1f} |'
                    f' {n["pdfium"]:>9}/{n["merged"]}/{n["pymupdf"]:<14} | {n_swaps:>5} | {method}')
            if poppler:
                ref = poppler_page(pdf, i)
                row += f' | {bigram_f1(raw, ref):.3f} -> {bigram_f1(clean, ref):.3f}'
            print(row)

            raw_all.append(f'===== PAGE {i} =====\n{raw}')
            clean_all.append(f'===== PAGE {i} =====\n{clean}')
            for r in records:
                c = r['candidates']
                block_rows.append('\t'.join([
                    str(i), str(r['block']), r['chosen'],
                    *(f'{c[k][1]:.2f}' if k in c else '' for k in ('pdfium', 'pymupdf')),
                    *(c[k][0].replace('\t', ' ').replace('\n', ' ') if k in c else ''
                      for k in ('pdfium', 'pymupdf')),
                    r['text'].replace('\t', ' ').replace('\n', ' ')]))

            gold_file = args.gold_dir / f'{stem}_p{i}.txt'
            if gold_file.exists():
                gold = gold_file.read_text(encoding='utf-8')
                v3_text = v3 if v3 is not None else extract_hindi_page(
                    page, is_word, ocr=False, engine='pymupdf', corrections=corrections)[0]
                gold_rows.append((i, [(lab, cer(t, gold), wer(t, gold))
                                      for lab, t in (('raw', raw), ('mupdf', v3_text),
                                                     ('final', clean))]))

    # ---------- outputs ----------
    clean_text = '\n'.join(clean_all)
    if args.audit:
        import random
        sents = []
        for page_txt in clean_all:
            page_no = page_txt.split('\n', 1)[0].strip('= PAGE')
            for sent in re.split(r'(?<=[।?!])\s+', page_txt.split('\n', 1)[1].replace('\n', ' ')):
                if len(WORD_RE.findall(sent)) >= 4:
                    sents.append((page_no, sent.strip()))
        picked = random.Random(13).sample(sents, min(args.audit, len(sents)))
        picked.sort(key=lambda x: int(x[0]))
        (OUT_DIR / f'hi_{stem}_audit.tsv').write_text(
            'id\tpage\tok\tsentence\n' + '\n'.join(f'{i}\t{pg}\t\t{t}' for i, (pg, t) in enumerate(picked, 1)),
            encoding='utf-8')
        print(f'Audit: tmp/hi_{stem}_audit.tsv ({len(picked)} of {len(sents)} sentences); '
              f'mark ok = 1/0, then run --score-audit')
    (OUT_DIR / f'hi_{stem}_raw.txt').write_text('\n'.join(raw_all), encoding='utf-8')
    (OUT_DIR / f'hi_{stem}_clean.txt').write_text(clean_text, encoding='utf-8')
    (OUT_DIR / f'hi_{stem}_blocks.tsv').write_text(
        'page\tblock\tchosen\tbad_pdfium\tbad_pymupdf\tpdfium_text\tpymupdf_text\tfinal_text\n'
        + '\n'.join(block_rows), encoding='utf-8')
    oov = Counter(w for w in WORD_RE.findall(clean_text) if not is_word.known(w))
    (OUT_DIR / f'hi_{stem}_oov.txt').write_text(
        '\n'.join(f'{n}\t{w}' for w, n in oov.most_common()), encoding='utf-8')

    total = quality(clean_text, is_word)
    print(f'\nWhole chapter: {total["words"]} words | bad/100: {total["invalid_per_100"]:.1f} | '
          f'OOV: {total["oov_rate"]:.1%} | blocks pdfium {engine_blocks["pdfium"]} / merged '
          f'{engine_blocks["merged"]} / pymupdf {engine_blocks["pymupdf"]} | word swaps '
          f'{engine_blocks["swaps"]} | {time.time() - start:.1f}s')
    print('Top unknown words:', ', '.join(f'{w}({n})' for w, n in oov.most_common(25)) or '-')
    for page_no, scores in gold_rows:
        print(f'Gold p{page_no}: ' + ' | '.join(f'{lab} CER {c:.1%} WER {w:.1%}'
                                               for lab, c, w in scores))
    if not gold_rows:
        print(f'(no gold pages: add {args.gold_dir.relative_to(ROOT)}/{stem}_p<N>.txt for CER/WER)')
    print(f'Saved tmp/hi_{stem}_raw.txt, _clean.txt, _oov.txt, _blocks.tsv')
    summary.append((name, total['words'], total['oov_rate'], engine_blocks['merged'],
                    engine_blocks['swaps']))

if len(summary) > 1:
    print('\nSummary')
    for name, n, o, a, b in summary:
        print(f'  {name:14} {n:>6} words  OOV {o:5.1%}  merged blocks {a}  word swaps {b}')
print(f'\nCompare:  code --diff tmp/hi_{Path(names[-1]).stem}_raw.txt '
      f'tmp/hi_{Path(names[-1]).stem}_clean.txt')