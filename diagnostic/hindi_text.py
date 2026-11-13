"""Extraction, repair and quality scoring for Hindi text in NCERT PDFs (v4).

Why the PyMuPDF text was broken
-------------------------------
The NCERT Hindi PDFs use a legacy-encoded Devanagari font whose glyph->Unicode
table is wrong, and they carry the *correct* text separately as PDF
``/ActualText`` spans.  PyMuPDF's default output mixes the two, which is where
ययह, हीी, संख्यायाएँ, कक्ा ... come from.  PDFium (``pypdfium2``) reads the
ActualText properly, so it gets almost all letters right; but it drops some
spaces and its character boxes are spread evenly over each glyph run.

Pipeline per page
-----------------
1. Layout from PyMuPDF (blocks, reading order, boilerplate removal).
2. Two candidate texts for every block:
     * ``pdfium``  - ActualText characters, grouped into aksharas, lines and
                     spaces rebuilt from glyph geometry;
     * ``pymupdf`` - the old text layer.
3. Each candidate gets Step A (deterministic Unicode repair) and Step B
   (lexicon-guided repair); the block keeps whichever candidate has fewer
   unknown words (ties go to pdfium).
4. Pages that still look bad can fall back to OCR (Tesseract 'hin').

``pypdfium2`` is optional: without it everything runs on PyMuPDF as in v3.
"""
import difflib
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

CONS   = '\u0915-\u0939\u0958-\u095F'   # consonants
INDEP  = '\u0904-\u0914'                # independent vowels
BASE   = CONS + INDEP
MATRA  = '\u093E-\u094C\u0962\u0963'    # dependent vowel signs
SIGNS  = '\u0901-\u0903'                # chandrabindu, anusvara, visarga
HALANT = '\u094D'
NUKTA  = '\u093C'
DEV    = '\u0900-\u097F'
WORD_RE = re.compile('[\u0900-\u0963\u0966-\u097F]+')   # Devanagari word, no ।/॥

HERE = Path(__file__).parent
LEXICON_FILE     = HERE / 'hindi_lexicon.txt'
CORRECTIONS_FILE = HERE / 'hindi_corrections.tsv'

# =====================================================================
# Step A: deterministic Unicode repair
# =====================================================================
_ZW         = re.compile('[\u200B-\u200D\u2060\uFEFF\u00AD]')
_DUP_CONJ   = re.compile(rf'{HALANT}{HALANT}([{CONS}]{NUKTA}?)\1')   # स््तत -> स्त
_DUP_HAL    = re.compile(rf'{HALANT}{{2,}}')                         # ््  -> ्
_DUP_MARK   = re.compile(rf'([{MATRA}{SIGNS}{NUKTA}])\1+')           # ीी  -> ी
_ECHO_MARK  = re.compile(rf'([{MATRA}{SIGNS}])\s+\1(?=\s|$)')        # कों ं -> कों
_SIGN_FIRST = re.compile(rf'([ँं])([{MATRA}])')            # गंेद -> गेंद
_SPACE_MARK = re.compile(rf'(?<=[{DEV}])\s+(?=[\u093E\u0940-\u094C\u0962\u0963{SIGNS}{NUKTA}])')  # गं े -> गंे (not ि: हैं िक = हैं कि)
_PUNCT_GLUE = re.compile(rf'([।॥,;:?!)])(?=[{BASE}])')               # है।ये -> है। ये
_STRAY_MARK = re.compile(rf"(?<=[0-9A-Za-z?!.,;:)\]’'\"])[{MATRA}{SIGNS}]+")
# PyMuPDF placeholders for clusters the legacy font draws as one glyph (pdfium drops them):
#   प्रदãशत -> प्रदर्शित (ã = र् before the next consonant + ि after it), उ°र -> उत्तर, ćृंखला -> श्रृंखला
_PH_RI   = re.compile(rf'(?<=[{DEV}])\u00E3((?:[{CONS}]{NUKTA}?{HALANT})*[{CONS}]{NUKTA}?)')
_PH_TT   = re.compile(rf'(?<=[{DEV}])\u00B0(?=[{DEV}])')
_PH_SHR  = re.compile(rf'\u0107(?=[{DEV}])')
_SPACE_PUNC = re.compile(r'\s+([।॥,;:?!)])')                         # है । -> है।


def repair_unicode(text: str) -> str:
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\uFFFD', '')
    text = _ZW.sub('', text)
    text = _SPACE_MARK.sub('', text)
    text = _PH_RI.sub(lambda m: '\u0930\u094D' + m.group(1) + '\u093F', text)
    text = _PH_TT.sub('\u0924\u094D\u0924', text)
    text = _PH_SHR.sub('\u0936\u094D\u0930', text)
    text = _DUP_CONJ.sub(HALANT + r'\1', text)
    text = _DUP_HAL.sub(HALANT, text)
    text = _DUP_MARK.sub(r'\1', text)
    text = _SIGN_FIRST.sub(r'\2\1', text)
    text = (text.replace('अा', 'आ')    # अ + ा -> आ
                .replace('\u093E\u0948', '\u094C')    # ा + ै -> ौ
                .replace('\u093E\u0947', '\u094B')    # ा + े -> ो
                .replace('\u090F\u0947', '\u0910')    # ए + े -> ऐ  (एेलब्रस)
                .replace('\u093E\u0945', '\u0949')    # ा + ॅ -> ॉ  (जैकपाॅट)
                .replace('\u0930\u094D\u0907', '\u0908'))   # legacy र्इ -> ई (हुर्इं)
    text = _ECHO_MARK.sub(r'\1', text)
    text = _STRAY_MARK.sub('', text)
    text = _SPACE_PUNC.sub(r'\1', text)
    text = _PUNCT_GLUE.sub(r'\1 ', text)
    return re.sub(r'[ \t]+', ' ', text).strip()


# =====================================================================
# Boilerplate: footers, sidebars, page numbers, running headers
# =====================================================================
_BOILER  = re.compile(r'^\s*(Reprint \d{4}-\d{2}|.*\.indd\s.*\d{1,2}:\d{2}(:\d{2})?)\s*$')
_SIDEBAR = {'गणित', 'चर्चा', 'प्रयास', 'करें', 'गणित चर्चा', 'प्रयास करें'}


def join_block_lines(block_text: str) -> str:
    lines = [l for l in block_text.splitlines() if l.strip() and not _BOILER.match(l)]
    return ' '.join(l.strip() for l in lines)


def _is_boilerplate(block, page_h):
    """Drop sidebars, page numbers and running headers; keep table numbers."""
    y0, y1 = block[1], block[3]
    text = repair_unicode(' '.join(block[4].split()))
    if not text or text in _SIDEBAR or _BOILER.match(text):
        return True
    at_edge = y0 > 0.88 * page_h or y1 < 0.10 * page_h
    return at_edge and (text.isdigit() or text.startswith('गणित प्रकाश')
                        or text == 'गणित में पैटर्न')


# =====================================================================
# PDFium engine: ActualText characters -> aksharas -> lines
# =====================================================================
_COMB = re.compile('[\u0900-\u0903\u093A-\u094F\u0951-\u0957\u0962\u0963\u200C\u200D]')
_REPH = 'र्'                       # र्
_DEV_CH = re.compile('[\u0900-\u097F]')


def _fitz():
    try:
        import pymupdf
    except ImportError:                     # older installs only have the 'fitz' name
        import fitz as pymupdf
    return pymupdf


def have_pdfium():
    try:
        import pypdfium2  # noqa: F401
        return True
    except ImportError:
        return False


_PDFIUM_CACHE = {}


def _pdfium_doc(doc):
    """PDFium handle for a PyMuPDF document (from its file, or its bytes if in memory)."""
    import pypdfium2 as pdfium
    key = (id(doc), doc.name)
    if key not in _PDFIUM_CACHE:
        if len(_PDFIUM_CACHE) > 8:
            _PDFIUM_CACHE.clear()
        src = doc.name if doc.name and Path(doc.name).is_file() else doc.tobytes()
        _PDFIUM_CACHE[key] = pdfium.PdfDocument(src)
    return _PDFIUM_CACHE[key]


def _pdfium_chars(pdf_page, matrix):
    """Characters with boxes in PyMuPDF coordinates; spaces become markers."""
    pymupdf = _fitz()
    import pypdfium2.raw as R
    tp = pdf_page.get_textpage()
    out = []
    for i in range(tp.count_chars()):
        c = tp.get_text_range(i, 1)
        if not c:
            continue
        if c.isspace():
            generated = R.FPDFText_IsGenerated(tp.raw, i) == 1
            out.append({'sp': 'gen' if generated or c in '\r\n' else 'real'})
            continue
        l, b, r, t = tp.get_charbox(i)
        rect = pymupdf.Rect(l, b, r, t) * matrix          # PDF space -> PyMuPDF space
        rect.normalize()
        out.append({'c': c, 'x0': rect.x0, 'x1': rect.x1, 'y0': rect.y0, 'y1': rect.y1})
    return out


def _aksharas(chars):
    """Group characters into aksharas (base + vowel signs + halant-joined consonants).
    Measuring gaps between aksharas (not characters) keeps ि (drawn left of its
    consonant) and reph from creating false spaces such as प्रकृ ति."""
    out = []
    for ch in chars:
        if 'sp' in ch:
            out.append(ch)
            continue
        c = ch['c']
        if _COMB.match(c):                  # a sign after a space belongs to the word before
            k = len(out)
            while k and 'sp' in out[k - 1]:
                k -= 1
            if k and k < len(out) and 'c' in out[k - 1]:
                del out[k:]
        prev = out[-1] if out and 'c' in out[-1] else None
        if prev and (_COMB.match(c) or prev['c'][-1] in (HALANT, '\u200D')):
            prev['c'] += c
            prev['x0'], prev['x1'] = min(prev['x0'], ch['x0']), max(prev['x1'], ch['x1'])
            prev['y0'], prev['y1'] = min(prev['y0'], ch['y0']), max(prev['y1'], ch['y1'])
        else:
            out.append(dict(ch))
    return out


def _pdfium_lines(chars, gap_ratio=0.15):
    """Rebuild lines and word spaces from akshara geometry."""
    lines, cur, pending = [], None, None
    for a in _aksharas(chars):
        if 'sp' in a:
            pending = 'real' if a['sp'] == 'real' or pending == 'real' else 'gen'
            continue
        h = max(a['y1'] - a['y0'], 1.0)
        if cur:
            p = cur['last']
            size = max(h, cur['h'])
            overlap = min(a['y1'], cur['y1']) - max(a['y0'], cur['y0'])
            if (overlap < 0.3 * min(h, cur['y1'] - cur['y0'])     # different baseline
                    or a['x0'] < p['x1'] - 2 * size):             # jumped back left
                lines.append(cur)
                cur = None
        if cur is None:
            cur = {'t': a['c'], 'x0': a['x0'], 'x1': a['x1'], 'y0': a['y0'],
                   'y1': a['y1'], 'h': h, 'last': a}
        else:
            gap = a['x0'] - cur['last']['x1']
            reph = a['c'].startswith(_REPH) and len(a['c']) > 2
            latin = not (_DEV_CH.search(a['c']) or _DEV_CH.search(cur['last']['c']))
            ratio = 2.5 * gap_ratio if latin else gap_ratio     # digits/Latin: kerning gaps
            if pending == 'real' or (gap > ratio * size and not reph):
                cur['t'] += ' '
            cur['t'] += a['c']
            cur['x0'], cur['x1'] = min(cur['x0'], a['x0']), max(cur['x1'], a['x1'])
            cur['y0'], cur['y1'] = min(cur['y0'], a['y0']), max(cur['y1'], a['y1'])
            cur['h'], cur['last'] = max(cur['h'], h), a
        pending = None
    if cur:
        lines.append(cur)
    return lines


def _pdfium_block_texts(page, blocks):
    """Text for each PyMuPDF block, built from PDFium lines (None if unavailable)."""
    if not have_pdfium():
        return None
    pymupdf = _fitz()
    try:
        pdf_page = _pdfium_doc(page.parent)[page.number]
        lines = _pdfium_lines(_pdfium_chars(pdf_page, page.transformation_matrix))
    except Exception as ex:                       # fall back to PyMuPDF, but say so
        if not getattr(_pdfium_block_texts, 'warned', False):
            print(f'[hindi_text] pdfium engine failed ({type(ex).__name__}: {ex}); using PyMuPDF only')
            _pdfium_block_texts.warned = True
        return None
    rects = [pymupdf.Rect(b[:4]) + (-3, -3, 3, 3) for b in blocks]
    texts = [[] for _ in blocks]
    margin_x = 0.70 * page.rect.width
    for ln in lines:
        if ln['x0'] > margin_x and repair_unicode(ln['t']) in _SIDEBAR:
            continue                                # 'गणित चर्चा' / 'प्रयास करें' labels                       # lines outside every block (slug, crop marks) are dropped
        r = pymupdf.Rect(ln['x0'], ln['y0'], ln['x1'], ln['y1'])
        areas = [(rb & r).get_area() for rb in rects]
        if areas and max(areas) > 0:
            texts[areas.index(max(areas))].append(ln['t'])
    return [' '.join(t) for t in texts]


# =====================================================================
# Lexicon
# =====================================================================
# (suffix, what to put back on the stem) - संख्याएँ -> संख्या, लंबाइयाँ -> लंबाई
SUFFIXES = [
    ('ियों', ''), ('ियाँ', ''), ('ियां', ''), ('ाओं', ''), ('ाएँ', ''), ('ाएं', ''),
    ('ओं', ''), ('एँ', ''), ('एं', ''), ('यों', ''), ('याँ', ''), ('यां', ''),
    ('\u094B\u0902', ''), ('\u0947\u0902', ''), ('\u0940\u0902', ''), ('\u093E\u0901', ''), ('\u093E\u0902', ''),
    ('इयों', 'ई'), ('इयाँ', 'ई'), ('ियों', '\u0940'), ('ियाँ', '\u0940'),
    ('ाइए', '\u093E'), ('िए', ''), ('इए', ''), ('िये', ''), ('ाइये', '\u093E'),
    ('ीय', ''), ('ता', ''), ('ना', ''), ('ने', ''), ('कर', ''),
    ('\u0947', ''), ('\u0940', ''), ('\u093E', ''),          # (no bare -ो: गुणनखंडो is not a form)
    ('\u0947', '\u093E'), ('\u094B\u0902', '\u093E'),   # गत्ते, खजानों -> गत्ता, खजाना
    ('\u092F\u093E\u0901', '\u092F\u093E'), ('\u092F\u093E\u0902', '\u092F\u093E'),   # गुजियाँ -> गुजिया
]
# verb endings, checked against the infinitive: खींचेंगे / खींचनी -> खींचना, दर्शाई -> दर्शाना
VERB_SUFFIXES = ('ेंगे', 'ेंगी', 'ेगा', 'ेगी', 'एँगे', 'एंगे', 'ते', 'ती', 'ता', 'नी', 'ने',
                 'ई', 'ईं', 'यी', 'या', 'ये', 'ए', 'कर', '\u094B', '\u0947\u0902', '\u093E')
# closed-class words used to split glued tokens: केसाथ -> के साथ
FUNCTION_WORDS = set('''के की का को में से ने पर और तथा या है हैं था थे थी भी ही यह वह ये वे
इस उस इन उन इसके उसके इनके उनके इसकी उसकी इनकी उनकी अपना अपनी अपने एक दो कुछ सभी
किया किए करें करना करने करते करता जा जाता जाती जाते गया गई गए होता होती होते सकते
सकता सकती लिए साथ बीच द्वारा बाद पहले तक जो जब तब कि क्या कौन कैसे वाला वाली वाले न'''.split())
# split points for glued words: function words that rarely begin another word
# (not न, पर, कि, जो, तक, या ... : नुकीला, परिमाणित, परमिता, रिहान must stay whole)
SPLIT_WORDS = FUNCTION_WORDS - set('न पर कि जो तक दो एक जा जब तब या इन उन इस उस'.split())
_SANDHI = {'\u093E': 'आ', '\u093F': 'इ', '\u0940': 'ई', '\u0941': 'उ',
           '\u0942': 'ऊ', '\u0947': 'ए', '\u094B': 'ओ'}     # ा->आ ...


def _aksharas_of(word):
    """Split a word into akshara strings (for compound split points)."""
    out = []
    for c in word:
        if out and (_COMB.match(c) or out[-1][-1] == HALANT):
            out[-1] += c
        else:
            out.append(c)
    return out


class Lexicon:
    """Word check = KG/question-bank terms + hindi_lexicon.txt + wordfreq ('hi').

    lex(w)          True if w (or w minus an inflection) is a known word
    lex.freq(w)     zipf-like score used to rank repair candidates
    lex.compound(w) split point if w = known + known (बहुभुज, वर्गाकार, दृश्यांकन)
    lex.split(w)    (a, b) if w is two words glued together around a function word
    """
    DOMAIN_SCORE = 8.0

    def __init__(self, domain_terms=(), lexicon_file=LEXICON_FILE, min_zipf=1.5):
        domain = {w for t in domain_terms if t for w in WORD_RE.findall(repair_unicode(t))}
        if lexicon_file and Path(lexicon_file).exists():
            for line in Path(lexicon_file).read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    domain.update(WORD_RE.findall(repair_unicode(line)))
        self.domain = domain
        self.min_zipf = min_zipf
        try:
            from wordfreq import zipf_frequency
            self._zipf = lambda w: zipf_frequency(w, 'hi')
        except ImportError:
            print('wordfreq not installed: only domain terms + hindi_lexicon.txt are used')
            self._zipf = lambda w: 0.0
        self.freq = lru_cache(maxsize=300_000)(self._freq)
        self.compound = lru_cache(maxsize=100_000)(self._compound)
        self.split = lru_cache(maxsize=100_000)(self._split)
        self._is = lru_cache(maxsize=300_000)(self._is_word)

    # ---- exact lookups -------------------------------------------------
    def _base(self, w):
        if w in self.domain or (w + '\u0903') in self.domain:   # उदाहरणत: = उदाहरणतः
            return self.DOMAIN_SCORE
        z = self._zipf(w)
        if z <= self.min_zipf:                            # उदाहरणत: (colon used as visarga)
            z = max(z, self._zipf(w + '\u0903'))
        if z <= self.min_zipf and '\u0901' in w:          # ँ / ं spelling variants
            z = max(z, self._zipf(w.replace('\u0901', '\u0902')))
        if z <= self.min_zipf and '\u0902' in w:
            z = max(z, self._zipf(w.replace('\u0902', '\u0901')))
        if w.replace('\u0901', '\u0902') in self.domain or w.replace('\u0902', '\u0901') in self.domain:
            return self.DOMAIN_SCORE
        return z if z > self.min_zipf else 0.0

    def _freq(self, w):
        best = self._base(w)
        if best >= self.DOMAIN_SCORE:
            return best
        if best:                       # a common word may still be a domain word's inflection
            dom = any(w.endswith(suf) and w[:-len(suf)] in self.domain for suf in _PLURALS)
            return self.DOMAIN_SCORE - 0.5 if dom else best
        for suf, back in SUFFIXES:
            if w.endswith(suf) and len(w) > len(suf) + 1:
                stem = w[:-len(suf)] + back
                if not re.match(rf'^[{BASE}]', stem):
                    continue
                if suf.startswith('\u092F') and not re.search('[\u093F\u0940\u0907\u0908]$', w[:-len(suf)]):
                    continue              # -यों/-याँ only after an i-stem: not बिंदुयां
                if back == '\u093E' and len(_aksharas_of(stem)) < 2:   # गत्ते -> गत्ता, never क -> का
                    continue
                s = self._base(stem)
                if s:
                    best = max(best, s - 0.5)                 # inflected: slightly less sure
        if not best:
            for suf in VERB_SUFFIXES:
                if w.endswith(suf) and len(_aksharas_of(w[:-len(suf)])) >= 2:
                    s = self._base(w[:-len(suf)] + 'ना')           # stem + ना
                    if s:
                        best = max(best, s - 0.5)
        return best

    def _is_word(self, w):
        return self.freq(w) > 0

    def __call__(self, w):
        return self._is(w)

    # ---- two-part words ------------------------------------------------
    def _parts(self, w, min_aks=2):
        aks = _aksharas_of(w)
        for k in range(min_aks, len(aks) - min_aks + 1):
            yield ''.join(aks[:k]), ''.join(aks[k:])

    def _solid(self, s):
        """A compound part: a real word (or inflected word) whose stem has 2+ aksharas,
        so that संख्या + याएँ (या = 'or') does not count."""
        if not re.match(rf'^[{BASE}]', s):
            return False
        stems = [s] + [s[:-len(suf)] + back for suf, back in SUFFIXES
                       if s.endswith(suf) and len(s) > len(suf) + 1]
        return any(len(_aksharas_of(t)) >= 2 and self._base(t) >= 2.0 for t in stems)

    def _compound(self, w):
        """बहु+भुज, वर्ग+(आ)कार, दृश्य+(अं)कन: both parts must be known words."""
        if len(_aksharas_of(w)) < 4:
            return None
        splits = list(self._parts(w))
        # a-sandhi inside an akshara: दृश्य|ांकन (दृश्य + अंकन), चित्र|ात्मक (चित्र + आत्मक)
        splits += [(w[:i], w[i:]) for i in range(2, len(w) - 2)
                   if w[i] == '\u093E' and re.match(rf'[{CONS}]', w[i - 1])]
        for a, b in splits:
            if not re.match(rf'^[{BASE}]', a) or not self(a) or self.freq(a) < 2.5:
                continue
            if b[0] == '\u093E':
                seconds = ['अ' + b[1:], 'आ' + b[1:]]          # अ… / आ…
            elif b[0] in _SANDHI:
                seconds = [_SANDHI[b[0]] + b[1:]]
            else:
                seconds = [b]
            if any(self._solid(s) for s in seconds):
                return a, b
        return None

    def _split(self, w):
        """Two words glued together, one of them a function word: केसाथ -> के साथ."""
        best = None
        for a, b in self._parts(w, min_aks=1):
            if not (re.match(rf'^[{BASE}]', a) and re.match(rf'^[{BASE}]', b)):
                continue
            if not all(x in FUNCTION_WORDS or len(_aksharas_of(x)) >= 2 for x in (a, b)):
                continue                                     # इनहें is not इन + हें
            if ((a in SPLIT_WORDS or b in SPLIT_WORDS)
                    and self.freq(a) >= 3.0 and self.freq(b) >= 3.0):
                score = self.freq(a) + self.freq(b)
                if best is None or score > best[0]:
                    best = (score, a, b)
        return best[1:] if best else None

    def known(self, w):
        """Used for scoring: a word, or a well-formed compound of words."""
        return self(w) or bool(self.compound(w))


def make_is_word(domain_terms=(), lexicon_file=LEXICON_FILE):
    """Backwards-compatible constructor: returns a callable Lexicon."""
    return Lexicon(domain_terms, lexicon_file)


def load_corrections(path=CORRECTIONS_FILE):
    """hindi_corrections.tsv: wrong<TAB>right, one pair per line (# = comment).
    `wrong` may be one token or a phrase ('ऊं पर'); an empty `right` deletes it."""
    pairs = {}
    if path and Path(path).exists():
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#') and '\t' in line:
                wrong, right = line.split('\t', 1)          # empty right side = delete
                right = right.strip()
                pairs[repair_unicode(wrong.strip())] = '' if right.lower() == '<del>' else repair_unicode(right)
    return pairs


def apply_corrections(text, corrections):
    if not corrections:
        return text
    for wrong, right in corrections.items():          # multi-word keys: 'ऊं पर' -> 'ऊपर'
        if ' ' in wrong:
            text = re.sub(rf'(?<!\S){re.escape(wrong)}(?=[\s,.;:?!)\u0964]|$)', right, text)
    out = []
    for tok in text.split(' '):
        if re.search(r'[-/]', tok) and not _TOKEN.match(tok):   # each part of a-b or a/b
            tok = ''.join(apply_corrections(part, corrections) if part not in '-/' else part
                          for part in re.split(r'([-/])', tok))
        m = _TOKEN.match(tok)
        if m and m.group(2) in corrections:              # keep punctuation around the word
            fixed = corrections[m.group(2)]
            tok = m.group(1) + fixed + m.group(3) if fixed else m.group(1) + m.group(3)
        elif tok in corrections:
            tok = corrections[tok]
        if tok:
            out.append(tok)
    return ' '.join(out)


# =====================================================================
# Step B: lexicon-guided repair
# =====================================================================
_IS_MARK   = re.compile(rf'[{MATRA}{SIGNS}]')
_LEAD_MARK = re.compile(rf'^([{MATRA}{SIGNS}{NUKTA}]+)(.*)$')
_INVALID   = re.compile(
    rf'^[{MATRA}{SIGNS}{NUKTA}{HALANT}]'      # word starts with a sign
    rf'|[{MATRA}][{MATRA}]'                    # two vowel signs together
    rf'|{HALANT}[{MATRA}{SIGNS}]'              # vowel sign right after halant
    rf'|[{SIGNS}][{MATRA}]'                    # ं/ँ before a vowel sign
)
_CONS_LIST = [chr(c) for c in range(0x0915, 0x093A)]
_TOKEN = re.compile(rf'^([^{DEV}]*)([{DEV}]+?)((?:[\u0964\u0965]|[^{DEV}])*)$')   # (prefix, word, suffix) - suffix may mix ) ’ and ।


def _valid(word):
    return not _INVALID.search(word)


def _is_dev(tok):
    return bool(re.search(rf'[{DEV}]', tok))


def _insert_mark(word, mark, is_word):
    """Place a stray mark back into `word`: 'त्रिभजाकार' + 'ु' -> 'त्रिभुजाकार'."""
    is_sign = mark in '\u0901\u0902\u0903'
    for i, ch in enumerate(word):
        if not re.match(rf'[{BASE}]', ch):
            continue
        j = i + 1
        while j < len(word) and (word[j] == NUKTA or
                                 (is_sign and re.match(rf'[{MATRA}]', word[j]))):
            j += 1
        cand = word[:j] + mark + word[j:]
        if _valid(cand) and is_word(cand):
            return cand
    return word


def _dedupe_candidates(word):
    """ययह -> यह, क्याया -> क्या, चित्रोंत्रों -> चित्रों (the lexicon decides)."""
    out = []
    for size in range(1, 7):
        for i in range(len(word) - 2 * size + 1):
            if word[i:i + size] == word[i + size:i + 2 * size]:
                cand = word[:i + size] + word[i + 2 * size:]
                if cand not in out:
                    out.append(cand)
    return out


def _fill_missing_candidates(word):
    """द्ारा -> द्वारा, कक्ा -> कक्षा, ्मरण -> स्मरण, सं्करण -> संस्करण."""
    out = []
    for i, ch in enumerate(word):
        if ch != HALANT:
            continue
        prev = word[i - 1] if i else ''
        nxt = word[i + 1] if i + 1 < len(word) else ''
        if not prev or not re.match(rf'[{CONS}]', prev):
            out += [word[:i] + c + word[i:] for c in _CONS_LIST]
        if not nxt or re.match(rf'[{MATRA}{SIGNS}]', nxt):
            out += [word[:i + 1] + c + word[i + 1:] for c in _CONS_LIST]
    return out


def _shift_candidates(word):
    """त्रिभजु -> त्रिभुज, गणुा -> गुणा: move one vowel sign / anusvara elsewhere."""
    chars, out = list(word), []
    for j, ch in enumerate(chars):
        if not re.match(rf'[{MATRA}{SIGNS}]', ch):
            continue
        rest = chars[:j] + chars[j + 1:]
        out += [''.join(rest[:k] + [ch] + rest[k:])
                for k in range(1, len(rest) + 1) if k != j]
    return out


def _mark_delete_candidates(word):
    """Delete one stray sign: ऊंपर -> ऊपर.  Used for one edit only, never chained, so a
    correct unknown word is not stripped into another word (खूंटियों -> खटियों)."""
    return [word[:j] + word[j + 1:] for j, ch in enumerate(word)
            if re.match(rf'[{MATRA}{SIGNS}{NUKTA}]', ch)]


def _mark_edit_candidates(word):
    """Delete one stray sign (ऊंपर -> ऊपर, सुंख्या -> संख्या) or add a missing
    anusvara/halant (संख्याओ -> संख्याओं, इनहें -> इन्हें)."""
    out = []
    if re.search(rf'[{MATRA}ओए]$', word):          # …ो / …ओ / …ए + ं
        out.append(word + '\u0902')
    for j in range(1, len(word)):
        if re.match(rf'[{CONS}]', word[j - 1]) and re.match(rf'[{CONS}]', word[j]):
            out.append(word[:j] + HALANT + word[j:])              # इनहें -> इन्हें
    return out


def _cluster_candidates(word):
    """A whole half-consonant lost: सिदांत -> सिद्धांत, उललेख -> उल्लेख."""
    out = []
    for j in range(1, len(word) + 1):
        if re.match(rf'[{CONS}]', word[j - 1]) and (j == len(word) or word[j] != HALANT):
            out += [word[:j] + HALANT + c + word[j:] for c in _CONS_LIST]
    return out


def _insert_matra_candidates(word):
    out = []
    for j in range(1, len(word) + 1):
        if re.match(rf'[{CONS}]', word[j - 1]) and (j == len(word) or not re.match(
                rf'[{MATRA}{HALANT}{NUKTA}]', word[j])):
            out += [word[:j] + m + word[j:] for m in '\u0941\u0942\u093F\u0940\u093E\u0947']
    return out


_PLURALS = ('\u094B\u0902', '\u0947\u0902', 'ाएँ', 'ाएं', 'एँ', 'एं', 'ियाँ', 'ियों', 'यों', 'ाओं', 'ओं')


def _stem_in(word, domain):
    """word = a domain word + a plural ending (गुणजों).  Not -ना/-ा/-ी: those would turn
    गुणनखंडन into गुणनखंडना."""
    return any(word.endswith(suf) and word[:-len(suf)] in domain for suf in _PLURALS)


def _candidates(w):
    return (_dedupe_candidates(w) + _fill_missing_candidates(w)
            + _shift_candidates(w) + _mark_edit_candidates(w))


def _best_form(word, is_word, depth=2, beam=40, gen=None):
    """Lexicon-approved repair of `word` (or None).  At the first depth that has
    valid candidates, return the one with the highest word frequency.
    Depth 2 allows chains such as विद्ालययों -> विद्यालययों -> विद्यालयों."""
    if is_word(word):
        return word
    freq = getattr(is_word, 'freq', lambda w: 1.0 if is_word(w) else 0.0)
    frontier, seen = [word], {word}
    for level in range(depth):
        found, nxt = [], []
        for w in frontier:
            cheap = gen(w) if gen else _candidates(w)
            extra = (_cluster_candidates(w) + _mark_delete_candidates(w)) if level == 0 and not gen else []   # only one costly edit
            extra_set = set(extra)
            for cand in cheap + extra:
                if cand in seen:
                    continue
                seen.add(cand)
                if _valid(cand) and is_word(cand):
                    found.append(cand)
                if level == 0 and cand not in extra_set:
                    nxt.append(cand)
        if found:
            return max(found, key=lambda c: (freq(c), -abs(len(c) - len(word))))
        frontier = nxt[:beam]
    return None


def _repair_token(tok, is_word):
    """Repair one Devanagari token, keeping leading/trailing punctuation."""
    if re.search(r'[-/]', tok) and not _TOKEN.match(tok):   # कौन-साखिलाड़ी, चित्रों/वस्तुओं:
        return ''.join(_repair_token(part, is_word) if _is_dev(part) else part   # each part
                       for part in re.split(r'([-/])', tok))
    m = _TOKEN.match(tok)
    if not m:
        return tok
    pre, word, post = m.groups()
    if is_word(word):
        return tok
    split = getattr(is_word, 'split', None)
    compound = getattr(is_word, 'compound', None)
    if word.endswith(HALANT):                              # संख्: half a word, the join
        return tok                                         # step deals with it
    dedup = _best_form(word, is_word, gen=_dedupe_candidates)   # doubling is the main
    if dedup:                                              # corruption: कियया -> किया
        return pre + dedup + post
    if split and (s := split(word)):                       # केसाथ -> के साथ
        return f'{pre}{s[0]} {s[1]}{post}'
    is_compound = bool(compound and compound(word))
    # a word that parses as a compound (बहुभुज, वर्गाकार) only gets de-duplication
    # (संख्यायाएँ -> संख्याएँ); other edits could turn it into a different word
    fixed = _best_form(word, is_word, gen=_dedupe_candidates if is_compound else None)
    if not fixed and is_compound:            # अनक्रम (अन+क्रम) -> अनुक्रम: only towards a
        cand = _best_form(word, is_word)     # curated domain word
        if cand and cand in getattr(is_word, 'domain', ()):
            fixed = cand
    domain = getattr(is_word, 'domain', ())
    if not fixed and domain:                 # a lost vowel sign, अनक्रम -> अनुक्रम, but only
        for cand in _insert_matra_candidates(word):          # towards a domain word, so
            if cand in domain or (is_word(cand) and _stem_in(cand, domain)):  # गणन stays
                fixed = cand
                break
    if fixed:
        return pre + fixed + post
    if is_compound:
        return tok
    if split:                    # glued + broken: कोंत्रिभज -> को त्रिभुज, औरुवर्ग -> और वर्ग,
        parts = list(is_word._parts(word, min_aks=1))      # अर्थात्वर्ग -> अर्थात् वर्ग
        parts += [(word[:i + 1], word[i + 1:]) for i, ch in enumerate(word[:-2]) if ch == HALANT]
        for a, b in parts:
            a_fixed = _strip_stray(a)
            if not a_fixed:
                continue
            b = re.sub(rf'^[{MATRA}{SIGNS}]', '', b)
            if re.match(rf'^[{BASE}]', b) and len(_aksharas_of(b)) >= 2:   # not वतृ -> व त
                fb = b if is_word(b) else _best_form(b, is_word, depth=1)
                if not fb:                                   # त्रिभज -> त्रिभुज (domain)
                    fb = next((c for c in _insert_matra_candidates(b)
                               if c in getattr(is_word, 'domain', ())), None)
                if fb:
                    return f'{pre}{a_fixed} {fb}{post}'
    return tok


def _strip_stray(a):
    """`a` as a function word, allowing one stray sign at its end (कों, कीं, औरु),
    or a word ending in halant (अर्थात्)."""
    if a in SPLIT_WORDS:
        return a
    if len(a) > 1 and re.match(rf'[{MATRA}{SIGNS}]', a[-1]) and a[:-1] in SPLIT_WORDS:
        return a[:-1]
    if a.endswith(HALANT) and a in ('अर्थात्', 'पश्चात्', 'किंचित्'):
        return a
    return None


def repair_with_lexicon(text, is_word, max_back=2):
    # Pass 1: a lone mark belongs to one of the previous 1–2 words
    out = []
    for tok in text.split():
        if _IS_MARK.fullmatch(tok) and out:
            for back in range(1, min(max_back, len(out)) + 1):
                fixed = _insert_mark(out[-back], tok, is_word)
                if fixed != out[-back]:
                    out[-back] = fixed
                    break
            continue                                   # not placeable -> drop it
        out.append(tok)

    # Pass 2: a word can't start with a mark.  A leading ि is in visual order and belongs
    # after the next consonant (हैं िक -> हैं कि, िग्रड -> ग्रिड); other marks go to the word before
    toks, out = out, []
    for tok in toks:
        v = re.match(rf'^\u093F((?:[{CONS}]{NUKTA}?{HALANT})*[{CONS}]{NUKTA}?)(.*)$', tok)
        if v:
            cand = v.group(1) + '\u093F' + v.group(2)
            core = _TOKEN.match(cand)
            if core and is_word(core.group(2)):
                out.append(cand)
                continue
        m = _LEAD_MARK.match(tok)
        if m and out:
            out[-1] += m.group(1)
            tok = m.group(2)
            if not tok:
                continue
        out.append(tok)

    # Pass 3: join split pieces first (protects अध्ययन, व्यय), then repair the rest.
    # संख् + यायाएँ must be joined *before* संख् is repaired on its own.
    known = getattr(is_word, 'known', is_word)
    toks, out, i = out, [], 0
    while i < len(toks):
        tok = toks[i]
        if WORD_RE.fullmatch(tok) and i + 1 < len(toks):
            m = _TOKEN.match(toks[i + 1])
            if m and not m.group(1) and not (known(tok) and known(m.group(2))):
                joined = _best_form(tok + m.group(2), is_word, depth=1)  # अध् + ययन
                if joined:
                    toks[i + 1] = joined + m.group(3)
                    i += 1
                    continue
        if _is_dev(tok):
            tok = _repair_token(tok, is_word)
        out.append(tok)
        i += 1
    return ' '.join(out)


# =====================================================================
# Quality score
# =====================================================================
_BAD = re.compile(
    rf'(?:^|\s)[{MATRA}{SIGNS}{NUKTA}{HALANT}]|[{MATRA}]{{2}}'
    rf'|{HALANT}[{MATRA}{SIGNS}]|{HALANT}{{2}}|[{SIGNS}][{MATRA}]|�'
)


def quality(text, is_word=None):
    """invalid_per_100: broken structures per 100 words. oov_rate: share of unknown
    words (catches doubled syllables like ययह, which are structurally 'valid')."""
    words = WORD_RE.findall(text)
    n = max(len(words), 1)
    score = {'words': len(words), 'invalid_per_100': 100 * len(_BAD.findall(text)) / n}
    if is_word:
        known = getattr(is_word, 'known', is_word)
        score['oov_rate'] = sum(not known(w) for w in words) / n
    return score


def _badness(text, is_word):
    q = quality(text, is_word)
    return q.get('oov_rate', 0) + q['invalid_per_100'] / 100


# =====================================================================
# Word-level merge of the two engines
# =====================================================================
# pdfium is right about letters and spaces but sometimes moves ं / ु to the wrong
# syllable (संबधित, शरू, ग्रिड बंद); PyMuPDF is right about mark placement but glues
# words (स्पष्टकर, जानेवाले).  Align both texts and, where they differ, keep the
# version made of better words.
def _tok_score(tok, lex):
    if not _is_dev(tok):
        return 5.0                                   # numbers, Latin, punctuation: neutral
    m = _TOKEN.match(tok)
    if not m:
        parts = re.split(r'[-–—/]', tok)             # एक-दूसरे: score each part
        if len(parts) > 1 and all(_TOKEN.match(x) or not _is_dev(x) for x in parts if x):
            return sum(_tok_score(x, lex) for x in parts if x) / len([x for x in parts if x])
        return 0.0                                   # Devanagari mixed with garbage (पैटना«े)
    w = m.group(2)
    if _INVALID.search(w):
        return -1.0
    if len(w) == 1 and w not in FUNCTION_WORDS:      # ग, र: fragments, not words
        return 0.0
    if w in getattr(lex, 'domain', ()):
        return 8.0
    f = lex.freq(w) if hasattr(lex, 'freq') else (5.0 if lex(w) else 0.0)
    if f:
        return f
    comp = getattr(lex, 'compound', None)
    return 3.0 if comp and comp(w) else 0.0


def _has_half_word(toks):
    return any((m := _TOKEN.match(t)) and m.group(2).endswith(HALANT) for t in toks if _is_dev(t))


def _word_share(toks, lex):
    dev = [t for t in toks if _is_dev(t)]
    if not dev:
        return 1.0
    def real(t):                             # a lone letter (the र of ऊर्ध्वाध र) is not a word
        m = _TOKEN.match(t)
        if not m:
            return False
        w = m.group(2)
        if len(w) == 1 and w not in FUNCTION_WORDS:
            return False
        return bool(getattr(lex, 'known', lex)(w))
    return sum(real(t) for t in dev) / len(dev)


def _all_words(toks, lex):
    """Every Devanagari token is a word, and none is half a word (क् + या)."""
    def ok(t):
        m = _TOKEN.match(t)
        return bool(m) and not m.group(2).endswith(HALANT) and lex(m.group(2))
    return all(not _is_dev(t) or ok(t) for t in toks)


def _resplit(B, A, lex=None):
    """Split glued tokens of B along A's word boundaries: होनेवाली -> होने वाली.
    Only where every piece is a real word (not ऊर्ध्वाधर -> ऊर्ध्वाध र)."""
    out = []
    for t in B:
        done = False
        for i in range(len(A)):
            for j in range(i + 2, min(i + 4, len(A)) + 1):
                if ''.join(A[i:j]) == t and (lex is None or (
                        not _has_half_word(A[i:j]) and _word_share(A[i:j], lex) == 1.0)):
                    out += A[i:j]
                    done = True
                    break
            if done:
                break
        if not done:
            out.append(t)
    return out


def merge_candidates(primary, secondary, lex, margin=1.0, _depth=0):
    """Merge two cleaned texts of the same block.  `primary` (pdfium) wins unless the
    `secondary` (PyMuPDF) words are clearly better.  Returns (text, n_swaps)."""
    a, b = primary.split(), secondary.split()
    out, swaps = [], 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        A, B = a[i1:i2], b[j1:j2]
        if op in ('equal', 'delete') or not A:       # pdfium-only text is kept; PyMuPDF-only
            out += A                                 # text is dropped (it is usually a repeat)
            continue
        if _depth == 0 and len(A) != len(B):         # शरू होने वाली / शुरू होनेवाली:
            B2 = _resplit(B, A, lex)                      # compare word by word after re-spacing
            if B2 != B:
                sub, n = merge_candidates(' '.join(A), ' '.join(B2), lex, margin, _depth=1)
                out += sub.split()
                swaps += n
                continue
        if ''.join(A) == ''.join(B):                 # only the spacing differs:
            longer, shorter = (A, B) if len(A) >= len(B) else (B, A)
            # the split side wins if it has no half-word (क् + या) and at least as large a
            # share of real words: स्पष्टकर -> स्पष्ट कर, औरएकऊर्ध्वाधर -> और एक ऊर्ध्वाधर
            sl, ss = _word_share(longer, lex), _word_share(shorter, lex)
            lone = any(_is_dev(t) and len(t) == 1 and t not in FUNCTION_WORDS for t in longer)
            pick = (longer if not _has_half_word(longer) and (sl > ss or (sl == ss and not lone))
                    else shorter)
        else:
            sa = sum(_tok_score(t, lex) for t in A) / len(A)
            sb = sum(_tok_score(t, lex) for t in B) / len(B)
            pick = B if sb > sa + margin else A      # संबधित -> संबंधित, बंद -> बिंदु
            if (pick is A and sa <= 0 and sb <= 0 and len(A) == len(B)
                    and sorted(''.join(A)) == sorted(''.join(B))):
                pick = B          # both unknown, same letters, a sign moved: PyMuPDF places
                                  # signs correctly (घमुाव -> घुमाव, मधुोल -> मुधोल)
        swaps += pick is B
        out += pick
    return ' '.join(out), swaps


# =====================================================================
# Page / document extraction (use these in the real pipeline)
# =====================================================================
def clean_block(block_text, is_word=None, corrections=None):
    text = apply_corrections(repair_unicode(join_block_lines(block_text)), corrections)
    if is_word:
        text = repair_with_lexicon(text, is_word)
    return apply_corrections(text, corrections)


def extract_hindi_page(page, is_word=None, threshold=2.0, oov_threshold=0.15, ocr=True,
                       engine='auto', corrections=None, return_blocks=False, margin=0.03):
    """Returns (clean_text, method, score)  [+ block records if return_blocks].

    engine: 'auto'    - merge pdfium and pymupdf word by word (default)
            'pdfium'  - pdfium text wherever it produced something
            'pymupdf' - v3 behaviour (no pdfium)
    method: 'pdfium', 'pymupdf', 'merged', 'mixed' or 'ocr'.
    score:  quality() of the chosen text-layer output (before any OCR).
    block records: {'block', 'bbox', 'chosen', 'text', 'candidates': {engine: (text, badness)}}
    """
    if corrections is None:
        corrections = load_corrections()
    page_h = page.rect.height
    blocks = [b for b in page.get_text("blocks", sort=True)
              if b[6] == 0 and not _is_boilerplate(b, page_h)]
    pdfium_texts = _pdfium_block_texts(page, blocks) if engine != 'pymupdf' else None

    records = []
    for k, b in enumerate(blocks):
        cands = {}
        if pdfium_texts and pdfium_texts[k].strip():
            cands['pdfium'] = clean_block(pdfium_texts[k], is_word, corrections)
        if engine != 'pdfium' or not cands:
            cands['pymupdf'] = clean_block(b[4], is_word, corrections)
        scored = {n: (t, _badness(t, is_word) if is_word else 0.0) for n, t in cands.items()}
        swaps = 0
        if len(cands) == 1:
            name, text = next(iter(cands.items()))
        elif is_word and scored['pymupdf'][1] + margin < scored['pdfium'][1] - 0.2:
            name, text = 'pymupdf', cands['pymupdf']          # pdfium block is a mess
        elif is_word:
            text, swaps = merge_candidates(cands['pdfium'], cands['pymupdf'], is_word)
            name = 'merged' if swaps else 'pdfium'
        else:
            name, text = 'pdfium', cands['pdfium']
        if text:
            records.append({'block': b[5], 'bbox': tuple(round(v, 1) for v in b[:4]),
                            'chosen': name, 'swaps': swaps, 'text': text, 'candidates': scored})

    text = "\n\n".join(r['text'] for r in records)
    used = {r['chosen'] for r in records}
    method = used.pop() if len(used) == 1 else ('mixed' if used else 'pymupdf')
    score = quality(text, is_word)
    bad = (score['invalid_per_100'] > threshold
           or score.get('oov_rate', 0) > oov_threshold)
    if ocr and bad:
        try:  # needs Tesseract installed with the Hindi ('hin') language pack
            tp = page.get_textpage_ocr(language="hin", dpi=300, full=True)
            ocr_text = "\n\n".join(
                clean_block(b[4], is_word, corrections)
                for b in page.get_text("blocks", sort=True, textpage=tp)
                if b[6] == 0 and not _is_boilerplate(b, page_h))
            if quality(ocr_text, is_word).get('oov_rate', 1) < score.get('oov_rate', 1):
                text, method = ocr_text, 'ocr'
        except Exception as ex:
            print(f'[hindi_text] OCR failed on page {page.number + 1}: {ex}')
    if return_blocks:
        return text, method, score, records
    return text, method, score


def extract_hindi_pdf(path, is_word=None, ocr=True, engine='auto'):
    """Convenience: list of {'page', 'text', 'method', 'score'} for a whole PDF."""
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    corrections = load_corrections()
    pages = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, 1):
            text, method, score = extract_hindi_page(page, is_word, ocr=ocr, engine=engine,
                                                     corrections=corrections)
            pages.append({'page': i, 'text': text, 'method': method, 'score': score})
    return pages


def normalize_query(text):
    """Apply to Hindi user queries before embedding/retrieval."""
    return repair_unicode(text)


# =====================================================================
# Evaluation helpers (CER / WER against hand-typed gold pages)
# =====================================================================
def _edit_distance(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _norm_eval(text):
    text = unicodedata.normalize('NFC', text)
    text = _ZW.sub('', text)
    return ' '.join(text.split())


def cer(hyp, ref):
    """Character error rate on NFC text with whitespace collapsed."""
    hyp, ref = _norm_eval(hyp), _norm_eval(ref)
    return _edit_distance(hyp, ref) / max(len(ref), 1)


def wer(hyp, ref):
    hyp, ref = _norm_eval(hyp).split(), _norm_eval(ref).split()
    return _edit_distance(hyp, ref) / max(len(ref), 1)