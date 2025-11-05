import streamlit as st
import pandas as pd
import numpy as np
import os

# --- Optional AI setup ---
USE_AI = False
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    USE_AI = True

st.set_page_config(page_title="Data Leaf – Waterloo Pilot MVP", page_icon="🌿", layout="wide")

# ---------- DEMO DATA (synthetic but realistic)
buildings_data = pd.DataFrame({
    "facility":["City Hall","Rec Complex","RIM Park","Community Centre","Operations Centre"],
    "month":["Jan","Feb","Mar","Apr","May","Jun"]*1,
    "kwh":[85000,83000,80000,78000,76000,75000],
    "natural_gas_m3":[18000,17500,17000,16000,15000,14500]
})
fleet_data = pd.DataFrame({
    "vehicle":["Waste Truck 1","Waste Truck 2","Bylaw Car 3","Facilities Van 7"],
    "fuel_type":["Diesel","Diesel","Gasoline","Diesel"],
    "liters":[1800,1700,350,900]
})
waste_data = pd.DataFrame({
    "stream":["Municipal Solid Waste","Recycling","Organics"],
    "amount":[42,30,18]
})
emission_factors = pd.DataFrame({
    "source":["kwh","natural_gas_m3","diesel_l","gasoline_l","tonnes_msw"],
    "tco2e_per_unit":[0.00003,0.00189,0.00268,0.00231,0.45]
})
grants = pd.DataFrame([
    ["FCM GMF – Community Buildings Retrofit","Rolling","Up to 50%","Varies",
     "buildings,retrofit,energy_efficiency,resilience",
     "https://greenmunicipalfund.ca/community-buildings-retrofit-initiative",
     "Supports deep energy retrofits and low-carbon upgrades."],
    ["FCM GMF – Fleet Electrification","Year-round","Up to 50%","Up to $1 M",
     "fleet,electrification,ev_charging",
     "https://greenmunicipalfund.ca/funding/fleet-electrification",
     "EVs, charging and feasibility studies."],
    ["GICB – Infrastructure Canada","Mar 2029","Up to 60%","Up to $25 M",
     "buildings,retrofit,renewable_energy,accessibility",
     "https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html",
     "Large retrofits / new low-carbon community facilities."],
    ["FCM GMF – Climate Adaptation Program","2025-26","Up to 60%","Up to $1.5 M",
     "resilience,adaptation,flooding,heat",
     "https://greenmunicipalfund.ca/funding/adaptation",
     "Helps assess & adapt to climate risks."],
    ["Ontario Community Infrastructure Fund","Annual","Up to 90%","Up to $500 k",
     "resilience,infrastructure,roads,water",
     "https://www.ontario.ca/page/ontario-community-infrastructure-fund",
     "Supports resilient local infrastructure."],
    ["Circular Economy & Waste Innovation Fund","2025-26","Up to 80%","Up to $500 k",
     "waste,circular_economy,innovation",
     "https://www.canada.ca/en/environment-climate-change/services/funding-programs/circular-economy-innovation.html",
     "Innovative waste reduction / reuse projects."]
], columns=["program","deadline","match_pct","max_amount","categories","link","notes"])
checklist = pd.DataFrame([
    ["Governance","Climate roles documented?",0.2],
    ["Strategy","Approved climate action plan?",0.2],
    ["Emissions","Scope 1 & 2 tracked quarterly?",0.2],
    ["Targets","Reduction targets set?",0.2],
    ["Disclosure","Annual climate report published?",0.2]
], columns=["area","question","weight"])

# ---------- CALCULATIONS
def calc_tco2e_buildings(df):
    f_kwh = emission_factors.loc[emission_factors["source"]=="kwh","tco2e_per_unit"].values[0]
    f_gas = emission_factors.loc[emission_factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
    df["tco2e"] = df["kwh"]*f_kwh + df["natural_gas_m3"]*f_gas
    return df
def calc_tco2e_fleet(df):
    f_d = emission_factors.loc[emission_factors["source"]=="diesel_l","tco2e_per_unit"].values[0]
    f_g = emission_factors.loc[emission_factors["source"]=="gasoline_l","tco2e_per_unit"].values[0]
    df["tco2e"] = np.where(df["fuel_type"].str.contains("Diesel"),df["liters"]*f_d,df["liters"]*f_g)
    return df
def calc_tco2e_waste(df):
    f = emission_factors.loc[emission_factors["source"]=="tonnes_msw","tco2e_per_unit"].values[0]
    df["tco2e"] = np.where(df["stream"].str.contains("Municipal"),df["amount"]*f,0)
    return df

bld = calc_tco2e_buildings(buildings_data)
flt = calc_tco2e_fleet(fleet_data)
wst = calc_tco2e_waste(waste_data)
bld_total, flt_total, wst_total = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
grand_total = bld_total + flt_total + wst_total
fmt = lambda n: f"{n:,.1f}"

# ---------- LAYOUT
st.title("🌿 Data Leaf – City of Waterloo Pilot MVP")
st.caption("Automated GHG snapshot → Real funding → Compliance → Stakeholder update")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total tCO₂e",fmt(grand_total))
c2.metric("Buildings",fmt(bld_total))
c3.metric("Fleet",fmt(flt_total))
c4.metric("Waste",fmt(wst_total))

st.subheader("Emissions Snapshot (Demo Data)")
st.bar_chart(bld.groupby("facility")["tco2e"].sum())

st.subheader("Relevant Funding (Real Programs Aligned to City Priorities)")
sel = st.multiselect("Filter by category (optional)",
                     sorted(set(",".join(grants["categories"]).split(","))),[])
if sel:
    show = grants[grants["categories"].apply(lambda x:any(s in x for s in sel))]
else:
    show = grants
st.dataframe(show[["program","deadline","match_pct","max_amount","categories","link"]],use_container_width=True)

st.subheader("Compliance Readiness (Preview)")
score=0;answers=[]
for i,row in checklist.iterrows():
    val=st.checkbox(row["question"],value=(i in [0,2]))
    answers.append(val)
    if val: score+=row["weight"]
st.progress(score,text=f"{int(score*100)}% ready")
gaps = checklist.loc[[i for i,a in enumerate(answers) if not a],"question"].tolist()[:3]
if not gaps: gaps=["Minor documentation updates needed."]
st.write("**Key gaps:** " + "; ".join(gaps))
next_step="Focus on target setting and updating public reporting to reach full readiness."
st.info(f"**Next Step:** {next_step}")

st.subheader("Stakeholder Update (One Click)")
aud = st.selectbox("Audience",["Council","Residents","Businesses"])
if st.button("Generate Update"):
    base = f"This period emissions ≈ {fmt(grand_total)} tCO₂e (mainly buildings and fleet). "
    base += f"We’re pursuing the {show.iloc[0]['program']} for support on {show.iloc[0]['categories'].split(',')[0]}."
    if USE_AI:
        prompt=f"Write a two-sentence update for {aud}. Info: {base}"
        try:
            out=client.chat.completions.create(model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],temperature=0.3,max_tokens=100)
            st.success(out.choices[0].message.content.strip())
        except Exception as e:
            st.warning("AI summary unavailable. Showing base text.")
            st.info(base)
    else:
        st.info(base)

st.caption("Demo data only; emission factors from ECCC/TAF; funding programs are real and current to City of Waterloo priorities.")
