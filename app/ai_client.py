# app/ai_client.py
"""
AI safety client.

Supports:
 - local heuristic scoring (default)
 - remote LLM scoring (LLM_PROVIDER=remote) using:
     - GEMINI_API_KEY (provided via Secret Manager binding)
     - LLM_API_URL (the model endpoint that accepts POST JSON)

This file is intentionally defensive and logs meaningful errors to make debugging easy.
"""

import os
import logging
import requests
import json
from typing import Tuple, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").lower()
LLM_API_URL = os.getenv("LLM_API_URL", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()


def _heuristic_score(url: str, text: str) -> float:
    score = 0.2
    url_lower = (url or "").lower()
    text_lower = (text or "").lower()

    suspicious_keywords = ['login', 'verify', 'account', 'update', 'bank', 'secure', 'confirm', 'password', 'signin', 'ssn', 'credit']
    for kw in suspicious_keywords:
        if kw in url_lower:
            score += 0.15
        if kw in text_lower:
            score += 0.1

    suspicious_tlds = ['.ru', '.cn', '.tk']
    for tld in suspicious_tlds:
        if url_lower.endswith(tld) or ('.' + tld) in url_lower:
            score += 0.15

    if not text or not text.strip():
        score += 0.2

    return min(max(score, 0.0), 1.0)


def _parse_model_response_text(text: str) -> Optional[Tuple[float, str, str]]:
    if not text:
        return None
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            blob = text[start:end+1]
            data = json.loads(blob)
            score = float(data.get('score', 0.5))
            label = str(data.get('label', 'medium_risk'))
            explanation = str(data.get('explanation', '') or '')
            return score, label, explanation
    except Exception as e:
        logger.debug("Failed to parse JSON from model text: %s ; error: %s", text[:300], e)
    return None


def _call_remote_model_generate_content(url: str, page_text: str) -> Optional[Tuple[float, str, str]]:
    """
    Call v1beta generateContent (Gemini) and try to parse a JSON blob from the candidate text.
    Returns (score, label, explanation) or None.
    """
    if not LLM_API_URL or not GEMINI_API_KEY:
        raise RuntimeError("Remote LLM configured but LLM_API_URL or GEMINI_API_KEY missing")

    prompt_text = (
        "You are a URL safety assistant. Return EXACTLY one valid JSON object and nothing else, with fields: "
        "score (0.0-1.0), label (low_risk|medium_risk|high_risk), explanation (short). "
        "Example: {\"score\":0.12,\"label\":\"low_risk\",\"explanation\":\"domain safe\"}\n\n"
        f"URL: {url}\n\nPAGE_SNIPPET: {(page_text or '')[:1200]}\n\nJSON:"
    )

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ]
    }

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(LLM_API_URL, json=body, headers=headers, timeout=25)
    except Exception as e:
        logger.exception("HTTP request to LLM endpoint failed: %s", e)
        raise

    # record status for debugging
    status = resp.status_code
    text = resp.text or ""
    logger.info("LLM response status=%s length=%d", status, len(text))

    if status != 200:
        # log body for debugging, but avoid logging keys; safe because resp is model result not secret
        logger.warning("LLM non-200 response: %s ; body=%s", status, text[:1000])
        # raise an HTTPError so outer caller can treat as failure and fallback
        resp.raise_for_status()

    # parse expected candidate shape
    try:
        data = resp.json()
    except Exception:
        # if not JSON at top-level, try to parse text for a JSON blob
        logger.debug("LLM top-level JSON parse failed; trying to parse response text")
        parsed = _parse_model_response_text(text)
        if parsed:
            return parsed
        logger.warning("LLM returned non-JSON and no parseable JSON found in text.")
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        logger.debug("LLM response contains no candidates; raw=%s", text[:800])
        # attempt text parse as last resort
        parsed = _parse_model_response_text(text)
        return parsed

    # join parts to model_text
    try:
        content = candidates[0].get("content", {}) or {}
        parts = content.get("parts") or []
        model_text = ""
        for p in parts:
            if isinstance(p, dict):
                model_text += p.get("text", "")
            elif isinstance(p, str):
                model_text += p
        parsed = _parse_model_response_text(model_text)
        if parsed:
            return parsed
        # keyword fallback
        lower = model_text.lower()
        if "high risk" in lower or "high_risk" in lower:
            return 0.9, "high_risk", model_text[:400]
        if "medium" in lower:
            return 0.5, "medium_risk", model_text[:400]
        if "low" in lower:
            return 0.1, "low_risk", model_text[:400]
    except Exception as e:
        logger.exception("Error processing LLM candidate content: %s", e)
        return None

    logger.debug("No usable result from LLM response.")
    return None


def call_safety(url: str, page_text: str) -> Tuple[float, str, str]:
    # local fallback
    if LLM_PROVIDER != 'remote':
        score = round(_heuristic_score(url, page_text), 3)
        if score >= 0.7:
            label = 'high_risk'
        elif score >= 0.4:
            label = 'medium_risk'
        else:
            label = 'low_risk'
        explanation = f'heuristic score={score}.'
        return float(score), label, explanation

    # remote path
    try:
        result = _call_remote_model_generate_content(url, page_text)
        if result:
            score, label, explanation = result
            return float(round(score, 3)), label, explanation
    except requests.exceptions.HTTPError as e:
        logger.warning("Remote model HTTP error, will fallback: %s", e)
    except Exception as e:
        logger.warning("Remote model unexpected error, will fallback: %s", e)

    # fallback heuristic
    score = round(_heuristic_score(url, page_text), 3)
    if score >= 0.7:
        label = 'high_risk'
    elif score >= 0.4:
        label = 'medium_risk'
    else:
        label = 'low_risk'
    explanation = f'fallback heuristic score={score}.'
    return float(score), label, explanation
