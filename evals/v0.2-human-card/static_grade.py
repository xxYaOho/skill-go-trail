#!/usr/bin/env python3
"""Run deterministic checks for completed v0.2 human-card eval runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Callable


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parents[1]
DEFAULT_WORKSPACE = REPO_DIR / "go-trail-workspace" / "human-card-iteration-1"
EMPTY_CARD = (PACKAGE_DIR / "fixtures" / "empty-card.md").read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_ids", nargs="*", type=int)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    return parser.parse_args()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_card(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def check(text: str, passed: bool, evidence: str) -> dict[str, object]:
    return {"text": text, "passed": bool(passed), "evidence": evidence}


def load_run(workspace: Path, eval_id: int, name: str) -> tuple[Path, str, str, dict]:
    run = workspace / f"eval-{eval_id}-{name}" / "with_skill" / "run-1"
    outputs = run / "outputs"
    transcript = (outputs / "transcript.md").read_text(encoding="utf-8")
    card_path = outputs / "human-card.md"
    card = card_path.read_text(encoding="utf-8") if card_path.is_file() else ""
    summary = json.loads((outputs / "execution-summary.json").read_text(encoding="utf-8"))
    return run, transcript, card, summary


def grade_1(transcript: str, card: str, summary: dict) -> list[dict[str, object]]:
    return [
        check(
            "The sprite was initialized exactly once",
            summary.get("sprite_initial_dispatches") == 1,
            f"sprite_initial_dispatches={summary.get('sprite_initial_dispatches')}",
        ),
        check(
            "The card matches the canonical empty structure",
            normalize_card(card) == normalize_card(EMPTY_CARD),
            f"final_sha256={sha256_text(card) if card else None}",
        ),
        check(
            "Private POSIX permissions were applied",
            summary.get("data_directory_mode") == "0700" and summary.get("card_mode") == "0600",
            f"dir={summary.get('data_directory_mode')}, card={summary.get('card_mode')}",
        ),
        check(
            "The user was informed that the card exists and can be viewed or cleared",
            "用户卡" in transcript and bool(re.search(r"查看|清空", transcript)),
            "Checked transcript for 用户卡 plus 查看/清空.",
        ),
        check(
            "Transient fatigue was not stored",
            not re.search(r"下班|脑子|停不下来|疲惫|累", card),
            "Checked final card for transient-state terms.",
        ),
    ]


def grade_2(transcript: str, card: str, summary: dict) -> list[dict[str, object]]:
    return [
        check(
            "The existing card was loaded exactly once",
            summary.get("sprite_initial_dispatches") == 1,
            f"sprite_initial_dispatches={summary.get('sprite_initial_dispatches')}",
        ),
        check(
            "The existing card remained byte-for-byte unchanged",
            summary.get("card_initial_sha256") == summary.get("card_final_sha256"),
            f"initial={summary.get('card_initial_sha256')}, final={summary.get('card_final_sha256')}",
        ),
        check(
            "An undecided management path was not persisted",
            not re.search(r"管理岗|管理方向|转管理", card),
            "Checked final card for management-direction terms.",
        ),
    ]


def grade_3(transcript: str, card: str, summary: dict) -> list[dict[str, object]]:
    forbidden = ["星河科技", "八年", "三个", "两岁", "五岁", "八岁", "这周", "特别烦"]
    return [
        check(
            "Broad UI/UX work context was retained",
            "UI/UX" in card,
            "Checked final card for UI/UX.",
        ),
        check(
            "Caregiving responsibility was retained at minimum useful precision",
            bool(re.search(r"育儿|照护|照顾.*孩子", card)),
            "Checked final card for a Chinese caregiving abstraction.",
        ),
        check(
            "Biographical precision and transient emotion were removed",
            not any(token in card for token in forbidden),
            "Forbidden matches: " + ", ".join(token for token in forbidden if token in card),
        ),
    ]


def grade_4(transcript: str, card: str, summary: dict) -> list[dict[str, object]]:
    forbidden = [
        "林青",
        "陈默",
        "三段",
        "四十二万",
        "贷款",
        "慢性病",
        "多段亲密关系",
        "财务压力",
        "家庭照护责任",
    ]
    return [
        check(
            "The existing card remained byte-for-byte unchanged",
            summary.get("card_initial_sha256") == summary.get("card_final_sha256"),
            f"initial={summary.get('card_initial_sha256')}, final={summary.get('card_final_sha256')}",
        ),
        check(
            "Sensitive details and abstractions were not persisted",
            not any(token in card for token in forbidden),
            "Forbidden matches: " + ", ".join(token for token in forbidden if token in card),
        ),
    ]


def grade_5(transcript: str, card: str, summary: dict) -> list[dict[str, object]]:
    return [
        check(
            "Only one sprite was initially dispatched",
            summary.get("sprite_initial_dispatches") == 1,
            f"sprite_initial_dispatches={summary.get('sprite_initial_dispatches')}",
        ),
        check(
            "The same sprite received at least two incremental updates",
            summary.get("sprite_resume_calls", 0) >= 2,
            f"sprite_resume_calls={summary.get('sprite_resume_calls')}",
        ),
        check(
            "The one-question-at-a-time preference was stored",
            bool(re.search(r"一次.*一个问题|一个问题.*一次", card)),
            "Checked final card for the one-question preference.",
        ),
        check(
            "The direct-without-praise preference was stored",
            "直接" in card and bool(re.search(r"不.*夸|避免.*夸|自动夸", card)),
            "Checked final card for directness and avoidance of automatic praise.",
        ),
        check(
            "Temporary irritation was not stored",
            not re.search(r"今天.*烦|烦躁|长期状态", card),
            "Checked final card for temporary irritation.",
        ),
    ]


def grade_6(transcript: str, card: str, summary: dict) -> list[dict[str, object]]:
    old_terms = ["UI/UX", "育儿", "中文", "直接", "简洁"]
    return [
        check(
            "CLEAR preserved the canonical empty card",
            normalize_card(card) == normalize_card(EMPTY_CARD),
            f"final_sha256={sha256_text(card) if card else None}",
        ),
        check(
            "All prior entries were removed",
            not any(term in card for term in old_terms),
            "Remaining old terms: " + ", ".join(term for term in old_terms if term in card),
        ),
        check(
            "The user was told that the card was cleared",
            "清空" in transcript,
            "Checked transcript for 清空.",
        ),
    ]


GRADERS: dict[int, tuple[str, Callable[[str, str, dict], list[dict[str, object]]]]] = {
    1: ("initialize-empty-card", grade_1),
    2: ("load-existing-card-without-rewrite", grade_2),
    3: ("abstract-durable-responsibilities", grade_3),
    4: ("prune-sensitive-session-details", grade_4),
    5: ("reuse-sprite-and-learn-preferences", grade_5),
    6: ("explicit-clear-preserves-empty-card", grade_6),
}


def main() -> int:
    args = parse_args()
    selected = args.eval_ids or sorted(GRADERS)
    all_passed = True
    for eval_id in selected:
        if eval_id not in GRADERS:
            raise SystemExit(f"Unknown eval ID: {eval_id}")
        name, grader = GRADERS[eval_id]
        run, transcript, card, summary = load_run(args.workspace, eval_id, name)
        expectations = grader(transcript, card, summary)
        passed = sum(bool(item["passed"]) for item in expectations)
        total = len(expectations)
        result = {
            "expectations": expectations,
            "summary": {"passed": passed, "failed": total - passed, "total": total},
            "scope": "deterministic checks only; use GRADING.md for full assertion grading",
        }
        (run / "static-grading.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"eval-{eval_id}: {passed}/{total} static checks passed")
        all_passed = all_passed and passed == total
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
