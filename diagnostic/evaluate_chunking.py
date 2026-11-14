"""Compare the four chunking methods with the existing retrieval relevance rule.

    python -m diagnostic.evaluate_chunking --tune     # pick semantic_tuned settings on DEV only
    python -m diagnostic.evaluate_chunking            # evaluate all four methods

Case sets
  test : reports/rag_eval_cases_v1.json (the 12 existing cases, chapters 2-3). Never used for tuning.
  dev  : reports/chunking_dev_cases_v1.json (20 cases, chapters 1, 4, 5). Used for tuning only.

Protocols (retrieval scoring is identical for every method: cosine similarity between the
query and chunk embeddings from the same local model, query = question + concept EN + HI name,
exactly as book_chat.retrieve_sources builds it)
  scoped  : only chunks from the 1-2 catalogued concept pages the chatbot searches today.
            Comparable with reports/rag_k_comparison.md (semantic must reproduce it).
  chapter : every chunk of the whole chapter (body pages, solutions excluded), same language.

Relevance is the existing proxy (evaluate_rag.relevant): chunk on a gold page AND containing
every evidence term.
"""
import argparse
import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone
from statistics import mean
from diagnostic import engine as e, kg_v2, textbooks
from diagnostic import chunking
from diagnostic import semantic_mapper as sm
from diagnostic.evaluate_rag import OUT, relevant, write_csv
from diagnostic.evaluate_retrieval_k import scores
from diagnostic.extraction import normalize_query

KS = (1, 2, 3, 5, 10)
TEST = OUT / 'rag_eval_cases_v1.json'
DEV = OUT / 'chunking_dev_cases_v1.json'
TUNED = OUT / 'chunking_tuned_config.json'
_CACHE = {}


def embed(texts):
    missing = [t for t in dict.fromkeys(texts) if t not in _CACHE]
    if missing:
        for t, v in zip(missing, sm.embed(missing)):
            _CACHE[t] = v
    import numpy as np
    return np.stack([_CACHE[t] for t in texts])


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def case_chapter(case):
    if 'chapter' in case:
        return case['chapter']
    version = textbooks.catalog()['concepts'][case['concept_id']]['versions'][case['language']]
    return int(version['chapter'])


def scoped_pages(case):
    """Exactly the pages book_chat.retrieve_sources searches for this concept."""
    version = textbooks.catalog()['concepts'][case['concept_id']]['versions'][case['language']]
    pages = [version['read_pdf_page']]
    if case['concept_id'] == 'MATH6_C0025' and 38 not in pages:
        pages.append(38)
    return set(pages[:2])


def query_for(case):
    nodes, _ = e.load_graph()
    if case['concept_id'] in nodes:                       # v1 concept: identical to the app
        en, hi = nodes[case['concept_id']]['en'], nodes[case['concept_id']]['hi']
    else:                                                 # v2-only concept (dev cases)
        c = next(c for c in kg_v2.CONCEPTS if c[0] == case['concept_id'])
        en, hi = c[4], c[5]
    return normalize_query(case['question'], case['language']) + ' ' + en + ' ' + hi


def build_index(method, params, chapters_langs):
    index = {}
    for chapter, language in sorted(chapters_langs):
        pages = kg_v2.body_pages(chapter, language)
        chunks = chunking.chunk_chapter(pages, language, method, chapter=chapter, encode=embed, **params)
        vectors = embed([c['text'] for c in chunks]) if chunks else None
        index[(chapter, language)] = (chunks, vectors)
    return index


def rank(case, index, protocol):
    chunks, vectors = index[(case_chapter(case), case['language'])]
    q = embed([query_for(case)])[0]
    allowed = scoped_pages(case) if protocol == 'scoped' else None
    ranked = []
    for c, s in zip(chunks, vectors @ q):
        if allowed is None or c['pdf_page'] in allowed:
            ranked.append({'pdf_page': c['pdf_page'], 'excerpt': c['text'], 'similarity': round(float(s), 4),
                           'concepts': c.get('concepts')})
    ranked.sort(key=lambda r: (-r['similarity'], r['pdf_page'], r['excerpt']))
    return ranked


def evaluate(method, params, cases, protocols, index=None):
    index = index or build_index(method, params, {(case_chapter(c), c['language']) for c in cases})
    rows, rankings = [], []
    for protocol in protocols:
        for case in cases:
            ranked = rank(case, index, protocol)
            flags = [relevant(r, case) for r in ranked]
            rankings.append({'case_id': case['id'], 'protocol': protocol, 'flags': flags[:10], 'top': ranked[:3]})
            for k in KS:
                rows.append({'method': method, 'protocol': protocol, 'case_id': case['id'],
                             'language': case['language'], 'k': k, **scores(flags, k)})
    return rows, rankings, index


def summarise(rows):
    out = []
    keys = sorted({(r['method'], r['protocol'], r['k']) for r in rows})
    for method, protocol, k in keys:
        for language in ('all', 'en', 'hi'):
            sel = [r for r in rows if (r['method'], r['protocol'], r['k']) == (method, protocol, k)
                   and language in ('all', r['language'])]
            rec = [r['recall'] for r in sel if r['recall'] is not None]
            out.append({'method': method, 'protocol': protocol, 'language': language, 'k': k, 'cases': len(sel),
                        'precision': mean(r['precision'] for r in sel), 'recall': mean(rec) if rec else None,
                        'mrr': mean(r['mrr'] for r in sel), 'hit_rate': mean(r['hit_rate'] for r in sel)})
    return out


def pick(summary, method, protocol, k, language='all'):
    return next(s for s in summary if (s['method'], s['protocol'], s['k'], s['language']) == (method, protocol, k, language))


# ------------------------------------------------------------------------------ tune
def tune():
    dev = load(DEV)['cases']
    grid = [dict(mode='absolute', threshold=t, max_chars=m, min_chars=n)
            for t, m, n in itertools.product((.3, .4, .48, .55, .6, .65, .7), (300, 450, 650, 900), (0, 150))]
    grid += [dict(mode='relative', threshold=z, max_chars=m, min_chars=n)
             for z, m, n in itertools.product((0., .5, 1., 1.5), (300, 450, 650, 900), (0, 150))]
    results = []
    for i, params in enumerate(grid):
        rows, _, _ = evaluate('semantic_tuned', params, dev, ['chapter'])
        s = summarise(rows)
        results.append({**params, 'dev_mrr@10': pick(s, 'semantic_tuned', 'chapter', 10)['mrr'],
                        'dev_hit@2': pick(s, 'semantic_tuned', 'chapter', 2)['hit_rate'],
                        'dev_hit@1': pick(s, 'semantic_tuned', 'chapter', 1)['hit_rate']})
        print(i + 1, len(grid), results[-1], flush=True)
    # Primary: MRR@10 on dev; ties -> Hit@2, then the setting closest to the current one.
    best = max(results, key=lambda r: (round(r['dev_mrr@10'], 6), round(r['dev_hit@2'], 6),
                                       -abs(r['max_chars'] - 650), r['mode'] == 'absolute'))
    config = {k: best[k] for k in ('mode', 'threshold', 'max_chars', 'min_chars')}
    TUNED.write_text(json.dumps({'selected': config, 'selection_rule': 'max dev MRR@10, then dev Hit@2 (chapter protocol)',
                                 'dev_cases_sha256': hashlib.sha256(DEV.read_bytes()).hexdigest(),
                                 'created_utc': datetime.now(timezone.utc).isoformat(), 'grid': results},
                                indent=2), encoding='utf-8')
    write_csv(OUT / 'chunking_tuning_grid.csv', results)
    print('selected', config)
    return config


# ------------------------------------------------------------------------------- run
def run():
    test, dev = load(TEST)['cases'], load(DEV)['cases']
    tuned = load(TUNED)['selected'] if TUNED.exists() else chunking.DEFAULTS['semantic_tuned']
    configs = {'fixed': chunking.DEFAULTS['fixed'], 'semantic': {}, 'semantic_tuned': tuned,
               'graph': chunking.DEFAULTS['graph']}
    all_rows, dev_rows, stats, examples = [], [], {}, {}
    for method, params in configs.items():
        print('method', method, params, flush=True)
        rows, rankings, index = evaluate(method, params, test, ['scoped', 'chapter'])
        all_rows += rows
        examples[method] = rankings
        drows, _, dindex = evaluate(method, params, dev, ['chapter'])
        dev_rows += drows
        chunks = [c for key in sorted({**index, **dindex}) for c in {**index, **dindex}[key][0]]
        stats[method] = chunking.chunk_stats(chunks)
    summary, dev_summary = summarise(all_rows), summarise(dev_rows)
    # Baseline check 1: semantic/scoped must give the live chatbot's ranking for every case.
    from diagnostic import book_chat as chat
    mine = {r['case_id']: r['flags'] for r in examples['semantic'] if r['protocol'] == 'scoped'}
    live = {}
    for case in test:
        sources, _ = chat.retrieve_sources(case['concept_id'], case['language'], case['question'], limit=None)
        live[case['id']] = [relevant(x, case) for x in sources][:10]
    reproduced = all(mine[k] == live[k] for k in live)
    # Baseline check 2: the stored report (rag_k_comparison.json, made 2026-11-02 on the older
    # Hindi extraction). English should match exactly; Hindi is expected to differ.
    reference = load(OUT / 'rag_k_comparison.json')
    stored = {lang: all(abs(pick(summary, 'semantic', 'scoped', r['k'], lang)['hit_rate'] - r['hit_rate']) < 1e-9
                        and abs(pick(summary, 'semantic', 'scoped', r['k'], lang)['mrr'] - r['mrr']) < 1e-9
                        for r in reference['summary'] if r['language'] == lang) for lang in ('en', 'hi')}
    stored_rows = [r for r in reference['summary'] if r['language'] in ('all', 'en', 'hi')]
    meta = {'created_utc': datetime.now(timezone.utc).isoformat(), 'configs': configs, 'chunk_stats': stats,
            'baseline_reproduced': reproduced, 'stored_report_matches': stored,
            'stored_report_created_utc': reference['created_utc'], 'stored_report_summary': stored_rows,
            'test_cases_sha256': hashlib.sha256(TEST.read_bytes()).hexdigest(),
            'dev_cases_sha256': hashlib.sha256(DEV.read_bytes()).hexdigest(),
            'kg_version': kg_v2.VERSION, 'test_summary': summary, 'dev_summary': dev_summary, 'test_rankings': examples}
    (OUT / 'chunking_comparison.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    write_csv(OUT / 'chunking_comparison.csv', summary + dev_summary)
    write_csv(OUT / 'chunking_case_results.csv', all_rows + dev_rows)
    write_report(meta)
    return meta


def write_report(meta):
    s, d = meta['test_summary'], meta['dev_summary']
    methods = list(meta['configs'])
    L = ['# Chunking method comparison', '',
         f"Baseline check: `semantic` + scoped protocol {'reproduces' if meta['baseline_reproduced'] else 'DOES NOT reproduce'} "
         'the live chatbot ranking (`book_chat.retrieve_sources`) for every test case.', '',
         f"Stored report `rag_k_comparison.md` ({meta['stored_report_created_utc'][:10]}): English "
         f"{'matches' if meta['stored_report_matches']['en'] else 'differs'}, Hindi "
         f"{'matches' if meta['stored_report_matches']['hi'] else 'differs'}. The stored Hindi run used the earlier, "
         'corrupted Hindi extraction (e.g. "न्ून कोण", "लिखाा जााए"); the app now reads the repaired v4.5 text. '
         'All comparisons below re-run the current method on the current text, so they are like-for-like.', '',
         '| Stored report (old Hindi text), semantic, scoped | Hit@1 | Hit@2 | MRR@2 |', '| --- | ---: | ---: | ---: |',
         *[f"| {r['language']} | {r['hit_rate']:.3f} | {next(x for x in meta['stored_report_summary'] if x['language'] == r['language'] and x['k'] == 2)['hit_rate']:.3f} | "
           f"{next(x for x in meta['stored_report_summary'] if x['language'] == r['language'] and x['k'] == 2)['mrr']:.3f} |"
           for r in meta['stored_report_summary'] if r['k'] == 1], '',
         '## Settings', '', '| Method | Settings | Chunks | Mean chars | Share truncated at 128 tokens |', '| --- | --- | ---: | ---: | ---: |']
    for m in methods:
        st = meta['chunk_stats'][m]
        L.append(f"| {m} | `{json.dumps(meta['configs'][m]) if meta['configs'][m] else 'current (.48, 650)'}` | {st['chunks']} | {st['mean_chars']} | {st['share_over_token_limit']:.3f} |")
    for title, summ, protocol in (('Test set (12 existing cases), scoped protocol — current app search', s, 'scoped'),
                                  ('Test set (12 existing cases), chapter-wide protocol', s, 'chapter'),
                                  ('Dev set (20 cases, ch 1/4/5), chapter-wide protocol — used to tune semantic_tuned', d, 'chapter')):
        L += ['', f'## {title}', '', '| Method | Lang | Hit@1 | Hit@2 | MRR@2 | P@2 | Hit@5 | MRR@10 | Recall@10 |',
              '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for m in methods:
            for lang in ('all', 'en', 'hi'):
                g = lambda k: pick(summ, m, protocol, k, lang)
                rec = g(10)['recall']
                L.append(f"| {m} | {lang} | {g(1)['hit_rate']:.3f} | {g(2)['hit_rate']:.3f} | {g(2)['mrr']:.3f} | {g(2)['precision']:.3f} | "
                         f"{g(5)['hit_rate']:.3f} | {g(10)['mrr']:.3f} | {rec if rec is None else f'{rec:.3f}'} |")
    L += ['', 'Hit@k = share of cases with a proxy-relevant chunk in the top k. MRR@k = mean reciprocal rank of the first relevant chunk '
          '(0 if none in top k). P@2 = relevant chunks in top 2 / 2. Recall@10 = relevant chunks in top 10 / all relevant chunks in the '
          'searched pool, averaged over cases where that pool is non-empty. Proportions 0-1.', '',
          '## Limits', '',
          '- 12 test and 20 dev cases are AI-authored development sets; differences of one case (0.083 on test) are within noise.',
          '- Relevance is the page-plus-substring proxy, which favours longer chunks (more likely to contain every term).',
          '- Only semantic_tuned was tuned (on dev). fixed and graph use fixed a-priori settings (650 chars, graph min 120).',
          '- The embedding model reads at most 128 tokens; longer chunks are embedded by their beginning only.',
          '- No generation was run; better retrieval is not shown to give better answers.']
    (OUT / 'chunking_comparison.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--tune', action='store_true', help='grid-search semantic_tuned on the dev cases')
    args = parser.parse_args()
    if args.tune:
        tune()
    run()
