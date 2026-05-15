# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import subprocess

def run_pytest():

    result = subprocess.run(
        [
            "pytest",
            "-v",
        ],
        capture_output=True,
        text=True,
    )

    return {
        "passed":
            result.returncode == 0,
        "output":
            result.stdout + result.stderr,
    }

def run_scenarios():

    result = subprocess.run(
        [
            "python",
            "dev.py",
        ],
        capture_output=True,
        text=True,
    )

    return {
        "passed":
            result.returncode == 0,
        "output":
            result.stdout + result.stderr,
    }
