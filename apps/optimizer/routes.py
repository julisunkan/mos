import os, io, uuid, json
from datetime import datetime
from flask import (Blueprint, render_template, request, jsonify,
                   send_file, redirect, url_for, session, Response)
from groq import Groq
from db import get_db, get_setting, set_setting
from cleanup import purge_optimizer_files

optimizer_bp = Blueprint("optimizer", __name__)

GEN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated", "optimizer")
os.makedirs(GEN_DIR, exist_ok=True)

ADMIN_PW_KEY = "opt_admin_pw"
DEFAULT_PW   = "admin123"

KDP_CATEGORIES = [
    "Arts & Photography","Biographies & Memoirs","Business & Money","Children's Books",
    "Comics & Graphic Novels","Computers & Technology","Cookbooks, Food & Wine",
    "Crafts, Hobbies & Home","Education & Teaching","Engineering & Transportation",
    "Health, Fitness & Dieting","History","Humor & Entertainment","Law","Literature & Fiction",
    "Medical Books","Mystery, Thriller & Suspense","Nonfiction","Parenting & Relationships",
    "Politics & Social Sciences","Professional & Technical","Reference","Religion & Spirituality",
    "Romance","Science & Math","Science Fiction & Fantasy","Self-Help","Sports & Outdoors",
    "Teen & Young Adult","Test Preparation","Travel",
]


def now():
    return datetime.utcnow().isoformat()

def get_groq_client():
    key = get_setting("opt_settings", "groq_api_key")
    return Groq(api_key=key) if key else None


def optimize_metadata(genre, audience, rough_title, raw_keywords, description_hint=""):
    client = get_groq_client()
    if not client:
        return None, "Groq API key not configured. Visit /optimizer/julisunkan"
    system = (
        "You are a KDP publishing expert and SEO specialist. "
        "You create optimized book titles, descriptions, and keywords that maximize discoverability on Amazon KDP. "
        "Always respond with valid JSON only."
    )
    prompt = f"""Optimize the following KDP book metadata for maximum discoverability and sales:

Genre/Category: {genre}
Target Audience: {audience}
Rough Title Idea: {rough_title}
Initial Keywords: {raw_keywords}
Description Hint: {description_hint or "N/A"}

Return ONLY this exact JSON:
{{
  "titles": [
    {{"title": "Title 1", "subtitle": "Subtitle 1", "reason": "why this works"}},
    {{"title": "Title 2", "subtitle": "Subtitle 2", "reason": "why this works"}},
    {{"title": "Title 3", "subtitle": "Subtitle 3", "reason": "why this works"}},
    {{"title": "Title 4", "subtitle": "Subtitle 4", "reason": "why this works"}},
    {{"title": "Title 5", "subtitle": "Subtitle 5", "reason": "why this works"}}
  ],
  "description": {{
    "hook": "attention-grabbing first sentence (max 150 chars)",
    "body": "full 400-600 word description with HTML formatting (use <p>, <b>, <ul>, <li> tags)",
    "cta": "call-to-action closing sentence"
  }},
  "keywords": [
    "keyword phrase 1 (max 50 chars)",
    "keyword phrase 2",
    "keyword phrase 3",
    "keyword phrase 4",
    "keyword phrase 5",
    "keyword phrase 6",
    "keyword phrase 7"
  ],
  "categories": [
    {{"primary": "KDP category path", "reason": "why this fits"}},
    {{"primary": "KDP category path 2", "reason": "why this fits"}}
  ],
  "a_plus_bullets": [
    "Benefit bullet 1 (Feature → Benefit format)",
    "Benefit bullet 2",
    "Benefit bullet 3",
    "Benefit bullet 4",
    "Benefit bullet 5"
  ],
  "seo_tips": ["tip1", "tip2", "tip3"]
}}"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            max_tokens=4096, temperature=0.3)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"AI returned invalid JSON: {e}"
    except Exception as e:
        return None, str(e)


def export_txt(result, genre, rough_title):
    lines = [
        "KDP BOOK METADATA OPTIMIZATION REPORT",
        "=" * 50,
        f"Genre: {genre}",
        f"Original Title: {rough_title}",
        "",
        "── OPTIMIZED TITLES ──",
    ]
    for i, t in enumerate(result.get("titles", []), 1):
        lines.append(f"{i}. {t.get('title','')}: {t.get('subtitle','')}")
        lines.append(f"   → {t.get('reason','')}")
    body = result.get("description", {}).get("body", "")
    body_plain = (body.replace("<p>","\n").replace("</p>","")
                     .replace("<b>","**").replace("</b>","**")
                     .replace("<ul>","").replace("</ul>","")
                     .replace("<li>","• ").replace("</li>",""))
    lines += ["", "── DESCRIPTION ──",
              result.get("description", {}).get("hook", ""),
              "", body_plain,
              "", "CTA: " + result.get("description", {}).get("cta", ""),
              "", "── 7 KEYWORDS ──"]
    for kw in result.get("keywords", []):
        lines.append(f"• {kw}")
    lines += ["", "── KDP CATEGORIES ──"]
    for cat in result.get("categories", []):
        lines.append(f"• {cat.get('primary','')} — {cat.get('reason','')}")
    lines += ["", "── A+ CONTENT BULLETS ──"]
    for b in result.get("a_plus_bullets", []):
        lines.append(f"• {b}")
    return "\n".join(lines)


# ── Routes ────────────────────────────────────────────────────────

@optimizer_bp.route("/")
def index():
    purge_optimizer_files(GEN_DIR)
    return render_template("optimizer/index.html", categories=KDP_CATEGORIES)


@optimizer_bp.route("/optimize", methods=["POST"])
def optimize():
    data = request.get_json(force=True)
    genre       = data.get("genre","").strip()[:100]
    audience    = data.get("audience","").strip()[:100]
    rough_title = data.get("rough_title","").strip()[:150]
    raw_kw      = data.get("keywords","").strip()[:300]
    desc_hint   = data.get("description_hint","").strip()[:500]
    if not genre or not rough_title:
        return jsonify({"error": "Genre and rough title are required"}), 400
    result, err = optimize_metadata(genre, audience, rough_title, raw_kw, desc_hint)
    if err:
        return jsonify({"error": err}), 500
    proj_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO opt_projects VALUES (?,?,?,?,?,?,?)",
                 (proj_id, genre, audience, rough_title, raw_kw, json.dumps(result), now()))
    conn.commit()
    conn.close()
    return jsonify({"project_id": proj_id, "result": result})


@optimizer_bp.route("/export/<proj_id>")
def export(proj_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM opt_projects WHERE id=?", (proj_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    result = json.loads(row["result"])
    content = export_txt(result, row["genre"], row["rough_title"])
    buf = io.BytesIO(content.encode("utf-8"))
    return send_file(buf, mimetype="text/plain", as_attachment=True,
                     download_name=f"kdp_metadata_{proj_id[:8]}.txt")


@optimizer_bp.route("/history")
def history():
    conn = get_db()
    rows = conn.execute("SELECT id,genre,rough_title,created_at FROM opt_projects ORDER BY created_at DESC LIMIT 30").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@optimizer_bp.route("/result/<proj_id>")
def get_result(proj_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM opt_projects WHERE id=?", (proj_id,)).fetchone()
    conn.close()
    if not row: return jsonify({"error":"Not found"}),404
    return jsonify({"result": json.loads(row["result"]), "genre": row["genre"], "rough_title": row["rough_title"]})


# ── Admin ────────────────────────────────────────────────────────

@optimizer_bp.route("/julisunkan", methods=["GET","POST"])
def admin():
    if not session.get("opt_admin"):
        if request.method == "POST":
            pw = request.form.get("password","")
            if pw == (get_setting("opt_settings", ADMIN_PW_KEY) or DEFAULT_PW):
                session["opt_admin"] = True
                return redirect(url_for("optimizer.admin"))
            return render_template("optimizer/admin.html", error="Wrong password", logged_in=False)
        return render_template("optimizer/admin.html", logged_in=False, error=None)
    conn = get_db()
    stats = {"total": conn.execute("SELECT COUNT(*) FROM opt_projects").fetchone()[0]}
    conn.close()
    settings = {"groq_api_key": get_setting("opt_settings","groq_api_key"),
                "admin_password": get_setting("opt_settings", ADMIN_PW_KEY) or DEFAULT_PW}
    return render_template("optimizer/admin.html", logged_in=True, settings=settings, stats=stats, error=None)


@optimizer_bp.route("/julisunkan/save", methods=["POST"])
def admin_save():
    if not session.get("opt_admin"): return redirect(url_for("optimizer.admin"))
    for key in ["groq_api_key","admin_password"]:
        val = request.form.get(key,"")
        if key=="admin_password" and not val: continue
        set_setting("opt_settings", ADMIN_PW_KEY if key=="admin_password" else key, val)
    return redirect(url_for("optimizer.admin"))


@optimizer_bp.route("/julisunkan/logout")
def admin_logout():
    session.pop("opt_admin", None)
    return redirect(url_for("optimizer.admin"))


@optimizer_bp.route("/julisunkan/purge-expired", methods=["POST"])
def admin_purge_expired():
    if not session.get("opt_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    purge_optimizer_files(GEN_DIR)
    return jsonify({"ok": True})


# ── User Reports ─────────────────────────────────────────────────

@optimizer_bp.route("/reports/submit", methods=["POST"])
def submit_report():
    data = request.get_json(force=True)
    content_id  = str(data.get("content_id", ""))[:100]
    reason      = str(data.get("reason", "")).strip()[:100]
    description = str(data.get("description", "")).strip()[:1000]
    if not reason:
        return jsonify({"error": "Reason is required"}), 400
    report_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO opt_reports VALUES (?,?,?,?,?,?,?,?)",
                 (report_id, content_id, reason, description, "pending", now(), None, None))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "report_id": report_id})


@optimizer_bp.route("/julisunkan/reports")
def admin_reports():
    if not session.get("opt_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM opt_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@optimizer_bp.route("/julisunkan/reports/<report_id>/review", methods=["POST"])
def admin_review_report(report_id):
    if not session.get("opt_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    action     = data.get("action", "")
    admin_note = str(data.get("note", "")).strip()[:500]
    if action not in ("approved", "declined"):
        return jsonify({"error": "Invalid action"}), 400
    conn = get_db()
    conn.execute("UPDATE opt_reports SET status=?, reviewed_at=?, admin_note=? WHERE id=?",
                 (action, now(), admin_note, report_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@optimizer_bp.route("/manifest.json")
def manifest():
    import json as _json
    data = {"name":"KDP Title & Description Optimizer","short_name":"KDPOptimize","start_url":"/optimizer/","display":"standalone","background_color":"#0d3340","theme_color":"#f59e0b","icons":[{"src":"/static/optimizer/icon.png","sizes":"192x192","type":"image/png","purpose":"any"},{"src":"/static/optimizer/icon-maskable.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]}
    return Response(_json.dumps(data), mimetype="application/manifest+json")

@optimizer_bp.route("/sw.js")
def sw():
    js = "self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"
    return Response(js, mimetype="application/javascript")
