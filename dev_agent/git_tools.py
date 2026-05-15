# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import subprocess


def ensure_clean_git():

    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
        ],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():

        raise RuntimeError(
            "Working tree not clean. "
            "Commit or restore changes "
            "before running dev agent."
        )


def create_restore_point():

    #
    # no-op now
    #
    # git commit is the restore point
    #

    return


def restore_git():

    subprocess.run(
        [
            "git",
            "reset",
            "--hard",
            "HEAD",
        ]
    )

    subprocess.run(
        [
            "git",
            "clean",
            "-fd",
        ]
    )

    print(
        "Hard git restore executed."
    )
