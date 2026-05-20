import json
import re
import os
from openai import AzureOpenAI

client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

SYSTEM_PROMPT = """You are a professional fact-checker. Analyze the claim and respond ONLY with valid JSON.

Rules:
- "label" MUST be exactly one of: true, false, misleading, unverified
- "score" is an integer 0-100 representing credibility (100 = definitely true, 0 = definitely false)
- "summary" is a 1-2 sentence plain-English explanation of your verdict

Example response format (no markdown, no extra keys):
{"label": "true", "score": 87, "summary": "This claim is supported by historical records."}"""


def analyze(content):
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ]
    )

    text = response.choices[0].message.content.strip()

    try:
        # Remove ```json ``` markdown fences if present
        text = re.sub(r"```json|```", "", text).strip()

        parsed = json.loads(text)

        score_raw = parsed.get("score", 0)
        try:
            score = float(score_raw)
            if score <= 1.0:
                score = int(score * 100)
            else:
                score = int(score)
        except (TypeError, ValueError):
            score = 0

        return {
            "label": parsed.get("label", "unverified"),
            "score": score,
            "summary": parsed.get("summary", "No summary provided.")
        }

    except Exception as e:
        print("PARSE ERROR:", text)
        return {
            "label": "unverified",
            "score": 0,
            "summary": text
        }