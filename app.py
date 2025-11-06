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
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, data=json.dumps(data))
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            return f"⚠️ OpenAI error {r.status_code}: {r.text}"
    except Exception as e:
        return f"❌ Request failed: {e}"

if OPENAI_API_KEY:
    USE_AI = True

# ================= Page =======================
st.set_page_config(
    page_title="Data Leaf – City of Waterloo Pilot MVP",
    page_icon="https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png",
    layout="wide"
)

# --- AI Connection Tester ---
st.markdown("### 🔍 AI Connection Check")
if st.button("Test AI Connection"):
    if not OPENAI_API_KEY:
        st.error("❌ No API key detected. Add it under Streamlit → Settings → Secrets")
    else:
        result = call_openai("Reply only with the single word: Connected.")
        if "Connected" in (result or ""):
            st.success("✅ Connected to OpenAI! Response: " + result)
        else:
            st.error("❌ Connection failed or restricted. Details: " + str(result))

ai_status = "🟢 AI: Connected" if USE_AI else "🔴 AI: Not connected"
st.caption(ai_status + " · Manage at Streamlit → Settings → Secrets")

# ------------------ MODE SWITCH ------------------
mode = st.radio("Select Mode", ["Demo Mode", "Pilot Mode"], horizontal=True)
demo = mode == "Demo Mode"
st.caption("🌿 Pilot Mode lets you upload your own data; Demo Mode uses sample Jan–Jun 2025 data.")

# ================= Demo Data ==================
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
    buildings=pd.DataFrame(rows)
    fleet=pd.DataFrame({
        "vehicle":["Waste Truck 1","Waste Truck 2","By-law Car 3","Facilities Van 7"],
        "fuel_type":["Diesel","Diesel","Gasoline","Diesel"],
        "liters":[1800,1700,350,900]
    })
    waste=pd.DataFrame({
        "stream":["Municipal Solid Waste","Recycling","Organics"],
        "amount":[42,30,18]
    })
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ================= Pilot Uploads =================
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    st.info("🔹 Upload CSVs below. If none provided, demo data is used.")
    ub = st.file_uploader("Upload Buildings CSV", type=["csv"], help="Columns: facility,month,year,kwh,natural_gas_m3")
    uf = st.file_uploader("Upload Fleet CSV", type=["csv"], help="Columns: vehicle,fuel_type,liters")
    uw = st.file_uploader("Upload Waste CSV", type=["csv"], help="Columns: stream,amount (tonnes)")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet     = pd.read_csv(uf) if uf else demo_fleet
    waste     = pd.read_csv(uw) if uw else demo_waste

# ================= Factors & Grants =================
factors = pd.DataFrame({
    "source":["kwh","natural_gas_m3","diesel_l","gasoline_l","tonnes_msw"],
    "tco2e_per_unit":[0.00003,0.00189,0.00268,0.00231,0.45]
})

grants = pd.DataFrame([
    ["FCM GMF – Community Buildings Retrofit","Rolling","Up to 50%","Varies",
     "buildings,retrofit,energy_efficiency,resilience",
     "https://greenmunicipalfund.ca/community-buildings-retrofit-initiative",
     "Supports deep retrofits and low-carbon upgrades."],
    ["FCM GMF – Fleet Electrification","Year-round","Up to 50%","Up to $1 M",
     "fleet,electrification,ev_charging",
     "https://greenmunicipalfund.ca/funding/fleet-electrification",
     "EVs, charging and feasibility studies."],
    ["GICB – Infrastructure Canada","Mar 2029","Up to 60%","Up to $25 M",
     "buildings,retrofit,renewable_energy,accessibility",
     "https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html",
     "Low-carbon community facilities."],
    ["Circular Economy & Waste Innovation Fund","2025-26","Up to 80%","Up to $500 k",
     "waste,circular_economy,innovation",
     "https://www.canada.ca/en/environment-climate-change/services/funding-programs/circular-economy-innovation.html",
     "Innovative waste reduction / reuse projects."]
], columns=["program","deadline","match_pct","max_amount","categories","link","notes"])

# ================= Calculations =================
fmt = lambda n: f"{n:,.1f}"

def calc_buildings(df):
    f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]
    f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
    out = df.copy()
    out["tco2e"] = df["kwh"]*f_elec + df["natural_gas_m3"]*f_gas
    return out

def calc_fleet(df):
    f_d = factors.loc[factors["source"]=="diesel_l","tco2e_per_unit"].values[0]
    f_g = factors.loc[factors["source"]=="gasoline_l","tco2e_per_unit"].values[0]
    out = df.copy()
    out["tco2e"] = np.where(df["fuel_type"].str.lower().str.contains("diesel"),
                            df["liters"]*f_d, df["liters"]*f_g)
    return out

def calc_waste(df):
    f = factors.loc[factors["source"]=="tonnes_msw","tco2e_per_unit"].values[0]
    out = df.copy()
    out["tco2e"] = np.where(df["stream"].str.contains("Municipal"), df["amount"]*f, 0)
    return out

bld, flt, wst = calc_buildings(buildings), calc_fleet(fleet), calc_waste(waste)
bld_total, flt_total, wst_total = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
grand_total = bld_total + flt_total + wst_total

# ================= Header ======================
st.title("Data Leaf – City of Waterloo Pilot MVP")

m1,m2,m3,m4 = st.columns(4)
m1.metric("Total (tCO₂e)", fmt(grand_total))
m2.metric("Buildings (tCO₂e)", fmt(bld_total))
m3.metric("Fleet (tCO₂e)", fmt(flt_total))
m4.metric("Waste (tCO₂e)", fmt(wst_total))

# ================= Tabs =======================
tabs = st.tabs(["Overview","Policy Scenarios","Funding","Engagement"])

# ---------- Overview ----------
with tabs[0]:
    st.subheader("Overview – Buildings, Fleet, Waste (tCO₂e)")
    cA,cB,cC = st.columns(3)
    order = ["Jan","Feb","Mar","Apr","May","Jun"]
    with cA:
        chart_b = bld.groupby(["month","facility"],as_index=False)["tco2e"].sum()
        chart_b["month"] = pd.Categorical(chart_b["month"], categories=order, ordered=True)
        st.altair_chart(
            alt.Chart(chart_b).mark_area(opacity=0.75).encode(
                x="month", y="tco2e", color="facility", tooltip=["facility","month","tco2e"]
            ).properties(height=260), use_container_width=True)
    with cB:
        st.altair_chart(
            alt.Chart(flt).mark_bar(color="#2a9d8f").encode(
                x="vehicle", y="tco2e", tooltip=["vehicle","fuel_type","tco2e"]
            ).properties(height=260), use_container_width=True)
    with cC:
        st.altair_chart(
            alt.Chart(wst).mark_bar(color="#8a5a44").encode(
                x="stream", y="tco2e", tooltip=["stream","tco2e"]
            ).properties(height=260), use_container_width=True)

# ---------- Policy Scenarios ----------
with tabs[1]:
    st.subheader("Policy Scenario Builder – Side-by-Side (tCO₂e)")
    col1, col2, col3 = st.columns(3)

    # Buildings
    with col1:
        retro = st.slider("Retrofit savings (%)",0,30,15)
        grid  = st.slider("Grid intensity change (%)",-50,50,-10)
        f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]*(1+grid/100)
        f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
        bld_sc_total = ((bld["kwh"]*f_elec + bld["natural_gas_m3"]*f_gas)*(1-retro/100)).sum()
        delta_b = bld_total - bld_sc_total
        st.metric("Scenario (tCO₂e)", fmt(bld_sc_total), f"-{fmt(delta_b)}")
        if USE_AI and st.button("Explain Buildings (AI)"):
            st.success(call_openai(
                f"Summarize retrofit {retro}% and grid {grid}% change impact on buildings. "
                f"Current {bld_total:.1f}→Scenario {bld_sc_total:.1f} tCO₂e."
            ))

    # Fleet
    with col2:
        ev = st.slider("EV adoption (%)",0,50,20)
        flt_sc_total = flt_total*(1-ev/100)
        delta_f = flt_total - flt_sc_total
        st.metric("Scenario (tCO₂e)", fmt(flt_sc_total), f"-{fmt(delta_f)}")
        if USE_AI and st.button("Explain Fleet (AI)"):
            st.success(call_openai(
                f"Fleet EV adoption {ev}% reduces emissions from {flt_total:.1f} to {flt_sc_total:.1f} tCO₂e."
            ))

    # Waste
    with col3:
        div = st.slider("Diversion increase (%)",0,50,10)
        msw = wst[wst["stream"].str.contains("Municipal")]["tco2e"].sum()
        wst_sc_total = wst_total - msw*(div/100)
        delta_w = wst_total - wst_sc_total
        st.metric("Scenario (tCO₂e)", fmt(wst_sc_total), f"-{fmt(delta_w)}")
        if USE_AI and st.button("Explain Waste (AI)"):
            st.success(call_openai(
                f"Waste diversion +{div}% changes emissions from {wst_total:.1f} to {wst_sc_total:.1f} tCO₂e."
            ))

# ---------- Funding ----------
with tabs[2]:
    st.subheader("Relevant Funding Programs")
    for _, r in grants.iterrows():
        st.markdown(
            f"- **{r['program']}** – *{r['match_pct']}* – {r['deadline']}  \n"
            f"  {r['notes']}  \n👉 [{r['link']}]({r['link']})"
        )

    st.divider()
    st.subheader("Prefilled Grant Application Template (.txt)")
    sel = st.selectbox("Choose a program", grants["program"])
    gr = grants[grants["program"]==sel].iloc[0]
    template = f"""=== GRANT APPLICATION TEMPLATE ===
Program: {gr['program']}
Deadline: {gr['deadline']}
Match: {gr['match_pct']} (Max {gr['max_amount']})
Link: {gr['link']}

City of Waterloo aims to reduce emissions in {gr['categories'].split(',')[0]}.
Corporate footprint ≈ {fmt(grand_total)} tCO₂e (Buildings {fmt(bld_total)}, Fleet {fmt(flt_total)}, Waste {fmt(wst_total)}).

Objectives:
• Reduce emissions per scenario
• Achieve regulatory readiness
• Access {gr['program']} support

Attachments:
• Data Leaf Dashboard results
• Scenario analysis
• Council support letter
"""
    st.text_area("Preview", template, height=240)
    st.download_button("Download Template", template.encode("utf-8"),
                       file_name="Grant_Template.txt", mime="text/plain")

# ---------- Engagement ----------
with tabs[3]:
    st.subheader("Stakeholder Engagement – Targeted Messages")
    audiences = st.multiselect("Select audience(s)",
        ["Council","Residents","Businesses","City Staff"], default=["Council","Residents"])
    base = f"In 2025 demo, Waterloo’s corporate emissions ≈ {fmt(grand_total)} tCO₂e. Focus: retrofits, EVs, diversion."
    for a in audiences:
        msg = call_openai(f"Write a short two-sentence update for {a} audience about {base}") if USE_AI else base
        st.markdown(f"**{a}**")
        st.text_area(f"Message for {a}", msg, height=100, key=f"{a}_msg")

st.caption("Demo unless Pilot uploads used. All charts labeled in tCO₂e. Funding programs reflect 2025 data.")
