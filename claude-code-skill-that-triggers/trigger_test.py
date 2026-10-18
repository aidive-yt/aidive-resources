"""Twenty-prompt trigger test for one skill, the method skill-creator describes, run on the real skill folder.
For each query: a fresh `claude -p` in the repo; the run counts as loaded if the Skill tool is called with the skill's name
before the run ends (stopped early as soon as it is). Usage:
  python3 trigger_test.py <repo> <skill-name> <SKILL.md to install> <evals.json> <out.json> [workers]"""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

repo, name, skill_md, evals_path, out = sys.argv[1:6]
workers = int(sys.argv[6]) if len(sys.argv) > 6 else 4
dest = os.path.join(repo, '.claude', 'skills', name)
os.makedirs(dest, exist_ok=True)
shutil.copy(skill_md, os.path.join(dest, 'SKILL.md'))
evals = json.load(open(evals_path))
allowed = ['Bash(rtk git log *)', 'Bash(git log *)', 'Bash(git show *)', 'Bash(date *)', 'Skill', 'Read']

def run(item):
    cmd = ['claude', '-p', item['query'], '--output-format', 'stream-json', '--verbose', '--allowedTools', *allowed]
    p = subprocess.Popen(cmd, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    loaded = False
    try:
        for line in p.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get('type') == 'assistant':
                for c in d['message'].get('content', []):
                    if c.get('type') == 'tool_use' and c['name'] == 'Skill' and name in json.dumps(c.get('input', {})):
                        loaded = True
            if loaded or d.get('type') == 'result':
                break
    finally:
        if p.poll() is None:
            p.kill()
    return {**item, 'loaded': loaded, 'pass': loaded == item['should_trigger']}

with ThreadPoolExecutor(workers) as ex:
    results = list(ex.map(run, evals))
should = [r for r in results if r['should_trigger']]
shouldnt = [r for r in results if not r['should_trigger']]
summary = {'loaded_when_it_should': sum(r['loaded'] for r in should), 'of_should': len(should),
           'loaded_when_it_should_not': sum(r['loaded'] for r in shouldnt), 'of_should_not': len(shouldnt),
           'passed': sum(r['pass'] for r in results), 'total': len(results)}
json.dump({'skill': name, 'skill_md': skill_md, 'summary': summary, 'results': results}, open(out, 'w'), indent=2)
for r in results:
    print(f"[{'PASS' if r['pass'] else 'FAIL'}] {'loaded ' if r['loaded'] else 'skipped'} expected={'load' if r['should_trigger'] else 'skip'}: {r['query']}")
print(json.dumps(summary))
