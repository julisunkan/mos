import os, io, uuid, json, sqlite3
from datetime import datetime
from flask import (Blueprint, render_template, request, jsonify,
                   send_file, redirect, url_for, session, Response)
from werkzeug.utils import secure_filename
from groq import Groq
from db import get_db, get_setting, set_setting
from cleanup import purge_legal_uploads

legal_bp = Blueprint("legal", __name__)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "legal")
GEN_DIR    = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated", "legal")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GEN_DIR, exist_ok=True)

ALLOWED = {"pdf", "docx", "txt", "doc"}
ADMIN_PW_KEY = "legal_admin_pw"
DEFAULT_PW   = "admin123"


# ── Helpers ─────────────────────────────────────────────────────

def now():
    return datetime.utcnow().isoformat()

def allowed(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED

def get_groq():
    key = get_setting("legal_settings", "groq_api_key")
    return Groq(api_key=key) if key else None

def extract_text(path, ext):
    if ext == "pdf":
        from pypdf import PdfReader
        r = PdfReader(path)
        return "\n".join(p.extract_text() or "" for p in r.pages)
    elif ext in ("docx", "doc"):
        import docx
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    else:
        with open(path, "r", errors="ignore") as f:
            return f.read()


def delete_document(doc_id):
    """Remove one document and its analysis from DB and filesystem."""
    conn = get_db()
    row = conn.execute("SELECT filename FROM legal_documents WHERE id=?", (doc_id,)).fetchone()
    if row:
        fpath = os.path.join(UPLOAD_DIR, row["filename"])
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass
        conn.execute("DELETE FROM legal_analyses WHERE doc_id=?", (doc_id,))
        conn.execute("DELETE FROM legal_documents WHERE id=?", (doc_id,))
        conn.commit()
    conn.close()

def analyze_with_groq(text):
    client = get_groq()
    if not client:
        return None, "Groq API key not configured. Set it in /legal/julisunkan"
    trimmed = text[:12000]
    system = (
        "You are an expert legal analyst specializing in contract law and risk assessment. "
        "Analyze legal documents and identify dangerous, unfair, or risky clauses. "
        "Always respond with valid JSON only, no markdown, no extra text."
    )
    prompt = f"""Analyze the following legal document and identify all risky, dangerous, or potentially harmful clauses.

DOCUMENT:
{trimmed}

Return ONLY this exact JSON structure:
{{
  "overall_risk": "HIGH or MEDIUM or LOW",
  "summary": "2-3 sentence overall assessment",
  "total_clauses_flagged": 0,
  "clauses": [
    {{
      "clause_text": "exact problematic text excerpt (max 200 chars)",
      "risk_level": "HIGH or MEDIUM or LOW",
      "risk_type": "category like Liability, Termination, Penalty, IP Rights, Non-Compete, Arbitration, etc.",
      "explanation": "detailed explanation of why this is risky",
      "recommendation": "specific actionable recommendation"
    }}
  ]
}}"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            max_tokens=4096, temperature=0.2)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"AI returned invalid JSON: {e}"
    except Exception as e:
        return None, str(e)

def build_pdf_report(analysis, original_name):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    navy   = HexColor("#1a2744")
    gold   = HexColor("#c9a84c")
    red    = HexColor("#c0392b")
    orange = HexColor("#e67e22")
    green  = HexColor("#27ae60")

    title_style   = ParagraphStyle("title",   fontName="Helvetica-Bold", fontSize=20, textColor=navy, spaceAfter=6)
    sub_style     = ParagraphStyle("sub",     fontName="Helvetica",      fontSize=11, textColor=HexColor("#555555"), spaceAfter=12)
    heading_style = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=13, textColor=navy, spaceBefore=12, spaceAfter=6)
    body_style    = ParagraphStyle("body",    fontName="Helvetica",      fontSize=10, textColor=black, spaceAfter=4, leading=14)
    risk_colors   = {"HIGH": red, "MEDIUM": orange, "LOW": green}

    story = []
    story.append(Paragraph("Legal Document Risk Analysis Report", title_style))
    story.append(Paragraph(f"Document: {original_name} &nbsp;|&nbsp; Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC", sub_style))
    story.append(Spacer(1, 0.1*inch))

    overall = analysis.get("overall_risk", "UNKNOWN")
    oc = risk_colors.get(overall, navy)
    story.append(Paragraph(f'<font color="{oc.hexval()}">● Overall Risk: {overall}</font>', ParagraphStyle("or", fontName="Helvetica-Bold", fontSize=14, textColor=oc, spaceAfter=6)))
    story.append(Paragraph(analysis.get("summary", ""), body_style))
    story.append(Spacer(1, 0.2*inch))

    for i, clause in enumerate(analysis.get("clauses", []), 1):
        rl = clause.get("risk_level", "MEDIUM")
        rc2 = risk_colors.get(rl, orange)
        story.append(Paragraph(f'<font color="{rc2.hexval()}">[{rl}] Clause {i}: {clause.get("risk_type","")}</font>',
                                ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=11, textColor=rc2, spaceBefore=10, spaceAfter=4)))
        story.append(Paragraph(f'<i>"{clause.get("clause_text","")}"</i>', ParagraphStyle("ct", fontName="Helvetica-Oblique", fontSize=9, textColor=HexColor("#333333"), spaceAfter=4, leftIndent=12)))
        story.append(Paragraph(f"<b>Risk:</b> {clause.get('explanation','')}", body_style))
        story.append(Paragraph(f"<b>Recommendation:</b> {clause.get('recommendation','')}", body_style))
        story.append(Spacer(1, 0.05*inch))

    doc.build(story)
    buf.seek(0)
    return buf


# ── Routes ───────────────────────────────────────────────────────

@legal_bp.route("/")
def index():
    purge_legal_uploads(UPLOAD_DIR)
    conn = get_db()
    docs = conn.execute("SELECT * FROM legal_documents ORDER BY created_at DESC LIMIT 20").fetchall()
    conn.close()
    return render_template("legal/index.html", docs=docs)


@legal_bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename or not allowed(f.filename):
        return jsonify({"error": "Upload PDF, DOCX, or TXT files only"}), 400
    ext = f.filename.rsplit(".", 1)[1].lower()
    doc_id  = str(uuid.uuid4())
    stored  = f"{doc_id}.{ext}"
    path    = os.path.join(UPLOAD_DIR, stored)
    f.save(path)
    conn = get_db()
    conn.execute("INSERT INTO legal_documents VALUES (?,?,?,?,?,?)",
                 (doc_id, stored, secure_filename(f.filename), ext, "pending", now()))
    conn.commit()
    conn.close()
    return jsonify({"doc_id": doc_id, "name": f.filename})


@legal_bp.route("/analyze/<doc_id>", methods=["POST"])
def analyze(doc_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM legal_documents WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Document not found"}), 404
    path = os.path.join(UPLOAD_DIR, row["filename"])
    if not os.path.exists(path):
        return jsonify({"error": "Document file has expired and was removed."}), 410
    text = extract_text(path, row["file_type"])
    if not text.strip():
        return jsonify({"error": "Could not extract text from document"}), 400
    result, err = analyze_with_groq(text)
    if err:
        return jsonify({"error": err}), 500
    analysis_id = str(uuid.uuid4())
    result["total_clauses_flagged"] = len(result.get("clauses", []))
    conn2 = get_db()
    conn2.execute("INSERT INTO legal_analyses VALUES (?,?,?,?,?,?)",
                  (analysis_id, doc_id, result.get("overall_risk","UNKNOWN"),
                   result.get("summary",""), json.dumps(result.get("clauses",[])), now()))
    conn2.execute("UPDATE legal_documents SET status='analysed' WHERE id=?", (doc_id,))
    conn2.commit()
    conn2.close()
    return jsonify({"analysis_id": analysis_id, "result": result})


@legal_bp.route("/report/<doc_id>")
def download_report(doc_id):
    conn = get_db()
    doc = conn.execute("SELECT * FROM legal_documents WHERE id=?", (doc_id,)).fetchone()
    ana = conn.execute("SELECT * FROM legal_analyses WHERE doc_id=? ORDER BY created_at DESC", (doc_id,)).fetchone()
    conn.close()
    if not doc or not ana:
        return jsonify({"error": "Report not found. The document may have been deleted or not yet analysed."}), 404
    analysis = {
        "overall_risk": ana["overall_risk"],
        "summary": ana["summary"],
        "clauses": json.loads(ana["clauses"])
    }
    buf = build_pdf_report(analysis, doc["original_name"])
    resp = send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name=f"risk_report_{doc_id[:8]}.pdf")
    resp.headers["Content-Disposition"] = f'attachment; filename="risk_report_{doc_id[:8]}.pdf"'
    return resp


@legal_bp.route("/history")
def history():
    conn = get_db()
    rows = conn.execute("""
        SELECT d.id, d.original_name, d.file_type, d.status, d.created_at,
               a.overall_risk, a.id as analysis_id
        FROM legal_documents d
        LEFT JOIN legal_analyses a ON a.doc_id=d.id
        ORDER BY d.created_at DESC""").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Admin ────────────────────────────────────────────────────────

@legal_bp.route("/julisunkan", methods=["GET", "POST"])
def admin():
    if not session.get("legal_admin"):
        if request.method == "POST":
            pw = request.form.get("password", "")
            stored = get_setting("legal_settings", ADMIN_PW_KEY) or DEFAULT_PW
            if pw == stored:
                session["legal_admin"] = True
                return redirect(url_for("legal.admin"))
            return render_template("legal/admin.html", error="Wrong password", logged_in=False)
        return render_template("legal/admin.html", logged_in=False, error=None)
    settings = {
        "groq_api_key": get_setting("legal_settings", "groq_api_key"),
        "admin_password": get_setting("legal_settings", ADMIN_PW_KEY) or DEFAULT_PW,
        "max_file_mb": get_setting("legal_settings", "max_file_mb") or "10",
    }
    conn = get_db()
    stats = {
        "total_docs": conn.execute("SELECT COUNT(*) FROM legal_documents").fetchone()[0],
        "analysed":   conn.execute("SELECT COUNT(*) FROM legal_documents WHERE status='analysed'").fetchone()[0],
        "high_risk":  conn.execute("SELECT COUNT(*) FROM legal_analyses WHERE overall_risk='HIGH'").fetchone()[0],
    }
    docs = conn.execute("""
        SELECT d.id, d.original_name, d.file_type, d.status, d.created_at,
               a.overall_risk
        FROM legal_documents d
        LEFT JOIN legal_analyses a ON a.doc_id=d.id
        ORDER BY d.created_at DESC""").fetchall()
    conn.close()
    return render_template("legal/admin.html", logged_in=True, settings=settings,
                           stats=stats, docs=docs, error=None)


@legal_bp.route("/julisunkan/save", methods=["POST"])
def admin_save():
    if not session.get("legal_admin"):
        return redirect(url_for("legal.admin"))
    for key in ["groq_api_key", "admin_password", "max_file_mb"]:
        val = request.form.get(key, "")
        if key == "admin_password" and not val:
            continue
        set_setting("legal_settings", key if key != "admin_password" else ADMIN_PW_KEY, val)
    return redirect(url_for("legal.admin"))


@legal_bp.route("/julisunkan/logout")
def admin_logout():
    session.pop("legal_admin", None)
    return redirect(url_for("legal.admin"))


@legal_bp.route("/julisunkan/documents/<doc_id>/delete", methods=["POST"])
def admin_delete_doc(doc_id):
    if not session.get("legal_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    delete_document(doc_id)
    return jsonify({"ok": True})


@legal_bp.route("/julisunkan/purge-expired", methods=["POST"])
def admin_purge_expired():
    if not session.get("legal_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    purge_legal_uploads(UPLOAD_DIR)
    return jsonify({"ok": True})


# ── User Reports ─────────────────────────────────────────────────

@legal_bp.route("/reports/submit", methods=["POST"])
def submit_report():
    data = request.get_json(force=True)
    content_id  = str(data.get("content_id", ""))[:100]
    reason      = str(data.get("reason", "")).strip()[:100]
    description = str(data.get("description", "")).strip()[:1000]
    if not reason:
        return jsonify({"error": "Reason is required"}), 400
    report_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO legal_reports VALUES (?,?,?,?,?,?,?,?)",
                 (report_id, content_id, reason, description, "pending", now(), None, None))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "report_id": report_id})


@legal_bp.route("/julisunkan/reports")
def admin_reports():
    if not session.get("legal_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM legal_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@legal_bp.route("/julisunkan/reports/<report_id>/review", methods=["POST"])
def admin_review_report(report_id):
    if not session.get("legal_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    action     = data.get("action", "")
    admin_note = str(data.get("note", "")).strip()[:500]
    if action not in ("approved", "declined"):
        return jsonify({"error": "Invalid action"}), 400
    conn = get_db()
    conn.execute("UPDATE legal_reports SET status=?, reviewed_at=?, admin_note=? WHERE id=?",
                 (action, now(), admin_note, report_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@legal_bp.route("/manifest.json")
def manifest():
    import json as _json
    data = {
        "name": "Legal Risk Checker",
        "short_name": "LegalCheck",
        "start_url": "/legal/",
        "display": "standalone",
        "background_color": "#1a2744",
        "theme_color": "#c9a84c",
        "icons": [
            {"src": "/static/legal/icon.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/legal/icon-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
        ]
    }
    return Response(_json.dumps(data), mimetype="application/manifest+json")

@legal_bp.route("/sw.js")
def sw():
    js = """self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));
});"""
    return Response(js, mimetype="application/javascript")
