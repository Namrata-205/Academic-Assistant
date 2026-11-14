"""Is any chunking method better than the current one? Paired tests on held-out cases.

    python -m diagnostic.significance_chunking     # writes reports/chunking_significance.{md,json}

Cases: the 12 existing test cases (rag_eval_cases_v1) + 40 new held-out cases
(rag_eval_cases_v2, chapters 1-5, frozen before any method was run on them) = 52.
The 20 dev cases used to tune semantic_tuned are NOT included.

For every case and method we compute MRR@10, Hit@1, Hit@2 under two relevance rules:
  strict    : chunk on a gold page AND contains every evidence term (the existing proxy;
              favours long chunks, which are likelier to contain every term)
  page-only : chunk on a gold page (insensitive to chunk length)
Each method is compared with `semantic` (current) on the same cases: mean paired difference,
95% bootstrap CI (10,000 resamples) and a two-sided paired sign-flip permutation test
(10,000 permutations), Holm-corrected over the three challengers. Protocol: chapter-wide
search (the scoped protocol only exists for the 12 catalogued cases; it is reported separately).
"""
import json
import random
import sys
from statistics import mean
from diagnostic import evaluate_chunking as ec, chunking
from diagnostic.evaluate_rag import OUT, relevant

TEST2 = OUT / 'rag_eval_cases_v2.json'
SEED, RESAMPLES = 20261114, 10000
METRICS = ('mrr@10', 'hit@1', 'hit@2')


def per_case(flags):
    first = next((i for i, f in enumerate(flags[:10]) if f), None)
    return {'mrr@10': 0. if first is None else 1 / (first + 1), 'hit@1': float(any(flags[:1])), 'hit@2': float(any(flags[:2]))}


def page_only(source, case):
    return source['pdf_page'] in case['pdf_pages']


def bootstrap(diffs, rng):
    n = len(diffs)
    means = sorted(mean(diffs[rng.randrange(n)] for _ in range(n)) for _ in range(RESAMPLES))
    return means[int(.025 * RESAMPLES)], means[int(.975 * RESAMPLES) - 1]


def permutation_p(diffs, rng):
    observed = abs(sum(diffs))
    hits = sum(abs(sum(d if rng.random() < .5 else -d for d in diffs)) >= observed - 1e-12 for _ in range(RESAMPLES))
    return (hits + 1) / (RESAMPLES + 1)


def holm(pvalues):
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    adjusted, running = [0.] * len(pvalues), 0.
    for rank, i in enumerate(order):
        running = max(running, min(1., (len(pvalues) - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def run():
    cases = ec.load(ec.TEST)['cases'] + ec.load(TEST2)['cases']
    tuned = ec.load(ec.TUNED)['selected']
    configs = {'fixed': chunking.DEFAULTS['fixed'], 'semantic': {}, 'semantic_tuned': tuned, 'graph': chunking.DEFAULTS['graph']}
    need = {(ec.case_chapter(c), c['language']) for c in cases}
    scores = {}          # (method, rule, protocol) -> {case_id: metrics}
    for method, params in configs.items():
        print('method', method, flush=True)
        index = ec.build_index(method, params, need)
        for protocol in ('chapter', 'scoped'):
            pool = cases if protocol == 'chapter' else [c for c in cases if c['id'].startswith('R')]
            for case in pool:
                ranked = ec.rank(case, index, protocol)
                for rule, fn in (('strict', relevant), ('page-only', page_only)):
                    scores.setdefault((method, rule, protocol), {})[case['id']] = per_case([fn(r, case) for r in ranked])
    rng = random.Random(SEED)
    results = []
    for rule in ('strict', 'page-only'):
        for protocol in ('chapter', 'scoped'):
            base = scores[('semantic', rule, protocol)]
            for subset in ('all', 'en', 'hi'):
                ids = [c['id'] for c in cases if c['id'] in base and subset in ('all', c['language'])]
                for metric in METRICS:
                    block = []
                    for method in ('fixed', 'semantic_tuned', 'graph'):
                        mine = scores[(method, rule, protocol)]
                        diffs = [mine[i][metric] - base[i][metric] for i in ids]
                        lo, hi = bootstrap(diffs, rng)
                        block.append({'rule': rule, 'protocol': protocol, 'subset': subset, 'metric': metric, 'method': method,
                                      'cases': len(ids), 'semantic': mean(base[i][metric] for i in ids),
                                      'method_score': mean(mine[i][metric] for i in ids), 'diff': mean(diffs),
                                      'ci95': [lo, hi], 'wins': sum(d > 0 for d in diffs), 'losses': sum(d < 0 for d in diffs),
                                      'p': permutation_p(diffs, rng)})
                    for row, adj in zip(block, holm([r['p'] for r in block])):
                        row['p_holm'] = adj
                        row['significant'] = adj < .05
                    results += block
    out = {'cases': len(cases), 'configs': configs, 'seed': SEED, 'resamples': RESAMPLES, 'results': results,
           'per_case': {f'{m}|{r}|{p}': v for (m, r, p), v in scores.items()}}
    (OUT / 'chunking_significance.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    write_report(out)
    return out


def write_report(out):
    R = out['results']
    L = ['# Is any chunking method better than the current one?', '',
         f"{out['cases']} held-out cases (12 existing + 40 new, chapters 1-5; the 20 tuning cases are excluded). "
         'Each method vs `semantic` (current) on the same cases. diff = method − current; CI = 95% bootstrap; '
         'p = paired permutation test, Holm-corrected over the three challengers. W/L = cases where the method ranks a relevant chunk higher / lower.', '']
    for rule in ('strict', 'page-only'):
        for protocol, label in (('chapter', 'whole-chapter search, 52 cases'), ('scoped', 'current app page search, 12 cases')):
            L += [f'## {rule} relevance, {label}', '', '| Subset | Metric | Method | Current | Method | Diff | 95% CI | W/L | p (Holm) |',
                  '| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: |']
            for r in R:
                if r['rule'] == rule and r['protocol'] == protocol:
                    mark = ' **sig.**' if r['significant'] else ''
                    L.append(f"| {r['subset']} | {r['metric']} | {r['method']} | {r['semantic']:.3f} | {r['method_score']:.3f} | "
                             f"{r['diff']:+.3f} | [{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}] | {r['wins']}/{r['losses']} | {r['p_holm']:.3f}{mark} |")
            L.append('')
    L += ['## Limits', '', '- All cases are AI-authored with a page-plus-substring relevance proxy; human relevance review is pending.',
          '- Retrieval only; answer quality was not measured.', '- semantic_tuned settings came from the separate dev set; graph and fixed were not tuned.']
    (OUT / 'chunking_significance.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    run()
