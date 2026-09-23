# go-trail v0.2 Human-card Eval Package

This package validates the new human-card workflow only. It does not rerun the v0.1 conversation-quality suite and has no baseline arm.

## Coverage

| Eval | Contract under test |
| --- | --- |
| 1 | Missing card initialization, private permissions, first-use notice |
| 2 | Existing card loaded before dialogue and left unchanged when no durable fact appears |
| 3 | Durable facts reduced to minimum useful professional and caregiving context |
| 4 | Sensitive, session-only history excluded even in abstract form |
| 5 | One sprite reused across turns; stable communication preferences retained |
| 6 | Explicit clear operation preserves the canonical empty card |

Each case uses a fresh temporary `HOME`. The real `~/.data/go-trail/human-card.md` is not read or written. The harness still needs to run inside the independent external sandbox selected for the evaluation; temporary HOME redirection is data isolation, not an operating-system security boundary.

## Run

From the repository root:

```bash
python3 evals/v0.2-human-card/run_eval.py
```

To run selected cases:

```bash
python3 evals/v0.2-human-card/run_eval.py 1 3 5
```

An optional main-agent model can be supplied without changing the low-intensity sprite model:

```bash
python3 evals/v0.2-human-card/run_eval.py --model glm-5.3-flash
```

The runner refuses to overwrite an existing run. Use a new workspace path for a new sample:

```bash
python3 evals/v0.2-human-card/run_eval.py \
  --workspace go-trail-workspace/human-card-iteration-2
```

Do not use `--keep-sandbox` unless debugging a failed run. When enabled, the temporary HOME path is saved in `sandbox-path.txt` and must be cleaned deliberately after inspection.

## Artifacts

The default output is:

```text
go-trail-workspace/human-card-iteration-1/
├── evals-snapshot.json
├── skill-snapshot/
└── eval-<id>-<name>/
    ├── eval_metadata.json
    └── with_skill/run-1/
        ├── claude_stdout.jsonl
        ├── claude_stderr.txt
        ├── timing.json
        └── outputs/
            ├── transcript.md
            ├── human-card.md
            └── execution-summary.json
```

`execution-summary.json` records card hashes and permissions plus observed sprite dispatch/resume calls. Raw JSONL is retained for lifecycle verification but should not be quoted wholesale into the report.

## Grade

Run deterministic checks first:

```bash
python3 evals/v0.2-human-card/static_grade.py
```

These checks write `static-grading.json`; they intentionally cover only mechanically verifiable behavior. Then give the completed artifacts and [GRADING.md](GRADING.md) to an independent grader to produce the final `grading.json` files.

Because this is a single-sample, single-configuration validation, report assertion counts and concrete failure modes. Do not report deltas, confidence intervals, or claims that v0.2 is globally better.
