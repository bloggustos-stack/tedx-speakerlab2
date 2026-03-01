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
pdf_folder
