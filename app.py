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
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ OpenAI error {r.status_code}"
    except Exception as e:
        return f"❌ Request failed: {e}"

# ----------------- MODE -----------------
mode = st.radio("Mode", ["Demo", "Pilot (upload your data)"], horizontal=True)
demo = mode == "Demo"

# ----------------- DEMO DATA -----------------
def load_demo():
    months = ["Jan","Feb","Mar","Apr","May","Jun"]
    facilities = ["City Hall","RIM Park","WMRC","Operations Centre","Community Centre"]
    rows = []
    for f in facilities:
        base_kwh = {"City Hall":85000,"RIM Park":140000,"WMRC":120000,"Operations Centre":100000,"Community Centre":90000}[f]
        base_gas = {"City Hall":18000,"RIM Park":30000,"WMRC":26000,"Operations Centre":22000,"Community Centre":20000}[f]
        for i,m in enumerate(months):
            mult=[1.15,1.10,1.05,0.95,0.90,0.88][i]
            rows.append({
                "facility": f,
                "month": m,
                "year": 2025,
                "kwh": int(base_kwh * mult),
                "natural_gas_m3": int(base_gas * mult)
            })
    buildings = pd.DataFrame(rows)
    fleet = pd.DataFrame({
        "vehicle": ["Waste Truck 1","Waste Truck 2","By-law Car 3","Facilities Van 7"],
        "fuel_type": ["Diesel","Diesel","Gasoline","Diesel"],
        "liters": [1800,1700,350,900]
    })
    waste = pd.DataFrame({
        "stream": ["Municipal Solid Waste","Recycling","Organics"],
        "amount_tonnes": [42,30,18]
    })
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ----------------- UPLOADS -----------------
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    c1, c2, c3 = st.columns(3)
    with c1: ub = st.file_uploader("Buildings CSV", type="csv")
    with c2: uf = st.file_uploader("Fleet CSV", type="csv")
    with c3: uw = st.file_uploader("Waste CSV", type="csv")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet = pd.read_csv(uf) if uf else demo_fleet
    waste = pd.read_csv(uw) if uw else demo_waste

# ----------------- COST SETTINGS -----------------
with st.expander("Cost Settings (CAD)", expanded=False):
    c1,c2,c3,c4 = st.columns(4)
    elec_rate = c1.number_input("Electricity ($/kWh)", value=0.17)
    gas_rate = c2.number_input("Natural Gas ($/m³)", value=0.45)
    diesel_rate = c3.number_input("Diesel ($/L)", value=1.80)
    gaso_rate = c4.number_input("Gasoline ($/L)", value=1.65)
    landfill_rate = st.number_input("Landfill ($/tonne)", value=125.0)

emission_factors = {
    "kwh": 0.00003, "natural_gas_m3": 0.00189,
    "diesel_l": 0.00268, "gasoline_l": 0.00231,
    "msw_tonne": 0.45
}

# ----------------- CALCS -----------------
def calc_build(df):
    df["tco2e"] = df["kwh"]*emission_factors["kwh"] + df["natural_gas_m3"]*emission_factors["natural_gas_m3"]
    df["cost"] = df["kwh"]*elec_rate + df["natural_gas_m3"]*gas_rate
    return df
def calc_fleet(df):
    df["tco2e"] = np.where(df["fuel_type"].str.lower().str.contains("diesel"),
                           df["liters"]*emission_factors["diesel_l"],
                           df["liters"]*emission_factors["gasoline_l"])
    df["cost"] = np.where(df["fuel_type"].str.lower().str.contains("diesel"),
                          df["liters"]*diesel_rate,
                          df["liters"]*gaso_rate)
    return df
def calc_waste(df):
    df["tco2e"] = np.where(df["stream"].str.contains("Municipal"),
                           df["amount_tonnes"]*emission_factors["msw_tonne"],0)
    df["cost"] = np.where(df["stream"].str.contains("Municipal"),
                          df["amount_tonnes"]*landfill_rate,0)
    return df

bld, flt, wst = calc_build(buildings), calc_fleet(fleet), calc_waste(waste)
bld_t, flt_t, wst_t = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
bld_c, flt_c, wst_c = bld["cost"].sum(), flt["cost"].sum(), wst["cost"].sum()
grand_t = bld_t+flt_t+wst_t
grand_c = bld_c+flt_c+wst_c
fmt = lambda n: f"{n:,.1f}"

# ----------------- KPIs -----------------
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Total tCO₂e", fmt(grand_t))
k2.metric("Buildings", fmt(bld_t))
k3.metric("Fleet", fmt(flt_t))
k4.metric("Waste", fmt(wst_t))
k5.metric("Est. Annual Cost", f"${grand_c:,.0f}")

# ----------------- OVERVIEW -----------------
st.markdown("### Overview (tCO₂e + $)")

cA,cB,cC = st.columns(3)
order = ["Jan","Feb","Mar","Apr","May","Jun"]

with cA:
    bld["month"] = pd.Categorical(bld["month"], categories=order, ordered=True)
    chart = alt.Chart(bld).mark_area(opacity=0.8).encode(
        x="month", y="tco2e", color="facility", tooltip=["facility","tco2e","cost"]
    ).properties(height=250)
    st.altair_chart(chart, use_container_width=True)

with cB:
    st.altair_chart(
        alt.Chart(flt).mark_bar(color="#2a9d8f").encode(
            x="vehicle", y="tco2e", tooltip=["fuel_type","tco2e","cost"]
        ).properties(height=250),
        use_container_width=True
    )

with cC:
    st.altair_chart(
        alt.Chart(wst).mark_bar(color="#8a5a44").encode(
            x="stream", y="tco2e", tooltip=["stream","tco2e","cost"]
        ).properties(height=250),
        use_container_width=True
    )

# ----------------- SCENARIO BUILDER -----------------
st.markdown("### Scenario Builder (side-by-side)")
s1,s2,s3 = st.columns(3)

with s1:
    r = st.slider("Retrofit (%)",0,30,15)
    new = bld_t*(1-r/100); newc=bld_c*(1-r/100)
    st.metric("Building Savings", f"{fmt(bld_t-new)} tCO₂e", f"${bld_c-newc:,.0f}")

with s2:
    ev = st.slider("EV adoption (%)",0,50,20)
    new = flt_t*(1-ev/100); newc=flt_c*(1-ev/100)
    st.metric("Fleet Savings", f"{fmt(flt_t-new)} tCO₂e", f"${flt_c-newc:,.0f}")

with s3:
    div = st.slider("Diversion (+%)",0,50,10)
    new = wst_t*(1-div/100); newc=wst_c*(1-div/100)
    st.metric("Waste Savings", f"{fmt(wst_t-new)} tCO₂e", f"${wst_c-newc:,.0f}")

# ----------------- FUNDING -----------------
st.markdown("### Funding Templates (clickable links)")
grants = {
    "Ontario": "https://www.ontario.ca/page/climate-change-funding",
    "Canada (GICB)": "https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html",
    "FCM GMF": "https://greenmunicipalfund.ca/funding/fleet-electrification"
}
pick = st.selectbox("Select Program", list(grants.keys()))
st.markdown(f"📎 [Program Link]({grants[pick]})")

temp = f"""Grant Template
Program: {pick}
Applicant: City of Waterloo Sustainability Office
Summary: Using Data Leaf analytics, total baseline ≈ {fmt(grand_t)} tCO₂e, annual cost ≈ ${grand_c:,.0f}.
Project: Buildings, Fleet, and Waste Efficiency Phase 1.
"""
st.download_button("Download Prefilled Template", temp, file_name="Grant_Template.txt")

# ----------------- ENGAGEMENT -----------------
st.markdown("### Stakeholder Engagement")
auds = st.multiselect("Audience",["Council","Residents","Businesses","City Staff"],default=["Council"])
topic = st.selectbox("Topic",["Progress","Budget impact","Compliance","Pilot invite"])
col1,col2=st.columns(2)
for i,a in enumerate(auds):
    with (col1 if i%2==0 else col2):
        msg = f"{a}: Update on {topic}. Data Leaf shows clear cost + emission reduction opportunities."
        st.text_area(a, msg, height=100)
        q=urllib.parse.quote(msg)
        st.markdown(f"[Share on LinkedIn](https://www.linkedin.com/sharing/share-offsite/?url=https://thedataleaf.com&summary={q})")

st.caption("✅ Final build – live, cost-integrated, clickable, and demo-ready.")
