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

TIERS = {
    "free":   {"name": "Explorer",  "color": "#6b7280", "analyses_per_day": 3},
    "paid1":  {"name": "Speaker",   "color": "#b45309", "analyses_per_day": 20},
    "paid2":  {"name": "Coach",     "color": "#1d4ed8", "analyses_per_day": 50},
    "paid3":  {"name": "Curator",   "color": "#be123c", "analyses_per_day": 999},
}

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

GALLO_9_PRINCIPLES = """
Cele 9 principii Talk Like TED (Carmine Gallo):
1. PASIUNEA - Ce iti face sufletul sa cante? Discursul porneste de la motivatia autentica.
2. POVESTEA - Povestile conecteaza la audienta si schimba perceptiile.
3. CONVERSATIA - Nu monolog, ci dialog natural cu publicul.
4. CEVA NOU - Invata audienta ceva pe care nu l-a stiut inainte.
5. WOW FACTOR - Depaseste asteptarile, lasa audienta cu gura cascata.
6. UMOR - Sare si piper: creierul retine mai bine cand rade.
7. REGULA CELOR 18 MINUTE + REGULA CELOR 3 - Titlu, 3 mesaje cheie, structura clara.
8. MULTISENZORIAL - Vorbeste prin imagine, metafore vizuale, experiente senzoriale.
9. AUTENTICITATE - Fii transparent, scopul nu e prezentarea ci inspirarea.
"""

SCORING_GUIDE = """
GHID STRICT DE ACORDARE A SCORURILOR — respecta-l cu strictete:
- Scor 1-2: Principiul LIPSESTE COMPLET din text. Nu exista nicio urma a lui.
- Scor 3-4: Principiul este FOARTE SLAB prezent. O singura mentiune vaga, fara dezvoltare.
- Scor 5-6: Principiul este PARTIAL prezent. Exista elemente dar sunt insuficient dezvoltate.
- Scor 7-8: Principiul este BINE implementat. Clar prezent si eficient.
- Scor 9-10: Principiul este EXCEPTIONAL, de nivel TED global. Rar intalnit.

REGULI IMPORTANTE:
1. Scorurile TREBUIE sa fie diferite intre ele — nu da acelasi scor la mai mult de 2 principii.
2. Citeaza INTOTDEAUNA un fragment concret din text pentru a justifica scorul.
3. Daca textul e scurt sau vag, scorurile trebuie sa fie mici (3-5), nu medii.
4. Fii critic si onest — un scor de 9-10 se acorda doar pentru discursuri exceptionale.
5. Analizeaza DOAR ce este efectiv scris in text, nu ce ar putea fi sau ce intentiona speakerul.
"""

TED_CASE_STUDIES = {
    "Pasiunea": [
        {"title": "De ce vei esua in a avea o cariera de succes", "speaker": "Larry Smith"},
        {"title": "Aspectul fizic nu e totul. Credeti-ma, sunt manechin!", "speaker": "Cameron Russell"},
        {"title": "8 secrete pentru succes", "speaker": "Richard St. John"},
        {"title": "Obisnuintele fericirii", "speaker": "Matthieu Ricard"},
        {"title": "Viata la 9144 de metri", "speaker": "Richard Branson"},
        {"title": "Vrei sa ajuti pe cineva? Taci si asculta!", "speaker": "Ernesto Sirolli"},
        {"title": "Cele 12 perechi de picioare ale sale", "speaker": "Aimee Mullins"},
        {"title": "Puternicul atac de iluminare", "speaker": "Jill Bolte Taylor"},
    ],
    "Povestea": [
        {"title": "Scolile distrug creativitatea?", "speaker": "Sir Ken Robinson"},
        {"title": "O baie fara apa", "speaker": "Ludwick Marishane"},
        {"title": "Indiciile unei povesti extraordinare", "speaker": "Andrew Stanton"},
        {"title": "Cum sa atragi atentia in Noua Era digitala", "speaker": "Seth Godin"},
        {"title": "Reteta perfecta pentru sosul de spaghete", "speaker": "Malcolm Gladwell"},
        {"title": "Trebuie sa vorbim despre o nedreptate", "speaker": "Bryan Stevenson"},
        {"title": "Povesti despre pasiune", "speaker": "Isabel Allende"},
        {"title": "Politica fictiunii", "speaker": "Elif Shafak"},
    ],
    "Conversatia": [
        {"title": "Arta de a cere", "speaker": "Amanda Palmer"},
        {"title": "Fotografii marturie pentru sclavia moderna", "speaker": "Lisa Kristine"},
    ],
    "Ceva Nou": [
        {"title": "Inainte de Avatar... un baiat curios", "speaker": "James Cameron"},
        {"title": "Surprinzatoarea stiinta a motivarii", "speaker": "Dan Pink"},
        {"title": "Puterea introvertitilor", "speaker": "Susan Cain"},
        {"title": "Luati inapoi orasul cu vopsea", "speaker": "Edi Rama"},
        {"title": "Cum sa vinzi prezervative in Congo", "speaker": "Amy Lockwood"},
        {"title": "10 lucruri pe care nu le-ati stiut despre orgasm", "speaker": "Mary Roach"},
        {"title": "Explorarea oceanelor", "speaker": "Robert Ballard"},
        {"title": "De ce iubim, de ce inselam", "speaker": "Helen Fisher"},
    ],
    "WOW Factor": [
        {"title": "Puternicul atac de iluminare", "speaker": "Jill Bolte Taylor"},
        {"title": "Minunatii subacvatice", "speaker": "David Gallo"},
        {"title": "Noua bionica ce ne permite sa alergam", "speaker": "Hugh Herr"},
        {"title": "Roboti care zboara si coopereaza", "speaker": "Vijay Kumar"},
        {"title": "Zorile reinvierii speciilor disparute", "speaker": "Stewart Brand"},
        {"title": "Viitorul in depistarea timpurie a cancerului", "speaker": "Jorge Soto"},
        {"title": "Cel mai bun dar caruia i-am supravietuit", "speaker": "Stacey Kramer"},
    ],
    "Umor": [
        {"title": "De ce devin videoclipurile virale", "speaker": "Kevin Allocca"},
        {"title": "Modul in care gandim despre caritate e complet gresit", "speaker": "Dan Pallotta"},
        {"title": "Vor fi copiii nostri o specie diferita?", "speaker": "Juan Enriquez"},
        {"title": "Despre usurare. Fara gluma.", "speaker": "Rose George"},
        {"title": "Matemagic", "speaker": "Arthur Benjamin"},
    ],
    "Regula celor 18 min": [
        {"title": "3 A pentru o viata minunata", "speaker": "Neil Pasricha"},
        {"title": "Despre renovarea urbana", "speaker": "Majora Carter"},
    ],
    "Multisenzorial": [
        {"title": "Cum sa transformi apa murdara in apa potabila", "speaker": "Michael Pritchard"},
        {"title": "Vestile bune despre saracie", "speaker": "Bono"},
        {"title": "Despre evitarea crizei climei", "speaker": "Al Gore"},
        {"title": "Misterul durerii cronice", "speaker": "Elliot Krane"},
        {"title": "Imagini cu statistici socante", "speaker": "Chris Jordan"},
        {"title": "Energie: Inovand spre zero!", "speaker": "Bill Gates"},
        {"title": "Cel mai bun dar caruia i-am supravietuit", "speaker": "Stacey Kramer"},
    ],
    "Autenticitate": [
        {"title": "De ce avem prea putini lideri femei", "speaker": "Sheryl Sandberg"},
        {"title": "Scolile distrug creativitatea?", "speaker": "Sir Ken Robinson"},
        {"title": "Puterea introvertitilor", "speaker": "Susan Cain"},
    ],
}

def format_case_studies_for_prompt():
    result = "\nSTUDII DE CAZ TED selectate curatorial de Tibi Ruczui, Curator TEDxBrasov (10+ ani):\n"
    for principle, talks in TED_CASE_STUDIES.items():
        result += f"\n{principle}:\n"
        for t in talks:
            result += f"  - '{t['title']}' de {t['speaker']}\n"
    return result

def analyze_speech_free(text):
    prompt = f"""
Esti un evaluator strict de discursuri TEDx.
Analizeaza urmatorul text si acorda scoruri DIFERENTIATE si JUSTIFICATE.

{SCORING_GUIDE}

Returneaza DOAR un JSON valid, fara alt text:
{{
  "Idea Strength": {{ "score": 0, "recommendation": "Citeaza un fragment din text si explica scorul." }},
  "Structural Integrity": {{ "score": 0, "recommendation": "Citeaza un fragment din text si explica scorul." }},
  "Cognitive Load": {{ "score": 0, "recommendation": "Citeaza un fragment din text si explica scorul." }},
  "Emotional Arc": {{ "score": 0, "recommendation": "Citeaza un fragment din text si explica scorul." }},
  "Memorability Factor": {{ "score": 0, "recommendation": "Citeaza un fragment din text si explica scorul." }}
}}

Text de analizat: {text}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return {"tier": "free", "analysis": json.loads(content)}
    except:
        return {"tier": "free", "error": content}

def analyze_speech_paid1(text):
    case_studies = format_case_studies_for_prompt()
    prompt = f"""
Esti un evaluator strict de discursuri TEDx, expert in metodologia Carmine Gallo.
Analizeaza textul urmator prin prisma celor 9 principii si acorda scoruri DIFERENTIATE si JUSTIFICATE.

{GALLO_9_PRINCIPLES}

{SCORING_GUIDE}

{case_studies}

IMPORTANT:
- Citeaza fragmente CONCRETE din text pentru fiecare scor.
- Cand scorul e sub 7, recomanda un studiu de caz TED din lista de mai sus.
- Scorurile TREBUIE sa fie diferite — reflecta realitatea textului, nu o medie.

Returneaza DOAR un JSON valid:
{{
  "Pasiunea": {{ "score": 0, "present": false, "recommendation": "Citat din text + explicatie scor + studiu de caz daca scorul < 7" }},
  "Povestea": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Conversatia": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Ceva Nou": {{ "score": 0, "present": false, "recommendation": "..." }},
  "WOW Factor": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Umor": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Regula celor 18 min": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Multisenzorial": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Autenticitate": {{ "score": 0, "present": false, "recommendation": "..." }}
}}

Text de analizat: {text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
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
    case_studies = format_case_studies_for_prompt()
    prompt = f"""
Esti un coach avansat de TED talks, cu experienta curatorului TEDxBrasov.
Analizeaza textul si creeaza un plan de coaching structurat pe 9 sesiuni.
Fii CRITIC si SPECIFIC — bazeaza-te exclusiv pe ce este scris in text.

{GALLO_9_PRINCIPLES}

{SCORING_GUIDE}

{case_studies}

IMPORTANT:
- Pentru fiecare sesiune, citeaza un fragment concret din text care justifica nivelul principiului.
- Include un studiu de caz TED din lista de mai sus pentru fiecare sesiune.
- Exercitiile trebuie sa fie SPECIFICE pentru acest text, nu generice.

Returneaza DOAR un JSON valid:
{{
  "overall_score": 0,
  "summary": "Analiza critica si specifica a discursului in 2-3 propozitii, cu referinte la text.",
  "strengths": ["punct forte specific din text 1", "punct forte specific 2", "punct forte specific 3"],
  "coaching_sessions": [
    {{
      "day": 1,
      "principle": "Pasiunea",
      "status": "absent",
      "score": 0,
      "text_evidence": "Citat sau referinta concreta din text",
      "exercise": "Exercitiu specific bazat pe textul analizat",
      "example_question": "Intrebare de reflectie personalizata",
      "ted_example": "Titlul TED talk-ului recomandat din lista",
      "ted_speaker": "Numele speakerului"
    }}
  ],
  "next_steps": ["actiune concreta 1 bazata pe text", "actiune concreta 2", "actiune concreta 3"]
}}

Text de analizat: {text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
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
    case_studies = format_case_studies_for_prompt()
    prompt = f"""
Esti Tibi Ruczui, curatorul TEDxBrasov, cu 10+ ani de experienta.
Vorbesti direct cu speakerul, ca un mentor personal, cald dar EXIGENT si CRITIC.
Bazeaza-te EXCLUSIV pe ce este scris in text — nu presupune, nu completa, nu inventa.

{GALLO_9_PRINCIPLES}

{SCORING_GUIDE}

{case_studies}

IMPORTANT:
- Fiecare scor trebuie sa fie JUSTIFICAT cu un citat sau referinta concreta din text.
- Scorurile TREBUIE sa fie diferite — reflecta realitatea textului.
- Pentru fiecare principiu cu scor sub 7, recomanda personal un studiu de caz TED.
- Fii sincer chiar daca scorul general e mic — un curator bun nu minte.

Returneaza DOAR un JSON valid:
{{
  "curator_message": "Mesaj personal direct catre speaker, bazat pe ce ai citit efectiv in text (3-4 propozitii sincere)",
  "overall_score": 0,
  "curator_verdict": "Gata pentru scena|Aproape gata|Mai avem de lucru|Revenim de la zero",
  "what_moved_me": "Ce anume din text te-a impresionat, cu citat",
  "what_worries_me": "Ce anume din text te ingrijoreaza, cu citat",
  "nine_principles_check": {{
    "Pasiunea": {{ "score": 0, "curator_note": "Citat din text + observatie personala + studiu de caz daca scorul < 7" }},
    "Povestea": {{ "score": 0, "curator_note": "..." }},
    "Conversatia": {{ "score": 0, "curator_note": "..." }},
    "Ceva Nou": {{ "score": 0, "curator_note": "..." }},
    "WOW Factor": {{ "score": 0, "curator_note": "..." }},
    "Umor": {{ "score": 0, "curator_note": "..." }},
    "Regula celor 18 min": {{ "score": 0, "curator_note": "..." }},
    "Multisenzorial": {{ "score": 0, "curator_note": "..." }},
    "Autenticitate": {{ "score": 0, "curator_note": "..." }}
  }},
  "stage_readiness": {{
    "ready_to_present": false,
    "estimated_sessions_needed": 0,
    "priority_action": "Cel mai important lucru specific de facut acum"
  }}
}}

Text de analizat: {text}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
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
    scores = {}
    if tier == "free":
        scores = {k: v.get("score", 0) for k, v in analysis.items() if isinstance(v, dict)}
    elif tier == "paid1":
        scores = {k: v.get("score", 0) for k, v in analysis.items() if isinstance(v, dict)}
    elif tier == "paid2":
        sessions = analysis.get("coaching_sessions", [])
        scores = {s["principle"]: s.get("score", 7) for s in sessions}
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
        for crit, data in analysis.items():
            if isinstance(data, dict):
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, clean(f"{crit}: {data.get('score', 0)}/10"), ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean(f"Recomandare: {data.get('recommendation', '')}"))
                pdf.ln(2)
    elif tier == "paid1" and isinstance(analysis, dict):
        for crit, data in analysis.items():
            if isinstance(data, dict):
                present = "+" if data.get("present") else "-"
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, clean(f"{present} {crit}: {data.get('score', 0)}/10"), ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean(data.get("recommendation", "")))
                pdf.ln(2)
    elif tier == "paid2" and isinstance(analysis, dict):
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, clean(f"Scor general: {analysis.get('overall_score', 'N/A')}/10"), ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(analysis.get("summary", "")))
        pdf.ln(4)
        for session in analysis.get("coaching_sessions", []):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, clean(f"Ziua {session.get('day', '')}: {session.get('principle', '')} — {session.get('score', 0)}/10"), ln=True)
            pdf.set_font("Arial", "", 10)
            if session.get("text_evidence"):
                pdf.multi_cell(0, 6, clean(f"Din textul tau: {session.get('text_evidence', '')}"))
            pdf.multi_cell(0, 6, clean(f"Exercitiu: {session.get('exercise', '')}"))
            if session.get("ted_example"):
                pdf.multi_cell(0, 6, clean(f"Studiu de caz: {session.get('ted_example')} - {session.get('ted_speaker', '')}"))
            pdf.ln(2)
    elif tier == "paid3" and isinstance(analysis, dict):
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, clean(f"Verdict curator: {analysis.get('curator_verdict', '')}"), ln=True)
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
        pdf.ln(4)
        for principle, data in analysis.get("nine_principles_check", {}).items():
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, clean(f"{principle}: {data.get('score', 0)}/10"), ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, clean(data.get("curator_note", "")))
            pdf.ln(2)
    if radar_img:
        pdf.ln(5)
        pdf.image(radar_img, x=55, w=100)
    pdf.output(pdf_filename)
    return pdf_filename

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
        flash("Email sau parola incorecta.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        users = load_users()
        if email in users:
            flash("Acest email este deja inregistrat.")
        elif len(password) < 6:
            flash("Parola trebuie sa aiba cel putin 6 caractere.")
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
