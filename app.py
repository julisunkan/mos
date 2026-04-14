import os
from flask import Flask, render_template, redirect, url_for, send_from_directory
from db import init_db
from apps.legal.routes import legal_bp
from apps.gen.routes import gen_bp
from apps.optimizer.routes import optimizer_bp
from apps.bulk.routes import bulk_bp
from apps.finder.routes import finder_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "mega-kdp-platform-2024")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

app.register_blueprint(legal_bp,     url_prefix="/legal")
app.register_blueprint(gen_bp,       url_prefix="/gen")
app.register_blueprint(optimizer_bp, url_prefix="/optimizer")
app.register_blueprint(bulk_bp,      url_prefix="/bulk")
app.register_blueprint(finder_bp,    url_prefix="/finder")

init_db()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "legal"),
        "icon.png", mimetype="image/png"
    )
