# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import json
import shutil

from build_topo.compiler.candidate_drift import is_candidate_run_root
from build_topo.compiler.candidates import compute_file_sha256
from build_topo.compiler.promotion_readiness import build_promotion_readiness
from build_topo.compiler.provenance import repo_relative_path


PROMOTION_FORMAT = "cairnos_build_topo_candidate_promotion_v1"
PROMOTION_REPORT_NAME = "candidate_promotion_report.json"
DRIFT_REPORT_NAME = "candidate_drift_report.json"
REPORT_NAME = "candidate_report.json"


def _infer_trail_root(candidate_root):
    candidate_root = Path(
        candidate_root
    ).resolve()

    if candidate_root.parent.name == "candidate":
        return candidate_root.parent.parent

    return candidate_root.parent


def _load_json_object(path, label):
    path = Path(
        path
    )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )
    except FileNotFoundError:
        return None, f"{label} is missing."
    except json.JSONDecodeError as exc:
        return None, f"{label} could not be parsed: {exc}"

    if not isinstance(
        payload,
        dict,
    ):
        return None, f"{label} must contain a JSON object."

    return payload, None


def _candidate_root_label(candidate_root, trail_root):
    return repo_relative_path(
        candidate_root,
        trail_root,
    )


def _snapshot_root(trail_root, promotion_id):
    return (
        Path(trail_root) /
        "promotion_snapshots" /
        promotion_id
    )


def _promotion_report_path(candidate_root):
    return (
        Path(candidate_root) /
        PROMOTION_REPORT_NAME
    )


def _default_promotion_id(candidate_root):
    timestamp = datetime.now(
        timezone.utc,
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    return f"{timestamp}-{Path(candidate_root).name}"


def _valid_promotion_id(promotion_id):
    return (
        promotion_id not in {"", ".", ".."}
        and "/" not in promotion_id
        and "\\" not in promotion_id
    )


def _relative_artifact_path(relative_path):
    if not isinstance(
        relative_path,
        str,
    ):
        return None

    path = PurePosixPath(
        relative_path
    )

    if (
        path.is_absolute()
        or not path.parts
        or path.parts[0] != "compiled"
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        return None

    return Path(
        *path.parts
    )


def _is_relative_to(path, root):
    try:
        Path(path).resolve().relative_to(
            Path(root).resolve()
        )
        return True
    except ValueError:
        return False


def _artifact_paths(candidate_root, trail_root, artifact):
    relative = _relative_artifact_path(
        artifact.get(
            "relative_path"
        )
    )

    if relative is None:
        return None, None, None

    candidate_path = (
        Path(candidate_root) /
        relative
    )
    promoted_path = (
        Path(trail_root) /
        relative
    )
    promoted_root = (
        Path(trail_root) /
        "compiled"
    )

    if not _is_relative_to(
        candidate_path,
        candidate_root,
    ) or not _is_relative_to(
        promoted_path,
        promoted_root,
    ):
        return None, None, None

    return relative.as_posix(), candidate_path, promoted_path


def _current_summary(path):
    path = Path(
        path
    )

    if not path.exists():
        return None

    return {
        "bytes": path.stat().st_size,
        "sha256": compute_file_sha256(
            path
        ),
    }


def _summary_matches(expected, actual):
    if expected is None or actual is None:
        return expected is actual

    return (
        expected.get("sha256") == actual.get("sha256")
        and expected.get("bytes") == actual.get("bytes")
    )


def _artifact_operations(candidate_root, trail_root, candidate_report):
    copy_items = []
    skipped_items = []
    blockers = []

    for artifact in candidate_report.get(
        "artifacts",
        [],
    ):
        relative_path, candidate_path, promoted_path = _artifact_paths(
            candidate_root,
            trail_root,
            artifact,
        )

        if relative_path is None:
            blockers.append(
                f"unsafe artifact path: {artifact.get('relative_path')}"
            )
            continue

        candidate_present = bool(
            artifact.get(
                "candidate_present",
                False,
            )
        )
        promoted_present = bool(
            artifact.get(
                "promoted_present",
                False,
            )
        )
        candidate_summary = _current_summary(
            candidate_path
        )
        promoted_summary = _current_summary(
            promoted_path
        )

        if candidate_present and candidate_summary is None:
            blockers.append(
                f"{relative_path} is marked candidate_present but is missing."
            )
            continue

        if not candidate_present and candidate_summary is not None:
            blockers.append(
                f"{relative_path} is marked absent but exists in candidate output."
            )
            continue

        if promoted_present and promoted_summary is None:
            blockers.append(
                f"{relative_path} is marked promoted_present but is missing."
            )
            continue

        if not promoted_present and promoted_summary is not None:
            blockers.append(
                f"{relative_path} is marked not promoted but exists in compiled/."
            )
            continue

        if candidate_present and not _summary_matches(
            artifact.get(
                "candidate"
            ),
            candidate_summary,
        ):
            blockers.append(
                f"{relative_path} hash does not match candidate_report.json."
            )
            continue

        if promoted_present and not _summary_matches(
            artifact.get(
                "promoted"
            ),
            promoted_summary,
        ):
            blockers.append(
                f"{relative_path} promoted hash does not match candidate_report.json."
            )
            continue

        item = {
            "relative_path": relative_path,
            "candidate_path": candidate_path,
            "promoted_path": promoted_path,
        }

        if candidate_present:
            copy_items.append(
                item
            )
        else:
            skipped_items.append(
                {
                    "relative_path": relative_path,
                    "reason": (
                        "candidate artifact absent; promoted file is left "
                        "unchanged"
                    ),
                }
            )

    return copy_items, skipped_items, blockers


def _snapshot_compiled(trail_root, snapshot_root):
    compiled_root = (
        Path(trail_root) /
        "compiled"
    )

    if not compiled_root.exists():
        return []

    target = (
        Path(snapshot_root) /
        "compiled"
    )

    shutil.copytree(
        compiled_root,
        target,
    )

    return [
        repo_relative_path(
            path,
            trail_root,
        )
        for path in sorted(
            target.glob("**/*")
        )
        if path.is_file()
    ]


def _copy_artifacts(copy_items, trail_root):
    copied = []

    for item in copy_items:
        destination = item["promoted_path"]
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copy2(
            item["candidate_path"],
            destination,
        )
        copied.append(
            {
                "relative_path": item["relative_path"],
                "source": repo_relative_path(
                    item["candidate_path"],
                    trail_root,
                ),
                "destination": repo_relative_path(
                    destination,
                    trail_root,
                ),
                "sha256": compute_file_sha256(
                    destination,
                ),
            }
        )

    return copied


def _verify_copied_hashes(copy_items):
    blockers = []

    for item in copy_items:
        source_hash = compute_file_sha256(
            item["candidate_path"]
        )
        destination_hash = compute_file_sha256(
            item["promoted_path"]
        )

        if source_hash != destination_hash:
            blockers.append(
                (
                    f"{item['relative_path']} copied hash does not match "
                    "candidate artifact."
                )
            )

    return blockers


def _report(
    *,
    status,
    candidate_root,
    trail_root,
    promotion_id,
    snapshot_root,
    dry_run,
    copied=None,
    skipped=None,
    snapshotted=None,
    blockers=None,
):
    copied = list(
        copied or []
    )
    skipped = list(
        skipped or []
    )
    snapshotted = list(
        snapshotted or []
    )
    blockers = list(
        blockers or []
    )

    return {
        "format": PROMOTION_FORMAT,
        "status": status,
        "dry_run": dry_run,
        "promotion_id": promotion_id,
        "candidate_root": _candidate_root_label(
            candidate_root,
            trail_root,
        ),
        "promoted_root": repo_relative_path(
            Path(trail_root) / "compiled",
            trail_root,
        ),
        "snapshot_root": repo_relative_path(
            snapshot_root,
            trail_root,
        ),
        "candidate_report": REPORT_NAME,
        "candidate_drift_report": DRIFT_REPORT_NAME,
        "promotion_report": PROMOTION_REPORT_NAME,
        "summary": {
            "copied": len(
                copied
            ),
            "skipped": len(
                skipped
            ),
            "snapshotted": len(
                snapshotted
            ),
        },
        "copied": copied,
        "skipped": skipped,
        "snapshotted": snapshotted,
        "blockers": blockers,
    }


def _write_promotion_report(candidate_root, report):
    path = _promotion_report_path(
        candidate_root
    )
    path.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return path


def promote_candidate_artifacts(
    candidate_root,
    *,
    promotion_id=None,
    accept_drift=False,
    dry_run=False,
):
    candidate_root = Path(
        candidate_root
    ).resolve()
    trail_root = _infer_trail_root(
        candidate_root
    )
    promotion_id = (
        str(promotion_id)
        if promotion_id is not None
        else _default_promotion_id(
            candidate_root
        )
    )
    snapshot_root = _snapshot_root(
        trail_root,
        promotion_id,
    )
    blockers = []

    if not is_candidate_run_root(
        candidate_root
    ):
        blockers.append(
            "candidate_root must be trails/<trail>/candidate/<run_id>."
        )

    if not _valid_promotion_id(
        promotion_id
    ):
        blockers.append(
            "promotion_id must be a non-empty directory name without path separators."
        )

    if snapshot_root.exists():
        blockers.append(
            (
                "promotion snapshot already exists: "
                f"{repo_relative_path(snapshot_root, trail_root)}"
            )
        )

    if not dry_run and _promotion_report_path(
        candidate_root
    ).exists():
        blockers.append(
            f"{PROMOTION_REPORT_NAME} already exists."
        )

    candidate_report, candidate_error = _load_json_object(
        candidate_root / REPORT_NAME,
        REPORT_NAME,
    )
    drift_report, drift_error = _load_json_object(
        candidate_root / DRIFT_REPORT_NAME,
        DRIFT_REPORT_NAME,
    )
    readiness = build_promotion_readiness(
        candidate_root
    )

    if candidate_error:
        blockers.append(
            candidate_error
        )

    if drift_error:
        blockers.append(
            drift_error
        )

    if readiness.get(
        "status"
    ) != "ready":
        blockers.append(
            f"promotion readiness is {readiness.get('status')}."
        )

    if drift_report is not None:
        drift_status = drift_report.get(
            "status"
        )

        if drift_status == "blocked":
            blockers.append(
                "candidate_drift_report.json status is blocked."
            )
        elif drift_status == "review_required" and not accept_drift:
            blockers.append(
                "candidate drift requires review; use --accept-drift after review."
            )
        elif drift_status not in {"no_drift", "review_required"}:
            blockers.append(
                f"candidate_drift_report.json status is {drift_status}."
            )

    copy_items = []
    skipped = []

    if candidate_report is not None:
        copy_items, skipped, operation_blockers = _artifact_operations(
            candidate_root,
            trail_root,
            candidate_report,
        )
        blockers.extend(
            operation_blockers
        )

    if blockers:
        return _report(
            status="blocked",
            candidate_root=candidate_root,
            trail_root=trail_root,
            promotion_id=promotion_id,
            snapshot_root=snapshot_root,
            dry_run=dry_run,
            skipped=skipped,
            blockers=blockers,
        )

    if dry_run:
        return _report(
            status="ready",
            candidate_root=candidate_root,
            trail_root=trail_root,
            promotion_id=promotion_id,
            snapshot_root=snapshot_root,
            dry_run=True,
            skipped=skipped,
            copied=[
                {
                    "relative_path": item["relative_path"],
                }
                for item in copy_items
            ],
        )

    snapshotted = _snapshot_compiled(
        trail_root,
        snapshot_root,
    )
    copied = _copy_artifacts(
        copy_items,
        trail_root,
    )
    copy_blockers = _verify_copied_hashes(
        copy_items
    )

    status = (
        "blocked"
        if copy_blockers
        else "promoted"
    )
    report = _report(
        status=status,
        candidate_root=candidate_root,
        trail_root=trail_root,
        promotion_id=promotion_id,
        snapshot_root=snapshot_root,
        dry_run=False,
        copied=copied,
        skipped=skipped,
        snapshotted=snapshotted,
        blockers=copy_blockers,
    )
    _write_promotion_report(
        candidate_root,
        report,
    )

    return report
