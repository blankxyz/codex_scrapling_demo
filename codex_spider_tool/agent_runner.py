from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render(template_path: Path, mapping: dict[str, str]) -> str:
    content = _load_text(template_path)
    for k, v in mapping.items():
        content = content.replace("{{" + k + "}}", v)
    return content


def _run_codex(prompt: str, workdir: Path, model: str | None, log_file: Path) -> int:
    cmd = [
        "codex",
        "exec",
        "--full-auto",
        "--sandbox",
        "workspace-write",
        "-C",
        str(workdir),
        "-o",
        str(log_file),
        "-",
    ]
    if model:
        cmd.extend(["-m", model])
    proc = subprocess.run(cmd, input=prompt, text=True)
    return proc.returncode


def _load_validation(path: Path) -> dict:
    if not path.exists():
        return {"ok": False, "notes": f"validation file not found: {path}"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "notes": f"failed to parse validation.json: {exc}"}


def _validation_summary(obj: dict) -> str:
    try:
        return json.dumps(
            {
                "ok": obj.get("ok"),
                "missing_fields": obj.get("missing_fields", []),
                "sample_url": obj.get("sample_url", ""),
                "notes": obj.get("notes", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception:
        return str(obj)


def run_agent(
    site_slug: str,
    list_url: str,
    template_json: str,
    workdir: Path,
    model: str | None,
    max_repair_rounds: int,
) -> int:
    out_dir = workdir / "out" / site_slug
    logs_dir = out_dir / "agent_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    common = {
        "SITE_SLUG": site_slug,
        "LIST_URL": list_url,
        "TEMPLATE_JSON": template_json,
    }

    stages = [
        ("analyze", Path("prompts/agent/analyze.md")),
        ("generate", Path("prompts/agent/generate.md")),
    ]

    for stage_name, tpl in stages:
        prompt = _render(workdir / tpl, common)
        rc = _run_codex(prompt, workdir, model, logs_dir / f"{stage_name}.txt")
        if rc != 0:
            return rc

    validation_tpl = workdir / "prompts/agent/validate.md"
    repair_tpl = workdir / "prompts/agent/repair.md"
    validation_file = out_dir / "validation.json"

    for round_idx in range(0, max_repair_rounds + 1):
        v_prompt = _render(validation_tpl, common)
        v_log = logs_dir / f"validate_round_{round_idx}.txt"
        rc = _run_codex(v_prompt, workdir, model, v_log)
        if rc != 0:
            # Keep going; rely on validation.json if created.
            pass

        report = _load_validation(validation_file)
        if bool(report.get("ok")):
            print(json.dumps({"ok": True, "site_slug": site_slug, "rounds": round_idx}, ensure_ascii=False))
            return 0

        if round_idx >= max_repair_rounds:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "site_slug": site_slug,
                        "rounds": round_idx,
                        "reason": "max repair rounds reached",
                        "validation": report,
                    },
                    ensure_ascii=False,
                )
            )
            return 2

        summary = _validation_summary(report)
        repair_prompt = _render(
            repair_tpl,
            {
                **common,
                "VALIDATION_SUMMARY": summary,
            },
        )
        r_log = logs_dir / f"repair_round_{round_idx}.txt"
        rc = _run_codex(repair_prompt, workdir, model, r_log)
        if rc != 0:
            return rc

    return 2


def main() -> int:
    p = argparse.ArgumentParser(description="Agent-style Codex workflow for spider authoring")
    p.add_argument("--site-slug", required=True)
    p.add_argument("--list-url", required=True)
    p.add_argument("--template-json", required=True)
    p.add_argument("--workdir", default=".")
    p.add_argument("--model")
    p.add_argument("--max-repair-rounds", type=int, default=2)
    args = p.parse_args()

    return run_agent(
        site_slug=args.site_slug,
        list_url=args.list_url,
        template_json=args.template_json,
        workdir=Path(args.workdir).resolve(),
        model=args.model,
        max_repair_rounds=args.max_repair_rounds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
