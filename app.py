# =============================================
# Data Leaf – City of Waterloo Pilot MVP (Full App)
# =============================================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests, os, urllib.parse, io
from datetime import datetime
import time

# ----------------- LOADING SCREEN -----------------
with st.spinner("🌿 Loading Data Leaf Dashboard — analyzing municipal emissions, costs, and funding insights..."):
    time.sleep(2)

# ----------------- PAGE CONFIG -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
st.set_page_config(page_title="Data Leaf – City of Waterloo Pilot MVP",
                   page_icon=LOGO_URL, layout="wide")

# ----------------- HEADER -----------------
st.markdown(f"""
<style>
.headerbar {{
  display:flex; align-items:center; gap:18px; margin-top:-10px; margin-bottom:12px;
}}
.headerbar img {{
  width:190px; height:auto; border-radius:14px; object-fit:contain;
}}
.headerbar h2 {{
  margin:0; font-weight:850; color:#1e6c93; font-size:2.2rem;
}}
.card {{
  border:1px solid #e5e7eb; border-radius:14px; padding:16px; background:#ffffff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
</style>
<div class="headerbar">
    <img src="{LOGO_URL}" alt="Data Leaf logo">
    <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
</div>
""", unsafe_allow_html=True)

# ----------------- SMART ASSIST (Developer only) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)
if USE_AI:
    with st.expander("🧩 Developer • Smart Assist Connection (Private)", expanded=False):
        st.caption("Visible only because your API key is active. Public users won’t see this.")
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini",
                      "messages": [{"role": "user", "content": "Reply only with Connected."}]}
            )
            if "Connected" in r.text:
                st.success("✅ Connected to Smart Assist.")
            else:
                st.warning("⚠️ Connection not verified.")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ----------------- NAVIGATION -----------------
if "page" not in st.session_state:
    st.session_state.page = "Overview"
st.session_state.page = st.segmented_control(
    "Navigate",
    options=["Overview", "Scenario Builder", "Funding & Grants", "Engagement"],
    default=st.session_state.page
)

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

buildings,fleet,waste = load_demo()

EF = {"kwh":0.00003, "natural_gas_m3":0.00189, "diesel":0.00268, "gasoline":0.00231, "waste":0.45}
RATE = {"kwh":0.17, "natural_gas_m3":0.45, "diesel":1.80, "gasoline":1.65, "waste":125.0}

def calc_build(df):
    df=df.copy()
    df["tco2e"]=df["kwh"]*EF["kwh"] + df["natural_gas_m3"]*EF["natural_gas_m3"]
    df["cost"]=df["kwh"]*RATE["kwh"] + df["natural_gas_m3"]*RATE["natural_gas_m3"]
    return df

def calc_fleet(df):
    df=df.copy()
    df["is_diesel"]=df["fuel_type"].str.contains("Diesel",case=False,na=False)
    df["tco2e"]=np.where(df["is_diesel"], df["liters"]*EF["diesel"], df["liters"]*EF["gasoline"])
    df["cost"]=np.where(df["is_diesel"], df["liters"]*RATE["diesel"], df["liters"]*RATE["gasoline"])
    return df

def calc_waste(df):
    df=df.copy()
    df["is_msw"]=df["stream"].str.contains("Municipal",case=False,na=False)
    df["tco2e"]=np.where(df["is_msw"], df["amount_tonnes"]*EF["waste"], 0)
    df["cost"]=np.where(df["is_msw"], df["amount_tonnes"]*RATE["waste"], 0)
    return df

bld, flt, wst = calc_build(buildings), calc_fleet(fleet), calc_waste(waste)
fmt = lambda n: f"{n:,.1f}"
bld_t, flt_t, wst_t = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
bld_c, flt_c, wst_c = bld["cost"].sum(), flt["cost"].sum(), wst["cost"].sum()
grand_t, grand_c = bld_t + flt_t + wst_t, bld_c + flt_c + wst_c

# =========================================================
# OVERVIEW
# =========================================================
if st.session_state.page=="Overview":
    st.subheader("Overview – Emissions and Cost")
    st.caption("_Demo data: Jan–Jun 2025. All units are labeled clearly._")

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total (tCO₂e)",fmt(grand_t))
    k2.metric("Buildings (tCO₂e)",fmt(bld_t))
    k3.metric("Fleet (tCO₂e)",fmt(flt_t))
    k4.metric("Waste (tCO₂e)",fmt(wst_t))
    k5.metric("Total Cost (CAD)",f"${grand_c:,.0f}")

    view_mode = st.selectbox("View mode:", ["Monthly", "Annual"], index=0)

    def overview_chart(df, category, color1, color2):
        df = df.groupby("month",as_index=False)[["tco2e","cost"]].sum()
        bars = alt.Chart(df).mark_bar(color=color1).encode(
            x="month:N", y=alt.Y("tco2e:Q", title="Emissions (tCO₂e)"), tooltip=["month","tco2e","cost"])
        line = alt.Chart(df).mark_line(point=True, color=color2).encode(
            x="month:N", y=alt.Y("cost:Q", title="Cost (CAD)"), tooltip=["month","tco2e","cost"])
        st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title=category,height=260),use_container_width=True)

    if view_mode=="Monthly":
        c1,c2,c3 = st.columns(3)
        with c1: overview_chart(bld,"Buildings","#1e6c93","#9ecae1")
        with c2: overview_chart(flt,"Fleet","#2a9d8f","#9fdacb")
        with c3: overview_chart(wst,"Waste","#8a5a44","#d6b7a6")
    else:
        annual = pd.DataFrame({
            "Category":["Buildings","Fleet","Waste"],
            "Emissions":[bld_t,flt_t,wst_t],
            "Cost":[bld_c,flt_c,wst_c]
        })
        c1,c2 = st.columns(2)
        with c1:
            st.altair_chart(alt.Chart(annual).mark_bar(color="#1e6c93").encode(
                x="Category", y="Emissions", tooltip=["Category","Emissions"]).properties(title="Annual Emissions by Category"),use_container_width=True)
        with c2:
            st.altair_chart(alt.Chart(annual).mark_bar(color="#9ecae1").encode(
                x="Category", y="Cost", tooltip=["Category","Cost"]).properties(title="Annual Cost by Category"),use_container_width=True)

# =========================================================
# SCENARIO BUILDER
# =========================================================
elif st.session_state.page=="Scenario Builder":
    st.subheader("Scenario Builder")
    sA,sB,sC=st.columns(3)
    with sA: retro=st.slider("Buildings retrofit (%)",0,30,15)
    with sB: ev=st.slider("Fleet EV adoption (%)",0,50,20)
    with sC: div=st.slider("Waste diversion (%)",0,50,10)

    def chart_block(title,cur_em,sc_em,cur_c,sc_c,col1,col2):
        df=pd.DataFrame({"Case":["Current","Scenario"],"Emissions":[cur_em,sc_em],"Cost":[cur_c,sc_c]})
        bars=alt.Chart(df).mark_bar(color=col1).encode(x="Case",y="Emissions",tooltip=["Case","Emissions","Cost"])
        line=alt.Chart(df).mark_line(point=True,color=col2).encode(x="Case",y="Cost",tooltip=["Case","Emissions","Cost"])
        st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title=title,height=260),use_container_width=True)

    pA,pB,pC=st.columns(3)
    with pA: chart_block("Buildings",bld_t,bld_t*(1-retro/100),bld_c,bld_c*(1-retro/100),"#1e6c93","#9ecae1")
    with pB: chart_block("Fleet",flt_t,flt_t*(1-ev/100),flt_c,flt_c*(1-ev/100),"#2a9d8f","#9fdacb")
    with pC: chart_block("Waste",wst_t,wst_t*(1-div/100),wst_c,wst_c*(1-div/100),"#8a5a44","#d6b7a6")

# =========================================================
# FUNDING & GRANTS — Full Intelligent Funding Centre
# =========================================================
elif st.session_state.page == "Funding & Grants":
    st.subheader("Funding & Grants – Smart Funding Centre")
    st.markdown("_Discover and apply for the most relevant climate and infrastructure programs._")

    total_em = grand_t if grand_t > 0 else 1
    share = {"Buildings": bld_t/total_em, "Fleet": flt_t/total_em, "Waste": wst_t/total_em}

    PROGRAMS = [
        {"name":"Infrastructure Canada – GICB","amount":"Up to $25M","deadline":"2026-03-31",
         "focus":["Buildings"],"summary":"Supports deep retrofits or new builds that improve efficiency and accessibility.",
         "examples":"City of Brampton retrofitted community centres ($7.8M, 2023).",
         "link":"https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html"},
        {"name":"FCM GMF – Community Buildings Retrofit","amount":"Up to $5M","deadline":"2025-12-15",
         "focus":["Buildings"],"summary":"Funds audits and retrofits improving performance in municipal facilities.",
         "examples":"Guelph upgraded HVAC ($3.4M, 2023).",
         "link":"https://greenmunicipalfund.ca/community-buildings-retrofit-initiative"},
        {"name":"FCM GMF – Fleet Electrification","amount":"Up to $1M+","deadline":"2025-11-30",
         "focus":["Fleet"],"summary":"Provides grants for fleet transition plans and pilot deployments.",
         "examples":"Durham EV waste truck pilot ($800k, 2023).",
         "link":"https://greenmunicipalfund.ca/funding/fleet-electrification"},
        {"name":"FCM GMF – Climate Adaptation","amount":"Up to $1M+","deadline":"2025-12-31",
         "focus":["Adaptation"],"summary":"Supports risk assessments and resilience-building projects.",
         "examples":"London flood resilience plan ($1.2M, 2022).",
         "link":"https://greenmunicipalfund.ca/funding/adaptation"},
    ]

    rows=[]
    for p in PROGRAMS:
        base = 0
        if "Buildings" in p["focus"]: base += share["Buildings"]
        if "Fleet" in p["focus"]: base += share["Fleet"]
        if "Adaptation" in p["focus"]: base += 0.1
        match_pct = int(round(min(0.95, max(0.15, base)) * 100))
        rows.append({"Program": f"[{p['name']}]({p['link']})","Amount":p["amount"],"Match %":f"{match_pct}%","Deadline":p["deadline"]})
# Create a clean, clickable funding table (no raw HTML or repetition)
funding_df = pd.DataFrame(rows)

def make_clickable(val):
    """Turn markdown link into an HTML hyperlink that opens in a new tab."""
    if "](" in val:  # Markdown link pattern
        label = val.split("](")[0].replace("[", "")
        url = val.split("](")[1].replace(")", "")
        return f'<a href="{url}" target="_blank" style="text-decoration:none; color:#1e6c93; font-weight:600;">{label}</a>'
    return val

funding_df["Program"] = funding_df["Program"].apply(make_clickable)

# Display as HTML so the links stay clickable
st.write(
    funding_df.to_html(escape=False, index=False),
    unsafe_allow_html=True
)

st.caption("_Click any program name to open the official page._")

    st.caption("_Click any program name to open the official page._")

    st.markdown("### Explore Program Summaries")
    for p in PROGRAMS:
        with st.expander(f"📄 {p['name']}"):
            st.markdown(f"**Amount:** {p['amount']}  \n**Deadline:** {p['deadline']}  \n**Focus:** {', '.join(p['focus'])}")
            st.markdown(f"**Summary:** {p['summary']}")
            st.markdown(f"**Example:** _{p['examples']}_")
            st.markdown(f"[🔗 View Program Page]({p['link']})")

    st.divider()
    st.markdown("### 🤖 Grant Assist – Find Best Fit Automatically")
    st.caption("Paste your project description below to get AI-powered grant matches.")
    user_input = st.text_area("Enter project description:", placeholder="e.g., Energy retrofit for city buildings and EV fleet transition.")
    if st.button("Analyze & Recommend Grants"):
        if OPENAI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                prompt = f"You are an AI grant advisor. Given this project description: {user_input}, match it to {', '.join([p['name'] for p in PROGRAMS])} and explain the top 3 fits briefly."
                r = requests.post("https://api.openai.com/v1/chat/completions",headers=headers,
                                  json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}]})
                out = r.json()["choices"][0]["message"]["content"]
                st.success("Top Matches:")
                st.markdown(out)
            except Exception as e:
                st.error(f"AI Grant Assist error: {e}")
        else:
            st.warning("OpenAI API key not found.")

    st.divider()
    st.markdown("### 📊 My Funding Tracker")
    total_open = len(PROGRAMS)
    matched = sum(1 for p in PROGRAMS if "Buildings" in p["focus"] or "Fleet" in p["focus"])
    next_deadline = sorted([p["deadline"] for p in PROGRAMS if p["deadline"]!="Rolling"])[0]
    c1,c2,c3=st.columns(3)
    c1.metric("Open Programs",total_open)
    c2.metric("Matched to City Priorities",matched)
    c3.metric("Next Deadline",next_deadline)

    if st.button("Generate Next Steps"):
        if OPENAI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                prompt = "Based on Waterloo’s funding readiness, list 4 key next steps to maximize grants and compliance."
                r = requests.post("https://api.openai.com/v1/chat/completions",headers=headers,
                                  json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}]})
                st.info(r.json()["choices"][0]["message"]["content"])
            except Exception as e:
                st.error(f"AI Tracker error: {e}")

# =========================================================
# ENGAGEMENT
# =========================================================
# =========================================================
# ENGAGEMENT — dropdowns → tailored message side-card
# =========================================================
elif nav == "Engagement":
    st.subheader("Stakeholder Engagement")

    stakeholders = ["Council","Residents","Businesses","City Staff"]
    topics = ["Buildings Retrofit","Fleet Electrification","Waste Diversion","Compliance Update","Pilot Invitation"]

    c1, c2 = st.columns(2)
    with c1:
        who = st.selectbox("Stakeholder", stakeholders)
    with c2:
        topic = st.selectbox("Program / Topic", topics)

    # Tailored messages (neutral tone, concise)
    base = {
        ("Council","Buildings Retrofit"): "Targeted retrofits lower utility spend and emissions. Scenario results show meaningful savings with grants improving payback.",
        ("Council","Fleet Electrification"): "Phased EV adoption for high-usage routes reduces fuel and maintenance costs while improving compliance readiness.",
        ("Council","Waste Diversion"): "Increased diversion and organics reduce landfill fees and stabilize operating costs.",
        ("Council","Compliance Update"): "Dashboards consolidate reporting evidence—fewer manual hours and clearer audit trails amid changing rules.",
        ("Council","Pilot Invitation"): "A focused 3–4 month pilot co-designed with staff delivers measurable outcomes and grant-ready documentation.",

        ("Residents","Buildings Retrofit"): "Improving energy efficiency in community buildings reduces costs and emissions—savings that support local services.",
        ("Residents","Fleet Electrification"): "Transitioning select city vehicles to electric cuts noise and emissions while saving on fuel.",
        ("Residents","Waste Diversion"): "Better recycling and organics keep materials out of landfill, reducing costs and climate impact.",
        ("Residents","Compliance Update"): "The city is tracking progress clearly and transparently with simple, public-friendly summaries.",
        ("Residents","Pilot Invitation"): "We’re testing practical steps that lower bills and emissions—your feedback helps shape next steps.",

        ("Businesses","Buildings Retrofit"): "Data identifies best-return retrofits; available programs offset upfront cost and reduce total cost of ownership.",
        ("Businesses","Fleet Electrification"): "EV pilots on predictable routes reduce fuel risk and maintenance downtime.",
        ("Businesses","Waste Diversion"): "Improved sorting and organics programs reduce fees and streamline operations.",
        ("Businesses","Compliance Update"): "Clear reporting supports supply-chain and lender requests with investor-grade summaries.",
        ("Businesses","Pilot Invitation"): "A focused pilot de-risks adoption and demonstrates value quickly.",

        ("City Staff","Buildings Retrofit"): "Upload, track, and visualize facility data—faster reporting, fewer spreadsheets, grant-ready outputs.",
        ("City Staff","Fleet Electrification"): "Target high-use units first. Scenario sliders quantify emissions and cost impacts instantly.",
        ("City Staff","Waste Diversion"): "Track streams, quantify landfill fees, and estimate savings from diversion.",
        ("City Staff","Compliance Update"): "Dashboards map metrics to reporting needs, creating an audit trail for submissions.",
        ("City Staff","Pilot Invitation"): "Pilot scope is co-designed; you choose the focus while we provide tooling and templates."
    }

    message = base.get((who, topic),
        "Data and dashboards make progress visible, reduce manual work, and support funding applications.")

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"**To:** {who}  \n**Subject:** {topic}")
    st.write(message)

    q = urllib.parse.quote(message)
    st.markdown(
        f"[LinkedIn](https://linkedin.com/shareArticle?mini=true&url=https://thedataleaf.com&summary={q}) | "
        f"[𝕏](https://twitter.com/intent/tweet?text={q}) | "
        f"[Facebook](https://facebook.com/sharer/sharer.php?u=https://thedataleaf.com&quote={q}) | "
        f"[Email](mailto:?subject={urllib.parse.quote(topic)}&body={q})"
    )
    st.caption("Tip: click inside the message and press ⌘/Ctrl + C to copy.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
st.caption("Demo data only. Units indicated on every chart. Costs in CAD. Data Leaf © 2025")
