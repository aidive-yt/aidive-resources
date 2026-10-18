"""Count whether a `claude -p --output-format stream-json` run loaded a given skill. Usage: python3 tally.py <skill> run1.jsonl [run2.jsonl ...]"""
import json, sys
skill, files = sys.argv[1], sys.argv[2:]
fired = 0
for f in files:
    hit = False
    for line in open(f):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get('type') == 'assistant':
            for c in d['message'].get('content', []):
                if c.get('type') == 'tool_use' and c['name'] == 'Skill' and skill in json.dumps(c.get('input', {})):
                    hit = True
    fired += hit
    print(f"{f}: {'loaded' if hit else 'skipped'}")
print(f"{skill}: loaded in {fired} of {len(files)} runs")
