# app/routes.py
from flask import Blueprint, request, jsonify
from .db import insert_scan, fetch_scans
from .ai_client import call_safety
from .fetcher import fetch_url
import uuid

bp = Blueprint('api', __name__)

# add this near the top of app/routes.py (below imports)
@bp.route('/', methods=['GET'])
def index():
    return """
    <!doctype html>
    <html>
    <head><title>Short URL Scanner</title></head>
    <body>
      <h2>Short URL Title & Safety Scanner</h2>
      <form id="f">
        <input id="u" placeholder="https://example.com" style="width:400px"/>
        <button type="submit">Scan</button>
      </form>
      <pre id="out" style="white-space:pre-wrap;background:#f2f2f2;padding:10px;border-radius:6px;"></pre>
      <script>
        const f = document.getElementById('f');
        f.addEventListener('submit', async e => {
          e.preventDefault();
          const url = document.getElementById('u').value;
          const res = await fetch('/scan', {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify({url})});
          const txt = await res.text();
          document.getElementById('out').textContent = txt;
        });
      </script>
    </body>
    </html>
    """, 200


@bp.route('/scan', methods=['POST'])
def scan_url():
    payload = request.get_json(force=True)
    url = (payload.get('url') or '').strip()
    if not url:
        return jsonify({'error': 'url required'}), 400

    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url

    fetched = fetch_url(url)
    if fetched.get('error'):
        return jsonify({'error': fetched['error']}), 502

    title = fetched.get('title', '')
    page_text = fetched.get('text', '')

    score, label, explanation = call_safety(url, page_text)

    scan_id = str(uuid.uuid4())
    insert_scan(scan_id, url, title, score, label, explanation)

    return jsonify({
        'id': scan_id,
        'url': url,
        'title': title,
        'safety_score': score,
        'label': label,
        'explanation': explanation,
        'timestamp': None
    }), 201


@bp.route('/scans', methods=['GET'])
def list_scans():
    items = fetch_scans(limit=100)
    return jsonify(items)
