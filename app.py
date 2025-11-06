# =========================
# Data Leaf MVP – Streamlit
# Fully updated version
# =========================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
import requests
import json

# ================= Optional AI Setup =================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = False

def call_openai(prompt):
    """Direct HTTPS call that works even with project-scoped keys."""
    if not OPENAI_API_KEY:
        return None
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 120,
            "temperature": 0.3
        }
        r = requests.post
