# =============================================
# Data Leaf – City of Waterloo Pilot MVP (Final)
# Streamlit | Built for Demo + Pilot Uploads
# =============================================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests, os, urllib.parse, time, math
from datetime import datetime

# ----------------- PAGE CONFIG -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
st.set_page_config(page_title="Data Leaf – City of Waterloo Pilot MVP",
                   page_icon=LOGO_URL, layout="wide")

# ----------------- STYLES -----------------
st.markdown(f"""
<style>
.headerbar {{
  display:flex; align-items:center; gap:14px; margin-top:-10px; margin-bottom:12px;
}}
.headerbar img {{
  width:80px; height:auto; border-radius:12px; object-fit:contain;
}}
.headerbar h2 {{
  margin:0; font-weight:800; color:#1e6c93;
}}
.navbtn {{padding:8px 14px;border-radius:999px;border:1px solid #e5e7eb;
background:#fff;color:#111827;text-decoration:none;font-weight:600;}}
.navbtn.active {{background:#1e6c93;color:#fff;border-color:#1e6c93;}}
.badge {{display:inline-block;padding:4px 8px;border-radius:14px;background:#eef6ff;color:#1e6c93;margin-right:6px;font-size:0.85rem;}}
.pulse {{width:8px;height:8px;border-radius:50%;background:#22c55e;
box-shadow:0 0 0 6px rgba(34,197,94,.15);display:inline-block;}}
.smallcap {{color:#6b7280;font-size:0.9rem;}}
hr {{border:none;border-top:1px solid #e5e7eb;margin:8px 0 12px 0;}}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(
    f"""<div class="headerbar">
        <img src="{LOGO_URL}" alt="Data Leaf logo">
        <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
    </div>""",
    unsafe_allow_html=True
)

# ----------------- PRIVATE ADMIN (DEVELOPER ONLY) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)

if st._is_running_with_streamlit and st.experimental_user.email:  # Only visible to developer logged in
    with st.expander("🧩 Developer • Smart Assist Connection (Private)", expanded=True):
        st.caption("Visible only in developer workspace; hidden for public demos.")
        if st.button("Test AI Connection"):
            if not USE_AI:
                st.error("No API key found. Add it under Streamlit → Settings → Secrets.")
            else:
                try:
                    r = requests.post("https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                                 "Content-Type":"application/json"},
                        json={"model":"gpt-4o-mini",
                              "messages":[{"role":"user","content":"Reply only with Connected."}]})
                    if "Connected" in r.text:
                        st.success("✅ Connected to Smart Assist.")
                    else:
                        st.warning("⚠️ Could not confirm. Check key or plan balance.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

# ----------------- NAVIGATION -----------------
if "page" not in st.session_state:
    st.session_state.page = "Overview"

st.session_state.page = st.segmented_control(
    "Navigate",
    options=["Overview","Scenario Builder","Funding & Grants","Engagement"],
    default=st.session_state.page,
)

# ----------------- MODE -----------------
mode = st.radio("Mode", ["Demo", "Pilot (upload data)"], horizontal=True)
demo = mode == "Demo"

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
    fleet = pd.DataFrame({"vehicle":["Waste Truck 1","Waste Truck 2","By-law Car 3","Facilities Van 7"],
                          "fuel_type":["Diesel","Diesel","Gasoline","Diesel"],
                          "liters":[1800,1700,350,900]})
    waste = pd.DataFrame({"stream":["Municipal Solid Waste","Recycling","Organics"],
                          "amount_tonnes":[42,30,18]})
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ----------------- UPLOAD -----------------
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    c1,c2,c3=st.columns(3)
    with c1: ub=st.file_uploader("Buildings CSV", type="csv")
    with c2: uf=st.file_uploader("Fleet CSV", type="csv")
    with c3: uw=st.file_uploader("Waste CSV", type="csv")
    buildings=pd.read_csv(ub) if ub else demo_buildings
    fleet=pd.read_csv(uf) if uf else demo_fleet
    waste=pd.read_csv(uw) if uw else demo_waste

# ----------------- COST + FACTORS -----------------
emission_factors={"kwh":0.00003,"natural_gas_m3":0.00189,"diesel_l":0.00268,"gasoline_l":0.00231,"msw_tonne":0.45}
elec_rate,gas_rate,diesel_rate,gasoline_rate,landfill_rate=0.17,0.45,1.8,1.65,125

def calc_build(df):
    df=df.copy(); df["tco2e"]=df["kwh"]*0.00003+df["natural_gas_m3"]*0.00189
    df["cost"]=df["kwh"]*elec_rate+df["natural_gas_m3"]*gas_rate; return df
def calc_fleet(df):
    df=df.copy()
    df["tco2e"]=np.where(df["fuel_type"].str.contains("Diesel",case=False),
                         df["liters"]*0.00268,df["liters"]*0.00231)
    df["cost"]=np.where(df["fuel_type"].str.contains("Diesel",case=False),
                        df["liters"]*diesel_rate,df["liters"]*gasoline_rate);return df
def calc_waste(df):
    df=df.copy(); df["tco2e"]=np.where(df["stream"].str.contains("Municipal"),df["amount_tonnes"]*0.45,0)
    df["cost"]=np.where(df["stream"].str.contains("Municipal"),df["amount_tonnes"]*landfill_rate,0);return df

bld,flt,wst=calc_build(buildings),calc_fleet(fleet),calc_waste(waste)
fmt=lambda n:f"{n:,.1f}"
bld_t,flt_t,wst_t=bld["tco2e"].sum(),flt["tco2e"].sum(),wst["tco2e"].sum()
bld_cost,flt_cost,wst_cost=bld["cost"].sum(),flt["cost"].sum(),wst["cost"].sum()
grand_t,grand_cost=bld_t+flt_t+wst_t,bld_cost+flt_cost+wst_cost

# =========================================================
# PAGE 1: OVERVIEW
# =========================================================
if st.session_state.page=="Overview":
    k1,k2,k3,k4,k5=st.columns(5)
    k1.metric("Total (tCO₂e)",fmt(grand_t))
    k2.metric("Buildings",fmt(bld_t))
    k3.metric("Fleet",fmt(flt_t))
    k4.metric("Waste",fmt(wst_t))
    k5.metric("Annual Cost (CAD)",f"${grand_cost:,.0f}")
    st.markdown("<div class='smallcap'><span class='pulse'></span> Live Overview</div>",unsafe_allow_html=True)

    play=st.button("▶ Animate 10s")
    def overview(wobble=1.0):
        ca,cb,cc=st.columns(3)
        with ca:
            chart=bld.groupby("month",as_index=False)["tco2e"].sum(); chart["tco2e"]*=wobble
            st.altair_chart(alt.Chart(chart).mark_line(point=True,color="#1e6c93").encode(x="month",y="tco2e"),use_container_width=True)
        with cb:
            chart=flt.copy(); chart["tco2e"]*=wobble
            st.altair_chart(alt.Chart(chart).mark_bar(color="#2a9d8f").encode(x="vehicle",y="tco2e"),use_container_width=True)
        with cc:
            chart=wst.copy(); chart["tco2e"]*=wobble
            st.altair_chart(alt.Chart(chart).mark_bar(color="#8a5a44").encode(x="stream",y="tco2e"),use_container_width=True)
    overview(1.0)
    if play:
        start=time.time()
        while time.time()-start<10:
            overview(1.0+0.03*math.sin(time.time()*2))
            time.sleep(0.4)

# =========================================================
# PAGE 2: SCENARIO BUILDER
# =========================================================
elif st.session_state.page=="Scenario Builder":
    sA,sB,sC=st.columns(3)
    with sA: retro=st.slider("Buildings retrofit (%)",0,30,15)
    with sB: ev=st.slider("Fleet EV adoption (%)",0,50,20)
    with sC: div=st.slider("Waste diversion (%)",0,50,10)
    bld_sc_em=bld_t*(1-retro/100);flt_sc_em=flt_t*(1-ev/100);wst_sc_em=wst_t*(1-div/100)
    bld_sc_cost=bld_cost*(1-retro/100);flt_sc_cost=flt_cost*(1-ev/100);wst_sc_cost=wst_cost*(1-div/100)

    def chart_block(title,cur_em,sc_em,cur_c,sc_c,col1,col2):
        df=pd.DataFrame({"Case":["Current","Scenario"],"Emissions":[cur_em,sc_em],"Cost":[cur_c,sc_c]})
        bars=alt.Chart(df).mark_bar(color=col1).encode(x="Case",y="Emissions")
        line=alt.Chart(df).mark_line(point=True,color=col2,strokeWidth=3).encode(x="Case",y="Cost")
        st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title=title,height=260),use_container_width=True)

    pA,pB,pC=st.columns(3)
    with pA: chart_block("Buildings",bld_t,bld_sc_em,bld_cost,bld_sc_cost,"#1e6c93","#9ecae1")
    with pB: chart_block("Fleet",flt_t,flt_sc_em,flt_cost,flt_sc_cost,"#2a9d8f","#9fdacb")
    with pC: chart_block("Waste",wst_t,wst_sc_em,wst_cost,wst_sc_cost,"#8a5a44","#d6b7a6")

    st.subheader("Smart Assist – Scenario Summary")
    if USE_AI:
        prompt=f"City of Waterloo scenario: retrofit {retro}%, EV {ev}%, diversion {div}%. Base {fmt(grand_t)} tCO2e ${grand_cost:,.0f}. Explain practical impacts for city staff."
        res=requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},
            json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}]}).json()
        st.write(res["choices"][0]["message"]["content"] if "choices" in res else "AI summary unavailable.")
    else:
        st.info("Smart Assist inactive; connect API key for automatic scenario summaries.")

# =========================================================
# PAGE 3: FUNDING & GRANTS
# =========================================================
elif st.session_state.page=="Funding & Grants":
    st.subheader("Funding Programs (clickable) + Prefilled Template")
    programs=[("Infrastructure Canada – GICB","https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html","Community Buildings retrofits"),
              ("FCM GMF – Community Buildings","https://greenmunicipalfund.ca/community-buildings-retrofit-initiative","Energy retrofits, M&V"),
              ("FCM GMF – Fleet Electrification","https://greenmunicipalfund.ca/funding/fleet-electrification","EV planning & charging"),
              ("Ontario Climate/EV Programs","https://www.ontario.ca/page/climate-change-funding","Provincial climate/EV funding")]
    for n,l,d in programs:
        st.markdown(f"- [{n}]({l}) — {d}")
    pick=st.selectbox("Select to generate template",[p[0] for p in programs])
    st.download_button("Download Prefilled Template",
        f"Program: {pick}\nApplicant: City of Waterloo Sustainability Office\nSummary: Emission & cost reduction pilot leveraging Data Leaf dashboard.".encode("utf-8"),
        file_name="Grant_Template.txt")

# =========================================================
# PAGE 4: ENGAGEMENT
# =========================================================
elif st.session_state.page=="Engagement":
    st.subheader("Stakeholder Messages – City of Waterloo")
    groups=["Council","Residents","Businesses","City Staff"]
    topic=st.selectbox("Topic",["Quarterly update","Budget impact","Compliance progress","Pilot invitation"])
    defaults={
        "Council":"Waterloo is advancing measurable climate action. Current footprint is about 1,200 tCO₂e. Retrofit and EV measures could cut 15–25 % while saving on fuel and utilities.",
        "Residents":"The City of Waterloo is working to lower costs and emissions through better data. You can see progress in buildings, fleet, and waste—each step keeps our community thriving.",
        "Businesses":"Waterloo is improving efficiency city-wide. Data insights help identify funding and compliance opportunities that lower energy costs for everyone.",
        "City Staff":"Together we’re simplifying reporting. Data Leaf lets us upload, track, and visualize progress in one place—making updates faster and grant-ready."
    }
    for g in groups:
        st.markdown(f"**{g}**")
        st.text_area("Message",defaults[g],height=110)
        q=urllib.parse.quote(defaults[g])
        st.markdown(f"[LinkedIn](https://linkedin.com/shareArticle?mini=true&url=https://thedataleaf.com&summary={q}) | "
                    f"[𝕏](https://twitter.com/intent/tweet?text={q}) | "
                    f"[Facebook](https://facebook.com/sharer/sharer.php?u=https://thedataleaf.com&quote={q}) | "
                    f"[Email](mailto:?subject=City%20of%20Waterloo%20update&body={q})")
        st.divider()

# =========================================================
st.caption("All data demo-only. Costs in CAD. Smart Assist private. Data Leaf © 2025")
