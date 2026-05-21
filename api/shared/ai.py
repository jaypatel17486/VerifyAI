import json
import re
import os
from openai import AzureOpenAI, OpenAI

def get_client():
    """Get the appropriate OpenAI client based on configured environment variables."""
    openai_key = os.getenv("OPENAI_API_KEY")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    if openai_key:
        print("Using standard OpenAI API")
        return OpenAI(api_key=openai_key)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview")
    if azure_key and endpoint:
        print("Using Azure OpenAI API")
        print("AzureOpenAI client configuration: endpoint=", endpoint)
        print("AzureOpenAI client configuration: deployment=", os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"))
        return AzureOpenAI(
            api_key=azure_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )

    raise ValueError(
        "OpenAI credentials not configured. Set OPENAI_API_KEY for standard OpenAI, or AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT for Azure OpenAI."
    )

FACT_CHECK_SYSTEM = """You are a professional fact-checker and investigative journalist.
Analyze the provided claim or article and return ONLY valid JSON (no markdown fences) with these exact keys:
- "label": one of "TRUE", "FALSE", "MISLEADING", or "UNVERIFIABLE"
- "score": integer 0-100 (credibility; 100 = fully credible, 0 = completely false)
- "summary": 2-3 sentence plain-English verdict
- "research": 3-5 sentences of supporting evidence, context, and reasoning"""

IMAGE_ANALYSIS_SYSTEM = """You are an expert image forensics analyst specializing in detecting
AI-generated, manipulated, or altered images.
Analyze the provided image and return ONLY valid JSON (no markdown fences) with these exact keys:
- "label": one of "AUTHENTIC", "MANIPULATED", "AI_GENERATED", or "SUSPICIOUS"
- "score": integer 0-100 (authenticity; 100 = definitely authentic, 0 = definitely fake)
- "summary": 2-3 sentence description of your findings
- "forensics": object with integer keys "elaScore", "noiseAnalysis", "compressionArtifacts" (0-100, higher = more consistent with authentic)
- "metadata": object with string keys "location", "date", "camera", "resolution" (use "Unknown" if unavailable)"""


def _parse(text):
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


def get_model_name():
    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_MODEL", "gpt-4o")
    return os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")


def analyze(content):
    """Fact-check a text claim or article content."""
    try:
        client = get_client()
        model_name = get_model_name()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": FACT_CHECK_SYSTEM},
                {"role": "user", "content": f"Analyze this claim or article:\n\n{content}"}
            ]
        )
        parsed = _parse(resp.choices[0].message.content.strip())
        return {
            "label": parsed.get("label", "UNVERIFIABLE"),
            "score": int(parsed.get("score", 50)),
            "summary": parsed.get("summary", ""),
            "research": parsed.get("research", "")
        }
    except Exception as e:
        error_msg = str(e)
        if "DeploymentNotFound" in error_msg:
            error_msg = (
                "Azure deployment not found. Check AZURE_OPENAI_DEPLOYMENT_NAME and verify the deployment exists "
                f"on your Azure OpenAI resource {os.getenv('AZURE_OPENAI_ENDPOINT')}.")
        print(f"analyze error: {error_msg}")
        return {"label": "ERROR", "score": 0, "summary": error_msg, "research": ""}


def analyze_image(image_b64, mime_type="image/jpeg"):
    """Analyze an image for authenticity and manipulation using GPT-4o vision."""
    try:
        client = get_client()
        model_name = get_model_name()
        resp = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": IMAGE_ANALYSIS_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}
                        },
                        {"type": "text", "text": "Analyze this image for authenticity, AI generation, and manipulation."}
                    ]
                }
            ]
        )
        parsed = _parse(resp.choices[0].message.content.strip())
        return {
            "label": parsed.get("label", "SUSPICIOUS"),
            "score": int(parsed.get("score", 50)),
            "summary": parsed.get("summary", ""),
            "forensics": parsed.get("forensics", {"elaScore": 50, "noiseAnalysis": 50, "compressionArtifacts": 50}),
            "metadata": parsed.get("metadata", {"location": "Unknown", "date": "Unknown", "camera": "Unknown", "resolution": "Unknown"})
        }
    except Exception as e:
        error_msg = str(e)
        if "DeploymentNotFound" in error_msg:
            error_msg = (
                "Azure deployment not found. Check AZURE_OPENAI_DEPLOYMENT_NAME and verify the deployment exists "
                f"on your Azure OpenAI resource {os.getenv('AZURE_OPENAI_ENDPOINT')}.")
        print(f"analyze_image error: {error_msg}")
        return {
            "label": "ERROR", "score": 0, "summary": error_msg,
            "forensics": {"elaScore": 0, "noiseAnalysis": 0, "compressionArtifacts": 0},
            "metadata": {"location": "Unknown", "date": "Unknown", "camera": "Unknown", "resolution": "Unknown"}
        }
