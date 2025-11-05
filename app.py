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
c3.metric
