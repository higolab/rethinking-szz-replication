"""Validate saved selections, scores, and command counts against raw logs."""
from collections import Counter
from pathlib import Path
from common import ROOT, data, load, require, sha, score, equivalent, relocated
import answers
import trace
import commands


def normalized(raw, saved):
    raw,saved=set(raw),set(saved)
    require(len(raw)==len(saved) and
            all(sum(full.startswith(short) for full in saved)==1 for short in raw) and
            all(sum(full.startswith(short) for short in raw)==1 for full in saved),
            'Recorded full-hash resolution does not match raw answer')
    return sorted(saved)


def audit():
    from run_llm_baseline_subject import parse_szz_agent_prediction
    from run_pyszz import validate_official_output
    current=data('rq1')
    resources={(r['method'],r['slot_id']):r for r in data('resources')['rows']}
    cases=load(ROOT/'dataset/metadata/cases.json')['cases']
    oracles={r['id']:r['oracle_bics'] for r in cases}
    checked=Counter()
    missing=[]
    for row in current['rows']:
        method,slot=row['method'],row['slot_id']
        if method not in ('Claude Code','LLM4SZZ','AgentSZZ','SZZ-Agent','Simple-SZZ-Agent'):
            continue
        ref=resources.get((method,slot))
        if ref is None:
            require(row['scoring_rule']=='unresolved_as_empty_prediction','Unexpected missing run')
            predicted=[]
            missing.append(dict(method=method,slot_id=slot))
        else:
            directory=relocated(ref['run_dir'])
            if method=='Claude Code':
                result=answers.load_result_entry(directory/'transcript.jsonl')
                raw=answers.extract_bic_hashes(result['result'])
            elif method=='AgentSZZ':
                run=load(directory/'engine/run.json')
                require(run['state']=='completed' and not run['test_stub'],'Non-scientific run')
                raw=run['predicted_bics']
                selected=load(directory/'engine/upstream-output/case/result.json')
                require(raw==([selected['bic']] if selected.get('bic') else []),'AgentSZZ selection changed')
            elif method=='LLM4SZZ':
                prediction=load(directory/'prediction.json')
                raw=prediction['predicted_bics']
                require(sha(relocated(prediction['raw_result']))==prediction['raw_result_sha256'],'Changed candidate log')
            else:
                run=load(directory/'run.json')
                require(run['state']=='completed' and not run['test_stub'],'Non-scientific run')
                raw_path=relocated(run['prediction']['raw_result_path'])
                require(sha(raw_path)==run['prediction']['raw_result_sha256'],'Upstream result changed')
                if method=='Simple-SZZ-Agent':
                    raw=load(raw_path)['results'][0]['predicted_bics']
                else:
                    raw,_=parse_szz_agent_prediction(directory/'runtime',raw_path,
                        raw_path if run['szz_agent_flow']['stage2_executed'] else None)
                require(set(raw)==set(run['prediction']['predicted_bics']),'Raw selection differs')
            predicted=normalized(raw,ref['predictions'])
            checked[method]+=1
        require(score(predicted,oracles[row['sample_id']])=={k:row[k] for k in ('tp','fp','fn')},'Score drift: '+method+'/'+slot)
    require(sum(checked.values())+len(missing)==1185,'Incomplete RQ1 slot grid')

    rule_checked={}
    for record in data('rules')['runs']:
        raw=load(relocated(record['path']))
        by_id={str(r['id']):r for r in raw}
        require(len(raw)==len(by_id)==80,'Historical rule-based case grid changed')
        rows={r['sample_id']:r for r in current['rows'] if r['method']==record['method']}
        require(set(rows)==set(oracles),'Historical rule-based cohort differs')
        for sid,row in rows.items():
            raw_case=by_id[sid]
            case=next(c for c in cases if c['id']==sid)
            require(raw_case['fix_commit_hash']==case['bfc'],'Historical BFC differs')
            counts=score(raw_case['inducing_commit_hash'],oracles[sid])
            require(counts=={k:row[k] for k in counts},'Historical score drift: '+record['method']+'/'+sid)
        rule_checked[record['method']]=len(rows)

    ra=load(ROOT/'results/raw/ra-szz-star/extended-timeout/summary.json')
    ra_rows={r['sample_id']:r for r in current['rows'] if r['method']=='RA-SZZ*'}
    for entry in ra['rows']:
        sid=entry['sample_id']
        selected=Path(entry['selected_attempt']).with_name('result.json')
        path=relocated(selected)
        match=[a for a in entry['attempts'] if Path(a['path'])==selected]
        require(len(match)==1 and sha(path)==match[0]['sha256'],'RA-SZZ source differs')
        result=load(path)
        if entry['status']=='success':
            files=[relocated(p) for p in result['artifacts'] if '/out/' in p and p.endswith('.json')]
            require(len(files)==1,'RA-SZZ output missing')
            _,pred=validate_official_output(load(files[0]),repository=result['repository'],fix_hash=result['fix_commit_hash'])
            require(pred==entry['predictions'],'RA-SZZ selection changed')
        else:
            pred=[]
        require(score(pred,oracles[sid])=={k:ra_rows[sid][k] for k in ('tp','fp','fn')},'RA-SZZ score differs')

    census_calls={(r['slot_id'],r['call_index']):r for r in data('census')['calls']}
    bash=0
    for r in data('rq2')['runs']:
        calls=trace.extract_tool_calls(trace.transcript_events(relocated(r['transcript_path'])))
        require(len(calls)==len(r['calls']),'Missing RQ2 call')
        for index,(raw,selected) in enumerate(zip(calls,r['calls']),1):
            require(raw['tool_name']=='Bash' and raw['tool_use_id']==selected['tool_use_id'] and raw['input']['command']==selected['command'],'RQ2 command drift')
            items,_=commands.split_commands(raw['input']['command'],r['slot_id'],raw['tool_use_id'])
            equivalent(items,census_calls[(r['slot_id'],index)]['invocations'],'shell-extraction')
        bash+=len(calls)

    message_audit = audit_messages(oracles)
    return dict(validated_saved_answers=dict(checked),unresolved_scored_empty=missing,
                rq2_runs=237,rq2_bash_calls=bash,ablation_transcripts=474,
                message_ablation=message_audit,
                ra_szz_saved_successes=ra['success'],ra_szz_saved_failures=ra['selected_failed'],
                historical_rule_based_answers=rule_checked,
                boundaries='Full hashes use saved resolution records. Manual labels are reapplied, not independently re-reviewed.')


def audit_messages(oracles):
    """Verify November primary slots, scores, tokens, and both time boundaries."""
    root=ROOT/'results/raw/claude-code-no-messages'
    source=data('messages')
    scores=data('free-scores')
    completion=load(root/'completion.json')
    require(source['execution_id']==scores['execution_id']==completion['execution_id']==
            'COMMIT-MESSAGE-FREE-DUAL-TIMING-20261103', 'Wrong ablation execution')
    require(completion['final'] and completion['normal_runs']==237 and
            all(completion[k]==0 for k in ('failed_runs','pending_runs','unresolved_runs')),
            'Incomplete ablation execution')
    require(scores['final'] and scores['pending_runs']==0 and scores['review_required_runs_scored_empty']==0,
            'Incomplete score mapping')
    def indexed(rows):
        result={(r['sample_id'],r['repeat']):r for r in rows}
        require(len(result)==len(rows)==237, 'Duplicate or missing ablation slots')
        require(set(result)=={(sid,rep) for sid in oracles for rep in (1,2,3)}, 'Wrong ablation cohort')
        return result
    free=indexed(scores['rows'])
    finished=indexed(completion['rows'])
    plan=[r for r in load(root/'execution-plan.json')['slots'] if r['repeat']==1]
    plan+=load(root/'r02-continuation-plan.json')['slots']
    plan+=load(root/'r03-queue-plan.json')['slots']
    mapped=indexed(plan)
    require(len(source['rows'])==len({(r['condition'],r['sample_id'],r['repeat']) for r in source['rows']})==474,
            'Duplicate or missing comparison rows')
    rates=source['method']['common_price_usd_per_million']
    for r in source['rows']:
        directory=relocated(r['run_dir'])
        run=load(directory/'run.json')
        require(run['state']=='completed' and run['transcript_validation']['valid'], 'Non-normal ablation run')
        require(tuple(run['claude'][k] for k in ('model','effort','version'))==
                ('claude-sonnet-5','high','2.1.232'), 'Ablation model drift')
        proc=run['process']
        require(proc['exit_code']==0 and not proc['timed_out'] and not proc['interrupted'], 'Failed ablation process')
        require(proc['stdout_sha256']==sha(directory/'transcript.jsonl'), 'Changed ablation transcript')
        events=trace.transcript_events(directory/'transcript.jsonl')
        end=trace.final_result_event(events)
        calls=trace.extract_tool_calls(events)
        require(not end['is_error'] and set(end['modelUsage'])=={'claude-sonnet-5'}, 'Invalid ablation result')
        require(len(calls)==r['bash_calls'] and all(c['tool_name']=='Bash' for c in calls),'Ablation call count drift')
        usage=end['usage']
        tokens={k:usage[k] for k in ('input_tokens','output_tokens','cache_read_input_tokens')}
        tokens.update(cache_write_5m_tokens=usage['cache_creation']['ephemeral_5m_input_tokens'],
                      cache_write_1h_tokens=usage['cache_creation']['ephemeral_1h_input_tokens'])
        require(tokens==r['usage'], 'Token count drift')
        require(tokens['cache_write_5m_tokens']+tokens['cache_write_1h_tokens']==usage['cache_creation_input_tokens'],
                'Cache token subtotal drift')
        equivalent(sum(tokens[k]*rate for k,rate in rates.items())/1e6,r['common_cost_usd'],'message-cost')
        require(end['total_cost_usd']==r['reported_cost_usd'] and end['duration_ms']/1000==r['cli_seconds'],
                'CLI measurement drift')
        require(proc['duration_seconds']==r['process_seconds'] and r['total_seconds']>=r['process_seconds']>0,
                'Process time drift')
        if r['condition']=='free':
            key=(r['sample_id'],r['repeat'])
            require(all(relocated(ref[key]['run_dir'])==directory for ref in (free,finished,mapped)), 'Primary mapping drift')
            timing=load(directory.parent/'timing.json')
            require(timing['state']=='completed' and timing['timing_valid'] and
                    timing['run_manifest_sha256']==sha(directory/'run.json'), 'Invalid timing record')
            require(sha(directory.parent/'timing.json')==finished[key]['timing_sha256'], 'Changed timing record')
            require(timing['total_seconds']==timing['finished_at']-timing['started_at']==r['total_seconds'] and
                    timing['process_seconds']==r['process_seconds'], 'Outer time drift')
            s=free[key]['score']
            require(not s['unresolved'],'Unresolved hash mapping')
            normalized(answers.extract_bic_hashes(end['result']),s['predicted_new'])
            counts=score(s['predicted_original'],oracles[r['sample_id']])
            require(counts=={k:r[k] for k in counts},'Ablation score drift')
        else:
            require(r['condition']=='present', 'Unknown ablation condition')
            ledger=load(directory.parent.parent/'retry-ledger.json')
            selected=ledger['attempts'][ledger['selected_attempt']-1]
            require(relocated(selected['directory'])/'run'==directory and selected['outcome']['action']=='completed',
                    'Wrong baseline attempt')
            require(selected['finished_at']-selected['started_at']==r['total_seconds'], 'Baseline outer time drift')
            ref=next(x for x in data('rq1')['rows'] if x['method']=='Claude Code' and
                     x['sample_id']==r['sample_id'] and x['replicate']==r['repeat'])
            require(all(ref[k]==r[k] for k in ('tp','fp','fn')), 'Baseline score drift')
    history=completion['historical_attempts']
    require(len(history)==1 and history[0]['included_in_primary_results'] is False, 'Historical attempt changed')
    require(load(relocated(history[0]['timing_path']))['state']=='interrupted', 'Missing interrupted attempt')
    return dict(primary_runs=237,historical_interrupted_runs=1,
                execution_id=source['execution_id'],total_time_verified=True,process_time_verified=True)
