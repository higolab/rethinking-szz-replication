"""Local saved-evidence access. No downloads, models, or compatibility tree."""
import hashlib
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'analysis/lib'))
sys.path.insert(1, str(ROOT / 'experiments/scripts'))

# Historical directory names remain in the sanitized run records.
RAW_RUN_DIRECTORIES = {
    'subject-bfc-message-neutralized-final-v2-dec017-retry10': 'claude-code',
    'commit-message-free-dual-timing-20261103': 'claude-code-no-messages',
    'agentszz-final-v2-api-600s-usd5-3r-20260907': 'agentszz',
    'llm4szz-original-v1-sonnet-20261001': 'llm4szz',
    'llm-baselines/simple-szz-agent-bfc-message-neutralized-final-v2-dec017-retry10': 'simple-szz-agent',
    'llm-baselines/szz-agent-bfc-message-neutralized-final-v2-dec017-retry10': 'szz-agent',
    'raszz-star-final-v2-local-origin-20260908': 'ra-szz-star/initial',
    'raszz-star-final-v2-extended-timeout-20260908': 'ra-szz-star/extended-timeout',
    'rule-based/20260816T032031Z__b': 'b-szz',
    'rule-based/20260816T032449Z__ag': 'ag-szz',
    'rule-based/20260816T034206Z__ma': 'ma-szz',
    'rule-based/20260816T035848Z__r': 'r-szz',
    'rule-based/20260816T041524Z__l': 'l-szz',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def data(name):
    return load(ROOT / 'results/inputs' / (name + '.json'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        require(path.read_text() == encoded, f'Refusing to replace a different result: {path}')
    else:
        with path.open('x') as stream:
            stream.write(encoded)


def score(predicted, oracle):
    predicted, oracle = set(predicted), set(oracle)
    return dict(tp=len(predicted & oracle), fp=len(predicted-oracle), fn=len(oracle-predicted))


def english(value):
    # Raw annotations remain unchanged; only these display labels are translated.
    if isinstance(value, str):
        return value.replace('順序保留{', 'Unresolved order {').replace('活動不明{', 'Unknown activity {')
    if isinstance(value, list):
        return [english(v) for v in value]
    if isinstance(value, dict):
        return {english(k): english(v) for k,v in value.items()}
    return value


def equivalent(actual, expected, location='result'):
    if isinstance(actual, (int,float)) and isinstance(expected, (int,float)):
        require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), f'Mismatch: {location}')
    elif isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), f'Keys differ: {location}')
        for k in expected:
            equivalent(actual[k], expected[k], location+'/'+str(k))
    elif isinstance(expected, list):
        require(isinstance(actual, (tuple,list)) and len(actual)==len(expected), f'Length differs: {location}')
        for i,(a,b) in enumerate(zip(actual,expected)):
            equivalent(a,b,location+'/'+str(i))
    else:
        require(actual==expected, f'Mismatch: {location}: {actual!r} != {expected!r}')


def relocated(path):
    """Resolve historical record paths directly to packaged raw files."""
    text = str(path)
    for prefix in ('/Users/user-01/research/workspaces/claude-szz/implementation/',
                   '/mnt/ssd/repos/research/claude-szz/implementation/'):
        if text.startswith(prefix):
            text = text[len(prefix):]
    if text.startswith('experiments/runs/'):
        text = 'results/raw/' + text[len('experiments/runs/'):]
    for old, new in RAW_RUN_DIRECTORIES.items():
        prefix = 'results/raw/' + old
        if text == prefix or text.startswith(prefix + '/'):
            text = 'results/raw/' + new + text[len(prefix):]
            break
    target = ROOT / text
    require(target.resolve().is_relative_to(ROOT) and not target.is_symlink(), f'Unsafe saved path: {path}')
    require(target.exists(), f'Unpackaged evidence: {path}')
    return target


def verify():
    manifest = load(ROOT/'results/manifest.json')
    seen = set()
    for row in manifest['files']:
        name = row['path']
        require(name not in seen, f'Duplicate input: {name}')
        seen.add(name)
        require(sha(relocated(name)) == row['sha256'], f'Changed evidence: {name}')
    return {'verified_files':len(seen), 'model_calls':0}
