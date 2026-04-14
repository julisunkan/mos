import os, io, uuid, json, csv
from datetime import datetime
from flask import (Blueprint, render_template, request, jsonify,
                   send_file, redirect, url_for, session, Response)
from groq import Groq
from db import get_db, get_setting, set_setting
from cleanup import purge_bulk_files

bulk_bp = Blueprint("bulk", __name__)

GEN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated", "bulk")
os.makedirs(GEN_DIR, exist_ok=True)

ADMIN_PW_KEY = "bulk_admin_pw"
DEFAULT_PW   = "admin123"

KDP_LANGUAGES = ["English","Spanish","French","German","Italian","Portuguese","Dutch","Japanese","Chinese","Korean","Arabic","Russian"]


def now():
    return datetime.utcnow().isoformat()

def get_groq_client():
    key = get_setting("bulk_settings","groq_api_key")
    return Groq(api_key=key) if key else None


def generate_batch_metadata(niche, count, extra_notes=""):
    client = get_groq_client()
    if not client:
        return None, "Groq API key not configured. Visit /bulk/julisunkan"
    system = (
        "You are a KDP publishing expert. Create unique, high-quality book metadata for Amazon KDP. "
        "Each book should be distinct with different angles, titles, and descriptions. "
        "Always respond with valid JSON only, no markdown."
    )
    prompt = f"""Create metadata for {count} unique KDP books in the "{niche}" niche.
Extra notes: {extra_notes or "Make each book appeal to a different sub-audience"}

Return ONLY a JSON array with exactly {count} book objects:
[
  {{
    "title": "Complete Title",
    "subtitle": "Descriptive Subtitle (max 200 chars)",
    "description": "300-500 word compelling description",
    "keywords": ["kw1","kw2","kw3","kw4","kw5","kw6","kw7"],
    "primary_category": "Books > Category > Subcategory",
    "secondary_category": "Books > Category > Subcategory",
    "language": "English",
    "pages": 120,
    "price_usd": 7.99,
    "target_audience": "who this is for",
    "unique_angle": "what makes this book different"
  }}
]"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            max_tokens=6000, temperature=0.7)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        books = json.loads(raw)
        if not isinstance(books, list): raise ValueError("Expected JSON array")
        return books[:count], None
    except json.JSONDecodeError as e:
        return None, f"AI returned invalid JSON: {e}"
    except Exception as e:
        return None, str(e)


def books_to_csv(books):
    buf = io.StringIO()
    fields = ["title","subtitle","description","keywords","primary_category",
              "secondary_category","language","pages","price_usd","target_audience","unique_angle"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for b in books:
        row = {f: b.get(f, "") for f in fields}
        if isinstance(b.get("keywords"), list):
            row["keywords"] = ", ".join(b["keywords"])
        elif isinstance(b.get("keywords"), str):
            try:
                row["keywords"] = ", ".join(json.loads(b["keywords"]))
            except Exception:
                row["keywords"] = b.get("keywords", "")
        writer.writerow(row)
    return buf.getvalue()


# ── Routes ────────────────────────────────────────────────────────

@bulk_bp.route("/")
def index():
    purge_bulk_files(GEN_DIR)
    conn = get_db()
    batches = conn.execute("SELECT * FROM bulk_batches ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return render_template("bulk/index.html", batches=batches, languages=KDP_LANGUAGES)


@bulk_bp.route("/generate", methods=["POST"])
def generate():
    data  = request.get_json(force=True)
    niche = data.get("niche","").strip()[:200]
    count = max(1, min(int(data.get("count", 5)), 50))
    name  = data.get("batch_name","").strip()[:100] or f"{niche} Batch"
    extra = data.get("extra_notes","").strip()[:500]
    if not niche:
        return jsonify({"error": "Niche is required"}), 400
    books, err = generate_batch_metadata(niche, count, extra)
    if err:
        return jsonify({"error": err}), 500
    batch_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO bulk_batches VALUES (?,?,?,?,?,?,?)",
                 (batch_id, name, niche, count, "done", None, now()))
    for book in books:
        book_id = str(uuid.uuid4())
        conn.execute("INSERT INTO bulk_books VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (book_id, batch_id,
                      book.get("title",""),
                      book.get("subtitle",""),
                      book.get("description",""),
                      json.dumps(book.get("keywords",[])),
                      book.get("primary_category",""),
                      book.get("secondary_category",""),
                      book.get("pages",120),
                      book.get("language","English"),
                      "draft",
                      book.get("price_usd"),
                      book.get("target_audience",""),
                      book.get("unique_angle","")))
    conn.commit()
    conn.close()
    return jsonify({"batch_id": batch_id, "books": books, "count": len(books)})


@bulk_bp.route("/batch/<batch_id>")
def get_batch(batch_id):
    conn = get_db()
    batch = conn.execute("SELECT * FROM bulk_batches WHERE id=?", (batch_id,)).fetchone()
    books = conn.execute("SELECT * FROM bulk_books WHERE batch_id=?", (batch_id,)).fetchall()
    conn.close()
    if not batch: return jsonify({"error":"Not found"}),404
    books_list = []
    for b in books:
        bd = dict(b)
        try: bd["keywords"] = json.loads(bd["keywords"])
        except: pass
        books_list.append(bd)
    return jsonify({"batch": dict(batch), "books": books_list})


@bulk_bp.route("/update-book/<book_id>", methods=["POST"])
def update_book(book_id):
    data = request.get_json(force=True)
    conn = get_db()
    existing = conn.execute("SELECT id FROM bulk_books WHERE id=?", (book_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({"error": "Book not found"}), 404
    conn.execute("""UPDATE bulk_books SET title=?,subtitle=?,description=?,keywords=?,
                    primary_category=?,secondary_category=?,pages=?,language=? WHERE id=?""",
                 (data.get("title",""),
                  data.get("subtitle",""),
                  data.get("description",""),
                  json.dumps(data.get("keywords",[])) if isinstance(data.get("keywords"),list) else data.get("keywords",""),
                  data.get("primary_category",""),
                  data.get("secondary_category",""),
                  data.get("pages",120),
                  data.get("language","English"),
                  book_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@bulk_bp.route("/export-csv/<batch_id>")
def export_csv(batch_id):
    conn = get_db()
    books = conn.execute("SELECT * FROM bulk_books WHERE batch_id=?", (batch_id,)).fetchall()
    conn.close()
    if not books: return jsonify({"error":"No books"}),404
    books_list = []
    for b in books:
        bd = dict(b)
        try: bd["keywords"] = ", ".join(json.loads(bd["keywords"]))
        except: pass
        books_list.append(bd)
    content = books_to_csv(books_list)
    buf = io.BytesIO(content.encode("utf-8"))
    return send_file(buf, mimetype="text/csv", as_attachment=True,
                     download_name=f"kdp_batch_{batch_id[:8]}.csv")


@bulk_bp.route("/batches")
def get_batches():
    conn = get_db()
    rows = conn.execute("SELECT * FROM bulk_batches ORDER BY created_at DESC LIMIT 30").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Admin ────────────────────────────────────────────────────────

@bulk_bp.route("/julisunkan", methods=["GET","POST"])
def admin():
    if not session.get("bulk_admin"):
        if request.method == "POST":
            pw = request.form.get("password","")
            if pw == (get_setting("bulk_settings", ADMIN_PW_KEY) or DEFAULT_PW):
                session["bulk_admin"] = True
                return redirect(url_for("bulk.admin"))
            return render_template("bulk/admin.html", error="Wrong password", logged_in=False)
        return render_template("bulk/admin.html", logged_in=False, error=None)
    conn = get_db()
    stats = {
        "batches": conn.execute("SELECT COUNT(*) FROM bulk_batches").fetchone()[0],
        "books":   conn.execute("SELECT COUNT(*) FROM bulk_books").fetchone()[0],
    }
    conn.close()
    settings = {"groq_api_key": get_setting("bulk_settings","groq_api_key"),
                "admin_password": get_setting("bulk_settings", ADMIN_PW_KEY) or DEFAULT_PW,
                "default_pages": get_setting("bulk_settings","default_pages") or "120"}
    return render_template("bulk/admin.html", logged_in=True, settings=settings, stats=stats, error=None)


@bulk_bp.route("/julisunkan/save", methods=["POST"])
def admin_save():
    if not session.get("bulk_admin"): return redirect(url_for("bulk.admin"))
    for key in ["groq_api_key","admin_password","default_pages"]:
        val = request.form.get(key,"")
        if key=="admin_password" and not val: continue
        set_setting("bulk_settings", ADMIN_PW_KEY if key=="admin_password" else key, val)
    return redirect(url_for("bulk.admin"))


@bulk_bp.route("/julisunkan/logout")
def admin_logout():
    session.pop("bulk_admin", None)
    return redirect(url_for("bulk.admin"))


@bulk_bp.route("/julisunkan/purge-expired", methods=["POST"])
def admin_purge_expired():
    if not session.get("bulk_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    purge_bulk_files(GEN_DIR)
    return jsonify({"ok": True})


# ── User Reports ─────────────────────────────────────────────────

@bulk_bp.route("/reports/submit", methods=["POST"])
def submit_report():
    data = request.get_json(force=True)
    content_id  = str(data.get("content_id", ""))[:100]
    reason      = str(data.get("reason", "")).strip()[:100]
    description = str(data.get("description", "")).strip()[:1000]
    if not reason:
        return jsonify({"error": "Reason is required"}), 400
    report_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO bulk_reports VALUES (?,?,?,?,?,?,?,?)",
                 (report_id, content_id, reason, description, "pending", now(), None, None))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "report_id": report_id})


@bulk_bp.route("/julisunkan/reports")
def admin_reports():
    if not session.get("bulk_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM bulk_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@bulk_bp.route("/julisunkan/reports/<report_id>/review", methods=["POST"])
def admin_review_report(report_id):
    if not session.get("bulk_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    action     = data.get("action", "")
    admin_note = str(data.get("note", "")).strip()[:500]
    if action not in ("approved", "declined"):
        return jsonify({"error": "Invalid action"}), 400
    conn = get_db()
    conn.execute("UPDATE bulk_reports SET status=?, reviewed_at=?, admin_note=? WHERE id=?",
                 (action, now(), admin_note, report_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@bulk_bp.route("/manifest.json")
def manifest():
    import json as _json
    data = {"name":"KDP Bulk Book Creator","short_name":"KDPBulk","start_url":"/bulk/","display":"standalone","background_color":"#0a2e1a","theme_color":"#84cc16","icons":[{"src":"/static/bulk/icon.png","sizes":"192x192","type":"image/png","purpose":"any"},{"src":"/static/bulk/icon-maskable.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]}
    return Response(_json.dumps(data), mimetype="application/manifest+json")

@bulk_bp.route("/sw.js")
def sw():
    js = "self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"
    return Response(js, mimetype="application/javascript")
