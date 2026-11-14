"""Four ways to cut a textbook chapter into retrieval chunks.

    from diagnostic.chunking import chunk_chapter
    chunks = chunk_chapter(pages, 'en', 'graph', chapter=2)   # [{'text','pdf_page','concepts',...}]

Methods (all page-preserving, so every chunk keeps one citable PDF page, and all start
from the same cleaned blocks the chatbot uses: book_chat._keep_blocks):

  fixed           equal-length pieces of about `size` characters, cut at word boundaries.
  semantic        the current method, unchanged: semantic_chunks.split_semantically
                  (split where adjacent-sentence cosine < .48, max 650 chars).
  semantic_tuned  the same algorithm with tunable settings: break threshold (absolute, or
                  relative to the page's own similarity distribution), max_chars, and a
                  min_chars floor so tiny fragments are not cut off.
  graph           cut wherever a knowledge-graph (v2) concept starts: at a section heading,
                  at the first sentence of the chapter that introduces a concept, or when a
                  sentence moves to concepts the running chunk does not mention. Each chunk
                  is tagged with the KG concept IDs it mentions.

The embedding model truncates input at 128 tokens; chunks longer than that are embedded
only by their beginning. chunk_stats() reports how often that happens.
"""
import re
from statistics import mean, pstdev
from diagnostic import semantic_chunks as sc
from diagnostic import semantic_mapper as sm

METHODS = ('fixed', 'semantic', 'semantic_tuned', 'graph')
DEFAULTS = {
    'fixed': {'size': 650},
    'semantic': {},
    # Chosen on the development cases (reports/chunking_dev_cases_v1.json) by
    # python -m diagnostic.evaluate_chunking --tune ; never on the test cases.
    'semantic_tuned': {'mode': 'absolute', 'threshold': .48, 'max_chars': 650, 'min_chars': 0},
    'graph': {'max_chars': 650, 'min_chars': 120},
}
_HEADING = re.compile(r'^\s*([1-9]\d?\.\d{1,2})\s+\S')
_SENT = re.compile(r'(?<=[.!?।])\s+')


def page_blocks(text, with_headings=False):
    """(kept blocks, heading-before-block flags). Same filtering as the chatbot; headings
    are under 30 characters so the chatbot drops them, but they are kept here as cut marks.
    with_headings=True also returns the heading text that precedes each block (or None)."""
    from diagnostic.book_chat import canonical
    blocks, heading_next, flags, names = [], None, [], []
    for raw in text.split('\n\n'):
        t = canonical(raw)
        if _HEADING.match(t) and len(t) < 90:
            heading_next = t
        if len(t) < 30 or 'Reprint 2026' in t:
            continue
        blocks.append(t)
        flags.append(heading_next is not None)
        names.append(heading_next)
        heading_next = None
    return (blocks, flags, names) if with_headings else (blocks, flags)


def sentences(blocks, max_chars=650, flags=None):
    """Sentence units bounded at max_chars (same rule as semantic_chunks.units).
    Returns [(sentence, starts_after_heading)]."""
    out = []
    flags = flags or [False] * len(blocks)
    for block, flag in zip(blocks, flags):
        first = True
        for sentence in _SENT.split(block):
            words, current, size = sentence.split(), [], 0
            for word in words:
                if current and size + len(word) + 1 > max_chars:
                    out.append((' '.join(current), flag and first)); first = False
                    current, size = [], 0
                current.append(word); size += len(word) + 1
            if current:
                out.append((' '.join(current), flag and first)); first = False
    return out


# ---------------------------------------------------------------------------- methods
def fixed(blocks, size=650):
    words = ' '.join(blocks).split()
    chunks, current, length = [], [], 0
    for w in words:
        if current and length + len(w) + 1 > size:
            chunks.append(' '.join(current)); current, length = [], 0
        current.append(w); length += len(w) + 1
    if current:
        chunks.append(' '.join(current))
    return chunks


def semantic(blocks, encode=sm.embed):
    return sc.split_semantically(blocks, encode=encode)


def semantic_tuned(blocks, mode='absolute', threshold=.48, max_chars=650, min_chars=0, encode=sm.embed):
    units = [s for s, _ in sentences(blocks, max_chars)]
    if not units:
        return []
    vectors = encode(units)
    sims = [float(vectors[i - 1] @ vectors[i]) for i in range(1, len(units))]
    if mode == 'relative' and len(sims) >= 2:
        cut = mean(sims) - threshold * pstdev(sims)   # threshold = number of std devs below mean
    else:
        cut = threshold
    chunks, current = [], units[0]
    for i, unit in enumerate(units[1:]):
        too_long = len(current) + len(unit) + 1 > max_chars
        if too_long or (sims[i] < cut and len(current) >= min_chars):
            chunks.append(current); current = unit
        else:
            current += ' ' + unit
    chunks.append(current)
    return chunks


class GraphState:
    """Per-chapter state for graph chunking: which concepts were already introduced."""
    def __init__(self, language, chapter):
        from diagnostic import kg_v2
        own = [c for c in kg_v2.CONCEPTS if c[1] == chapter and c[3] == 'taught']
        self.compiled = kg_v2.compile_anchors(own, language)
        self.find = kg_v2.find_concepts
        self.introduced = set()


def graph(blocks, flags, state, max_chars=650, min_chars=120):
    units = sentences(blocks, max_chars, flags)
    chunks, current, focus = [], '', set()
    for text, after_heading in units:
        mentioned = set(state.find(text, state.compiled))
        new = mentioned - state.introduced
        state.introduced |= mentioned
        shift = bool(mentioned) and bool(focus) and not (mentioned & focus)
        starts = after_heading or bool(new) or shift
        if current and (len(current) + len(text) + 1 > max_chars or (starts and (after_heading or len(current) >= min_chars))):
            chunks.append((current, sorted(focus))); current, focus = '', set()
        current = (current + ' ' + text).strip()
        focus |= mentioned
    if current:
        chunks.append((current, sorted(focus)))
    return chunks


# ------------------------------------------------------------------------------ API
def chunk_chapter(pages, language, method, chapter=None, encode=sm.embed, annotate_chunks=True, **params):
    """pages: [{'page': n, 'text': raw page text}] in reading order (one chapter)."""
    if method not in METHODS:
        raise ValueError(f'unknown method {method!r}; choose from {METHODS}')
    params = {**DEFAULTS[method], **params}
    state = GraphState(language, chapter) if method == 'graph' else None
    out = []
    for p in pages:
        blocks, flags = page_blocks(p['text'])
        if not blocks:
            continue
        if method == 'fixed':
            pieces = [(t, None) for t in fixed(blocks, **params)]
        elif method == 'semantic':
            pieces = [(t, None) for t in semantic(blocks, encode=encode)]
        elif method == 'semantic_tuned':
            pieces = [(t, None) for t in semantic_tuned(blocks, encode=encode, **params)]
        else:
            pieces = graph(blocks, flags, state, **params)
        for i, (text, concepts) in enumerate(pieces):
            out.append({'text': text, 'pdf_page': p['page'], 'index_on_page': i, 'method': method,
                        **({'cut_concepts': concepts} if concepts is not None else {})})
    if annotate_chunks:
        annotate(out, pages, language, chapter, method, params)
    return out


# --------------------------------------------------------------------------- metadata
METADATA_VERSION = 'chunk-meta-v1'
_PAGE_NUMBER = re.compile(r'^\s*(\d{1,3})\s*$')


def printed_page_offset(chapter):
    """printed page - PDF page for a chapter, by majority vote over the standalone page
    numbers printed on the English body pages (Hindi body pages are aligned with English)."""
    from collections import Counter
    from diagnostic import kg_v2
    votes = Counter()
    for p in kg_v2.body_pages(chapter, 'en'):
        for line in p['text'].split('\n')[:6]:
            m = _PAGE_NUMBER.match(line)
            if m:
                votes[int(m[1]) - p['page']] += 1
                break
    return votes.most_common(1)[0][0] if votes else None


def _source(language, chapter):
    import hashlib
    from diagnostic import kg_v2
    stem = kg_v2.CHAPTER_FILES[chapter] if language == 'en' else kg_v2.CHAPTER_FILES[chapter].replace('fegp', 'fhgp')
    path = kg_v2.ROOT / 'assets' / 'extracted' / language / f'{language}_{stem}_clean.txt'
    return stem + '.pdf', path.relative_to(kg_v2.ROOT).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def annotate(chunks, pages, language, chapter, method, params):
    """Add the same metadata to every chunk, whatever the method:
    ids, location (chapter, section, PDF/printed page, char offsets on the page), size
    (chars, tokens, truncated by the 128-token embedder), KG v2 concept tags, provenance."""
    from diagnostic import kg_v2
    from diagnostic.semantic_mapper import runtime
    tokenizer = runtime()[2]
    pdf_name, clean_file, sha = _source(language, chapter) if chapter else (None, None, None)
    offset = printed_page_offset(chapter) if chapter else None
    title = kg_v2.CHAPTER_TITLES.get(chapter, ('', ''))[0 if language == 'en' else 1]
    tag_concepts = [c for c in kg_v2.CONCEPTS if c[1] in (chapter, 0)]
    compiled = kg_v2.compile_anchors(tag_concepts, language)
    names = {c[0]: (c[4], c[5]) for c in kg_v2.CONCEPTS}
    # Section headings and the character offset where each page's kept text continues.
    page_text, page_heads = {}, {}
    for p in pages:
        blocks, _, heads = page_blocks(p['text'], with_headings=True)
        text, starts = '', []
        for b, h in zip(blocks, heads):
            if h:
                starts.append((len(text), h))
            text += (' ' if text else '') + b
        page_text[p['page']], page_heads[p['page']] = ' '.join(text.split()), starts
    section, cursor, last_page = None, 0, None
    for n, c in enumerate(chunks):
        page = c['pdf_page']
        if page != last_page:
            cursor, last_page = 0, page
        body = page_text.get(page, '')
        start = body.find(c['text'][:60], cursor)
        start = cursor if start < 0 else start
        end = start + len(c['text'])
        cursor = end
        for pos, head in page_heads.get(page, []):
            if pos <= start + 1:
                section = head
        ids = kg_v2.find_concepts(c['text'], compiled)
        tokens = len(tokenizer.encode(c['text']).ids)
        c.update({
            'chunk_id': f"{language}-ch{chapter:02d}-{method}-p{page:03d}-{c['index_on_page']:02d}" if chapter else f'{method}-{n}',
            'language': language, 'chapter': chapter, 'chapter_title': title,
            'section': section, 'printed_page': page + offset if offset is not None else None,
            'char_start': start, 'char_end': end, 'char_count': len(c['text']), 'token_count': tokens,
            'truncated_for_embedding': tokens >= 128,
            'concepts': ids, 'concept_names': [names[i][0 if language == 'en' else 1] for i in ids],
            'primary_concept': ids[0] if ids else None,
            'source_pdf': pdf_name, 'source_clean_file': clean_file, 'source_sha256': sha,
            'citation_url': f'/api/textbooks/{language}/{pdf_name}#page={page}' if pdf_name else None,
            'method_params': params, 'kg_version': kg_v2.VERSION, 'metadata_version': METADATA_VERSION})
    return chunks


def export(out_dir=None, methods=METHODS, params=None):
    """Write every chunk with its metadata: output/chunks/<method>/<lang>_ch<NN>.jsonl + manifest.json."""
    import json
    from datetime import datetime, timezone
    from diagnostic import kg_v2
    out_dir = out_dir or kg_v2.ROOT / 'output' / 'chunks'
    params = params or {}
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'metadata_version': METADATA_VERSION,
                'kg_version': kg_v2.VERSION, 'methods': {}}
    for method in methods:
        folder = out_dir / method
        folder.mkdir(parents=True, exist_ok=True)
        files = {}
        for chapter in sorted(kg_v2.CHAPTER_FILES):
            for language in ('en', 'hi'):
                chunks = chunk_chapter(kg_v2.body_pages(chapter, language), language, method, chapter=chapter,
                                       **params.get(method, {}))
                path = folder / f'{language}_ch{chapter:02d}.jsonl'
                path.write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in chunks), encoding='utf-8')
                files[path.name] = {'chunks': len(chunks), **chunk_stats(chunks)}
        manifest['methods'][method] = {'params': {**DEFAULTS[method], **params.get(method, {})}, 'files': files}
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def chunk_stats(chunks, token_limit=128):
    from diagnostic.semantic_mapper import runtime
    _, _, tokenizer = runtime()
    if not chunks:
        return {'chunks': 0}
    lengths = [len(c['text']) for c in chunks]
    tokens = [len(tokenizer.encode(c['text']).ids) for c in chunks]
    return {'chunks': len(chunks), 'mean_chars': round(mean(lengths), 1), 'min_chars': min(lengths),
            'max_chars': max(lengths), 'share_over_token_limit': round(sum(t >= token_limit for t in tokens) / len(tokens), 3)}
