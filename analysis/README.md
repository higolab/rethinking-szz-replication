# Reproduce the analyses

- Use the Docker command in the [root README](../README.md).
- The runner verifies [checksums](../results/manifest.json) and regenerated values against saved results; saved answers and measurements are preserved.

## Notebook

- Open [results.ipynb](results.ipynb) to view saved tables: RQ1, commit-message ablation, then supplementary DIO-V.
- To rerun: `python -m pip install -r analysis/notebook-requirements.txt`, then `python -m jupyterlab analysis/results.ipynb` from the package directory. Select **Run All**.
- The notebook calls the existing offline analysis scripts and writes to a fresh directory under `outputs/`. It makes no model or API calls.

## Outputs

- `rq1/`: accuracy, Holm-adjusted Wilcoxon tests, token-based cost and elapsed time.
- `rq2/`: command counts, ABC classifications, operation sequences, tables and figures.
- `rq3/`: 22 case classifications and source/test evidence checks.
- `further_analysis/`: message ablation, efficiency tests, DIO-V rescoring and overlap figures.

## Analysis rules

- Average TP/FP/FN and accuracy across repetitions; incomplete runs count as empty answers. Resource averages use completed runs.
- Score the study's 79 cases, including when historical rule-based logs contain 80. Resolve commit hashes using saved records.
- RQ2 uses recorded commands and Git-query results, without executing logged commands or downloading repositories.
- Apply the [20 manual labels](../results/inputs/rq2-manual-labels.csv); `B+C` is an unordered set. Preserve unknown and overlapping operations.
- Check the [case-3109 illustration](assets/case-3109.pdf) against its three logged sequences.
- [RQ3](rq3/README.md) and [performance differences](anti-patterns/README.md) reuse the saved reviews; they are not new independent assessments.

## Message ablation

- Message-free results use the 237 primary runs of `COMMIT-MESSAGE-FREE-DUAL-TIMING-20261103`, replacing the September message-free results. RQ1, RQ2, RQ3 and DIO-V evidence is unchanged.
- The primary mapping combines r01 in `execution-plan.json`, `r02-continuation-plan.json`, and `r03-queue-plan.json` under `results/raw/claude-code-no-messages/`. ID 10/r02 uses `manual-restarts/r02/10/a02/`; the interrupted `r02/10/` is retained but excluded.
- `total_seconds` includes pre/postflight validation; `process_seconds` measures the Claude process only. Both conditions use total time in the main comparison. Queue waits and discarded attempts are excluded. Conditions ran at different times; total time includes different validation work.
- Two-sided Wilcoxon tests use 79 paired case means, with zero differences removed, average tied ranks, normal approximation, and no continuity correction. Holm correction covers F1, Bash calls, total time, and cost. Exact conditional p-values and process-time, repository-weighted, and identity-header sensitivity analyses are also reproduced.
- API-equivalent USD per million tokens: input 2, output 10, cache write (5 min) 2.5, cache write (1 hour) 4, cache read 0.2. CLI-reported cost is retained separately; neither is an actual subscription bill.
- Exported logs mask personal paths. Packaged checksum references are updated; `source_sha256` in the manifest retains the original source hash. Debug and API-traffic captures are not distributed.
