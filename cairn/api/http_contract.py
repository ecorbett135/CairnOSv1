# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
"""Shared HTTP contract helpers for CairnOS API adapters."""

from __future__ import annotations

import os


DEFAULT_MAX_BODY_BYTES = 32768
NO_STORE_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
}
JSON_HEADERS = {
    "content-type": "application/json",
    **NO_STORE_HEADERS,
}


def max_body_bytes() -> int:
    try:
        configured = int(
            os.environ.get("CAIRNOS_API_MAX_BODY_BYTES", DEFAULT_MAX_BODY_BYTES)
        )
    except ValueError:
        return DEFAULT_MAX_BODY_BYTES
    if configured <= 0:
        return DEFAULT_MAX_BODY_BYTES
    return configured
