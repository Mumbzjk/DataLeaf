import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os

# --- Optional AI setup
USE_AI = False
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    USE_AI = True

# -------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------
st.set_page_config(page_title="Data Leaf – City of Waterloo Pilot", page_icon="🌿", layout="wide")

# ---------------- DEMO DATA (synthetic but realistic, Jan–Jun 2025)
months = ["Jan","Feb","Mar","Apr","May","Jun"]
facilities = ["City Hall","RIM Park","WMRC","Operations Centre","Community Centre"]

rows=[]
for f in facilities:
    base_kwh={"City Hall":85000,"RIM Park":140000,"WMRC":120000,"Operations Centre":100000,"Community Centre":90000}[f]
    base_gas={"City Hall":18000,"RIM Park":30000,"WMRC":26000,"Operations Centre":22000,"Community Centre":20000}[f]
    for i,m in enumerate(months):
        mult=[1.15,1.10,1.05,0.95,0.90,0.88][i]
        rows.append({
            "facility":f,"month":m,"year":2025,
            "kwh":int(base_kwh*mult),
            "natural_gas_m3":int(base_gas*mult)
        })
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
factors=pd.DataFrame({
    "source":["kwh","natural_gas_m3","diesel_l","gasoline_l","tonnes_msw"],
    "tco2e_per_unit":[0.00003,0.00189,0.00268,0.00231,0.45]
})
grants=pd.DataFrame([
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
],columns=["program","deadline","match_pct","max_amount","categories","link","notes"])
checklist=pd.DataFrame([
    ["Governance","Climate roles documented?",0.2],
    ["Strategy","Approved climate action plan?",0.2],
    ["Emissions","Scope 1 & 2 tracked quarterly?",0.2],
    ["Targets","Reduction targets set?",0.2],
    ["Disclosure","Annual climate report published?",0.2]
],columns=["area","question","weight"])

# ---------------- CALCULATIONS
def calc_buildings(df):
    f_elec=factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]
    f_gas=factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
    df=df.copy()
    df["tco2e"]=df["kwh"]*f_elec+df["natural_gas_m3"]*f_gas
    return df
def calc_fleet(df):
    f_d=factors.loc[factors["source"]=="diesel_l","tco2e_per_unit"].values[0]
    f_g=factors.loc[factors["source"]=="gasoline_l","tco2e_per_unit"].values[0]
    df=df.copy()
    df["tco2e"]=np.where(df["fuel_type"].str.contains("Diesel"),df["liters"]*f_d,df["liters"]*f_g)
    return df
def calc_waste(df):
    f=factors.loc[factors["source"]=="tonnes_msw","tco2e_per_unit"].values[0]
    df=df.copy();df["tco2e"]=np.where(df["stream"].str.contains("Municipal"),df["amount"]*f,0)
    return df

bld=calc_buildings(buildings)
flt=calc_fleet(fleet)
wst=calc_waste(waste)

bld_total=bld["tco2e"].sum()
flt_total=flt["tco2e"].sum()
wst_total=wst["tco2e"].sum()
grand_total=bld_total+flt_total+wst_total
fmt=lambda n:f"{n:,.1f}"

# -------------------------------------------------------
# MAIN LAYOUT
# -------------------------------------------------------
st.title("🌿 Data Leaf – City of Waterloo Pilot MVP")
st.caption("Demo version (synthetic 2025 data) – shows how Waterloo can track GHG emissions, funding, and compliance in minutes.")

# KPIs
c1,c2,c3,c4=st.columns(4)
c1.metric("Total tCO₂e",fmt(grand_total))
c2.metric("Buildings",fmt(bld_total))
c3.metric("Fleet",fmt(flt_total))
c4.metric("Waste",fmt(wst_total))

# Trend chart
st.subheader("Emissions Trend by Facility – Jan to Jun 2025 (demo)")
chart=bld.groupby(["month","facility"],as_index=False)["tco2e"].sum()
order=["Jan","Feb","Mar","Apr","May","Jun"]
chart["month"]=pd.Categorical(chart["month"],categories=order,ordered=True)
chart=chart.sort_values("month")
st.altair_chart(
    alt.Chart(chart).mark_area(opacity=0.6).encode(
        x="month",y="tco2e",color="facility",tooltip=["facility","month","tco2e"]
    ).properties(height=300),
    use_container_width=True
)

# Top facilities
st.subheader("Top 3 Emission Sources (2025 demo)")
top3=bld.groupby("facility",as_index=False)["tco2e"].sum().sort_values("tco2e",ascending=False).head(3)
st.dataframe(top3.rename(columns={"tco2e":"tCO₂e"}),use_container_width=True)

# Funding
st.subheader("Relevant Funding – Aligned to Waterloo Priorities")
cat_opts=sorted(set(",".join(grants["categories"]).split(",")))
chosen=st.multiselect("Filter by category (optional)",cat_opts,[])
show=grants if not chosen else grants[grants["categories"].apply(lambda c:any(x in c for x in chosen))]
st.dataframe(show[["program","deadline","match_pct","max_amount","categories","link"]],use_container_width=True)

# Compliance
st.subheader("Compliance Readiness (Preview)")
score=0;answers=[]
for i,row in checklist.iterrows():
    val=st.checkbox(row["question"],value=(i in [0,2]))
    answers.append(val)
    if val:score+=row["weight"]
st.progress(score,text=f"{int(score*100)}% ready")
gaps=checklist.loc[[i for i,a in enumerate(answers) if not a],"question"].tolist()[:3]
if not gaps:gaps=["Minor updates needed."]
st.write("**Key gaps:** "+", ".join(gaps))
if "Targets" in " ".join(gaps):
    next_step="Document corporate reduction target (PCP Milestone 3) and publish short action plan."
elif "Emissions" in " ".join(gaps):
    next_step="Combine Scope 1 & 2 data into a quarterly tracker (buildings + fleet)."
else:
    next_step="Finalize governance roles and quarterly report schedule."
st.info(f"**Next Step:** {next_step}")

# ===================== Scenario Builder (Preview) =====================
st.subheader("Scenario Builder (Preview)")

colA, colB, colC = st.columns(3)
with colA:
    retro_pct = st.slider("Buildings retrofit savings", 0, 30, 15, help="Applies to building emissions from both electricity and natural gas.")
with colB:
    ev_pct = st.slider("Fleet EV adoption", 0, 50, 20, help="Reduces fleet tailpipe emissions proportionally (demo assumption).")
with colC:
    grid_pct = st.slider("Grid intensity change", -50, 50, -10, help="Adjusts the electricity emissions factor up/down (%).")

f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]
f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
f_elec_sc = f_elec * (1 + grid_pct/100.0)

tmp_b = buildings.copy()
tmp_b["tco2e_elec_sc"] = tmp_b["kwh"] * f_elec_sc
tmp_b["tco2e_gas_sc"]  = tmp_b["natural_gas_m3"] * f_gas
tmp_b["tco2e_sc_raw"]  = tmp_b["tco2e_elec_sc"] + tmp_b["tco2e_gas_sc"]
tmp_b["tco2e_sc"] = tmp_b["tco2e_sc_raw"] * (1 - retro_pct/100.0)
bld_total_sc = tmp_b["tco2e_sc"].sum()
flt_total_sc = flt_total * (1 - ev_pct/100.0)
wst_total_sc = wst_total
grand_sc = bld_total_sc + flt_total_sc + wst_total_sc
abs_savings = (bld_total + flt_total + wst_total) - grand_sc
pct_savings = 0.0 if (bld_total + flt_total + wst_total) == 0 else abs_savings / (bld_total + flt_total + wst_total) * 100

cc1, cc2, cc3 = st.columns(3)
cc1.metric("Current total (tCO₂e)", f"{grand_total:,.1f}")
cc2.metric("Scenario total (tCO₂e)", f"{grand_sc:,.1f}")
cc3.metric("Savings", f"{abs_savings:,.1f}", f"{pct_savings:,.1f}%")

comp_df = pd.DataFrame({
    "Case": ["Current","Scenario"],
    "tCO2e": [grand_total, grand_sc]
})
st.bar_chart(comp_df.set_index("Case"))
st.caption("Demo assumptions: retrofit savings apply uniformly to building electricity & gas; fleet EV % reduces tailpipe emissions; grid slider scales Ontario kWh factor. Precise modeling will be co-defined in the pilot.")
# =================== End Scenario Builder (Preview) ===================

# Stakeholder update
st.subheader("Stakeholder Update – 1 Click")
top_src=top3.iloc[0]["facility"]
sel_grant=show.iloc[0] if len(show)>0 else None
aud=st.selectbox("Audience",["Council","Residents","Businesses"])
if st.button("Generate Update"):
    base=f"In 2025 so far, Waterloo’s estimated emissions ≈ {fmt(grand_total)} tCO₂e. Top source: {top_src}. "
    if sel_grant is not None:
        base+=f"We’re pursuing the {sel_grant['program']} to support {sel_grant['categories'].split(',')[0]} projects."
    if USE_AI:
        try:
            out=client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":f"Write a two-sentence update for {aud}: {base}"}],
                temperature=0.3,max_tokens=100)
            st.success(out.choices[0].message.content.strip())
        except Exception:
            st.info(base)
    else:
        st.info(base)

st.caption("Demo data only; emission factors from ECCC/TAF; funding programs reflect real 2025 City of Waterloo priorities.")
