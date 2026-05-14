# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import subprocess
import tempfile

def apply_patch(patch_text):
    with tempfile.NamedTemporaryFile(
        suffix=".diff",
        mode="w",
        delete=False,
    ) as f:
        f.write(patch_text)
        temp_path = f.name

    subprocess.run(["git", "apply", temp_path])
