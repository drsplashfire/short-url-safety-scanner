# app/ai_client.py
"""
AI safety client.

Supports:
 - local heuristic scoring (default)
 - remote LLM scoring (LLM_PROVIDER=remote) using:
     - GEMINI_API_KEY (provided via Secret Manager binding)
     - LLM_API_URL (the model endpoint that accepts POST JSON)

Notes:
 - LLM_API_URL should be set to the REST endpoint your model exposes.
 - This client is defensive: if the remote call fails or returns unexpected data,
   it falls back to the local heuristic.
"""

import os
import logging
import requests
import json
from typing import Tuple

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


def _parse_model_response_text(text: str) -> Tuple[float, str, str]:
    """
    Try to parse model output for a JSON-like payload. The model prompt
    asks for JSON: {"score":0.xx,"label":"...","explanation":"..."}.
    If parsing fails, return None to indicate fallback is needed.
    """
    if not text:
        return None
    # try to find first JSON object in the text
    try:
        # naive: find first '{' and '}' and parse
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
        logger.warning("Failed to parse model JSON from text: %s ; error: %s", text[:400], e)
    return None


def _call_remote_model(url: str, page_text: str) -> Tuple[float, str, str]:
    """
    Calls the remote LLM endpoint (user-specified). This function assumes:
     - LLM_API_URL is a full URL accepting POST with JSON payload
     - Authorization via Bearer token with GEMINI_API_KEY

    The prompt asks the model to return a small JSON object. Because different
    endpoints differ, the model may return plain text — attempt to parse JSON.
    """
    if not LLM_API_URL or not GEMINI_API_KEY:
        raise RuntimeError("Remote LLM configured but LLM_API_URL or GEMINI_API_KEY missing")

    payload = {
        "url": url,
        "text": (page_text or "")[:20000],  # truncate to reasonable length
        "instructions": (
            "Return a JSON object only, with fields: score (0.0-1.0), "
            "label (one of low_risk|medium_risk|high_risk), and explanation (short). "
            "Example output: {\"score\":0.13,\"label\":\"low_risk\",\"explanation\":\"...\"}"
        )
    }

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(LLM_API_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        resp_text = resp.text
        # Some endpoints return JSON; others return text. Try JSON first.
        try:
            data = resp.json()
            # Look for fields in common shapes: either direct {'score':...} or {'candidates':[{'content':...}]}
            if isinstance(data, dict):
                if 'score' in data or 'label' in data:
                    score = float(data.get('score', 0.5))
                    label = data.get('label', 'medium_risk')
                    explanation = data.get('explanation', '') or ''
                    return score, label, explanation
                # try nested content fields
                candidate_text = None
                # some providers return {'candidates': [{'content': '...'}]}
                if 'candidates' in data and isinstance(data['candidates'], list) and data['candidates']:
                    candidate_text = data['candidates'][0].get('content')
                # some providers return {'output': '...'} etc.
                if not candidate_text:
                    # attempt to stringify and parse text
                    candidate_text = json.dumps(data)
                parsed = _parse_model_response_text(candidate_text)
                if parsed:
                    return parsed
        except ValueError:
            # not JSON, fall through to parse resp.text
            pass

        parsed = _parse_model_response_text(resp_text)
        if parsed:
            return parsed

        # If parsing failed, as a final fallback, run a lightweight heuristic score to avoid blocking
        logger.warning("Model response returned no parsable JSON; falling back to heuristic")
        return None
    except Exception as e:
        logger.exception("Remote model call failed: %s", e)
        raise


def call_safety(url: str, page_text: str) -> Tuple[float, str, str]:
    """
    Public function used by the rest of the app.
    Returns (score, label, explanation)
    """
    # local path
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

    # remote provider path
    try:
        result = _call_remote_model(url, page_text)
        if result:
            score, label, explanation = result
            score = float(round(score, 3))
            return score, label, explanation
    except Exception as e:
        logger.warning("Remote scoring failed, falling back to heuristic: %s", e)

    # fallback
    score = round(_heuristic_score(url, page_text), 3)
    if score >= 0.7:
        label = 'high_risk'
    elif score >= 0.4:
        label = 'medium_risk'
    else:
        label = 'low_risk'
    explanation = f'fallback heuristic score={score}.'
    return float(score), label, explanation
