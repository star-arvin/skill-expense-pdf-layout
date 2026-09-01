"""Command-line orchestration for portable document layout."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import yaml

from .classify import classify_paths
from .inspect import SUPPORTED_EXTENSIONS
from .manifest import manifest_dict
from .models import ClassifiedPage, DocumentType, ProcessingError, RenderMode
from .plan import build_layout_plan
from .render import render_plan


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify reimbursement materials and create a print-safe A4 PDF."
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument(
        "--render-mode",
        choices=[mode.value for mode in RenderMode],
        default=RenderMode.AUTO.value,
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _discover(input_dir: Path) -> tuple[Path, ...]:
    if not input_dir.is_dir():
        raise ProcessingError("input directory does not exist")
    files = tuple(
        sorted(
            (path for path in input_dir.iterdir() if path.is_file() and not path.name.startswith(".")),
            key=lambda path: path.name.casefold(),
        )
    )
    unsupported = [path.name for path in files if path.suffix.casefold() not in SUPPORTED_EXTENSIONS]
    if unsupported:
        raise UnsupportedInputError(f"unsupported input: {', '.join(unsupported)}")
    if not files:
        raise UnsupportedInputError("no supported documents found")
    return files


class UnsupportedInputError(ProcessingError):
    pass


def _load_overrides(config: Path | None) -> dict[str, DocumentType]:
    if config is None:
        return {}
    try:
        payload = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ProcessingError(f"invalid configuration: {config.name}") from exc
    raw_overrides = payload.get("type_overrides", {})
    if not isinstance(raw_overrides, dict):
        raise ProcessingError("type_overrides must be a mapping")
    try:
        return {str(filename): DocumentType(str(value)) for filename, value in raw_overrides.items()}
    except ValueError as exc:
        raise ProcessingError("configuration contains an unknown document type") from exc


def _apply_overrides(
    documents: tuple[ClassifiedPage, ...],
    overrides: dict[str, DocumentType],
) -> tuple[ClassifiedPage, ...]:
    return tuple(
        replace(
            document,
            document_type=overrides[document.page.source.name],
            confidence=1.0,
            evidence=("config:type-override",),
        )
        if document.page.source.name in overrides
        else document
        for document in documents
    )


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output: Path = args.output
    manifest: Path = args.manifest or output.with_name(f"{output.stem}.manifest.json")

    if not args.overwrite and (output.exists() or manifest.exists()):
        print("error: output already exists", file=sys.stderr)
        return 2

    try:
        paths = _discover(args.input_dir)
        documents = _apply_overrides(classify_paths(paths), _load_overrides(args.config))
        unclassified = [
            document.page.source.name
            for document in documents
            if document.document_type is DocumentType.UNCLASSIFIED
        ]
        if unclassified:
            print(f"error: unclassified input: {', '.join(unclassified)}", file=sys.stderr)
            return 3
        plan = build_layout_plan(documents, RenderMode(args.render_mode))
        if args.dry_run:
            payload = manifest_dict(plan, output)
            payload["dry_run"] = True
            _print_json(payload)
            return 0
        payload = render_plan(
            plan,
            output,
            manifest,
            dpi=args.dpi,
            overwrite=args.overwrite,
        )
        payload["dry_run"] = False
        _print_json(payload)
        return 0
    except UnsupportedInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except ProcessingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

