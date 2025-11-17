# app/fetcher.py
import requests
import re

DEFAULT_HEADERS = {'User-Agent': 'ShortURLScanner/1.0'}

def fetch_url(url, timeout=5):
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True, headers=DEFAULT_HEADERS)
        content = resp.text or ''

        m = re.search(r'<title>(.*?)</title>', content, flags=re.IGNORECASE | re.DOTALL)
        title = m.group(1).strip() if m else (content.strip()[:200] if content else '')

        return {'title': title, 'text': content}
    except requests.RequestException as e:
        return {'error': str(e)}
