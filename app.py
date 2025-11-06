# =========================
# Data Leaf MVP – Streamlit
# End-to-end demo + pilot (compact, no-scrolling main sections)
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

# Minimal CSS for compact layout and subtle polish
st.markdown("""
<style>
.block-container { padding-top: 0.8rem; padding-bottom: 1rem; }
.stRadio > div { gap: 0.75rem; }
.stSlider { margin-top: -0.25rem; }
.badge { display:inline-block; padding:4px 8px; border-radius:14px; background:#eef6ff; color:#1e6c93; margin-right:6px; font-size:0.85rem; }
.headerbar { display:flex; align-items:center; gap:12px; margin:6px 0 10px 0; }
.headerbar img { width:36px; height:36px; border-radius:6px; object-fit:contain; }
.headerbar h2 { margin:0; font-weight:800; }
.pulse { width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 6px rgba(34,197,94,.15); display:inline-block; }
.smallcap { color:#6b7280; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# Header (Data Leaf logo only)
st.markdown(
    f"""<div class="headerbar">
        <img src="{LOGO_URL}" alt="Data Leaf logo">
        <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
    </div>""",
    unsafe_allow_html=True
)

# ----------------- AI (PRIVATE / ADMIN) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)

def call_openai(prompt, max_tokens=140, temperature=0.3):
    if not OPENAI_API_KEY:
        return None
    try:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
        data = {"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],
                "max_tokens":max_tokens,"temperature":temperature}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, data=json.dumps(data), timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ OpenAI error {r.status_code}: {r.text}"
    except Exception as e:
        return f"❌ Request failed: {e}"

with st.expander("Admin • Smart Assist status (hidden in demos)", expanded=False):
    st.caption("Keep AI private. Use this check pre-demo only.")
    if st.button("Test connection"):
        if not USE_AI:
            st.error("No API key detected. Add it under Streamlit → Settings → Secrets.")
        else:
            res = call_openai("Reply only with: Connected.")
            if res and "Connected" in res:
                st.success("Connected")
            else:
                st.error(f"Connection issue: {res}")
    st.caption("Tip: collapse this during live demos.")

# ----------------- MODE -----------------
mode = st.radio("Mode", ["Demo", "Pilot (upload your data)"], horizontal=True)
demo = mode == "Demo"
st.caption("Pilot mode enables secure uploads; Demo uses Jan–Jun 2025 sample data.")

# ----------------- DEMO DATA -----------------
def load_demo():
    months = ["Jan","Feb","Mar","Apr","May","Jun"]
    facilities = ["City Hall","RIM Park","WMRC","Operations Centre","Community Centre"]
    rows=[]
    for f in facilities:
        base_kwh = {"City Hall":85000,"RIM Park":140000,"WMRC":120000,"Operations Centre":100000,"Community Centre":90000}[f]
        base_gas = {"City Hall":18000,"RIM Park":30000,"WMRC":26000,"Operations Centre":22000,"Community Centre":20000}[f]
        for i,m in enumerate(months):
            mult=[1.15,1.10,1.05,0.95,0.90,0.88][i]
            rows.append({"facility":f,"month":m,"year":2025,
                         "kwh":int(base_kwh*mult),"natural_gas_m3":int(base_gas*mult)})
    buildings = pd.DataFrame(rows)
    fleet = pd.DataFrame({
        "vehicle":["Waste Truck 1","Waste Truck 2","By-law Car 3","Facilities Van 7"],
        "fuel_type":["Diesel","Diesel","Gasoline","Diesel"],
        "liters":[1800,1700,350,900]
    })
    waste = pd.DataFrame({
        "stream":["Municipal Solid Waste","Recycling","Organics"],
        "amount_tonnes":[42,30,18]
    })
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ----------------- UPLOADS (PILOT) -----------------
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    c_up_a, c_up_b, c_up_c = st.columns(3)
    with c_up_a:
        ub = st.file_uploader("Buildings CSV", type=["csv"],
                              help="Columns: facility,month,year,kwh,natural_gas_m3")
    with c_up_b:
        uf = st.file_uploader("Fleet CSV", type=["csv"],
                              help="Columns: vehicle,fuel_type,liters")
    with c_up_c:
        uw = st.file_uploader("Waste CSV", type=["csv"],
                              help="Columns: stream,amount_tonnes")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet     = pd.read_csv(uf) if uf else demo_fleet
    waste     = pd.read_csv(uw) if uw else demo_waste

# ----------------- COST SETTINGS -----------------
with st.expander("Cost Settings (CAD) – used everywhere", expanded=False):
    colc1, colc2, colc3, colc4 = st.columns(4)
    with colc1:
        elec_rate = st.number_input("Electricity ($/kWh)", value=0.17, min_value=0.0, step=0.01)
    with colc2:
        gas_rate  = st.number_input("Natural gas ($/m³)", value=0.45, min_value=0.0, step=0.01)
    with colc3:
        diesel_rate = st.number_input("Diesel ($/L)", value=1.80, min_value=0.0, step=0.01)
    with colc4:
        gasoline_rate = st.number_input("Gasoline ($/L)", value=1.65, min_value=0.0, step=0.01)
    colc5, _ = st.columns([1,3])
    with colc5:
        landfill_rate = st.number_input("Landfill tipping ($/tonne)", value=125.0, min_value=0.0, step=1.0)

# Emission factors
emission_factors = {
    "kwh": 0.00003,
    "natural
