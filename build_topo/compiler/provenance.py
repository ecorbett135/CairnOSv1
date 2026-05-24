# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path


def project_root_for_trail(trail_root):
    trail_root = Path(
        trail_root
    ).resolve()

    if (
        trail_root.parent.name == "trails"
        and trail_root.parent.parent != trail_root.parent
    ):
        return trail_root.parent.parent

    return trail_root.parent


def repo_relative_path(path, trail_root):
    path = Path(
        path
    ).resolve()

    project_root = project_root_for_trail(
        trail_root
    )

    try:
        return path.relative_to(
            project_root
        ).as_posix()
    except ValueError:
        return path.name
