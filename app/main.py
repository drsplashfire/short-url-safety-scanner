# app/main.py
from flask import Flask
from .routes import bp
from .db import init_db

def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    init_db()
    return app

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
