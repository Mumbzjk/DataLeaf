# =========================
# Data Leaf MVP – Streamlit
# City of Waterloo Pilot – Complete
# =========================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os, requests, json, urllib.parse, time, math

# ----------------- BRAND / PAGE -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"

st.set_page_config(
    page_title="Data Leaf – City of Waterloo Pilot MVP",
    page_icon=LOGO_URL,
    layout="wide"
)

# ----------------- STYLES -----------------
st.markdown("""
<style>
.block-container { padding-top: 0.8rem; padding-bottom: 1rem; }
.headerbar { display:flex; align-items:center; gap:12px; margin:6px 0 10px 0; }
.headerbar img { width:36px; height:36px; border-radius:6px; object-fit:contain; }
.headerbar h2 { margin:0; font-weight:800; }
.badge { display:inline-block; padding:4px 8px; border-radius:14px; background:#eef6ff; color:#1e6c93; margin-right:6px; font-size:0.85rem; }
.pulse { width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 6px rgba(34,197,94,.15); display:inline-block; }
.smallcap { color:#6b7280; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    f"""<div class="headerbar">
        <img src="{LOGO_URL}" alt="Data Leaf logo">
        <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
    </div>""",
    unsafe_allow_html=True
)

# ----------------- AI CONNECTION -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)

def call_openai(prompt, max_tokens=120, temperature=0.3):
    if not OPENAI_API_KEY:
        return None
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        if r.status_code == 200:
            return r.json()["choices"][0]["me]()
