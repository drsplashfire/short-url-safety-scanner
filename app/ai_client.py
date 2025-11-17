# app/ai_client.py
import os

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'local')

def _heuristic_score(url, text):
    score = 0.2
    url_lower = (url or '').lower()
    text_lower = (text or '').lower()

    suspicious_keywords = ['login', 'verify', 'account', 'update', 'bank', 'secure', 'confirm', 'password']

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


def call_safety(url, page_text):
    if LLM_PROVIDER == 'local':
        score = round(_heuristic_score(url, page_text), 3)

        if score >= 0.7:
            label = 'high_risk'
        elif score >= 0.4:
            label = 'medium_risk'
        else:
            label = 'low_risk'

        explanation = f'heuristic score={score}. Checked keywords and TLDs.'
        return float(score), label, explanation

    api_url = os.getenv('LLM_API_URL')
    api_key = os.getenv('LLM_API_KEY')
    if not api_url or not api_key:
        raise RuntimeError('Remote LLM configured but LLM_API_URL or LLM_API_KEY missing')

    import requests
    payload = {'url': url, 'text': page_text, 'prompt': 'Rate safety 0-1 and explain.'}
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    r = requests.post(api_url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    data = r.json()

    return float(data.get('score', 0.5)), data.get('label', 'medium_risk'), data.get('explanation', '')
