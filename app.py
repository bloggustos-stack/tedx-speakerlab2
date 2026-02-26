import os

from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
from openai import OpenAI
from fpdf import FPDF
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from datetime import datetime
import numpy as np
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tedx-speakerlab-secret-2024")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ─────────────────────────────────────────────
# TIER SYSTEM
# ─────────────────────────────────────────────
TIERS = {
    "free":   {"name": "Explorer",  "color": "#6b7280", "analyses_per_day": 3},
    "paid1":  {"name": "Speaker",   "color": "#b45309", "analyses_per_day": 20},
    "paid2":  {"name": "Coach",     "color": "#1d4ed8", "analyses_per_day": 50},
    "paid3":  {"name": "Curator",   "color": "#be123c", "analyses_per_day": 999},
}

# ─────────────────────────────────────────────
# SIMPLE USER STORE (file-based, no DB needed)
# ─────────────────────────────────────────────
if not os.path.exists("data"):
    os.makedirs("data")

users_file   = "data/users.json"
history_file = "data/history.json"
pdf_folder   = "data/pdf"
if not os.path.exists(pdf_folder):
    os.makedirs(pdf_folder)

def load_users():
    if os.path.exists(users_file):
        with open(users_file) as f:
            return json.load(f)
    # Default admin user
    return {
        "tibiruczui@yahoo.com": {
            "password": hash_password("admin123"),
            "name": "Tibi Ruczui",
            "tier": "paid3",
            "created": datetime.now().isoformat()
        }
    }

def save_users(users):
    with open(users_file, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ─────────────────────────────────────────────
# AUTH HELPERS
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_email" not in session:
        return None
    users = load_users()
    email = session["user_email"]
    user = users.get(email, {})
    user["email"] = email
    return user

# ─────────────────────────────────────────────
# ANALYSIS ENGINE
# ─────────────────────────────────────────────
GALLO_9_PRINCIPLES = """
Cele 9 principii "Talk Like TED" (Carmine Gallo), prin vocea curatorului TEDxBrașov:
1. PASIUNEA — Ce îți face sufletul să cânte? Discursul pornește de la motivația autentică.
2. POVESTEA — Poveștile conectează la audiență și schimbă percepțiile.
3. CONVERSAȚIA — Nu monolog, ci dialog natural cu publicul.
4. CEVA NOU — Învață audiența ceva pe care nu l-a știut înainte.
5. WOW FACTOR — Depășește așteptările, lasă audiența cu gura căscată.
6. UMOR — Sare și piper: creierul reține mai bine când râde.
7. REGULA CELOR 18 MINUTE + REGULA CELOR 3 — Titlu, 3 mesaje cheie, structură clară.
8. MULTISENZORIAL — Vorbește prin imagine, metafore vizuale, experiențe senzoriale.
9. AUTENTICITATE — Fii transparent, scopul nu e prezentarea ci inspirarea.
"""

def analyze_speech_free(text):
    """Free tier: 5 basic criteria, GPT-3.5"""
    prompt = f"""
Analizeaza urmatorul text ca pentru un speaker TEDx.
Returneaza DOAR un JSON valid, fara alt text, cu structura exacta:
{{
  "Idea Strength": {{ "score": 7, "recommendation": "..." }},
  "Structural Integrity": {{ "score": 7, "recommendation": "..." }},
  "Cognitive Load": {{ "score": 7, "recommendation": "..." }},
  "Emotional Arc": {{ "score": 7, "recommendation": "..." }},
  "Memorability Factor": {{ "score": 7, "recommendation": "..." }}
}}
Scorurile sunt intre 0 si 10. Recomandarile sa fie scurte si practice.
Text: {text}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    content = response.choices[0].message.content.strip()
    # Extract JSON even if wrapped in markdown
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return {"tier": "free", "analysis": json.loads(content)}
    except:
        return {"tier": "free", "error": content}

def analyze_speech_paid1(text):
    """Paid 1 (Speaker): 9 Gallo principles analysis, GPT-4o"""
    prompt = f"""
Ești un coach de public speaking expert în metodologia TED.
Analizează textul următor prin prisma celor 9 principii ale lui Carmine Gallo din "Talk Like TED".

{GALLO_9_PRINCIPLES}

Returnează DOAR un JSON valid cu această structură exactă:
{{
  "Pasiunea": {{ "score": 7, "present": true, "recommendation": "..." }},
  "Povestea": {{ "score": 7, "present": true, "recommendation": "..." }},
  "Conversatia": {{ "score": 7, "present": true, "recommendation": "..." }},
  "Ceva Nou": {{ "score": 7, "present": true, "recommendation": "..." }},
  "WOW Factor": {{ "score": 7, "present": false, "recommendation": "..." }},
  "Umor": {{ "score": 7, "present": false, "recommendation": "..." }},
  "Regula celor 18 min": {{ "score": 7, "present": true, "recommendation": "..." }},
  "Multisenzorial": {{ "score": 7, "present": false, "recommendation": "..." }},
  "Autenticitate": {{ "score": 7, "present": true, "recommendation": "..." }}
}}

Text: {text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    content = response.choices[0].message.content.strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return {"tier": "paid1", "analysis": json.loads(content)}
    except:
        return {"tier": "paid1", "error": content}

def analyze_speech_paid2(text):
    """Paid 2 (Coach): Full coaching session, day-by-day guide"""
    prompt = f"""
Ești un coach avansat de TED talks, cu experiența curatorului TEDxBrașov.
Analizează textul și creează un plan de coaching structurat pe 9 sesiuni (ca în blogul TEDxBrașov).

{GALLO_9_PRINCIPLES}

Returnează DOAR un JSON valid:
{{
  "overall_score": 7,
  "summary": "Rezumat general al discursului în 2-3 propoziții",
  "strengths": ["punct forte 1", "punct forte 2", "punct forte 3"],
  "coaching_sessions": [
    {{
      "day": 1,
      "principle": "Pasiunea",
      "status": "present",
      "exercise": "Exercițiu specific pentru speaker",
      "example_question": "Întrebare de reflecție pentru speaker",
      "ted_example": "Titlul unui TED talk relevant ca exemplu"
    }}
  ],
  "next_steps": ["acțiune concretă 1", "acțiune concretă 2", "acțiune concretă 3"]
}}

Text: {text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8
    )
    content = response.choices[0].message.content.strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return {"tier": "paid2", "analysis": json.loads(content)}
    except:
        return {"tier": "paid2", "error": content}

def analyze_speech_paid3(text):
    """Paid 3 (Curator): Tibi's voice, personal curator feedback"""
    prompt = f"""
Ești Tibi Ruczui, curatorul TEDxBrașov, cu ani de experiență în selectarea și pregătirea speakerilor.
Vorbești direct cu speakerul, ca un mentor personal, cald dar exigent.
Folosești perspectiva ta de curator bazată pe cele 9 principii Gallo și ghidul Chris Anderson.

{GALLO_9_PRINCIPLES}

Analizează textul și oferă feedback în vocea ta personală de curator.

Returnează DOAR un JSON valid:
{{
  "curator_message": "Mesaj personal direct către speaker, ca și cum i-ai vorbi față în față (3-4 propoziții calde și sincere)",
  "overall_score": 8,
  "curator_verdict": "Gata pentru scenă|Aproape gata|Mai avem de lucru|Revenim de la zero",
  "what_moved_me": "Ce te-a impresionat personal în discurs",
  "what_worries_me": "Ce te îngrijorează ca și curator",
  "nine_principles_check": {{
    "Pasiunea": {{ "score": 8, "curator_note": "observație personală scurtă" }},
    "Povestea": {{ "score": 7, "curator_note": "observație personală scurtă" }},
    "Conversatia": {{ "score": 6, "curator_note": "observație personală scurtă" }},
    "Ceva Nou": {{ "score": 8, "curator_note": "observație personală scurtă" }},
    "WOW Factor": {{ "score": 5, "curator_note": "observație personală scurtă" }},
    "Umor": {{ "score": 4, "curator_note": "observație personală scurtă" }},
    "Regula celor 18 min": {{ "score": 7, "curator_note": "observație personală scurtă" }},
    "Multisenzorial": {{ "score": 6, "curator_note": "observație personală scurtă" }},
    "Autenticitate": {{ "score": 9, "curator_note": "observație personală scurtă" }}
  }},
  "stage_readiness": {{
    "ready_to_present": false,
    "estimated_sessions_needed": 3,
    "priority_action": "Cel mai important lucru de făcut acum"
  }}
}}

Text: {text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )
    content = response.choices[0].message.content.strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return {"tier": "paid3", "analysis": json.loads(content)}
    except:
        return {"tier": "paid3", "error": content}

def analyze_by_tier(text, tier):
    if tier == "paid3":
        return analyze_speech_paid3(text)
    elif tier == "paid2":
        return analyze_speech_paid2(text)
    elif tier == "paid1":
        return analyze_speech_paid1(text)
    else:
        return analyze_speech_free(text)

# ─────────────────────────────────────────────
# HISTORY & PDF
# ─────────────────────────────────────────────
def save_history(email, text, result):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "email": email,
        "text": text[:200] + "..." if len(text) > 200 else text,
        "result": result
    }
    data = []
    if os.path.exists(history_file):
        with open(history_file) as f:
            data = json.load(f)
    data.append(entry)
    with open(history_file, "w") as f:
        json.dump(data, f, indent=2)

def generate_radar_image(scores, filename="radar.png"):
    labels = list(scores.keys())
    num_vars = len(labels)
    values = list(scores.values())
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, color='#be123c', linewidth=2)
    ax.fill(angles, values, color='#be123c', alpha=0.2)
    ax.set_xticks(angles[:-1])
    short_labels = [l[:12] for l in labels]
    ax.set_xticklabels(short_labels, size=8)
    ax.set_yticks(range(0, 11, 2))
    ax.set_ylim(0, 10)
    ax.grid(color='gray', linestyle='--', alpha=0.3)
    fig.patch.set_facecolor('#0f0f0f')
    ax.set_facecolor('#1a1a1a')
    ax.tick_params(colors='white')
    plt.tight_layout()
    plt.savefig(filename, dpi=150, facecolor='#0f0f0f')
    plt.close()
    return filename

def clean(text):
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def generate_pdf(text, result, user_name, tier):
    pdf_filename = f"{pdf_folder}/scorecard_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    analysis = result.get("analysis", {})

    # Extract scores for radar
    scores = {}
    if tier == "free":
        scores = {k: v.get("score", 0) for k, v in analysis.items() if isinstance(v, dict)}
    elif tier in ("paid1",):
        scores = {k: v.get("score", 0) for k, v in analysis.items() if isinstance(v, dict)}
    elif tier == "paid2":
        sessions = analysis.get("coaching_sessions", [])
        scores = {s["principle"]: 7 for s in sessions}
    elif tier == "paid3":
        principles = analysis.get("nine_principles_check", {})
        scores = {k: v.get("score", 0) for k, v in principles.items()}

    radar_img = None
    if scores:
        radar_img = generate_radar_image(scores, filename=pdf_filename.replace(".pdf", ".png"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "Speaker Lab AI - TEDxBrasov", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, clean(f"Speaker: {user_name} | Tier: {TIERS[tier]['name']} | {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    pdf.ln(8)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Discurs analizat:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, clean(text[:500] + ("..." if len(text) > 500 else "")))
    pdf.ln(6)

    if tier == "free" and isinstance(analysis, dict):
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, "Analiza de baza:", ln=True)
        for crit, data in analysis.items():
            if isinstance(data, dict):
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, clean(f"{crit}: {data.get('score', 0)}/10"), ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean(f"Recomandare: {data.get('recommendation', '')}"))
                pdf.ln(2)

    elif tier == "paid1" and isinstance(analysis, dict):
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, "Analiza - 9 Principii Gallo:", ln=True)
        for crit, data in analysis.items():
            if isinstance(data, dict):
                present = "✓" if data.get("present") else "✗"
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, clean(f"{present} {crit}: {data.get('score', 0)}/10"), ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean(data.get("recommendation", "")))
                pdf.ln(2)

    elif tier == "paid2" and isinstance(analysis, dict):
        pdf.set_font("Arial", "B", 13)
        overall = analysis.get("overall_score", "N/A")
        pdf.cell(0, 8, clean(f"Scor general: {overall}/10"), ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(analysis.get("summary", "")))
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 7, "Plan de coaching (9 sesiuni):", ln=True)
        for session in analysis.get("coaching_sessions", []):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, clean(f"Ziua {session.get('day', '')}: {session.get('principle', '')}"), ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, clean(f"Exercitiu: {session.get('exercise', '')}"))
            pdf.ln(2)

    elif tier == "paid3" and isinstance(analysis, dict):
        pdf.set_font("Arial", "B", 13)
        verdict = analysis.get("curator_verdict", "")
        pdf.cell(0, 8, clean(f"Verdict curator: {verdict}"), ln=True)
        pdf.set_font("Arial", "I", 11)
        pdf.multi_cell(0, 7, clean(analysis.get("curator_message", "")))
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 7, "Ce m-a impresionat:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(analysis.get("what_moved_me", "")))
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 7, "Ce ma ingrijoreaza:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(analysis.get("what_worries_me", "")))

    if radar_img:
        pdf.ln(5)
        pdf.image(radar_img, x=55, w=100)

    pdf.output(pdf_filename)
    return pdf_filename

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        users = load_users()
        user = users.get(email)
        if user and user["password"] == hash_password(password):
            session["user_email"] = email
            return redirect(url_for("index"))
        flash("Email sau parolă incorectă.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        users = load_users()
        if email in users:
            flash("Acest email este deja înregistrat.")
        elif len(password) < 6:
            flash("Parola trebuie să aibă cel puțin 6 caractere.")
        else:
            users[email] = {
                "password": hash_password(password),
                "name": name,
                "tier": "free",
                "created": datetime.now().isoformat()
            }
            save_users(users)
            session["user_email"] = email
            return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    user = get_current_user()
    result = None
    pdf_file = ""
    if request.method == "POST":
        text = request.form.get("speech_text", "")
        if text.strip():
            result = analyze_by_tier(text, user["tier"])
            save_history(user["email"], text, result)
            try:
                pdf_file = generate_pdf(text, result, user.get("name", "Speaker"), user["tier"])
            except Exception as e:
                print(f"PDF error: {e}")
    return render_template("index.html", result=result, pdf_file=pdf_file, user=user, tiers=TIERS)

@app.route("/upgrade")
@login_required
def upgrade():
    user = get_current_user()
    return render_template("upgrade.html", user=user, tiers=TIERS)

@app.route("/admin/set-tier", methods=["POST"])
@login_required
def set_tier():
    """Admin only: change user tier"""
    user = get_current_user()
    if user["tier"] != "paid3":
        return "Unauthorized", 403
    email = request.form.get("email")
    tier = request.form.get("tier")
    if tier not in TIERS:
        return "Invalid tier", 400
    users = load_users()
    if email in users:
        users[email]["tier"] = tier
        save_users(users)
    return redirect(url_for("admin"))

@app.route("/admin")
@login_required
def admin():
    user = get_current_user()
    if user["tier"] != "paid3":
        return "Unauthorized", 403
    users = load_users()
    return render_template("admin.html", user=user, users=users, tiers=TIERS)

@app.route("/download/<path:filename>")
@login_required
def download_pdf(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
