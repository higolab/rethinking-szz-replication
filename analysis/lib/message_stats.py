"""Paired message-ablation tests; no model calls."""
from fractions import Fraction
from collections import Counter,defaultdict
from statistics import mean,median
from scipy.stats import rankdata,wilcoxon
import accuracy
METRICS=("f1","bash_calls","total_seconds","common_cost_usd")
RESOURCES=(*METRICS[1:], 'process_seconds', 'cli_seconds', 'reported_cost_usd')

def require(ok, message):
    if not ok:
        raise ValueError(message)

def f1_fraction(row):
    denom = 2 * row['tp'] + row['fp'] + row['fn']
    return Fraction(2 * row['tp'], denom) if denom else Fraction(0)

def holm(pvalues):
    require(all(0 <= p <= 1 for p in pvalues), 'invalid p value')
    result, running = [0.] * len(pvalues), 0.
    for order, idx in enumerate(sorted(range(len(pvalues)), key=lambda i: pvalues[i])):
        running = max(running, min(1., (len(pvalues) - order) * pvalues[idx]))
        result[idx] = running
    return result

def signed_rank(diffs):
    """RQ1-compatible approximation plus exact conditional sign distribution."""
    d = [float(x) for x in diffs]
    nz = [x for x in d if x != 0]
    positive, negative = sum(x > 0 for x in d), sum(x < 0 for x in d)
    if not nz:
        return dict(n=len(d), positive=0, negative=0, zero=len(d), statistic=0.,
                    p_raw=1., p_exact=1., rank_biserial=0., w_plus=0., w_minus=0.,
                    tied_absolute_groups=0)
    ranks = rankdata([abs(x) for x in nz], method='average')
    doubled = [int(round(2 * x)) for x in ranks]
    observed = sum(r for r, x in zip(doubled, nz) if x > 0)
    total = sum(doubled)
    # Counts of subset rank sums across all 2**n equally likely sign assignments.
    ways = [0] * (total + 1)
    ways[0] = 1
    reachable = 0
    for r in doubled:
        for s in range(reachable, -1, -1):
            ways[s + r] += ways[s]
        reachable += r
    tail = sum(ways[:min(observed, total-observed) + 1])
    p_exact = min(1., float(Fraction(2 * tail, 2 ** len(nz))))
    approx = wilcoxon(d, alternative='two-sided', zero_method='wilcox',
                      correction=False, method='approx')
    return dict(n=len(d), positive=positive, negative=negative, zero=len(d)-len(nz),
                statistic=float(approx.statistic), p_raw=float(approx.pvalue),
                p_exact=p_exact, w_plus=observed/2, w_minus=(total-observed)/2,
                rank_biserial=(2*observed-total)/total,
                tied_absolute_groups=sum(n > 1 for n in Counter(abs(x) for x in nz).values()))

def case_means(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r['condition'], r['sample_id'])].append(r)
    ids = sorted({r['sample_id'] for r in rows}, key=int)
    require(len(ids) == 79 and len(rows) == 474, 'Incomplete ablation grid')
    require({r['condition'] for r in rows} == {'present', 'free'}, 'Unknown condition')
    result = []
    for sid in ids:
        record = {'sample_id': sid}
        require(len({r['repository'] for cond in ('present', 'free') for r in groups[(cond, sid)]}) == 1,
                f'cross-condition repository mismatch: {sid}')
        for cond in ('present', 'free'):
            group = groups[(cond, sid)]
            require(len(group) == 3 and {r['repeat'] for r in group} == {1, 2, 3}, f'coverage: {sid}/{cond}')
            require(len({r['repository'] for r in group}) == 1, 'repository mismatch')
            record['repository'] = group[0]['repository']
            record[cond] = {k: sum((f1_fraction(r) if k == 'f1' else Fraction(str(r[k]))
                                    for r in group), Fraction(0)) / 3
                            for k in ('f1', *RESOURCES)}
        result.append(record)
    return result

def test_family(cases, time_key='total_seconds'):
    tests = {}
    for metric in METRICS:
        key = time_key if metric == 'total_seconds' else metric
        diffs = [r['free'][key]-r['present'][key] for r in cases]
        tests[key] = dict(signed_rank(diffs),
                            mean_present=float(mean(r['present'][key] for r in cases)),
                            mean_free=float(mean(r['free'][key] for r in cases)),
                            mean_difference=float(mean(diffs)), median_difference=float(median(diffs)))
    for metric, padj, pexact in zip(tests, holm([v['p_raw'] for v in tests.values()]),
                                  holm([v['p_exact'] for v in tests.values()])):
        tests[metric].update(p_holm=padj, p_exact_holm=pexact,
                             significant_005=padj < .05)
    return tests

def descriptive(rows):
    ids = {r['sample_id'] for r in rows}
    return dict(accuracy=accuracy.summarize([dict(r, replicate=r['repeat']) for r in rows], ids, (1,2,3)),
                case_mean_f1=float(mean(f1_fraction(r) for r in rows)),
                resources={k: dict(mean=mean(r[k] for r in rows), median=median(r[k] for r in rows),
                                   total=sum(r[k] for r in rows))
                           for k in RESOURCES})


def analyze(source):
    """Recompute the primary, supplementary, and sensitivity results."""
    cases = case_means(source['rows'])
    repositories = defaultdict(list)
    for case in cases:
        repositories[case['repository']].append(case)
    repo_cases = [dict(repository=repo, **{cond: {k: mean(r[cond][k] for r in group)
                  for k in ('f1', *RESOURCES)} for cond in ('present', 'free')})
                  for repo, group in sorted(repositories.items())]
    excluded = source['sensitivity']['excluded_identity_header_ids']
    require(set(excluded).issubset({r['sample_id'] for r in cases}), 'Unknown sensitivity case')
    return dict(primary=test_family(cases),
                descriptive={c: descriptive([r for r in source['rows'] if r['condition']==c])
                             for c in ('present', 'free')},
                sensitivity=dict(process_time_family=test_family(cases, 'process_seconds'),
                                 repository_equal_weight=test_family(repo_cases),
                                 exclude_identity_header_cases=test_family([r for r in cases if r['sample_id'] not in excluded]),
                                 excluded_identity_header_ids=excluded))
