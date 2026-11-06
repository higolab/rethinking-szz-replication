# Rethinking SZZ Search Strategies: Lessons from Claude Code

Replication package. Clone this repository or extract the release ZIP, then run the commands below from the package directory.

- Requirements: Python 3.11+ and Git for data preparation; Docker for saved analyses; macOS for new experiments.
- `dataset/`: metadata, [edited BFC messages](dataset/metadata/commit-messages.json) and [DIO-V](dataset/dio-verified/README.md).
- `preprocess/`, `experiments/`, `analysis/`: preparation, execution and analysis scripts.
- `results/`: saved inputs and logs grouped by method; `outputs/`: generated results.

## 1. Collect and prepare data

```sh
python3 -B preprocess/collect.py --ids 10
python3 -B preprocess/prepare.py --ids 10 --execute
python3 -B preprocess/prepare.py --ids 10 --verify
python3 -B preprocess/remove_messages.py --ids 10 --execute
```

- Replace `--ids 10` with `--all` for all 79 cases.
- Original clones stay in `dataset/repositories/`; BFC-ancestry inputs go to `dataset/prepared/`.
- Message-free copies go to `dataset/message_free/`; hash maps stay outside agent-visible repositories.

## 2. Reproduce the saved results

- View [the results notebook](analysis/results.ipynb): RQ1, commit-message ablation, and supplementary DIO-V. Outputs are saved; [setup](analysis/README.md#notebook) is only needed to rerun it.
- No subject downloads, credentials or model calls are needed.
- Detailed RefactoringMiner event dumps are omitted; saved RA-SZZ* predictions and run records are retained.

```sh
docker build -f docker/analysis.Dockerfile -t szz-analysis .
mkdir -p outputs
docker run --rm --network none -u "$(id -u):$(id -g)" \
  -v "$PWD:/package:ro" -v "$PWD/outputs:/package/outputs:rw" \
  szz-analysis --output outputs/analysis
```

- Use a fresh output directory for each run.
- Options: `--sections rq2` for one section; `--numeric-only` to skip figures.
- See [analysis](analysis/README.md) for outputs and evidence.

## 3. Run new experiments

- These commands only print plans; [execution instructions](experiments/README.md) include setup and resource-use flags.

```sh
python3 -B experiments/claude_code.py all --ids 10 --replicates 3
python3 -B experiments/baselines.py --method agentszz --id 10
python3 -B experiments/rules.py --id 10
```

- New model runs may differ from the saved answers.
- Public copy: personal paths and embedded credentials are masked; checksums refer to these sanitized files.
- No manuscript or credentials are included. See [third-party licenses](THIRD-PARTY.md).
