#!/bin/zsh
# Usage: run-task.sh <name> <A|B> <plan|alt|alt-nobare> [timeout_s]
# Runs one task on a fresh copy of slugkit and records time, output, diff and the check.
set -u
NAME=$1; TASK=$2; MODE=$3; TO=${4:-1800}
SRC=${SLUGKIT:?set SLUGKIT to the slugkit repo}
OUT=${RUNS:?set RUNS to the output dir}/$NAME
rm -rf $OUT; mkdir -p $OUT; cp -R $SRC $OUT/repo; cd $OUT/repo
A='In slugkit/cli.py add a --prefix option: when given, the slug starts with the prefix and the separator (python3 -m slugkit --prefix blog Hello World prints blog-hello-world). Then run that command to check it.'
B='Rename the function smart_truncate to truncate_words everywhere in this repo (definition, imports, calls, tests, __all__). Keep smart_truncate as an alias of truncate_words in slugkit/truncate.py so old imports still work. Then run python3 -m unittest discover tests and make sure every test passes.'
[[ $TASK == A ]] && P=$A || P=$B
TOOLS=(--allowedTools "Read" "Edit" "Write" "Glob" "Grep" "Bash(python3:*)" "Bash(grep:*)" "Bash(ls:*)")
start=$(date +%s)
case $MODE in
  plan) perl -e 'alarm shift; exec @ARGV' $TO claude -p "$P" --output-format json $TOOLS > $OUT/out.json 2> $OUT/err.log ;;
  alt) CLAUDE_CODE_ATTRIBUTION_HEADER=0 ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY=ollama ANTHROPIC_BASE_URL=http://localhost:11434 \
       perl -e 'alarm shift; exec @ARGV' $TO claude --bare --model qwen3.5:9b -p "$P" --output-format json $TOOLS > $OUT/out.json 2> $OUT/err.log ;;
  alt-nobare) CLAUDE_CODE_ATTRIBUTION_HEADER=0 ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY="" ANTHROPIC_BASE_URL=http://localhost:11434 \
       perl -e 'alarm shift; exec @ARGV' $TO claude --model qwen3.5:9b -p "$P" --output-format json $TOOLS > $OUT/out.json 2> $OUT/err.log ;;
esac
rc=$?; end=$(date +%s)
git diff --stat > $OUT/diff.stat; git diff > $OUT/diff.patch
if [[ $TASK == A ]]; then python3 -m slugkit --prefix blog Hello World > $OUT/check.txt 2>&1; else python3 -m unittest discover tests > $OUT/check.txt 2>&1; grep -rn smart_truncate slugkit tests >> $OUT/check.txt; fi
echo "{\"name\":\"$NAME\",\"task\":\"$TASK\",\"mode\":\"$MODE\",\"rc\":$rc,\"seconds\":$((end-start))}" > $OUT/meta.json
cat $OUT/meta.json; tail -3 $OUT/check.txt
