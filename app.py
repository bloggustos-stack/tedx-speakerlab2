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
import time

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

MOTTO = "What you are speaks so loudly that I cannot hear what you say. - Ralph Waldo Emerson"

ARCHETYPES = {
    "Inocentul": {
        "emoji": "🌱", "group": "Ego-ul",
        "desire": "Sa fie fericit si in siguranta", "fear": "Sa fie pedepsit pentru o greseala",
        "description": "Puritate, optimism, credinta in bine.",
        "ted_example": "Malala Yousafzai", "superpower": "Inspira prin simplitate si autenticitate pura",
        "shadow": "Poate parea naiv, evita realitatea dificila",
        "qualities": ["optimism", "simplitate", "sinceritate", "incredere", "puritate"]
    },
    "Orfanul": {
        "emoji": "🌿", "group": "Ego-ul",
        "desire": "Sa apartina, sa fie conectat", "fear": "Sa fie abandonat sau exploatat",
        "description": "Realistul care intelege suferinta, cauta conexiunea.",
        "ted_example": "Brene Brown", "superpower": "Creeaza conexiune profunda prin vulnerabilitate",
        "shadow": "Poate cadea in victimizare sau cinism",
        "qualities": ["vulnerabilitate", "realitate", "conexiune", "empatie", "solidaritate"]
    },
    "Razboinicul": {
        "emoji": "🦁", "group": "Ego-ul",
        "desire": "Sa-si dovedeasca valoarea prin curaj", "fear": "Sa para slab sau vulnerabil",
        "description": "Depaseste obstacole, inspira prin curaj si actiune.",
        "ted_example": "Simon Sinek", "superpower": "Inspira actiune si curaj in fata obstacolelor",
        "shadow": "Poate parea arogant, nu cere ajutor",
        "qualities": ["curaj", "disciplina", "determinare", "actiune", "depasirea obstacolelor"]
    },
    "Ingrijitorul": {
        "emoji": "❤️", "group": "Ego-ul",
        "desire": "Sa ii ajute pe ceilalti", "fear": "Egoismul si ingratitudinea",
        "description": "Empatia si conexiunea umana sunt motorul sau.",
        "ted_example": "Brene Brown", "superpower": "Creeaza conexiune emotionala profunda",
        "shadow": "Poate deveni martirul, neglijeaza propriile nevoi",
        "qualities": ["empatie", "compasiune", "grija", "generozitate", "caldura"]
    },
    "Exploratorul": {
        "emoji": "🚀", "group": "Sufletul",
        "desire": "Libertatea de a se descoperi", "fear": "Constrangerea, rutina, golul interior",
        "description": "Curiozitate, descoperire, aventura intelectuala.",
        "ted_example": "Richard Feynman", "superpower": "Infecteaza audienta cu curiozitate",
        "shadow": "Se pierde, nu finalizeaza nimic, fuge de profunzime",
        "qualities": ["curiozitate", "descoperire", "aventura", "perspective noi", "libertate"]
    },
    "Rebelul": {
        "emoji": "⚡", "group": "Sufletul",
        "desire": "Revolutia, distrugerea a ce nu merge", "fear": "Sa fie neputincios sau ineficient",
        "description": "Contesta status quo-ul, provoaca conventiile.",
        "ted_example": "Elon Musk", "superpower": "Schimba paradigme si sparge tipare",
        "shadow": "Poate aliena audienta, distruge fara a construi",
        "qualities": ["nonconformism", "provocare", "energie", "rupere de tipare", "revolutie"]
    },
    "Indragostitul": {
        "emoji": "💫", "group": "Sufletul",
        "desire": "Intimitatea si experienta senzoriala", "fear": "Sa fie singur sau nedorit",
        "description": "Pasiune, conexiune profunda, experienta senzoriala.",
        "ted_example": "Isabel Allende", "superpower": "Transmite pasiune contagioasa",
        "shadow": "Dependenta emotionala, pierderea limitelor",
        "qualities": ["pasiune", "conexiune", "sensorialitate", "dedicare", "intensitate emotionala"]
    },
    "Creatorul": {
        "emoji": "🎨", "group": "Sufletul",
        "desire": "Sa realizeze ceva cu valoare durabila", "fear": "Viziunea sau executia mediocra",
        "description": "Imagineaza, construieste, aduce frumusete si inovatie.",
        "ted_example": "Jony Ive", "superpower": "Inspira prin viziune, estetica si inovatie",
        "shadow": "Perfectionism paralizant, dificultate in colaborare",
        "qualities": ["viziune", "originalitate", "inovatie", "estetica", "constructie"]
    },
    "Conducatorul": {
        "emoji": "👑", "group": "Sinele",
        "desire": "Controlul si ordinea", "fear": "Haosul, rasturnarea de la putere",
        "description": "Viziune clara, autoritate naturala.",
        "ted_example": "Nelson Mandela", "superpower": "Creeaza miscare si schimbare la scara mare",
        "shadow": "Poate fi perceput ca rigid sau autoritar",
        "qualities": ["viziune", "autoritate", "responsabilitate", "ordine", "leadership"]
    },
    "Magicianul": {
        "emoji": "✨", "group": "Sinele",
        "desire": "Intelegerea legilor universului", "fear": "Consecintele negative neintentionate",
        "description": "Transforma realitatea, face imposibilul posibil.",
        "ted_example": "Steve Jobs", "superpower": "Surprinde si transforma perspectivele",
        "shadow": "Poate parea manipulator sau deconectat de realitate",
        "qualities": ["transformare", "surpriza", "catalizare", "viziune holistica", "WOW"]
    },
    "Inteleptul": {
        "emoji": "🔮", "group": "Sinele",
        "desire": "Descoperirea adevarului", "fear": "Sa fie indus in eroare sau ignorant",
        "description": "Aduce claritate, cunoastere profunda si perspective noi.",
        "ted_example": "Hans Rosling", "superpower": "Transforma complexul in simplu si clar",
        "shadow": "Poate fi prea academic, detasat emotional",
        "qualities": ["claritate", "profunzime", "date", "analiza", "intelepciune"]
    },
    "Bufonul": {
        "emoji": "🤡", "group": "Sinele",
        "desire": "Sa traiasca clipa cu bucurie", "fear": "Sa fie plictisit sau plictisitor",
        "description": "Foloseste umorul si ironia pentru a critica si a elibera.",
        "ted_example": "Sir Ken Robinson", "superpower": "Spune adevaruri incomode prin ras",
        "shadow": "Poate fi perceput ca neserios, ascunde durerea prin umor",
        "qualities": ["umor", "ironie", "bucurie", "critica prin ras", "dezarmare"]
    },
}

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
9. AUTENTICITATE - Ceea ce esti vorbeste atat de tare incat nu pot auzi ceea ce spui. (Emerson)
"""

SCORING_GUIDE = """
GHID STRICT DE ACORDARE A SCORURILOR:
- Scor 1-2: Principiul LIPSESTE COMPLET din text.
- Scor 3-4: Principiul este FOARTE SLAB prezent. O singura mentiune vaga.
- Scor 5-6: Principiul este PARTIAL prezent. Elemente insuficient dezvoltate.
- Scor 7-8: Principiul este BINE implementat. Clar prezent si eficient.
- Scor 9-10: Principiul este EXCEPTIONAL, de nivel TED global. Rar intalnit.

REGULI IMPORTANTE:
1. Scorurile TREBUIE sa fie diferite intre ele.
2. Citeaza INTOTDEAUNA un fragment concret din text pentru a justifica scorul.
3. Daca textul e scurt sau vag, scorurile trebuie sa fie mici (3-5).
4. Fii critic si onest - un scor de 9-10 se acorda doar pentru discursuri exceptionale.
5. Analizeaza DOAR ce este efectiv scris in text.

SPECIAL PENTRU AUTENTICITATE:
- Nu da recomandari tehnice pentru autenticitate.
- Ofera 3 intrebari de reflectie profunda personalizate pe textul speakerului.

SPECIAL PENTRU AUTENTICITATEA ARHETIPALA:
- Evalueaza cat de fidel isi exprima speakerul propriul arhetip identificat.
- Un Explorator cu umor mic NU e penalizat.
- Intreaba: vorbeste din DORINTA sau din TEAMA arhetipului sau?
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

ARCHETYPES_FOR_PROMPT = "\n".join([
    f"- {name} {data['emoji']} [{data['group']}]: Dorinta: {data['desire']} | Teama/Umbra: {data['fear']} | Calitati: {', '.join(data['qualities'])} | Exemplu TED: {data['ted_example']}"
    for name, data in ARCHETYPES.items()
])

def format_case_studies_for_prompt():
    result = "\nSTUDII DE CAZ TED selectate curatorial de Tibi Ruczui, Curator TEDxBrasov (10+ ani):\n"
    for principle, talks in TED_CASE_STUDIES.items():
        result += f"\n{principle}:\n"
        for t in talks:
            result += f"  - '{t['title']}' de {t['speaker']}\n"
    return result

def calculate_total_score(result):
    """Calculeaza scorul total din rezultatul analizei. Returneaza (total, max_possible)."""
    analysis = result.get("analysis", {})
    tier = result.get("tier", "free")
    scores = []

    if tier == "free":
        for k, v in analysis.items():
            if isinstance(v, dict) and "score" in v:
                scores.append(v["score"])
    elif tier == "paid1":
        for k, v in analysis.items():
            if k != "archetype" and isinstance(v, dict) and "score" in v:
                scores.append(v["score"])
        arch = analysis.get("archetype", {})
        if arch.get("archetype_authenticity_score"):
            scores.append(arch["archetype_authenticity_score"])
    elif tier == "paid2":
        sessions = analysis.get("coaching_sessions", [])
        for s in sessions:
            if "score" in s:
                scores.append(s["score"])
        arch = analysis.get("archetype", {})
        if arch.get("archetype_authenticity_score"):
            scores.append(arch["archetype_authenticity_score"])
    elif tier == "paid3":
        principles = analysis.get("nine_principles_check", {})
        for k, v in principles.items():
            if isinstance(v, dict) and "score" in v:
                scores.append(v["score"])
        arch = analysis.get("archetype", {})
        if arch.get("archetype_authenticity_score"):
            scores.append(arch["archetype_authenticity_score"])

    if not scores:
        return 0, 0
    total = sum(scores)
    max_possible = len(scores) * 10
    return total, max_possible

def get_score_label(total, max_possible):
    """Returneaza eticheta verbala pentru scorul total."""
    if max_possible == 0:
        return ""
    pct = total / max_possible
    if pct >= 0.90:
        return "Nivel TED Global 🌍"
    elif pct >= 0.75:
        return "Aproape gata de scenă 🎤"
    elif pct >= 0.60:
        return "Progres solid 📈"
    elif pct >= 0.40:
        return "Potential mare, mai avem de lucru 💪"
    else:
        return "La început, dar cu direcție clară 🌱"

def load_history():
    if os.path.exists(history_file):
        with open(history_file) as f:
            return json.load(f)
    return []

def save_history(email, text, result, total_score, max_score):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "email": email,
        "text_preview": text[:200] + "..." if len(text) > 200 else text,
        "tier": result.get("tier", "free"),
        "total_score": total_score,
        "max_score": max_score,
        "result": result
    }
    data = load_history()
    data.append(entry)
    with open(history_file, "w") as f:
        json.dump(data, f, indent=2)

def get_user_history(email, limit=10):
    """Returneaza ultimele analize ale unui user, cele mai recente primele."""
    data = load_history()
    user_entries = [e for e in data if e.get("email") == email]
    return list(reversed(user_entries[-limit:]))

def get_previous_score(email, current_timestamp):
    """Returneaza scorul analizei anterioare pentru comparatie."""
    data = load_history()
    user_entries = [e for e in data if e.get("email") == email and e.get("timestamp") != current_timestamp]
    if not user_entries:
        return None, None
    last = user_entries[-1]
    return last.get("total_score"), last.get("max_score")

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
Esti un evaluator strict de discursuri TEDx, expert in metodologia Carmine Gallo si psihologia arhetipurilor (Carol S. Pearson / Carl Jung).

{GALLO_9_PRINCIPLES}
{SCORING_GUIDE}
{case_studies}

CELE 12 ARHETIPURI (Carol S. Pearson / Carl Jung):
{ARCHETYPES_FOR_PROMPT}

IMPORTANT:
- Identifica arhetipul DOMINANT si cel SECUNDAR al speakerului.
- Evalueaza autenticitatea arhetipala: vorbeste din DORINTA sau din TEAMA arhetipului?
- Citeaza fragmente CONCRETE din text pentru fiecare scor.
- Cand scorul e sub 7 (exceptand Autenticitate), recomanda un studiu de caz TED.
- Pentru Autenticitate: ofera 3 intrebari de reflectie profunda.
- Scorurile TREBUIE sa fie diferite.
- NU penaliza un Explorator pentru umor mic sau un Bufon pentru date putine.

Returneaza DOAR un JSON valid:
{{
  "archetype": {{
    "primary": "Numele arhetipului dominant",
    "secondary": "Numele arhetipului secundar",
    "emoji": "emoji-ul arhetipului dominant",
    "group": "Ego-ul|Sufletul|Sinele",
    "confidence": "mare|medie|mica",
    "desire": "Dorinta principala a arhetipului identificat",
    "fear": "Teama/Umbra arhetipului identificat",
    "evidence": "Ce din text indica acest arhetip, cu citat",
    "superpower": "Superputerea acestui arhetip pe scena TED",
    "shadow_present": "Apare umbra arhetipului in text? Da/Nu si cum",
    "archetype_authenticity_score": 0,
    "archetype_authenticity_note": "Evalueaza cat de fidel isi exprima speakerul arhetipul"
  }},
  "Pasiunea": {{ "score": 0, "present": false, "recommendation": "Citat + explicatie + studiu de caz daca scorul < 7" }},
  "Povestea": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Conversatia": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Ceva Nou": {{ "score": 0, "present": false, "recommendation": "..." }},
  "WOW Factor": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Umor": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Regula celor 18 min": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Multisenzorial": {{ "score": 0, "present": false, "recommendation": "..." }},
  "Autenticitate": {{ "score": 0, "present": false, "reflection_questions": ["intrebare 1", "intrebare 2", "intrebare 3"] }}
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
Esti un coach avansat de TED talks, expert in metodologia Carmine Gallo si psihologia arhetipurilor (Carol S. Pearson / Carl Jung).

{GALLO_9_PRINCIPLES}
{SCORING_GUIDE}
{case_studies}

CELE 12 ARHETIPURI (Carol S. Pearson / Carl Jung):
{ARCHETYPES_FOR_PROMPT}

IMPORTANT:
- Identifica arhetipul dominant si secundar.
- Coaching-ul trebuie sa amplifice arhetipul, nu sa il schimbe.
- Pentru sesiunea Autenticitate: ofera intrebari de reflectie profunda.
- Include studii de caz TED pentru fiecare sesiune.

Returneaza DOAR un JSON valid:
{{
  "archetype": {{
    "primary": "Numele arhetipului dominant",
    "secondary": "Numele arhetipului secundar",
    "emoji": "emoji",
    "group": "Ego-ul|Sufletul|Sinele",
    "desire": "Dorinta principala",
    "fear": "Teama/Umbra",
    "evidence": "Ce din text indica acest arhetip",
    "archetype_authenticity_score": 0,
    "coaching_note": "Cum sa amplifice arhetipul pe scena TED"
  }},
  "overall_score": 0,
  "summary": "Analiza critica in 2-3 propozitii.",
  "strengths": ["punct forte 1", "punct forte 2", "punct forte 3"],
  "coaching_sessions": [
    {{
      "day": 1,
      "principle": "Pasiunea",
      "status": "absent",
      "score": 0,
      "text_evidence": "Citat din text",
      "exercise": "Exercitiu specific",
      "example_question": "Intrebare de reflectie",
      "ted_example": "Titlul TED talk-ului",
      "ted_speaker": "Numele speakerului"
    }}
  ],
  "next_steps": ["actiune 1", "actiune 2", "actiune 3"]
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
Esti expert in metodologia Carmine Gallo SI in psihologia arhetipurilor Carol S. Pearson / Carl Jung.
Vorbesti direct cu speakerul, ca un mentor personal, cald dar EXIGENT si CRITIC.
Motto-ul tau: "{MOTTO}"

{GALLO_9_PRINCIPLES}
{SCORING_GUIDE}
{case_studies}

CELE 12 ARHETIPURI (Carol S. Pearson / Carl Jung):
{ARCHETYPES_FOR_PROMPT}

IMPORTANT:
- Identifica arhetipul dominant SI secundar.
- Evalueaza autenticitatea arhetipala: vorbeste din DORINTA sau din TEAMA?
- Pentru Autenticitate: 3 intrebari de reflectie profunda.
- Fiecare scor justificat cu citat din text.
- NU penaliza un Explorator pentru umor mic.
- Scorurile TREBUIE sa fie diferite.

Returneaza DOAR un JSON valid:
{{
  "archetype": {{
    "primary": "Numele arhetipului dominant",
    "secondary": "Numele arhetipului secundar",
    "emoji": "emoji",
    "group": "Ego-ul|Sufletul|Sinele",
    "confidence": "mare|medie|mica",
    "desire": "Dorinta principala",
    "fear": "Teama/Umbra arhetipului",
    "evidence": "Ce din text indica acest arhetip, cu citat",
    "curator_message_about_archetype": "Mesajul tau personal (2-3 propozitii)",
    "ted_example": "Speaker TED cu acelasi arhetip",
    "superpower": "Superputerea pe scena TED",
    "shadow": "Riscul arhetipului",
    "shadow_present": "Apare umbra in text? Da/Nu si cum",
    "archetype_authenticity_score": 0,
    "archetype_authenticity_note": "Vorbeste din dorinta sau din teama?"
  }},
  "curator_message": "Mesaj personal direct (3-4 propozitii)",
  "overall_score": 0,
  "curator_verdict": "Gata pentru scena|Aproape gata|Mai avem de lucru|Revenim de la zero",
  "what_moved_me": "Ce te-a impresionat, cu citat",
  "what_worries_me": "Ce te ingrijoreaza, cu citat",
  "nine_principles_check": {{
    "Pasiunea": {{ "score": 0, "curator_note": "Citat + observatie + studiu de caz daca scorul < 7" }},
    "Povestea": {{ "score": 0, "curator_note": "..." }},
    "Conversatia": {{ "score": 0, "curator_note": "..." }},
    "Ceva Nou": {{ "score": 0, "curator_note": "..." }},
    "WOW Factor": {{ "score": 0, "curator_note": "..." }},
    "Umor": {{ "score": 0, "curator_note": "..." }},
    "Regula celor 18 min": {{ "score": 0, "curator_note": "..." }},
    "Multisenzorial": {{ "score": 0, "curator_note": "..." }},
    "Autenticitate": {{ "score": 0, "reflection_questions": ["intrebare 1", "intrebare 2", "intrebare 3"] }}
  }},
  "stage_readiness": {{
    "ready_to_present": false,
    "estimated_sessions_needed": 0,
    "priority_action": "Cel mai important lucru de facut acum"
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

def generate_pdf(text, result, user_name, tier, total_score=0, max_score=0):
    pdf_filename = f"{pdf_folder}/scorecard_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    analysis = result.get("analysis", {})
    scores = {}
    if tier == "free":
        scores = {k: v.get("score", 0) for k, v in analysis.items() if isinstance(v, dict)}
    elif tier == "paid1":
        scores = {k: v.get("score", 0) for k, v in analysis.items() if isinstance(v, dict) and k != "archetype"}
    elif tier == "paid2":
        sessions = analysis.get("coaching_sessions", [])
        scores = {s["principle"]: s.get("score", 7) for s in sessions}
    elif tier == "paid3":
        principles = analysis.get("nine_principles_check", {})
        scores = {k: v.get("score", 0) for k, v in principles.items()}
    radar_img = None
    if scores:
        radar_img = generate_radar_image(scores, filename=pdf_filename.replace(".pdf", ".png"))
        time.sleep(0.5)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "Speaker Lab AI - TEDxBrasov", ln=True, align="C")
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 6, clean(MOTTO))
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, clean(f"Speaker: {user_name} | Tier: {TIERS[tier]['name']} | {datetime.now().strftime('%d.%m.%Y %H:%M')}"), ln=True, align="C")
    if total_score and max_score:
        pdf.set_font("Arial", "B", 14)
        label = get_score_label(total_score, max_score)
        pdf.cell(0, 10, clean(f"SCOR TOTAL: {total_score}/{max_score} — {label}"), ln=True, align="C")
    pdf.ln(6)
    archetype = analysis.get("archetype")
    if archetype and isinstance(archetype, dict):
        pdf.set_font("Arial", "B", 13)
        primary = archetype.get("primary", "")
        secondary = archetype.get("secondary", "")
        pdf.cell(0, 8, clean(f"Arhetip dominant: {primary} | Secundar: {secondary}"), ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(f"Grup: {archetype.get('group', '')}"))
        pdf.multi_cell(0, 6, clean(f"Dorinta: {archetype.get('desire', '')}"))
        pdf.multi_cell(0, 6, clean(f"Teama/Umbra: {archetype.get('fear', '')}"))
        pdf.multi_cell(0, 6, clean(f"Dovada: {archetype.get('evidence', '')}"))
        if archetype.get("archetype_authenticity_score"):
            pdf.multi_cell(0, 6, clean(f"Autenticitate arhetipala: {archetype.get('archetype_authenticity_score')}/10 — {archetype.get('archetype_authenticity_note', '')}"))
        if archetype.get("curator_message_about_archetype"):
            pdf.set_font("Arial", "I", 10)
            pdf.multi_cell(0, 6, clean(archetype.get("curator_message_about_archetype", "")))
        pdf.ln(4)
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
                pdf.multi_cell(0, 6, clean(data.get("recommendation", "")))
                pdf.ln(2)
    elif tier == "paid1" and isinstance(analysis, dict):
        for crit, data in analysis.items():
            if isinstance(data, dict) and crit != "archetype":
                present = "+" if data.get("present") else "-"
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 7, clean(f"{present} {crit}: {data.get('score', 0)}/10"), ln=True)
                pdf.set_font("Arial", "", 10)
                if crit == "Autenticitate" and data.get("reflection_questions"):
                    for q in data.get("reflection_questions", []):
                        pdf.multi_cell(0, 6, clean(f"- {q}"))
                else:
                    pdf.multi_cell(0, 6, clean(data.get("recommendation", "")))
                pdf.ln(2)
    elif tier == "paid2" and isinstance(analysis, dict):
        arch = analysis.get("archetype", {})
        if arch:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, clean(f"Coaching bazat pe arhetipul: {arch.get('primary','')}"), ln=True)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, clean(arch.get("coaching_note", "")))
            pdf.ln(4)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, clean(f"Scor general AI: {analysis.get('overall_score', 'N/A')}/10"), ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(analysis.get("summary", "")))
        pdf.ln(4)
        for session in analysis.get("coaching_sessions", []):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, clean(f"Ziua {session.get('day', '')}: {session.get('principle', '')} - {session.get('score', 0)}/10"), ln=True)
            pdf.set_font("Arial", "", 10)
            if session.get("text_evidence"):
                pdf.multi_cell(0, 6, clean(f"Din text: {session.get('text_evidence', '')}"))
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
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 7, "Ce ma ingrijoreaza:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(analysis.get("what_worries_me", "")))
        pdf.ln(4)
        for principle, data in analysis.get("nine_principles_check", {}).items():
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 7, clean(f"{principle}: {data.get('score', 0)}/10"), ln=True)
            pdf.set_font("Arial", "", 10)
            if principle == "Autenticitate" and data.get("reflection_questions"):
                for q in data.get("reflection_questions", []):
                    pdf.multi_cell(0, 6, clean(f"- {q}"))
            else:
                pdf.multi_cell(0, 6, clean(data.get("curator_note", "")))
            pdf.ln(2)
    if radar_img:
        try:
            if os.path.exists(radar_img) and os.path.getsize(radar_img) > 0:
                pdf.ln(5)
                pdf.image(radar_img, x=55, w=100)
        except Exception as e:
            print(f"Radar image error: {e}")
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
    total_score = 0
    max_score = 0
    score_label = ""
    prev_score = None
    prev_max = None
    score_diff = None
    current_timestamp = None

    if request.method == "POST":
        text = request.form.get("speech_text", "")
        if text.strip():
            result = analyze_by_tier(text, user["tier"])
            total_score, max_score = calculate_total_score(result)
            score_label = get_score_label(total_score, max_score)
            current_timestamp = datetime.now().isoformat()
            prev_score, prev_max = get_previous_score(user["email"], current_timestamp)
            if prev_score is not None and prev_max == max_score:
                score_diff = total_score - prev_score
            save_history(user["email"], text, result, total_score, max_score)
            try:
                pdf_file = generate_pdf(text, result, user.get("name", "Speaker"), user["tier"], total_score, max_score)
            except Exception as e:
                print(f"PDF error: {e}")

    history = get_user_history(user["email"], limit=5)

    return render_template("index.html",
        result=result,
        pdf_file=pdf_file,
        user=user,
        tiers=TIERS,
        total_score=total_score,
        max_score=max_score,
        score_label=score_label,
        score_diff=score_diff,
        prev_score=prev_score,
        history=history
    )

@app.route("/history")
@login_required
def history_page():
    user = get_current_user()
    history = get_user_history(user["email"], limit=20)
    return render_template("history.html", user=user, tiers=TIERS, history=history)

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

@app.route('/icon-<size>.png')
def serve_icon(size):
    import os
    return send_file(os.path.join(app.root_path, 'static', f'icon-{size}.png'))

@app.route('/service-worker.js')
def service_worker():
    return send_file('static/service-worker.js'), 200, {'Content-Type': 'application/javascript'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
