import os
from flask import Flask, render_template, request, send_file
from openai import OpenAI
from fpdf import FPDF
import matplotlib.pyplot as plt
import json
from datetime import datetime
import numpy as np

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

if not os.path.exists("data"):
    os.makedirs("data")
history_file = "data/history.json"
pdf_folder = "data/pdf"
if not os.path.exists(pdf_folder):
    os.makedirs(pdf_folder)

def analyze_speech(text):
    prompt = f"""
Analizeaza urmatorul text ca pentru un speaker TEDx:
1. Idea Strength
2. Structural Integrity
3. Cognitive Load
4. Emotional Arc
5. Memorability Factor

Returneaza un JSON cu structura:
{{
  "Idea Strength": {{ "score": 0, "recommendation": "..." }},
  "Structural Integrity": {{ "score": 0, "recommendation": "..." }},
  "Cognitive Load": {{ "score": 0, "recommendation": "..." }},
  "Emotional Arc": {{ "score": 0, "recommendation": "..." }},
  "Memorability Factor": {{ "score": 0, "recommendation": "..." }}
}}

Text: {text}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    try:
        result_json = json.loads(content)
    except:
        result_json = {"error": content}
    return result_json

def save_history(text, result):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "text": text,
        "result": result
    }
    if os.path.exists(history_file):
        with open(history_file, "r+") as f:
            data = json.load(f)
            data.append(entry)
            f.seek(0)
            json.dump(data, f, indent=2)
    else:
        with open(history_file, "w") as f:
            json.dump([entry], f, indent=2)

def generate_radar_image(scores, filename="radar.png"):
    labels = ['Idea Strength', 'Structural Integrity', 'Cognitive Load', 'Emotional Arc', 'Memorability Factor']
    num_vars = len(labels)
    values = list(scores.values())
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(5,5), subplot_kw=dict(polar=True))
    ax.plot(angles, values, color='blue', linewidth=2, linestyle='solid')
    ax.fill(angles, values, color='blue', alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticks(range(0,11,2))
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    return filename

def clean(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_with_radar(text, result_json):
    pdf_filename = f"{pdf_folder}/scorecard_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    scores = {k:v['score'] for k,v in result_json.items()}
    radar_img = generate_radar_image(scores, filename=pdf_filename.replace(".pdf",".png"))
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Speaker Lab AI - TEDxBrasov", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.multi_cell(0, 8, clean("Discurs:\n" + text))
    pdf.ln(5)
    pdf.multi_cell(0, 8, "Analiza si recomandari:")
    pdf.ln(5)
    for crit, data in result_json.items():
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, clean(f"{crit}: {data['score']}/10"), ln=True)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 8, clean(f"Recomandare: {data['recommendation']}"))
        pdf.ln(2)
    pdf.image(radar_img, x=60, w=90)
    pdf.output(pdf_filename)
    return pdf_filename

@app.route("/", methods=["GET","POST"])
def index():
    result_json = None
    pdf_file = ""
    if request.method == "POST":
        text = request.form["speech_text"]
        result_json = analyze_speech(text)
        save_history(text, result_json)
        pdf_file = generate_pdf_with_radar(text, result_json)
    return render_template("index.html", result=result_json, pdf_file=pdf_file)

@app.route("/download/<path:filename>")
def download_pdf(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))


