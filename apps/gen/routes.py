import os, io, uuid, json
from datetime import datetime
from flask import (Blueprint, render_template, request, jsonify,
                   send_file, redirect, url_for, session, Response)
from groq import Groq
from db import get_db, get_setting, set_setting
from cleanup import purge_gen_files

gen_bp = Blueprint("gen", __name__)

GEN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated", "gen")
os.makedirs(GEN_DIR, exist_ok=True)

ADMIN_PW_KEY = "gen_admin_pw"
DEFAULT_PW   = "admin123"

PAPER_SIZES = {
    "6x9":    (432, 648),
    "8.5x11": (612, 792),
    "5x8":    (360, 576),
    "7x10":   (504, 720),
}

INTERIOR_TEMPLATES = [
    {"id": "wide_lined",    "name": "Wide-Ruled Lined",    "icon": "≡"},
    {"id": "college_lined", "name": "College-Ruled Lined", "icon": "≡"},
    {"id": "narrow_lined",  "name": "Narrow-Ruled Lined",  "icon": "≡"},
    {"id": "blank",         "name": "Blank Pages",         "icon": "□"},
    {"id": "dot_grid",      "name": "Dot Grid",            "icon": "⁞"},
    {"id": "graph",         "name": "Graph / Grid",        "icon": "⊞"},
    {"id": "cornell",       "name": "Cornell Notes",       "icon": "📋"},
    {"id": "daily_planner", "name": "Daily Planner",       "icon": "📅"},
    {"id": "weekly_plan",   "name": "Weekly Planner",      "icon": "🗓"},
    {"id": "habit_tracker", "name": "Habit Tracker",       "icon": "✅"},
    {"id": "budget",        "name": "Budget Tracker",      "icon": "💰"},
    {"id": "gratitude",     "name": "Gratitude Journal",   "icon": "🙏"},
    {"id": "prayer",        "name": "Prayer Journal",      "icon": "✝"},
    {"id": "meal_plan",     "name": "Meal Planner",        "icon": "🥗"},
    {"id": "password_log",  "name": "Password Log",        "icon": "🔐"},
    {"id": "recipe",        "name": "Recipe Template",     "icon": "📖"},
    {"id": "goal_tracker",  "name": "Goal Tracker",        "icon": "🎯"},
    {"id": "storyboard",    "name": "Storyboard",          "icon": "🎬"},
    {"id": "music_staff",   "name": "Music Staff",         "icon": "🎵"},
    {"id": "bullet_journal","name": "Bullet Journal",      "icon": "•"},
]

COVER_TEMPLATES = [
    {"id": "minimal",    "name": "Minimal Classic"},
    {"id": "bold",       "name": "Bold & Modern"},
    {"id": "elegant",    "name": "Elegant Dark"},
    {"id": "vibrant",    "name": "Vibrant Gradient"},
    {"id": "rustic",     "name": "Rustic Texture"},
    {"id": "academic",   "name": "Academic Blue"},
    {"id": "playful",    "name": "Playful Color"},
    {"id": "monochrome", "name": "Monochrome"},
    {"id": "nature",     "name": "Nature Green"},
    {"id": "sunset",     "name": "Sunset Warm"},
]


# ── Helpers ─────────────────────────────────────────────────────

def now():
    return datetime.utcnow().isoformat()

def get_groq():
    key = get_setting("gen_settings", "groq_api_key")
    return Groq(api_key=key) if key else None


def draw_interior(tpl_id, page_w, page_h, c, margin=36):
    """Draw one page of interior content using reportlab canvas."""
    from reportlab.lib.colors import HexColor
    gray    = HexColor("#CCCCCC")
    lt_gray = HexColor("#EEEEEE")
    blue    = HexColor("#334477")
    red_l   = HexColor("#FFAAAA")

    w = page_w - 2*margin
    h = page_h - 2*margin
    x0 = margin
    y0 = margin

    if tpl_id in ("wide_lined", "college_lined", "narrow_lined"):
        spacing = {"wide_lined": 28, "college_lined": 22, "narrow_lined": 18}[tpl_id]
        c.setStrokeColor(gray)
        c.setLineWidth(0.5)
        # Red margin line
        c.setStrokeColor(red_l)
        c.setLineWidth(1)
        c.line(x0 + 40, y0, x0 + 40, y0 + h)
        c.setStrokeColor(HexColor("#AACCFF"))
        c.setLineWidth(0.5)
        # Top blue line
        c.line(x0, y0 + h - 8, x0 + w, y0 + h - 8)
        c.setStrokeColor(gray)
        y = y0 + h - spacing - 8
        while y >= y0:
            c.line(x0, y, x0 + w, y)
            y -= spacing

    elif tpl_id == "blank":
        c.setStrokeColor(lt_gray)
        c.setLineWidth(0.3)
        c.rect(x0, y0, w, h)

    elif tpl_id == "dot_grid":
        spacing = 18
        c.setFillColor(gray)
        y = y0
        while y <= y0 + h:
            x = x0
            while x <= x0 + w:
                c.circle(x, y, 0.8, fill=1, stroke=0)
                x += spacing
            y += spacing

    elif tpl_id == "graph":
        spacing = 18
        c.setStrokeColor(lt_gray)
        c.setLineWidth(0.4)
        y = y0
        while y <= y0 + h:
            c.line(x0, y, x0 + w, y)
            y += spacing
        x = x0
        while x <= x0 + w:
            c.line(x, y0, x, y0 + h)
            x += spacing

    elif tpl_id == "cornell":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        # Cue column (left 1/4)
        cue_x = x0 + w * 0.28
        c.line(cue_x, y0 + 60, cue_x, y0 + h)
        # Summary area (bottom)
        c.line(x0, y0 + 60, x0 + w, y0 + 60)
        # Lines in main area
        spacing = 22
        y = y0 + h - spacing
        while y >= y0 + 65:
            c.line(cue_x + 4, y, x0 + w, y)
            y -= spacing
        # Lines in cue area
        y = y0 + h - spacing
        while y >= y0 + 65:
            c.line(x0, y, cue_x - 4, y)
            y -= spacing

    elif tpl_id == "daily_planner":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        from reportlab.lib.colors import HexColor
        c.setFillColor(HexColor("#2d1b69")); c.setFont("Helvetica-Bold", 9)
        # Time slots 6am-10pm
        hours = list(range(6, 23))
        slot_h = (h - 40) / len(hours)
        y = y0 + h - 20
        c.drawString(x0, y, "DATE: _______________   PRIORITY TODAY: ______________________")
        y -= 25
        for hr in hours:
            label = f"{'0'+str(hr) if hr<10 else hr}:00"
            c.setFillColor(HexColor("#2d1b69")); c.drawString(x0, y - slot_h/2, label)
            c.setStrokeColor(gray); c.line(x0+30, y, x0+w, y)
            c.setStrokeColor(lt_gray); c.line(x0+30, y - slot_h/2, x0+w, y - slot_h/2)
            y -= slot_h

    elif tpl_id == "weekly_plan":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        days = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
        col_w = w / 7
        c.setFillColor(HexColor("#2d1b69")); c.setFont("Helvetica-Bold", 8)
        for i, day in enumerate(days):
            dx = x0 + i * col_w
            c.drawCentredString(dx + col_w/2, y0 + h - 14, day)
            c.line(dx, y0, dx, y0 + h - 18)
            # Lines inside column
            line_y = y0 + h - 30
            while line_y >= y0:
                c.setStrokeColor(gray); c.line(dx+2, line_y, dx+col_w-2, line_y)
                line_y -= 20

    elif tpl_id == "habit_tracker":
        c.setStrokeColor(gray); c.setLineWidth(0.4)
        c.setFont("Helvetica-Bold", 8); c.setFillColor(HexColor("#2d1b69"))
        rows = 20; cols = 31
        cell_w = (w - 100) / cols; cell_h = (h - 40) / rows
        # Header: MONTH ___
        c.drawString(x0, y0 + h - 14, "MONTH: _______________")
        # Col numbers
        for col in range(cols):
            c.drawCentredString(x0 + 100 + col * cell_w + cell_w/2, y0 + h - 28, str(col+1))
        # Rows
        for row in range(rows):
            ry = y0 + h - 40 - row * cell_h
            c.setFont("Helvetica", 7)
            c.drawString(x0, ry - cell_h/2 + 2, f"Habit {row+1}: ___________")
            for col in range(cols):
                cx = x0 + 100 + col * cell_w
                c.rect(cx, ry - cell_h, cell_w, cell_h)

    elif tpl_id == "budget":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        c.setFont("Helvetica-Bold", 9); c.setFillColor(HexColor("#2d1b69"))
        headers = ["CATEGORY","BUDGETED","ACTUAL","DIFFERENCE"]
        col_ws = [w*0.35, w*0.2, w*0.2, w*0.25]
        header_y = y0 + h - 20
        c.drawString(x0, header_y + 6, "BUDGET TRACKER  ·  Month: _______________")
        header_y -= 16
        cx = x0
        for i, (hdr, cw) in enumerate(zip(headers, col_ws)):
            c.drawString(cx + 2, header_y, hdr)
            cx += cw
        c.line(x0, header_y - 4, x0+w, header_y - 4)
        rows = 22
        row_h = (header_y - 30 - y0) / rows
        for row in range(rows):
            ry = header_y - 8 - row * row_h
            cx = x0
            for cw in col_ws:
                c.line(cx, ry, cx+cw, ry)
                cx += cw
        # Totals row
        c.setLineWidth(1)
        c.line(x0, y0+20, x0+w, y0+20)
        c.setFont("Helvetica-Bold", 9); c.drawString(x0+2, y0+8, "TOTAL:")

    elif tpl_id == "gratitude":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        c.setFont("Helvetica-BoldOblique", 11); c.setFillColor(HexColor("#2d1b69"))
        c.drawCentredString(x0+w/2, y0+h-16, "Gratitude Journal")
        c.setFont("Helvetica", 8)
        c.drawCentredString(x0+w/2, y0+h-28, "Date: ________________")
        prompts = [
            "Today I am grateful for...",
            "Something beautiful I noticed...",
            "A person who made my day better...",
            "A challenge I am grateful for...",
            "Affirmation for today...",
        ]
        y = y0 + h - 50
        spacing = 22
        for prompt in prompts:
            c.setFont("Helvetica-Bold", 8); c.setFillColor(HexColor("#2d1b69"))
            c.drawString(x0, y, prompt)
            y -= spacing / 2
            for _ in range(3):
                c.setStrokeColor(gray); c.line(x0, y, x0+w, y)
                y -= spacing
            y -= 8

    elif tpl_id == "prayer":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        c.setFont("Helvetica-BoldOblique", 11); c.setFillColor(HexColor("#2d1b69"))
        c.drawCentredString(x0+w/2, y0+h-16, "Prayer Journal")
        c.setFont("Helvetica", 8); c.drawCentredString(x0+w/2, y0+h-28, "Date: ________________")
        sections = ["Prayer Requests:", "Praises & Answered Prayers:", "Scripture / Verse:", "Reflection:"]
        y = y0 + h - 50
        for sec in sections:
            c.setFont("Helvetica-Bold", 9); c.setFillColor(HexColor("#2d1b69"))
            c.drawString(x0, y, sec); y -= 16
            for _ in range(4):
                c.setStrokeColor(gray); c.line(x0, y, x0+w, y); y -= 22
            y -= 8

    elif tpl_id == "meal_plan":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        days = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
        meals = ["Breakfast","Lunch","Dinner","Snack"]
        col_w = (w-60) / len(days); row_h = (h-40) / len(meals)
        c.setFont("Helvetica-Bold", 8); c.setFillColor(HexColor("#2d1b69"))
        c.drawString(x0, y0+h-14, "MEAL PLANNER  ·  Week of: _______________")
        for i, day in enumerate(days):
            c.drawCentredString(x0+60+i*col_w+col_w/2, y0+h-28, day)
        for j, meal in enumerate(meals):
            my = y0+h-40-j*row_h
            c.drawString(x0+2, my-row_h/2+4, meal)
            c.line(x0+60, my, x0+w, my)
            for i in range(len(days)):
                c.line(x0+60+i*col_w, my, x0+60+i*col_w, my-row_h)

    elif tpl_id == "password_log":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        headers = ["Website/App", "Username/Email", "Password Hint", "Notes"]
        col_ws = [w*0.27, w*0.25, w*0.25, w*0.23]
        c.setFont("Helvetica-Bold", 9); c.setFillColor(HexColor("#2d1b69"))
        c.drawString(x0, y0+h-14, "PASSWORD LOG")
        hy = y0+h-28
        cx = x0
        for hdr, cw in zip(headers, col_ws):
            c.drawString(cx+2, hy, hdr); cx += cw
        c.line(x0, hy-4, x0+w, hy-4)
        rows = 25; row_h = (hy-10-y0)/rows
        for row in range(rows):
            ry = hy - 8 - row*row_h
            cx = x0
            for cw in col_ws:
                c.line(cx, ry, cx+cw, ry); cx += cw

    elif tpl_id == "recipe":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        c.setFont("Helvetica-Bold", 11); c.setFillColor(HexColor("#2d1b69"))
        c.drawString(x0, y0+h-16, "Recipe: _________________________________")
        c.setFont("Helvetica", 8)
        meta = ["Prep Time: _______  Cook Time: _______  Servings: _______  Difficulty: _______"]
        c.drawString(x0, y0+h-30, meta[0])
        c.line(x0, y0+h-34, x0+w, y0+h-34)
        half = w/2 - 5
        # Ingredients column
        c.setFont("Helvetica-Bold", 9); c.drawString(x0, y0+h-46, "INGREDIENTS")
        y = y0+h-60
        while y >= y0 + h//2:
            c.setStrokeColor(gray); c.line(x0, y, x0+half, y); y -= 20
        # Instructions column
        c.drawString(x0+half+10, y0+h-46, "INSTRUCTIONS")
        y = y0+h-60; step = 1
        while y >= y0:
            c.setFont("Helvetica", 8); c.setFillColor(HexColor("#999999"))
            c.drawString(x0+half+10, y, str(step)+"."); step+=1
            c.setStrokeColor(gray); c.line(x0+half+22, y, x0+w, y); y -= 22
        # Notes
        c.setFont("Helvetica-Bold",9); c.setFillColor(HexColor("#2d1b69"))
        c.drawString(x0, y0+h//2-6, "NOTES:"); c.line(x0, y0+h//2-10, x0+w, y0+h//2-10)

    elif tpl_id == "goal_tracker":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        c.setFont("Helvetica-Bold",11); c.setFillColor(HexColor("#2d1b69"))
        c.drawString(x0, y0+h-16, "GOAL TRACKER")
        c.setFont("Helvetica",8); c.drawString(x0, y0+h-28, "Goal: ________________________________  Deadline: ________________")
        c.line(x0, y0+h-32, x0+w, y0+h-32)
        sections = [("WHY THIS GOAL MATTERS", 4), ("ACTION STEPS", 8), ("OBSTACLES & SOLUTIONS", 4), ("MILESTONES", 4), ("NOTES & REFLECTION", 4)]
        y = y0+h-46
        for title, lines in sections:
            c.setFont("Helvetica-Bold",9); c.setFillColor(HexColor("#2d1b69"))
            c.drawString(x0, y, title); y -= 14
            for _ in range(lines):
                c.setStrokeColor(gray); c.line(x0, y, x0+w, y); y -= 20
            y -= 8

    elif tpl_id == "storyboard":
        c.setStrokeColor(gray); c.setLineWidth(0.5)
        cols, rows = 2, 3
        frame_w = (w-10) / cols; frame_h = (h-10) / rows
        c.setFont("Helvetica",7); c.setFillColor(HexColor("#2d1b69"))
        for r in range(rows):
            for col in range(cols):
                fx = x0 + col*(frame_w+5)
                fy = y0 + h - (r+1)*(frame_h+2) + 2
                c.rect(fx, fy+20, frame_w, frame_h-20)
                c.drawString(fx, fy+8, f"Scene {r*cols+col+1}: ____________________")
                c.line(fx, fy+4, fx+frame_w, fy+4)

    elif tpl_id == "music_staff":
        from reportlab.lib.colors import black as blk
        c.setStrokeColor(HexColor("#333333")); c.setLineWidth(0.8)
        staff_h = 8; staff_gap = 6; staves_per_group = 5; groups = 6
        group_height = staves_per_group*staff_h + 30
        y = y0 + h - 20
        for g in range(groups):
            for line in range(staves_per_group):
                ly = y - line*staff_h
                c.line(x0, ly, x0+w, ly)
            c.setLineWidth(1.5); c.line(x0, y, x0, y - (staves_per_group-1)*staff_h)
            c.setLineWidth(0.8)
            y -= group_height

    elif tpl_id == "bullet_journal":
        spacing = 20
        c.setStrokeColor(lt_gray); c.setLineWidth(0.4)
        y = y0
        while y <= y0+h:
            c.line(x0, y, x0+w, y); y += spacing
        x = x0
        while x <= x0+w:
            c.line(x, y0, x, y0+h); x += spacing
        # Dot at intersections
        c.setFillColor(gray)
        y = y0
        while y <= y0+h:
            x = x0
            while x <= x0+w:
                c.circle(x, y, 1, fill=1, stroke=0); x += spacing
            y += spacing


def generate_interior_pdf(tpl_id, page_count, paper_size):
    from reportlab.pdfgen import canvas as rc
    pw, ph = PAPER_SIZES.get(paper_size, PAPER_SIZES["6x9"])
    buf = io.BytesIO()
    c = rc.Canvas(buf, pagesize=(pw, ph))
    for _ in range(page_count):
        draw_interior(tpl_id, pw, ph, c)
        c.showPage()
    c.save()
    buf.seek(0)
    return buf


COVER_SCHEMES = {
    "minimal":    {"bg": "#FFFFFF", "fg": "#1a1a1a", "accent": "#444444"},
    "bold":       {"bg": "#1a1a2e", "fg": "#FFFFFF",  "accent": "#e94560"},
    "elegant":    {"bg": "#0f0f0f", "fg": "#D4AF37",  "accent": "#8B7536"},
    "vibrant":    {"bg": "#6c3483", "fg": "#FFFFFF",  "accent": "#f39c12"},
    "rustic":     {"bg": "#4a3728", "fg": "#f5deb3",  "accent": "#cd853f"},
    "academic":   {"bg": "#1B3A6B", "fg": "#FFFFFF",  "accent": "#FFD700"},
    "playful":    {"bg": "#FF6B6B", "fg": "#FFFFFF",  "accent": "#FFE66D"},
    "monochrome": {"bg": "#2C2C2C", "fg": "#FFFFFF",  "accent": "#AAAAAA"},
    "nature":     {"bg": "#1B4332", "fg": "#D8F3DC",  "accent": "#52B788"},
    "sunset":     {"bg": "#7F2700", "fg": "#FFE8D6",  "accent": "#E76F51"},
}


def generate_cover_pdf(title, subtitle, author, cover_tpl, prompt):
    from reportlab.pdfgen import canvas as rc
    from reportlab.lib.colors import HexColor
    # KDP full cover: front + spine + back (approx 6x9, 130 pages, no bleed for simplicity)
    # Front cover only for simplicity: 6x9 at 300dpi → 1800x2700px, but PDF points 432x648
    pw, ph = 432, 648
    buf = io.BytesIO()
    c = rc.Canvas(buf, pagesize=(pw, ph))
    scheme = COVER_SCHEMES.get(cover_tpl, COVER_SCHEMES["minimal"])
    bg_c  = HexColor(scheme["bg"])
    fg_c  = HexColor(scheme["fg"])
    acc_c = HexColor(scheme["accent"])

    # Background
    c.setFillColor(bg_c); c.rect(0, 0, pw, ph, fill=1, stroke=0)

    # Decorative element top
    c.setFillColor(acc_c)
    c.rect(0, ph-80, pw, 80, fill=1, stroke=0)

    # Accent stripe bottom
    c.setFillColor(acc_c)
    c.rect(0, 0, pw, 60, fill=1, stroke=0)

    # Title
    c.setFillColor(fg_c)
    title_lines = []
    words = title.split()
    line = ""
    for w2 in words:
        test = line + " " + w2 if line else w2
        if len(test) > 22:
            title_lines.append(line); line = w2
        else:
            line = test
    if line: title_lines.append(line)

    font_size = 42 if len(title) < 20 else 32 if len(title) < 35 else 24
    y_title = ph * 0.62
    c.setFont("Helvetica-Bold", font_size)
    for line in title_lines:
        c.drawCentredString(pw/2, y_title, line)
        y_title -= font_size + 4

    # Subtitle
    if subtitle:
        c.setFont("Helvetica-Oblique", 16)
        c.setFillColor(acc_c if scheme["bg"] != "#FFFFFF" else HexColor("#555555"))
        c.drawCentredString(pw/2, y_title - 14, subtitle[:50])

    # Author
    c.setFont("Helvetica", 14)
    c.setFillColor(fg_c)
    c.drawCentredString(pw/2, 24, author or "Author Name")

    # Decorative line
    c.setStrokeColor(acc_c); c.setLineWidth(2)
    c.line(40, ph*0.42, pw-40, ph*0.42)

    c.save()
    buf.seek(0)
    return buf


# ── Routes ───────────────────────────────────────────────────────

@gen_bp.route("/")
def index():
    purge_gen_files(GEN_DIR)
    return render_template("gen/index.html",
                           interior_templates=INTERIOR_TEMPLATES,
                           cover_templates=COVER_TEMPLATES,
                           paper_sizes=list(PAPER_SIZES.keys()))


@gen_bp.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    ptype      = data.get("type", "interior")
    tpl_id     = data.get("template_id", "wide_lined")
    paper_size = data.get("paper_size", "6x9")
    page_count = max(1, min(int(data.get("page_count", 120)), 500))
    title      = data.get("title", "My Book")[:100]
    subtitle   = data.get("subtitle", "")[:80]
    author     = data.get("author", "")[:60]
    prompt     = data.get("prompt", "")[:500]

    proj_id  = str(uuid.uuid4())
    out_name = f"{proj_id}.pdf"
    out_path = os.path.join(GEN_DIR, out_name)

    try:
        if ptype == "interior":
            buf = generate_interior_pdf(tpl_id, page_count, paper_size)
        else:
            buf = generate_cover_pdf(title, subtitle, author, tpl_id, prompt)

        with open(out_path, "wb") as f:
            f.write(buf.read())

        conn = get_db()
        conn.execute("INSERT INTO gen_projects VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (proj_id, title, ptype, tpl_id, prompt, page_count, paper_size, out_name, "done", now()))
        conn.commit()
        conn.close()
        return jsonify({"project_id": proj_id, "filename": out_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gen_bp.route("/enhance-prompt", methods=["POST"])
def enhance_prompt():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
    ptype  = data.get("type", "interior")
    client = get_groq()
    if not client:
        return jsonify({"error": "Groq API key not set in admin panel"}), 400
    system = "You are a KDP book publishing expert. Help users create better book descriptions and prompts."
    user_msg = f"""Given this prompt for a KDP {ptype}: "{prompt}"
Suggest improvements and return a JSON object:
{{"enhanced_prompt": "improved description", "suggested_title": "great title", "suggested_subtitle": "subtitle", "target_audience": "description", "tips": ["tip1","tip2","tip3"]}}
Return ONLY valid JSON."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":user_msg}],
            max_tokens=1024, temperature=0.7)
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return jsonify(json.loads(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@gen_bp.route("/download/<proj_id>")
def download(proj_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM gen_projects WHERE id=?", (proj_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    path = os.path.join(GEN_DIR, row["out_file"])
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    label = "interior" if row["project_type"] == "interior" else "cover"
    return send_file(path, mimetype="application/pdf",
                     as_attachment=True, download_name=f"kdp_{label}_{proj_id[:8]}.pdf")


@gen_bp.route("/history")
def history():
    conn = get_db()
    rows = conn.execute("SELECT * FROM gen_projects ORDER BY created_at DESC LIMIT 30").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── Admin ────────────────────────────────────────────────────────

@gen_bp.route("/julisunkan", methods=["GET", "POST"])
def admin():
    if not session.get("gen_admin"):
        if request.method == "POST":
            pw = request.form.get("password", "")
            stored = get_setting("gen_settings", ADMIN_PW_KEY) or DEFAULT_PW
            if pw == stored:
                session["gen_admin"] = True
                return redirect(url_for("gen.admin"))
            return render_template("gen/admin.html", error="Wrong password", logged_in=False)
        return render_template("gen/admin.html", logged_in=False, error=None)
    settings = {
        "groq_api_key":  get_setting("gen_settings", "groq_api_key"),
        "admin_password": get_setting("gen_settings", ADMIN_PW_KEY) or DEFAULT_PW,
    }
    conn = get_db()
    stats = {
        "total": conn.execute("SELECT COUNT(*) FROM gen_projects").fetchone()[0],
        "interiors": conn.execute("SELECT COUNT(*) FROM gen_projects WHERE project_type='interior'").fetchone()[0],
        "covers": conn.execute("SELECT COUNT(*) FROM gen_projects WHERE project_type='cover'").fetchone()[0],
    }
    conn.close()
    return render_template("gen/admin.html", logged_in=True, settings=settings, stats=stats, error=None)


@gen_bp.route("/julisunkan/save", methods=["POST"])
def admin_save():
    if not session.get("gen_admin"): return redirect(url_for("gen.admin"))
    for key in ["groq_api_key", "admin_password"]:
        val = request.form.get(key, "")
        if key == "admin_password" and not val: continue
        set_setting("gen_settings", ADMIN_PW_KEY if key == "admin_password" else key, val)
    return redirect(url_for("gen.admin"))


@gen_bp.route("/julisunkan/logout")
def admin_logout():
    session.pop("gen_admin", None)
    return redirect(url_for("gen.admin"))


@gen_bp.route("/julisunkan/purge-expired", methods=["POST"])
def admin_purge_expired():
    if not session.get("gen_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    purge_gen_files(GEN_DIR)
    return jsonify({"ok": True})


# ── User Reports ─────────────────────────────────────────────────

@gen_bp.route("/reports/submit", methods=["POST"])
def submit_report():
    data = request.get_json(force=True)
    content_id  = str(data.get("content_id", ""))[:100]
    reason      = str(data.get("reason", "")).strip()[:100]
    description = str(data.get("description", "")).strip()[:1000]
    if not reason:
        return jsonify({"error": "Reason is required"}), 400
    report_id = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO gen_reports VALUES (?,?,?,?,?,?,?,?)",
                 (report_id, content_id, reason, description, "pending", now(), None, None))
    conn.commit(); conn.close()
    return jsonify({"ok": True, "report_id": report_id})


@gen_bp.route("/julisunkan/reports")
def admin_reports():
    if not session.get("gen_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = conn.execute("SELECT * FROM gen_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@gen_bp.route("/julisunkan/reports/<report_id>/review", methods=["POST"])
def admin_review_report(report_id):
    if not session.get("gen_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    action     = data.get("action", "")
    admin_note = str(data.get("note", "")).strip()[:500]
    if action not in ("approved", "declined"):
        return jsonify({"error": "Invalid action"}), 400
    conn = get_db()
    conn.execute("UPDATE gen_reports SET status=?, reviewed_at=?, admin_note=? WHERE id=?",
                 (action, now(), admin_note, report_id))
    conn.commit(); conn.close()
    return jsonify({"ok": True})


@gen_bp.route("/manifest.json")
def manifest():
    import json as _json
    data = {"name":"KDP Interior with Cover Generator","short_name":"KDP Interior with Cover Generator","start_url":"/gen/","display":"standalone","background_color":"#2d1b69","theme_color":"#ff6b6b","icons":[{"src":"/static/gen/icon.png","sizes":"192x192","type":"image/png","purpose":"any"},{"src":"/static/gen/icon-maskable.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]}
    return Response(_json.dumps(data), mimetype="application/manifest+json")

@gen_bp.route("/sw.js")
def sw():
    js = "self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"
    return Response(js, mimetype="application/javascript")
