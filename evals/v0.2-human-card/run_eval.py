#!/usr/bin/env python3
"""Run the go-trail v0.2 human-card evals in isolated temporary homes.

This harness intentionally runs only the with-skill configuration. It redirects
HOME for every case so the real ~/.data/go-trail/human-card.md is never read or
written. Run the harness itself inside the external sandbox chosen by the human.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
from typing import Any


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parents[1]
SKILL_DIR = REPO_DIR / "skill"
EVALS_PATH = PACKAGE_DIR / "evals.json"
DEFAULT_WORKSPACE = REPO_DIR / "go-trail-workspace" / "human-card-iteration-1"

FRAMING = """You are the main conversation agent in an isolated evaluation.

Before replying to the user:
1. Read {skill_path} completely and follow it.
2. Use the available custom agent `human-card-sprite` exactly as the skill requires.
3. Treat the current HOME as the user's home. Never read or write a human card outside it.

Your visible result for each turn must be only the natural reply to the user. Do not
mention the evaluation, tools, subagents, LOAD_OR_INIT, CARD_CONTEXT, or internal
workflow. Do not write evaluation artifacts; the harness captures them.

User message:
{message}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_ids", nargs="*", type=int, help="Eval IDs; default: all")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--model", help="Optional main-agent model override")
    parser.add_argument("--keep-sandbox", action="store_true")
    return parser.parse_args()


def load_suite() -> dict[str, Any]:
    return json.loads(EVALS_PATH.read_text(encoding="utf-8"))


def user_line(text: str) -> str:
    return json.dumps(
        {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        },
        ensure_ascii=False,
    )


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_mode(path: Path) -> str | None:
    if not path.exists():
        return None
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def extract_agent_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        message = event.get("message") or {}
        for block in message.get("content") or []:
            if block.get("type") != "tool_use":
                continue
            if str(block.get("name", "")).lower() not in {"agent", "task"}:
                continue
            payload = block.get("input") or {}
            resume = payload.get("resume") or payload.get("agent_id") or payload.get("agentId")
            serialized = json.dumps(payload, ensure_ascii=False)
            if "human-card-sprite" not in serialized and not resume:
                continue
            calls.append(
                {
                    "tool_use_id": block.get("id"),
                    "subagent_type": payload.get("subagent_type") or payload.get("agent"),
                    "description": payload.get("description"),
                    "resume": resume,
                    "is_initial_dispatch": not bool(resume),
                }
            )
    return calls


def extract_agent_ids(events: list[dict[str, Any]]) -> list[str]:
    ids: set[str] = set()
    pattern = re.compile(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", re.IGNORECASE)
    for event in events:
        if event.get("type") != "user":
            continue
        message = event.get("message") or {}
        for block in message.get("content") or []:
            if block.get("type") != "tool_result":
                continue
            content = block.get("content")
            text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
            if "agent" not in text.lower():
                continue
            ids.update(pattern.findall(text))
    return sorted(ids)


def make_agent_definition(contract: str) -> str:
    return json.dumps(
        {
            "human-card-sprite": {
                "description": (
                    "Load, initialize, and minimally maintain the go-trail human card. "
                    "Reuse this agent throughout the current conversation."
                ),
                "prompt": contract,
                "tools": ["Read", "Bash", "Edit", "Write"],
                "model": "haiku",
            }
        },
        ensure_ascii=False,
    )


def prepare_sandbox(eval_case: dict[str, Any]) -> tuple[Path, Path, Path, str | None]:
    root = Path(tempfile.mkdtemp(prefix=f"go-trail-eval-{eval_case['id']}.")).resolve()
    home = root / "home"
    home.mkdir(mode=0o700)
    shutil.copytree(SKILL_DIR, root / "skill")

    card = home / ".data" / "go-trail" / "human-card.md"
    fixture = eval_case.get("initial_card")
    initial_hash = None
    if fixture:
        source = PACKAGE_DIR / fixture
        card.parent.mkdir(parents=True, mode=0o700)
        shutil.copyfile(source, card)
        card.chmod(0o600)
        initial_hash = sha256(card)
    return root, home, card, initial_hash


def run_case(
    eval_case: dict[str, Any],
    workspace: Path,
    model: str | None,
    keep_sandbox: bool,
) -> bool:
    eval_dir = workspace / f"eval-{eval_case['id']}-{eval_case['name']}"
    run_dir = eval_dir / "with_skill" / "run-1"
    outputs_dir = run_dir / "outputs"
    if run_dir.exists():
        raise RuntimeError(f"Refusing to overwrite existing run: {run_dir}")
    outputs_dir.mkdir(parents=True)

    metadata = {
        "eval_id": eval_case["id"],
        "eval_name": eval_case["name"],
        "prompt": eval_case["prompt"],
        "assertions": eval_case["expectations"],
        "configuration": "with_skill",
        "run_number": 1,
    }
    (eval_dir / "eval_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    root, home, card, initial_hash = prepare_sandbox(eval_case)
    contract = (root / "skill" / "subagents" / "human-card-sprite.md").read_text(
        encoding="utf-8"
    )
    command = [
        "claude",
        "--safe-mode",
        "--tools",
        "Read,Write,Edit,Bash,Agent",
        "--permission-mode",
        "acceptEdits",
        "--agents",
        make_agent_definition(contract),
        "--forward-subagent-text",
        "--no-session-persistence",
        "--verbose",
        "-p",
        "--input-format",
        "stream-json",
        "--output-format",
        "stream-json",
    ]
    if model:
        command[1:1] = ["--model", model]

    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment["NO_COLOR"] = "1"

    stderr_path = run_dir / "claude_stderr.txt"
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=root,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr_handle,
        text=True,
        bufsize=1,
    )

    messages = eval_case["messages"]
    events: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    responses: list[str] = []
    turn_seconds: list[float] = []
    start = time.time()
    turn_start = start
    next_message = 1

    first_input = FRAMING.format(
        skill_path=root / "skill" / "SKILL.md", message=messages[0]
    )

    try:
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(user_line(first_input) + "\n")
        process.stdin.flush()

        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(event)
            if event.get("type") != "result":
                continue

            results.append(event)
            responses.append(str(event.get("result") or "").strip())
            turn_seconds.append(round(time.time() - turn_start, 1))
            if next_message < len(messages):
                process.stdin.write(user_line(messages[next_message]) + "\n")
                process.stdin.flush()
                next_message += 1
                turn_start = time.time()
            else:
                process.stdin.close()

        process.wait(timeout=120)
    finally:
        stderr_handle.close()
        if process.poll() is None:
            process.kill()

    duration_seconds = round(time.time() - start, 1)
    raw_path = run_dir / "claude_stdout.jsonl"
    raw_path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )

    transcript: list[str] = []
    for index, message in enumerate(messages):
        transcript.append(f"用户：{message}")
        response = responses[index] if index < len(responses) else "（缺失）"
        transcript.append(f"\n你：{response}\n")
    (outputs_dir / "transcript.md").write_text("\n".join(transcript), encoding="utf-8")

    if card.is_file():
        shutil.copyfile(card, outputs_dir / "human-card.md")

    usage = {"input_tokens": 0, "output_tokens": 0}
    for result in results:
        result_usage = result.get("usage") or {}
        usage["input_tokens"] += int(result_usage.get("input_tokens") or 0)
        usage["output_tokens"] += int(result_usage.get("output_tokens") or 0)

    calls = extract_agent_calls(events)
    summary = {
        "returncode": process.returncode,
        "turns_expected": len(messages),
        "turns_completed": len(results),
        "sprite_calls": calls,
        "sprite_initial_dispatches": sum(call["is_initial_dispatch"] for call in calls),
        "sprite_resume_calls": sum(not call["is_initial_dispatch"] for call in calls),
        "observed_agent_ids": extract_agent_ids(events),
        "card_exists": card.is_file(),
        "card_initial_sha256": initial_hash,
        "card_final_sha256": sha256(card),
        "data_directory_mode": file_mode(card.parent),
        "card_mode": file_mode(card),
        "sandbox_home": str(home),
    }
    (outputs_dir / "execution-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (run_dir / "timing.json").write_text(
        json.dumps(
            {
                "total_tokens": usage["input_tokens"] + usage["output_tokens"],
                "usage": usage,
                "duration_ms": int(duration_seconds * 1000),
                "total_duration_seconds": duration_seconds,
                "turn_duration_seconds": turn_seconds,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if keep_sandbox:
        (run_dir / "sandbox-path.txt").write_text(str(root) + "\n", encoding="utf-8")
    else:
        shutil.rmtree(root)

    completed = process.returncode == 0 and len(results) == len(messages)
    print(
        f"eval-{eval_case['id']} {eval_case['name']}: "
        f"{'DONE' if completed else 'FAILED'} ({len(results)}/{len(messages)} turns)"
    )
    return completed


def main() -> int:
    args = parse_args()
    suite = load_suite()
    selected = set(args.eval_ids or [case["id"] for case in suite["evals"]])
    cases = [case for case in suite["evals"] if case["id"] in selected]
    missing = selected - {case["id"] for case in cases}
    if missing:
        raise SystemExit(f"Unknown eval IDs: {sorted(missing)}")

    args.workspace.mkdir(parents=True, exist_ok=True)
    snapshot = args.workspace / "skill-snapshot"
    if not snapshot.exists():
        shutil.copytree(SKILL_DIR, snapshot)
    eval_snapshot = args.workspace / "evals-snapshot.json"
    if not eval_snapshot.exists():
        shutil.copyfile(EVALS_PATH, eval_snapshot)

    success = True
    for eval_case in cases:
        success = run_case(eval_case, args.workspace, args.model, args.keep_sandbox) and success
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
