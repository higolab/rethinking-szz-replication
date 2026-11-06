#!/usr/bin/env python3
"""Regenerate reported analyses from saved runs. Never calls a model."""
import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path
import shutil
from common import ROOT, data, load, save, score, require, equivalent, english, verify
import accuracy
import stats
import message_stats
import rq2

AGENTS = ('Claude Code', *stats.AGENT_METHODS)
RULES = ('B-SZZ','AG-SZZ','MA-SZZ','R-SZZ','L-SZZ','RA-SZZ*')


def accuracy_results():
    reports = {}
    for group,name in [('rq1','rq1'),('messages','messages'),('dio_v','dio')]:
        source = data(name)
        rows = source['rows']
        ids = {r['sample_id'] for r in rows}
        require(len(ids)==(67 if group=='dio_v' else 79), 'Unexpected cohort')
        grouped = defaultdict(list)
        for r in rows:
            method = r['condition'] if group=='messages' else r['method']
            counts = r['revised'] if group=='dio_v' else r
            grouped[method].append(dict(sample_id=r['sample_id'],
                replicate=r['repeat'] if group=='messages' else r['replicate'],
                **{k:counts[k] for k in ('tp','fp','fn')}))
        expected = set(AGENTS+RULES if group=='rq1' else ('present','free') if group=='messages' else AGENTS)
        require(set(grouped)==expected, 'Missing methods')
        reports[group] = {m:accuracy.summarize(rs,ids,(1,) if m in RULES else (1,2,3)) for m,rs in sorted(grouped.items())}
    equivalent(reports,data('accuracy')['analyses'],'accuracy')
    return reports


def paired(rows, ids, baselines):
    scores = {m:stats.case_scores([r for r in rows if r['method']==m],ids) for m in ('Claude Code',*baselines)}
    tests = {m:stats.paired_test(scores['Claude Code'],scores[m]) for m in baselines}
    adjusted = stats.holm([t['p_value'] for t in tests.values()])
    return {m:{**t,'p_holm':p} for (m,t),p in zip(tests.items(),adjusted)}


def resources():
    source = data('resources')
    result = {}
    for method in AGENTS:
        rows = [r for r in source['rows'] if r['method']==method and r.get('status',r.get('source_status'))=='completed']
        require(len(rows)==len({r['slot_id'] for r in rows}), 'Duplicate resource record')
        costs = []
        for r in rows:
            cost = sum(r.get(k,0)*v for k,v in source['rates_usd_per_million'].items())/1e6
            equivalent(cost,r['usd_common'],'cost/'+method+'/'+r['slot_id'])
            costs.append(cost)
        result[method] = dict(normal_runs=len(rows),mean_seconds=sum(r['time_sec'] for r in rows)/len(rows),mean_usd=sum(costs)/len(costs))
        old = source['expected'][method]
        equivalent(result[method],dict(normal_runs=old['runs'],mean_seconds=old['time_mean_sec'],mean_usd=old['usd_mean']),method)
    return dict(methods=result, rates_usd_per_million=source['rates_usd_per_million'])


def write_table(path, groups):
    with path.open('x',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=['method','cases','runs','tp','fp','fn','precision','recall','f1'])
        writer.writeheader()
        for m,v in groups.items():
            writer.writerow(dict(method=m,cases=v['cases'],runs=v['runs'],**v['mean']))


def rq2_result():
    rebuilt = english(rq2.build())
    expected = english(data('rq2'))
    for k,v in rebuilt.items():
        equivalent(v,expected[k],'rq2/'+k)
    return rebuilt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/analysis')
    p.add_argument('--sections',nargs='+',choices=('rq1','rq2','rq3','further_analysis'),default=['rq1','rq2','rq3','further_analysis'])
    p.add_argument('--font-dir',type=Path,default=Path('/opt/replication-fonts'))
    p.add_argument('--numeric-only',action='store_true')
    args=p.parse_args()
    out=args.output.resolve()
    require(not out.exists(),'Choose a fresh output directory')
    require(out.is_relative_to(ROOT/'outputs'),'Output must be under outputs/')
    proof=verify()
    reports=accuracy_results()
    out.mkdir(parents=True)
    from audit import audit
    save(out/'validation.json',{**proof,**audit()})
    for section in dict.fromkeys(args.sections):
        dest=out/section
        dest.mkdir()
        if section=='rq1':
            write_table(dest/'accuracy.csv',reports['rq1'])
            source=data('rq1')
            tests=paired(source['rows'],source['sample_ids'],RULES+stats.AGENT_METHODS)
            for m,t in tests.items():
                equivalent({k:v for k,v in t.items() if k!='p_holm'},source['comparisons'][m],'rq1-test/'+m)
            save(dest/'tests.json',tests)
            save(dest/'resources.json',resources())
        elif section=='rq2':
            from classify import classify
            classify()
            rebuilt=rq2_result()
            save(dest/'summary.json',{k:rebuilt[k] for k in ('groups','cases','audit')})
            import figures
            figures.TABLE_DIR=dest
            figures.compact_tables(rebuilt)
            case_runs=sorted((r for r in rebuilt['runs'] if r['sample_id']=='3109'),key=lambda r:r['slot_id'])
            require([r['serial_projection'] for r in case_runs]==['ABC','ABCABC','ABCABA'],
                    'Case-3109 illustration differs from the recorded operations')
            require(all(r['prediction']==['0dd84a04f05c4a852194e92db650588d1a8166c0'] for r in case_runs),
                    'Case-3109 illustrated answer differs')
            if not args.numeric_only:
                figures.fonts(args.font_dir)
                figures.histogram(rebuilt,dest/'bash-all.pdf')
                figures.histogram(rebuilt,dest/'bash-outcomes.pdf',compare=True)
                figures.patterns(rebuilt,dest/'operation-patterns.pdf')
                shutil.copyfile(ROOT/'analysis/assets/case-3109.pdf',dest/'case-3109.pdf')
        elif section=='rq3':
            from rq3.verify import validate
            save(dest/'evidence-checks.json',validate())
            source=load(ROOT/'analysis/rq3/classification.json')
            counts=dict(Counter(r['category'] for r in source['cases']))
            require(counts==source['counts'] and len(source['cases'])==22,'Classification changed')
            save(dest/'classification.json',dict(counts=counts,cases=source['cases']))
        else:
            from dataset import validate
            save(dest/'dio-v-validation.json',validate())
            from anti_patterns import validate as validate_patterns
            save(dest/'anti-patterns.json',validate_patterns())
            write_table(dest/'message-accuracy.csv',reports['messages'])
            write_table(dest/'dio-v-accuracy.csv',reports['dio_v'])
            source=data('messages')
            message_results=message_stats.analyze(source)
            for key, value in message_results.items():
                equivalent(value,source[key],'messages/'+key)
            save(dest/'message-tests.json',message_results['primary'])
            save(dest/'message-resources.json',message_results['descriptive'])
            save(dest/'message-sensitivity.json',message_results['sensitivity'])
            revised=data('dio')
            revised_rows=[{**r,**r['revised']} for r in revised['rows']]
            tests=paired(revised_rows,revised['sample_ids'],stats.AGENT_METHODS)
            for m,t in tests.items():
                old=data('dio-tests')['comparisons'][m]
                equivalent(t,{k:old[k] for k in t if k!='multiple_comparison_correction'} | {'multiple_comparison_correction':None},'dio-test/'+m)
            save(dest/'dio-v-tests.json',tests)
            original=stats.overlap(data('rq1')['rows'],data('rq1')['sample_ids'])
            for revision,source in [('original',data('overlap')),('dio-v',revised)]:
                rows=data('rq1')['rows'] if revision=='original' else revised_rows
                computed=stats.overlap(rows,source['sample_ids'] if 'sample_ids' in source else data('rq1')['sample_ids'])
                equivalent(computed['comparisons'],source['comparisons'],revision+'-overlap')
                save(dest/(revision+'-overlap.json'),computed)
                if not args.numeric_only:
                    import overlap
                    from reportlab.graphics import renderPDF,renderSVG
                    draw=overlap.drawing(source,args.font_dir)
                    renderPDF.drawToFile(draw,str(dest/(revision+'-overlap.pdf')))
                    overlap.save_svg(draw,dest/(revision+'-overlap.svg'),revised=revision=='dio-v')
    print('Verified and regenerated: '+', '.join(args.sections)+'. No model calls.')


if __name__=='__main__':
    main()
