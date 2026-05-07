#!/usr/bin/env bash
# Run the TogoMCP benchmark across all four ablation conditions and save the
# raw answer CSVs (and per-condition logs) to ../results/.
#
#   With Guide  →  config.yaml             →  ../results/with_guide-<DATE>.csv
#   NG1         →  config_no_guide1.yaml   →  ../results/ng1-<DATE>.csv
#   NG2         →  config_no_guide2.yaml   →  ../results/ng2-<DATE>.csv
#   No MIE      →  config_no_mie.yaml      →  ../results/no_mie-<DATE>.csv
#
# Conditions run sequentially (not in parallel) — they share the same Anthropic
# API key, the same TogoMCP MCP endpoint, and benefit from per-condition
# isolation when comparing tool-use behaviour.
#
# Usage:
#   ./run_all_conditions.sh               # use today's date
#   ./run_all_conditions.sh 2026-05-04    # use specific date
#
# An existing CSV for a (condition, date) pair is skipped, so the script is
# safely re-runnable after a partial run — delete the file to force a re-run.

set -euo pipefail

DATE="${1:-$(date +%Y-%m-%d)}"

# cd into the directory holding this script so relative paths work regardless
# of where the user invokes it from.
cd "$(dirname "$0")"

mkdir -p ../results

CONDITIONS=(
    "config.yaml:with_guide"
    "config_no_guide1.yaml:ng1"
    "config_no_guide2.yaml:ng2"
    "config_no_mie.yaml:no_mie"
)

START_TIME=$(date +%s)

for entry in "${CONDITIONS[@]}"; do
    config="${entry%%:*}"
    prefix="${entry##*:}"
    output="../results/${prefix}-${DATE}.csv"
    log="../results/${prefix}-${DATE}.log"

    echo
    echo "=========================================================="
    echo "Condition: ${prefix}"
    echo "Config:    ${config}"
    echo "Output:    ${output}"
    echo "Log:       ${log}"
    echo "Started:   $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================================="

    if [[ ! -f "$config" ]]; then
        echo "✗ Config file not found: $config — skipping condition."
        continue
    fi
    if [[ -f "$output" ]]; then
        echo "⚠  $output already exists. Skipping (delete it to force a re-run)."
        continue
    fi

    python3 automated_test_runner.py \
        ../questions/question_*.yaml \
        -c "$config" \
        -o "$output" 2>&1 | tee "$log"

    echo "✓ Completed ${prefix} at $(date '+%Y-%m-%d %H:%M:%S')"
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
HOURS=$((ELAPSED / 3600))
MINUTES=$(((ELAPSED % 3600) / 60))

echo
echo "=========================================================="
echo "All conditions complete (total wall-clock: ${HOURS}h ${MINUTES}m)"
echo "=========================================================="
ls -la ../results/*-${DATE}.csv 2>/dev/null || echo "(no CSVs produced this run)"
