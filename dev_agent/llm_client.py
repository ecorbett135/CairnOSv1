# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
import json
import os
from openai import OpenAI

SYSTEM_PROMPT = """
You are maintaining CairnOS.

Rules:
- Preserve planner behavior
- Preserve overnight semantics
- Preserve traversal semantics
- Preserve passing tests
- Preserve scenario validity
- Prefer minimal edits
- Never include markdown fences
- Never explain changes

Return ONLY valid JSON.

Schema:

{
  "operations": [
    {
      "file": "path/to/file.py",
      "search": "exact text",
      "replace": "new text"
    }
  ]
}
"""

def generate_operations(context):

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not set."
        )

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": context,
            },
        ],
    )

    raw = response.output_text.strip()

    return json.loads(raw)
