# KDP Platform Suite

## Overview
A 5-app KDP/Legal mega platform built with Flask. Each app has a unique URL prefix, theme, font, and completely isolated logic.

## Apps
| App | URL | Theme | Font | Purpose |
|-----|-----|-------|------|---------|
| Legal Risk Checker | /legal/ | Navy #1a2744 + Gold #c9a84c | Crimson Pro | Upload & analyze legal documents for risky clauses |
| KDP Generator | /gen/ | Purple #2d1b69 + Coral #ff6b6b | Poppins | Generate book interiors (20 templates) & covers (10 templates) |
| KDP Optimizer | /optimizer/ | Teal #0d3340 + Amber #f59e0b | Montserrat | Optimize titles, descriptions, keywords for KDP |
| KDP Bulk Creator | /bulk/ | Forest #0a2e1a + Lime #84cc16 | Inter | Create up to 50 books at once with AI metadata |
| KDP Finder | /finder/ | Crimson #1a0a0a + Gold #ffd700 | Raleway | Find profitable niches and keywords for KDP |

## Admin Pages
Each app has an admin page at `/<app>/julisunkan`:
- Default password: `admin123`
- Configure Groq API key per app
- View usage statistics
- Change admin password

## Architecture
- **Framework**: Flask with blueprints
- **Database**: SQLite (`database.db`) with separate tables per app (prefixed by app name)
- **AI**: Groq API (`llama-3.3-70b-versatile`) — configured per app in admin
- **PDF Generation**: reportlab (interiors + covers)
- **Document Parsing**: pypdf (PDF), python-docx (DOCX)
- **PWA**: Each app has its own manifest.json and sw.js served as routes
- **File Storage**: `uploads/<app>/` for uploads, `generated/<app>/` for outputs

## File Structure
```
app.py          - Flask app, blueprint registration, home route
main.py         - Entry point
db.py           - SQLite init, helpers
apps/
  legal/routes.py
  gen/routes.py
  optimizer/routes.py
  bulk/routes.py
  finder/routes.py
templates/
  home.html
  legal/index.html, admin.html
  gen/index.html, admin.html
  optimizer/index.html, admin.html
  bulk/index.html, admin.html
  finder/index.html, admin.html
static/
  legal/style.css, app.js, icon.png
  gen/style.css, app.js, icon.png
  optimizer/style.css, app.js, icon.png
  bulk/style.css, app.js, icon.png
  finder/style.css, app.js, icon.png
uploads/legal/   - uploaded documents
generated/*/     - generated PDFs and CSVs
```

## Gen App Templates (20 Interior + 10 Cover)
Interior: Wide-ruled, College-ruled, Narrow-ruled, Blank, Dot Grid, Graph, Cornell Notes, Daily Planner, Weekly Planner, Habit Tracker, Budget Tracker, Gratitude Journal, Prayer Journal, Meal Planner, Password Log, Recipe, Goal Tracker, Storyboard, Music Staff, Bullet Journal

Cover: Minimal, Bold, Elegant Dark, Vibrant, Rustic, Academic, Playful, Monochrome, Nature, Sunset

## Descriptions
Full descriptions, features, and keywords for all 5 apps are in the `descriptions/` folder:
- `descriptions/legal_risk_checker.txt`
- `descriptions/kdp_generator.txt`
- `descriptions/kdp_optimizer.txt`
- `descriptions/kdp_bulk_creator.txt`
- `descriptions/kdp_niche_finder.txt`

## Dependencies (requirements.txt)
```
flask==3.1.1
gunicorn==23.0.0
groq==1.1.1
pypdf==5.4.0
python-docx==1.1.2
reportlab==4.4.1
Pillow==11.2.1
```

## Running (local)
```
python3 -m gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

## Deploying to Render
A `render.yaml` blueprint is included for one-click deployment.

Steps:
1. Push this repo to GitHub.
2. In Render, click **New → Blueprint** and connect the repo.
3. Render will auto-detect `render.yaml` and configure the service.
4. Set any required environment variables (e.g. Groq API keys) in the Render dashboard.

**Note:** Render's free tier uses ephemeral disk storage — the SQLite `database.db`
and any files in `uploads/` and `generated/` will be wiped on each redeploy.
For persistent storage, upgrade to a paid Render plan and attach a persistent disk,
or migrate to a hosted database (e.g. PostgreSQL via Render's managed DB).
