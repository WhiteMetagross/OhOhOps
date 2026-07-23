"""Transactional patch application with automatic rollback."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PatchTransaction:
    target: Path
    backup: Path
    existed: bool


def resolve_target(project_path: str, target_file: str) -> Path:
    project = Path(project_path).resolve()
    if not project.is_dir():
        raise ValueError(f"Project directory not found: {project_path}")
    if not target_file.strip():
        raise ValueError("Patch target is required")

    requested = Path(target_file)
    candidate = requested.resolve() if requested.is_absolute() else (project / requested).resolve()
    if os.path.commonpath((str(project), str(candidate))) != str(project):
        raise ValueError("Patch target escapes project directory")
    if candidate.exists() and not candidate.is_file():
        raise ValueError("Patch target must be a file")

    if not candidate.exists():
        matches = [
            path.resolve()
            for path in project.rglob(requested.name)
            if path.is_file()
        ]
        if len(matches) != 1:
            raise FileNotFoundError(
                f"Expected one target named {requested.name}, found {len(matches)}"
            )
        candidate = matches[0]
    return candidate


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def apply_patch_transaction(
    project_path: str,
    target_file: str,
    patch_code: str,
) -> PatchTransaction:
    target = resolve_target(project_path, target_file)
    backup = target.with_name(f".{target.name}.ohohops.bak")
    existed = target.exists()
    if existed:
        shutil.copy2(target, backup)
    _atomic_write(target, patch_code)
    return PatchTransaction(target=target, backup=backup, existed=existed)


def rollback_patch(transaction: PatchTransaction) -> None:
    if transaction.existed:
        if not transaction.backup.exists():
            raise FileNotFoundError(f"Rollback backup missing: {transaction.backup}")
        os.replace(transaction.backup, transaction.target)
    else:
        transaction.target.unlink(missing_ok=True)
        transaction.backup.unlink(missing_ok=True)


def finalize_patch(transaction: PatchTransaction) -> None:
    transaction.backup.unlink(missing_ok=True)
