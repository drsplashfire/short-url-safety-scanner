# app/db.py
import os
import sqlite3
from datetime import datetime
try:
    from google.cloud import firestore
except Exception:
    firestore = None

DB_PATH = os.getenv('DB_PATH', 'scans.db')
USE_FIRESTORE = os.getenv('USE_FIRESTORE', '0') == '1'

def init_db():
    if USE_FIRESTORE:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS scans (
        id TEXT PRIMARY KEY,
        url TEXT,
        title TEXT,
        safety_score REAL,
        label TEXT,
        explanation TEXT,
        timestamp TEXT
    )
    ''')
    conn.commit()
    conn.close()

def insert_scan(scan_id, url, title, safety_score, label, explanation):
    ts = datetime.utcnow().isoformat() + 'Z'

    if USE_FIRESTORE:
        if firestore is None:
            raise RuntimeError('google-cloud-firestore not installed')

        client = firestore.Client()
        client.collection('scans').document(scan_id).set({
            'url': url,
            'title': title,
            'safety_score': float(safety_score),
            'label': label,
            'explanation': explanation,
            'timestamp': ts
        })
        return scan_id

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO scans (id, url, title, safety_score, label, explanation, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (scan_id, url, title, safety_score, label, explanation, ts))
    conn.commit()
    conn.close()
    return scan_id


def fetch_scans(limit=100):
    if USE_FIRESTORE:
        if firestore is None:
            raise RuntimeError('google-cloud-firestore not installed')

        client = firestore.Client()
        docs = client.collection('scans').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [{ 'id': d.id, **d.to_dict() } for d in docs]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, url, title, safety_score, label, explanation, timestamp FROM scans ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            'id': r[0],
            'url': r[1],
            'title': r[2],
            'safety_score': r[3],
            'label': r[4],
            'explanation': r[5],
            'timestamp': r[6]
        } for r in rows
    ]
