import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
from io import BytesIO

# ============== Optional AI =================
USE_AI = False
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        USE_AI = True
    except Exception:
        USE_AI = False

# ============== Page ========================
st.set_page_config(
    page_title="Data Leaf – City of Waterloo Pilot",
    page_icon="https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png",
    layout="wide"
)

# --- Display Data Leaf logo ---
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
st.markdown(
    f"""
    <div style='text-align:center; margin-bottom: 10px;'>
        <img src='{LOGO_URL}' alt='Data Leaf logo' width='180'>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------ MODE SWITCH ------------------
mode = st.radio("Select Mode", ["Demo Mode", "Pilot Mode"], horizontal=True)
demo = mode == "Demo Mode"
st.caption("🌿 *Switch to Pilot Mode to upload your own data; Demo Mode uses sample data.*")

# ============== Load Data (demo or upload) ==============
def load_demo():
    months = ["Jan","Feb","Mar","Apr","May","Jun"]
    facilities = ["City Hall","RIM Park","WMRC","Operations Centre","Community Centre"]
    rows=[]
    for f in facilities:
        base_kwh={"City Hall":85000,"RIM Park":140000,"WMRC":120000,"Operations Centre":100000,"Community Centre":90000}[f]
        base_gas={"City Hall":18000,"RIM Park":30000,"WMRC":26000,"Operations Centre":22000,"Community Centre":20000}[f]
        for i,m in enumerate(months):
            mult=[1.15,1.10,1.05,0.95,0.90,0.88][i]
            rows.append({"facility":f,"month":m,"year":2025,"kwh":int(base_kwh*mult),"natural_gas_m3":int(base_gas*mult)})
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

# --- Demo fallback
demo_buildings, demo_fleet, demo_waste = load_demo()

# --- Pilot Uploads
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    st.info("🔹 Upload your monthly CSVs for Buildings, Fleet, and Waste below.")
    ub = st.file_uploader("Upload Buildings CSV", type=["csv"], help="Columns: facility,month,year,kwh,natural_gas_m3")
    uf = st.file_uploader("Upload Fleet CSV", type=["csv"], help="Columns: vehicle,fuel_type,liters")
    uw = st.file_uploader("Upload Waste CSV", type=["csv"], help="Columns: stream,amount (tonnes)")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet = pd.read_csv(uf) if uf else demo_fleet
    waste = pd.read_csv(uw) if uw else demo_waste

# ============== Factors & Grants ==============
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
    ["FCM GMF – Climate Adaptation Program","2025-26","Up to 60%","Up to $1.5 M",
     "resilience,adaptation,flooding,heat",
     "https://greenmunicipalfund.ca/funding/adaptation",
     "Helps municipalities adapt to climate risks."],
    ["Circular Economy & Waste Innovation Fund","2025-26","Up to 80%","Up to $500 k",
     "waste,circular_economy,innovation",
     "https://www.canada.ca/en/environment-climate-change/services/funding-programs/circular-economy-innovation.html",
     "Innovative waste reduction / reuse projects."]
], columns=["program","deadline","match_pct","max_amount","categories","link","notes"])

# ============== Calculations =================
def calc_buildings(df):
    f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]
    f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
    df = df.copy()
    df["tco2e"] = df["kwh"]*f_elec + df["natural_gas_m3"]*f_gas
    return df

def calc_fleet(df):
    f_d = factors.loc[factors["source"]=="diesel_l","tco2e_per_unit"].values[0]
    f_g = factors.loc[factors["source"]=="gasoline_l","tco2e_per_unit"].values[0]
    df = df.copy()
    df["tco2e"] = np.where(df["fuel_type"].str.lower().str.contains("diesel"), df["liters"]*f_d, df["liters"]*f_g)
    return df

def calc_waste(df):
    f = factors.loc[factors["source"]=="tonnes_msw","tco2e_per_unit"].values[0]
    df = df.copy()
    df["tco2e"] = np.where(df["stream"].str.contains("Municipal"), df["amount"]*f, 0)
    return df

bld = calc_buildings(buildings)
flt = calc_fleet(fleet)
wst = calc_waste(waste)

bld_total, flt_total, wst_total = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
grand_total = bld_total + flt_total + wst_total
fmt = lambda n: f"{n:,.1f}"

# ============== Layout =======================
st.title("🌿 Data Leaf – City of Waterloo Pilot MVP")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total tCO₂e", fmt(grand_total))
c2.metric("Buildings", fmt(bld_total))
c3.metric("Fleet", fmt(flt_total))
c4.metric("Waste", fmt(wst_total))

tabs = st.tabs(["Overview","Buildings","Fleet","Waste","Funding","Engagement"])

# ============== Overview =====================
with tabs[0]:
    st.subheader("Emissions Trend — Buildings (Jan–Jun 2025)")
    order = ["Jan","Feb","Mar","Apr","May","Jun"]
    chart = bld.groupby(["month","facility"],as_index=False)["tco2e"].sum()
    if "month" in chart.columns:
        chart["month"] = pd.Categorical(chart["month"], categories=order, ordered=True)
    st.altair_chart(
        alt.Chart(chart).mark_area(opacity=0.6).encode(
            x="month", y="tco2e", color="facility", tooltip=["facility","month","tco2e"]
        ).properties(height=300), use_container_width=True
    )
    st.caption("Automatic refresh with your data when uploaded in Pilot Mode.")

# ============== Buildings ====================
with tabs[1]:
    st.subheader("Buildings Scenario")
    retro = st.slider("Retrofit savings (%)",0,30,15)
    grid = st.slider("Grid intensity change (%)",-50,50,-10)
    f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]*(1+grid/100)
    f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
    bld_sc = (bld["kwh"]*f_elec + bld["natural_gas_m3"]*f_gas)*(1-retro/100)
    bld_sc_total = bld_sc.sum()
    st.metric("Scenario total (tCO₂e)", fmt(bld_sc_total), f"-{fmt(bld_total-bld_sc_total)}")

# ============== Fleet ========================
with tabs[2]:
    st.subheader("Fleet Scenario")
    ev = st.slider("EV adoption (%)",0,50,20)
    flt_sc_total = flt_total*(1-ev/100)
    st.metric("Scenario total (tCO₂e)", fmt(flt_sc_total), f"-{fmt(flt_total-flt_sc_total)}")

# ============== Waste ========================
with tabs[3]:
    st.subheader("Waste Scenario")
    div = st.slider("Diversion increase (%)",0,50,10)
    msw = wst[wst["stream"].str.contains("Municipal")]["tco2e"].sum()
    wst_sc_total = wst_total - msw*(div/100)
    st.metric("Scenario total (tCO₂e)", fmt(wst_sc_total), f"-{fmt(wst_total-wst_sc_total)}")

# ============== Funding ======================
with tabs[4]:
    st.subheader("Relevant Funding (clickable)")
    for _, r in grants.iterrows():
        st.markdown(f"- **{r['program']}** – *{r['match_pct']}* – {r['deadline']}  \n"
                    f"  {r['notes']}  \n"
                    f"  👉 [{r['link']}]({r['link']})")
    st.divider()
    sel = st.selectbox("Generate Prefilled Grant Template", grants["program"])
    gr = grants[grants["program"]==sel].iloc[0]
    top_src = bld.groupby("facility",as_index=False)["tco2e"].sum().sort_values("tco2e",ascending=False).iloc[0]["facility"]
    key_cat = gr["categories"].split(",")[0]
    template = f"""PROGRAM: {gr['program']}
Deadline: {gr['deadline']}
Match: {gr['match_pct']} (Max {gr['max_amount']})
Link: {gr['link']}

Project Summary:
The City of Waterloo aims to reduce emissions in {key_cat}, focusing on {top_src}.
Current corporate footprint ≈ {fmt(grand_total)} tCO₂e (Buildings {fmt(bld_total)}, Fleet {fmt(flt_total)}, Waste {fmt(wst_total)}).
"""
    st.text_area("Preview", template, height=200)
    st.download_button("Download Template (.txt)", template.encode("utf-8"),
                       file_name="Grant_Template.txt", mime="text/plain")

# ============== Engagement ===================
with tabs[5]:
    st.subheader("Stakeholder Update")
    msg = f"In 2025 (demo), Waterloo’s emissions ≈ {fmt(grand_total)} tCO₂e. Focus: retrofits & EV transition."
    if USE_AI and st.button("Generate AI Message"):
        try:
            prompt = f"Write a two-sentence upbeat city update using this context: {msg}"
            out = client.chat.completions.create(model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}], temperature=0.3, max_tokens=80)
            msg = out.choices[0].message.content.strip()
        except Exception:
            pass
    st.text_area("Copy & share", msg, height=120)
    st.caption("Paste into council notes, newsletter, or LinkedIn. Pilot Mode = your real numbers.")

st.caption("Demo data only unless Pilot Mode uploads used. Emission factors from ECCC/TAF. Funding programs 2025 real examples.")
