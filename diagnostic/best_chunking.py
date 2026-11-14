"""Which chunking method is best? A fair contest: every method gets its own tuning.

    python -m diagnostic.best_chunking      # writes reports/best_chunking.{md,json}

1. Tune every method on the 20 dev cases (chapters 1/4/5, chapter-wide search) with the
   same rule: max strict MRR@10, ties -> strict Hit@2 -> page-only MRR@10.
     fixed           size in {200, 300, 450, 650, 900}
     semantic        current settings (no tuning; it is the baseline)
     semantic_tuned  the 88-setting grid already run (reports/chunking_tuned_config.json)
     graph           max_chars in {300, 450, 650, 900} x min_chars in {0, 60, 120, 200}
2. Metadata variant ("+meta") of every method: every chunk carries KG v2 concept tags
   (chunking.annotate); retrieval adds beta to the cosine score when the chunk is tagged
   with the question's concept. beta in {0, .02, .05, .1, .2} is tuned on dev per method.
3. Test on the 52 held-out cases (12 existing + 40 new; dev excluded), chapter-wide search,
   strict and page-only relevance. Each variant vs the current method: paired difference,
   bootstrap 95% CI, sign-flip permutation p, Holm-corrected over all challengers.
4. Best = highest mean of strict and page-only MRR@10 on test (rule fixed before running).
"""
import itertools
import json
import random
import sys
from datetime import datetime, timezone
from statistics import mean
from diagnostic import evaluate_chunking as ec, chunking
from diagnostic.evaluate_rag import OUT, relevant
from diagnostic.significance_chunking import TEST2, per_case, page_only, bootstrap, permutation_p, holm, SEED

BETAS = (0., .02, .05, .1, .2)
GRIDS = {'fixed': [{'size': s} for s in (200, 300, 450, 650, 900)],
         'semantic': [{}],
         'graph': [{'max_chars': m, 'min_chars': n} for m, n in itertools.product((300, 450, 650, 900), (0, 60, 120, 200))]}


def ranked(case, index, beta=0.):
    chunks, vectors = index[(ec.case_chapter(case), case['language'])]
    q = ec.embed([ec.query_for(case)])[0]
    rows = []
    for c, s in zip(chunks, vectors @ q):
        tagged = case['concept_id'] in c.get('concepts', [])
        rows.append({'pdf_page': c['pdf_page'], 'excerpt': c['text'], 'score': float(s) + beta * tagged,
                     'chunk_id': c['chunk_id'], 'section': c['section'], 'tagged': tagged})
    rows.sort(key=lambda r: (-r['score'], r['pdf_page'], r['excerpt']))
    return rows


def case_scores(cases, index, beta=0.):
    out = {}
    for case in cases:
        r = ranked(case, index, beta)
        out[case['id']] = {'strict': per_case([relevant(x, case) for x in r]), 'page-only': per_case([page_only(x, case) for x in r]),
                           'top': r[0]}
    return out


def summary(scores):
    return {f'{rule}_{m}': mean(v[rule][m] for v in scores.values()) for rule in ('strict', 'page-only') for m in ('mrr@10', 'hit@1', 'hit@2')}


def key(s):
    return (round(s['strict_mrr@10'], 6), round(s['strict_hit@2'], 6), round(s['page-only_mrr@10'], 6))


def run():
    dev, test = ec.load(ec.DEV)['cases'], ec.load(ec.TEST)['cases'] + ec.load(TEST2)['cases']
    grids = {**GRIDS, 'semantic_tuned': [ec.load(ec.TUNED)['selected']]}
    need_dev = {(ec.case_chapter(c), c['language']) for c in dev}
    need_test = {(ec.case_chapter(c), c['language']) for c in test}
    tuning, chosen = {}, {}
    for method in chunking.METHODS:
        trials = []
        for params in grids[method]:
            index = ec.build_index(method, params, need_dev)
            for beta in BETAS:
                s = summary(case_scores(dev, index, beta))
                trials.append({'params': params, 'beta': beta, **s})
            print(method, params, 'dev strict mrr', round(trials[-len(BETAS)]['strict_mrr@10'], 3), flush=True)
        plain = max((t for t in trials if t['beta'] == 0), key=key)
        meta = max((t for t in trials if t['params'] == plain['params']), key=key)
        tuning[method] = trials
        chosen[method] = {'params': plain['params'], 'beta': meta['beta'], 'dev_plain': plain, 'dev_meta': meta}
    # ---- test
    test_scores, stats = {}, {}
    for method in chunking.METHODS:
        index = ec.build_index(method, chosen[method]['params'], need_test)
        stats[method] = chunking.chunk_stats([c for k in index for c in index[k][0]])
        test_scores[method] = case_scores(test, index)
        test_scores[method + '+meta'] = case_scores(test, index, chosen[method]['beta'])
    base = test_scores['semantic']
    rng = random.Random(SEED)
    comparisons = []
    for rule in ('strict', 'page-only'):
        for metric in ('mrr@10', 'hit@1', 'hit@2'):
            block = []
            for variant in test_scores:
                if variant == 'semantic':
                    continue
                diffs = [test_scores[variant][i][rule][metric] - base[i][rule][metric] for i in base]
                lo, hi = bootstrap(diffs, rng)
                block.append({'rule': rule, 'metric': metric, 'variant': variant, 'current': mean(base[i][rule][metric] for i in base),
                              'score': mean(test_scores[variant][i][rule][metric] for i in base), 'diff': mean(diffs),
                              'ci95': [lo, hi], 'wins': sum(d > 0 for d in diffs), 'losses': sum(d < 0 for d in diffs),
                              'p': permutation_p(diffs, rng)})
            for row, adj in zip(block, holm([r['p'] for r in block])):
                row['p_holm'], row['significant'] = adj, adj < .05
            comparisons += block
    table = {v: summary(s) for v, s in test_scores.items()}
    for v in table:
        table[v]['combined_mrr@10'] = (table[v]['strict_mrr@10'] + table[v]['page-only_mrr@10']) / 2
    best = max(table, key=lambda v: table[v]['combined_mrr@10'])
    out = {'created_utc': datetime.now(timezone.utc).isoformat(), 'test_cases': len(test), 'dev_cases': len(dev),
           'chosen': chosen, 'chunk_stats': stats, 'test_table': table, 'comparisons': comparisons, 'best': best,
           'selection_rule': 'highest mean of strict and page-only MRR@10 on the 52 test cases',
           'tuning': tuning}
    (OUT / 'best_chunking.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    (OUT / 'best_chunking_config.json').write_text(json.dumps({'best': best, 'method': best.split('+')[0],
        'params': chosen[best.split('+')[0]]['params'], 'concept_boost_beta': chosen[best.split('+')[0]]['beta'] if '+meta' in best else 0.},
        indent=2), encoding='utf-8')
    write_report(out)
    return out


def write_report(out):
    t, cmp_ = out['test_table'], out['comparisons']
    sig = lambda v, rule: next(r for r in cmp_ if r['variant'] == v and r['rule'] == rule and r['metric'] == 'mrr@10')
    L = ['# Best chunking method', '', f"Every method tuned on {out['dev_cases']} dev cases; tested on {out['test_cases']} held-out cases "
         '(chapter-wide search). "+meta" adds a boost for chunks whose metadata tags the question\'s KG concept.', '',
         '## Tuned settings', '', '| Method | Settings | Concept boost β | Chunks | Mean chars | Truncated share |', '| --- | --- | ---: | ---: | ---: | ---: |']
    for m, c in out['chosen'].items():
        st = out['chunk_stats'][m]
        L.append(f"| {m} | `{json.dumps(c['params'])}` | {c['beta']} | {st['chunks']} | {st['mean_chars']} | {st['share_over_token_limit']:.3f} |")
    L += ['', '## Test results (52 cases)', '', '| Variant | Strict MRR@10 | Strict Hit@1 | Strict Hit@2 | Page MRR@10 | Page Hit@1 | Combined MRR | vs current (strict / page, Holm p) |',
          '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for v in sorted(t, key=lambda v: -t[v]['combined_mrr@10']):
        r = t[v]
        vs = '—' if v == 'semantic' else ' / '.join(f"{sig(v, rule)['diff']:+.3f} (p={sig(v, rule)['p_holm']:.2f}{', sig.' if sig(v, rule)['significant'] else ''})" for rule in ('strict', 'page-only'))
        L.append(f"| {'**' + v + '**' if v == out['best'] else v} | {r['strict_mrr@10']:.3f} | {r['strict_hit@1']:.3f} | {r['strict_hit@2']:.3f} | "
                 f"{r['page-only_mrr@10']:.3f} | {r['page-only_hit@1']:.3f} | {r['combined_mrr@10']:.3f} | {vs} |")
    L += ['', f"Best by the pre-set rule ({out['selection_rule']}): **{out['best']}**.", '',
          '## Limits', '', '- AI-authored cases with a page/substring relevance proxy; human review pending.',
          '- Holm correction is over all 7 challengers; with 52 cases only gains of roughly ≥0.15 MRR are detectable.',
          '- Retrieval only; answer quality not measured.']
    (OUT / 'best_chunking.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run()
