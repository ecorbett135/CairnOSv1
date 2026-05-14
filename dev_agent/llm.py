# Copyright 2026 Eric Corbett
# SPDX-License-Identifier: Apache-2.0
from openai import OpenAI
import json

client = OpenAI()

SYSTEM_PROMPT = '''
You are maintaining CairnOS.

Focus on:
- hiking planner stability
- preserving streamlit compatibility
- keeping pytest passing

Return only unified diff patches.
'''

def call_llm(context):
    prompt = SYSTEM_PROMPT + "\n\n" + json.dumps(context)[:15000]

    response = client.responses.create(
        model="gpt-5.3",
        input=prompt,
    )

    return response.output_text
