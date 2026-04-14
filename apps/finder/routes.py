import os, io, uuid, json, csv
from datetime import datetime
from flask import (Blueprint, render_template, request, jsonify,
                   send_file, redirect, url_for, session, Response)
from groq import Groq
from db import get_db, get_setting, set_setting
from cleanup import purge_finder_files

finder_bp = Blueprint("finder", __name__)

GEN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated", "finder")
os.makedirs(GEN_DIR, exist_ok=True)

ADMIN_PW_KEY = "finder_admin_pw"
DEFAULT_PW   = "admin123"


def now():
    return datetime.utcnow().isoformat()

def get_groq_client():
    key = get_setting("finder_settings","groq_api_key")
    return Groq(api_key=key) if key else None


def find_niches(topic, search_type="full"):
    client = get_groq_client()
    if not client:
        return None, "Groq API key not configured. Visit /finder/julisunkan"
    system = (
        "You are a KDP market research expert with deep knowledge of Amazon publishing niches. "
        "Analyze markets and provide data-driven insights for KDP publishers. "
        "Always respond with valid JSON only, no markdown."
    )
    prompt = f"""Perform comprehensive KDP market research for this topic: "{topic}"

Return ONLY this JSON structure:
{{
  "market_summary": "2-3 sentence overview of this market's potential",
  "overall_opportunity": "HIGH or MEDIUM or LOW",
  "niches": [
    {{
      "niche": "specific niche name",
      "description": "what this niche covers",
      "competition": "HIGH or MEDIUM or LOW",
      "opportunity": "HIGH or MEDIUM or LOW",
      "opportunity_score": 8,
      "estimated_monthly_searches": "5,000-15,000",
      "avg_bsr": "50,000-200,000",
      "price_range": "$7.99-$14.99",
      "keywords": ["keyword1","keyword2","keyword3","keyword4","keyword5","keyword6","keyword7","keyword8","keyword9","keyword10"],
      "potential_titles": ["Title 1","Title 2","Title 3","Title 4","Title 5"],
      "target_audience": "description of ideal reader",
      "content_types": ["lined journal","workbook","planner"],
      "trend": "Growing or Stable or Declining",
      "insider_tip": "specific actionable insight"
    }}
  ],
  "top_keywords": [
    {{
      "keyword": "exact keyword phrase",
      "monthly_searches": "estimate like 10,000",
      "competition": "HIGH or MEDIUM or LOW",
      "opportunity_score": 8,
      "avg_selling_price": "$8.99",
      "suggested_use": "title, subtitle, or keyword slot"
    }}
  ],
  "quick_wins": ["actionable recommendation 1","actionable recommendation 2","actionable recommendation 3"],
  "books_to_avoid": ["type of book with saturated market 1","type 2"],
  "seasonal_trends": "insights about seasonal demand patterns"
}}
Include 5-8 niches and 15-20 keywords."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            max_tokens=5000, temperature=0.4)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"AI returned invalid JSON: {e}"
    except Exception as e:
        return None, str(e)


def results_to_csv(results, topic):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["KDP NICHE & KEYWORD FINDER REPORT"])
    writer.writerow(["Topic:", topic])
    writer.writerow(["Overall Opportunity:", results.get("overall_opportunity","")])
    writer.writerow(["Market Summary:", results.get("market_summary","")])
    writer.writerow([])
    writer.writerow(["NICHES"])
    writer.writerow(["Niche","Competition","Opportunity","Score","Est. Searches","Price Range","Trend","Target Audience"])
    for n in results.get("niches",[]):
        writer.writerow([n.get("niche",""), n.get("competition",""), n.get("opportunity",""),
                         n.get("opportunity_score",""), n.get("estimated_monthly_searches",""),
                         n.get("price_range",""), n.get("trend",""), n.get("target_audience","")])
    writer.writerow([])
    writer.writerow(["TOP KEYWORDS"])
    writer.writerow(["Keyword","Monthly Searches","Competition","Score","Avg Price","Suggested Use"])
    for k in results.get("top_keywords",[]):
        writer.writerow([k.get("keyword",""), k.get("monthly_searches",""), k.get("competition",""),
                         k.get("opportunity_score",""), k.get("avg_selling_price",""), k.get("suggested_use","")])
    writer.writerow([])
    writer.writerow(["QUICK WINS"])
    for qw in results.get("quick_wins",[]): writer.writerow([qw])
    return buf.getvalue()


# ── Routes ────────────────────────────────────────────────────────

@finder_bp.route("/")
def index():
    purge_finder_files(GEN_DIR)
    conn = get_db()
    recent = conn.execute("SELECT id,seed_topic,created_at FROM finder_searches ORDER BY created_at DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("finder/index.html", recent=recent)


@finder_bp.route("/search", methods=["POST"])
def search():
    data  = request.get_json(force=True)
    topic = data.get("topic","").strip()[:200]
    if not topic:
        return jsonify({"error": "Search topic is required"}), 400
    results, err = find_niches(topic)
    if err:
        return jsonify({"error": err}), 500
    search_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO finder_searches VALUES (?,?,?,?)",
                 (search_id, topic, json.dumps(results), now()))
    conn.commit()
    conn.close()
    return jsonify({"search_id": search_id, "results": results})


@finder_bp.route("/result/<search_id>")
def get_result(search_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM finder_searches WHERE id=?", (search_id,)).fetchone()
    conn.close()
    if not row: return jsonify({"error":"Not found"}),404
    return jsonify({"topic": row["seed_topic"], "results": json.loads(row["results"]), "created_at": row["created_at"]})


@finder_bp.route("/export/<search_id>")
def export(search_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM finder_searches WHERE id=?", (search_id,)).fetchone()
    conn.close()
    if not row: return jsonify({"error":"Not found"}),404
    results = json.loads(row["results"])
    content = results_to_csv(results, row["seed_topic"])
    buf = io.BytesIO(content.encode("utf-8"))
    return send_file(buf, mimetype="text/csv", as_attachment=True,
                     download_name=f"kdp_research_{search_id[:8]}.csv")


@finder_bp.route("/history")
def history():
    conn = get_db()
    rows = conn.execute("SELECT id,seed_topic,created_at FROM finder_searches ORDER BY created_at DESC LIMIT 30").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Admin ────────────────────────────────────────────────────────

@finder_bp.route("/julisunkan", methods=["GET","POST"])
def admin():
    if not session.get("finder_admin"):
        if request.method == "POST":
            pw = request.form.get("password","")
            if pw == (get_setting("finder_settings", ADMIN_PW_KEY) or DEFAULT_PW):
                session["finder_admin"] = True
                return redirect(url_for("finder.admin"))
            return render_template("finder/admin.html", error="Wrong password", logged_in=False)
        return render_template("finder/admin.html", logged_in=False, error=None)
    conn = get_db()
    stats = {"total_searches": conn.execute("SELECT COUNT(*) FROM finder_searches").fetchone()[0]}
    conn.close()
    settings = {"groq_api_key": get_setting("finder_settings","groq_api_key"),
                "admin_password": get_setting("finder_settings", ADMIN_PW_KEY) or DEFAULT_PW}
    return render_template("finder/admin.html", logged_in=True, settings=settings, stats=stats, error=None)


@finder_bp.route("/julisunkan/save", methods=["POST"])
def admin_save():
    if not session.get("finder_admin"): return redirect(url_for("finder.admin"))
    for key in ["groq_api_key","admin_password"]:
        val = request.form.get(key,"")
        if key=="admin_password" and not val: continue
        set_setting("finder_settings", ADMIN_PW_KEY if key=="admin_password" else key, val)
    return redirect(url_for("finder.admin"))


@finder_bp.route("/julisunkan/logout")
def admin_logout():
    session.pop("finder_admin", None)
    return redirect(url_for("finder.admin"))


@finder_bp.route("/julisunkan/purge-expired", methods=["POST"])
def admin_purge_expired():
    if not session.get("finder_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    purge_finder_files(GEN_DIR)
    return jsonify({"ok": True})


# ── User Reports ─────────────────────────────────────────────────

@finder_bp.route("/reports/submit", methods=["POST"])
def submit_report():
    data = request.get_json(force=True)
    content_id  = str(data.get("content_id", ""))[:100]
    reason      = str(data.get("reason", "")).strip()[:100]
    description = str(data.get("description", "")).strip()[:1000]
    if not reason:
        return jsonify({"error": "Reason is required"}), 400
    report_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO finder_reports VALUES (?,?,?,?,?,?,?,?)",
                 (report_id, content_id, reason, description, "pending", now(), None, None))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "report_id": report_id})


@finder_bp.route("/julisunkan/reports")
def admin_reports():
    if not session.get("finder_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM finder_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@finder_bp.route("/julisunkan/reports/<report_id>/review", methods=["POST"])
def admin_review_report(report_id):
    if not session.get("finder_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    action     = data.get("action", "")
    admin_note = str(data.get("note", "")).strip()[:500]
    if action not in ("approved", "declined"):
        return jsonify({"error": "Invalid action"}), 400
    conn = get_db()
    conn.execute("UPDATE finder_reports SET status=?, reviewed_at=?, admin_note=? WHERE id=?",
                 (action, now(), admin_note, report_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@finder_bp.route("/manifest.json")
def manifest():
    import json as _json
    data = {"name":"KDP Niche & Keyword Finder","short_name":"KDPFinder","start_url":"/finder/","display":"standalone","background_color":"#1a0a0a","theme_color":"#ffd700","icons":[{"src":"/static/finder/icon.png","sizes":"192x192","type":"image/png","purpose":"any"},{"src":"/static/finder/icon-maskable.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]}
    return Response(_json.dumps(data), mimetype="application/manifest+json")

@finder_bp.route("/sw.js")
def sw():
    js = "self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"
    return Response(js, mimetype="application/javascript")
