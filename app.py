# =============================================
# Data Leaf – City of Waterloo Pilot MVP
# Overview clarity + Funding scoring + Engagement dropdowns
# =============================================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests, os, urllib.parse, io
from datetime import datetime

# ----------------- PAGE CONFIG -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
# ----------------- LOADING SCREEN -----------------
with st.spinner("🌿 Loading Data Leaf Dashboard — analyzing municipal emissions, costs, and funding insights..."):
    import time
    time.sleep(2)  # short 2-second splash delay for smooth load

st.set_page_config(page_title="Data Leaf – City of Waterloo Pilot MVP",
                   page_icon=LOGO_URL, layout="wide")

# ----------------- HEADER -----------------
st.markdown(f"""
<style>
.headerbar {{
  display:flex; align-items:center; gap:18px; margin-top:-10px; margin-bottom:12px;
}}
.headerbar img {{
  width:180px; height:auto; border-radius:14px; object-fit:contain;
}}
.headerbar h2 {{
  margin:0; font-weight:850; color:#1e6c93; font-size:2.1rem;
}}
.card {{
  border:1px solid #e5e7eb; border-radius:14px; padding:16px; background:#ffffff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
.badge {{display:inline-block;padding:4px 8px;border-radius:14px;background:#eef6ff;color:#1e6c93;margin-right:6px;font-size:0.85rem;}}
.smallcap {{color:#6b7280;font-size:0.9rem;}}
.table-note {{color:#6b7280;font-size:0.85rem;margin-top:-6px}}
</style>
<div class="headerbar">
    <img src="{LOGO_URL}" alt="Data Leaf logo">
    <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
</div>
""", unsafe_allow_html=True)

# ----------------- (Optional) Developer Admin (shows only when key present) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)
if USE_AI:
    with st.expander("🧩 Developer • Smart Assist Connection (Private)", expanded=False):
        st.caption("Visible only because your API key is active. Public users won’t see this.")
        if st.button("Test AI Connection"):
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
                    st.warning("⚠️ Could not confirm connection. Check key or plan balance.")
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

# ----------------- FACTORS & RATES -----------------
EF = {"kwh":0.00003, "natural_gas_m3":0.00189, "diesel":0.00268, "gasoline":0.00231, "waste":0.45}
RATE = {"kwh":0.17, "natural_gas_m3":0.45, "diesel":1.80, "gasoline":1.65, "waste":125.0}

# ----------------- CALCULATIONS -----------------
def calc_build(df):
    df=df.copy()
    df["tco2e"]=df["kwh"]*EF["kwh"] + df["natural_gas_m3"]*EF["natural_gas_m3"]
    df["cost"]=df["kwh"]*RATE["kwh"] + df["natural_gas_m3"]*RATE["natural_gas_m3"]
    df["elec_cost"]=df["kwh"]*RATE["kwh"]
    df["gas_cost"]=df["natural_gas_m3"]*RATE["natural_gas_m3"]
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

# ----------------- PDF EXPORT (Overview) -----------------
def build_overview_report_pdf(monthly: bool) -> bytes:
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=LETTER)
        w, h = LETTER

        title = "Data Leaf – Overview Report"
        sub = f"View mode: {'Monthly' if monthly else 'Annual'} • Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        totals = [
            f"Total emissions: {fmt(grand_t)} tCO2e",
            f"Total annual cost: ${grand_c:,.0f}",
            f"Buildings: {fmt(bld_t)} tCO2e • ${bld_c:,.0f}",
            f"Fleet: {fmt(flt_t)} tCO2e • ${flt_c:,.0f}",
            f"Waste: {fmt(wst_t)} tCO2e • ${wst_c:,.0f}",
        ]

        y = h - 1.0*inch
        c.setFont("Helvetica-Bold", 14); c.drawString(1*inch, y, title); y -= 0.3*inch
        c.setFont("Helvetica", 10); c.drawString(1*inch, y, sub); y -= 0.4*inch
        c.setFont("Helvetica", 11)
        for line in totals:
            c.drawString(1*inch, y, f"• {line}"); y -= 0.24*inch

        if not monthly:
            y -= 0.2*inch
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(1*inch, y, "Annual totals are aggregated from all facilities and sources.")

        c.showPage(); c.save()
        buf.seek(0)
        return buf.read()
    except Exception:
        return b""

def build_overview_report_markdown(monthly: bool) -> bytes:
    md = f"""# Data Leaf – Overview Report

**View mode:** {'Monthly' if monthly else 'Annual'}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Totals (Demo period: Jan–Jun 2025)**
- Total emissions: {fmt(grand_t)} tCO₂e  
- Total annualized cost: ${grand_c:,.0f}  
- Buildings: {fmt(bld_t)} tCO₂e • ${bld_c:,.0f}  
- Fleet: {fmt(flt_t)} tCO₂e • ${flt_c:,.0f}  
- Waste: {fmt(wst_t)} tCO₂e • ${wst_c:,.0f}

{('*Annual totals are aggregated from all facilities and sources.*' if not monthly else '')}
"""
    return md.encode("utf-8")

# =========================================================
# OVERVIEW — Monthly/Annual toggle + clear units + clarity note
# =========================================================
if st.session_state.page=="Overview":
    st.subheader("Overview – Emissions and Cost")
    st.markdown("_Explore emissions and cost trends by month or in annual summary._")
    # Clarify what the big numbers represent
    st.caption("**Period totals shown below reflect the demo dataset (Jan–Jun 2025). Charts include units.**")

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total (tCO₂e)",fmt(grand_t))
    k2.metric("Buildings (tCO₂e)",fmt(bld_t))
    k3.metric("Fleet (tCO₂e)",fmt(flt_t))
    k4.metric("Waste (tCO₂e)",fmt(wst_t))
    k5.metric("Total Cost (CAD)",f"${grand_c:,.0f}")

    # View mode (defaults to Monthly)
    view_mode = st.selectbox("View mode:", ["Monthly", "Annual"], index=0)

    # Insight helpers
    def buildings_insight():
        share = 100* bld_t / grand_t if grand_t>0 else 0
        elec = bld["elec_cost"].sum(); gas = bld["gas_cost"].sum()
        driver = "natural gas for heating" if gas >= elec else "electricity use"
        mgrp = bld.groupby("month",as_index=False)["tco2e"].sum()
        peak_month = mgrp.sort_values("tco2e", ascending=False)["month"].iloc[0] if len(mgrp) else ""
        return (
            f"*Buildings account for **{share:,.0f}%** of total emissions. The largest cost driver is {driver}. "
            f"Emissions are highest in **{peak_month}**, suggesting a seasonal effect; efficiency retrofits and "
            f"electrification can lower both emissions and utility spend.*"
        )
    def fleet_insight():
        share = 100* flt_t / grand_t if grand_t>0 else 0
        diesel_cost = flt.loc[flt["is_diesel"],"cost"].sum()
        gaso_cost = flt.loc[~flt["is_diesel"],"cost"].sum()
        driver = "diesel operations" if diesel_cost >= gaso_cost else "gasoline operations"
        top_vehicle = flt.sort_values("tco2e", ascending=False)["vehicle"].iloc[0] if len(flt) else ""
        return (
            f"*Fleet contributes **{share:,.0f}%** of total emissions. Costs are primarily driven by **{driver}**. "
            f"Targeting high-usage units (e.g., **{top_vehicle}**) and piloting EV replacements can reduce "
            f"both emissions and fuel/maintenance costs.*"
        )
    def waste_insight():
        share = 100* wst_t / grand_t if grand_t>0 else 0
        top_stream = wst.sort_values("tco2e", ascending=False)["stream"].iloc[0] if len(wst) else ""
        return (
            f"*Waste contributes **{share:,.0f}%** of total emissions, mainly from **{top_stream}**. "
            f"Increasing diversion and organics programs can lower landfill fees and emissions.*"
        )

    # Monthly view — three panels with insights
    if view_mode == "Monthly":
        def panel_buildings():
            data = bld.groupby("month",as_index=False)[["tco2e","cost"]].sum()
            bars = alt.Chart(data).mark_bar(color="#1e6c93").encode(
                x=alt.X("month:N", title="Month"),
                y=alt.Y("tco2e:Q", title="Emissions (tCO₂e)"),
                tooltip=["month","tco2e","cost"]
            )
            line = alt.Chart(data).mark_line(point=True, color="#9ecae1", strokeWidth=3).encode(
                x="month:N",
                y=alt.Y("cost:Q", title="Cost (CAD)"),
                tooltip=["month","tco2e","cost"]
            )
            st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title="Buildings", height=260),
                            use_container_width=True)
            st.markdown(buildings_insight())

        def panel_fleet():
            data = flt.copy()
            bars = alt.Chart(data).mark_bar(color="#2a9d8f").encode(
                x=alt.X("vehicle:N", title="Vehicle"),
                y=alt.Y("tco2e:Q", title="Emissions (tCO₂e)"),
                tooltip=["vehicle","tco2e","cost"]
            )
            line = alt.Chart(data).mark_line(point=True, color="#9fdacb", strokeWidth=3).encode(
                x="vehicle:N",
                y=alt.Y("cost:Q", title="Cost (CAD)"),
                tooltip=["vehicle","tco2e","cost"]
            )
            st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title="Fleet", height=260),
                            use_container_width=True)
            st.markdown(fleet_insight())

        def panel_waste():
            data = wst.copy()
            bars = alt.Chart(data).mark_bar(color="#8a5a44").encode(
                x=alt.X("stream:N", title="Stream"),
                y=alt.Y("tco2e:Q", title="Emissions (tCO₂e)"),
                tooltip=["stream","tco2e","cost"]
            )
            line = alt.Chart(data).mark_line(point=True, color="#d6b7a6", strokeWidth=3).encode(
                x="stream:N",
                y=alt.Y("cost:Q", title="Cost (CAD)"),
                tooltip=["stream","tco2e","cost"]
            )
            st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title="Waste", height=260),
                            use_container_width=True)
            st.markdown(waste_insight())

        c1,c2,c3 = st.columns(3)
        with c1: panel_buildings()
        with c2: panel_fleet()
        with c3: panel_waste()

    # Annual view — single comparative chart + summary + footnote
    else:
        annual = pd.DataFrame({
            "Category":["Buildings","Fleet","Waste"],
            "Emissions":[bld_t, flt_t, wst_t],
            "Cost":[bld_c, flt_c, wst_c],
        })
        st.markdown("*Annual totals show relative contributions by category, helping identify where action yields the greatest impact.*")

        ca, cb = st.columns(2)
        with ca:
            st.altair_chart(
                alt.Chart(annual).mark_bar(color="#1e6c93").encode(
                    x=alt.X("Category:N", title="Category"),
                    y=alt.Y("Emissions:Q", title="Emissions (tCO₂e)"),
                    tooltip=["Category","Emissions"]
                ).properties(title="Annual Emissions by Category", height=320),
                use_container_width=True
            )
        with cb:
            st.altair_chart(
                alt.Chart(annual).mark_bar(color="#9ecae1").encode(
                    x=alt.X("Category:N", title="Category"),
                    y=alt.Y("Cost:Q", title="Cost (CAD)"),
                    tooltip=["Category","Cost"]
                ).properties(title="Annual Cost by Category", height=320),
                use_container_width=True
            )

        st.caption("*Annual totals are aggregated from all facilities and sources.*")

    # ---- Download Overview Report (PDF or Markdown fallback)
    st.divider()
    want_pdf = st.checkbox("Download Overview Report as PDF (fallback to Markdown if PDF not available)", value=True)
    monthly_flag = (view_mode == "Monthly")
    pdf_bytes = build_overview_report_pdf(monthly_flag) if want_pdf else b""
    if want_pdf and pdf_bytes:
        st.download_button("Download Overview Report (PDF)", pdf_bytes,
                           file_name="DataLeaf_Overview_Report.pdf",
                           mime="application/pdf", use_container_width=True)
    else:
        md_bytes = build_overview_report_markdown(monthly_flag)
        st.download_button("Download Overview Report (Markdown)", md_bytes,
                           file_name="DataLeaf_Overview_Report.md",
                           mime="text/markdown", use_container_width=True)

# =========================================================
# SCENARIO BUILDER (fixed and working)
# =========================================================
elif st.session_state.page=="Scenario Builder":
    st.subheader("Scenario Builder")
    sA,sB,sC=st.columns(3)
    with sA: retro=st.slider("Buildings retrofit (%)",0,30,15)
    with sB: ev=st.slider("Fleet EV adoption (%)",0,50,20)
    with sC: div=st.slider("Waste diversion (%)",0,50,10)

    # Recompute totals
    bld_t = bld["tco2e"].sum(); flt_t = flt["tco2e"].sum(); wst_t = wst["tco2e"].sum()
    bld_c = bld["cost"].sum();   flt_c = flt["cost"].sum();   wst_c = wst["cost"].sum()

    bld_sc_em=bld_t*(1-retro/100); flt_sc_em=flt_t*(1-ev/100); wst_sc_em=wst_t*(1-div/100)
    bld_sc_cost=bld_c*(1-retro/100); flt_sc_cost=flt_c*(1-ev/100); wst_sc_cost=wst_c*(1-div/100)

    def chart_block(title,cur_em,sc_em,cur_c,sc_c,col1,col2):
        df=pd.DataFrame({"Case":["Current","Scenario"],"Emissions":[cur_em,sc_em],"Cost":[cur_c,sc_c]})
        bars=alt.Chart(df).mark_bar(color=col1).encode(
            x=alt.X("Case:N", title="Case"),
            y=alt.Y("Emissions:Q", title="Emissions (tCO₂e)"),
            tooltip=["Case","Emissions","Cost"]
        )
        line=alt.Chart(df).mark_line(point=True,color=col2,strokeWidth=3).encode(
            x="Case:N",
            y=alt.Y("Cost:Q", title="Cost (CAD)"),
            tooltip=["Case","Emissions","Cost"]
        )
        st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title=title,height=260),
                        use_container_width=True)

    pA,pB,pC=st.columns(3)
    with pA: chart_block("Buildings",bld_t,bld_sc_em,bld_c,bld_sc_cost,"#1e6c93","#9ecae1")
    with pB: chart_block("Fleet",flt_t,flt_sc_em,flt_c,flt_sc_cost,"#2a9d8f","#9fdacb")
    with pC: chart_block("Waste",wst_t,wst_sc_em,wst_c,wst_sc_cost,"#8a5a44","#d6b7a6")

# =========================================================
# FUNDING & GRANTS (clickable + realistic deadlines + numeric match%)
# =========================================================
elif st.session_state.page=="Funding & Grants":
    st.subheader("Funding & Grants")

    # Baseline shares for heuristic "match %" (simple, transparent)
    total_em = grand_t if grand_t > 0 else 1
    share = {
        "Buildings": bld_t/total_em,
        "Fleet": flt_t/total_em,
        "Waste": wst_t/total_em
    }

    PROGRAMS = [
        {"name":"Infrastructure Canada – GICB",
         "focus":["Buildings","Community"],
         "amount":"Up to $25M",
         "deadline":"2026-03-31",
         "link":"https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html",
         "notes":"Community buildings: deep retrofits/new builds; accessibility; M&V."},
        {"name":"FCM GMF – Community Buildings Retrofit",
         "focus":["Buildings"],
         "amount":"Up to $5M (varies by stream)",
         "deadline":"2025-12-15",
         "link":"https://greenmunicipalfund.ca/community-buildings-retrofit-initiative",
         "notes":"Audits, retrofits, commissioning; strong M&V expected."},
        {"name":"FCM GMF – Fleet Electrification",
         "focus":["Fleet"],
         "amount":"Up to $1M+",
         "deadline":"2025-11-30",
         "link":"https://greenmunicipalfund.ca/funding/fleet-electrification",
         "notes":"EV transition plans, charging, pilot deployments."},
        {"name":"FCM GMF – Climate Adaptation",
         "focus":["Adaptation","Risk"],
         "amount":"Up to $1M+",
         "deadline":"2025-12-31",
         "link":"https://greenmunicipalfund.ca/funding/adaptation",
         "notes":"Risk assessment, adaptation planning/implementation."},
        {"name":"Ontario – Climate/EV Programs (hub)",
         "focus":["Buildings","Fleet"],
         "amount":"Varies",
         "deadline":"Rolling",
         "link":"https://www.ontario.ca/page/climate-change-funding",
         "notes":"Entry page to active provincial programs."},
        {"name":"NRCan – Green Infrastructure (hub)",
         "focus":["Buildings","Fleet","Adaptation"],
         "amount":"Varies",
         "deadline":"Varies",
         "link":"https://natural-resources.canada.ca/science-and-data/funding-partnerships/funding-opportunities",
         "notes":"Federal funding opportunities hub."},
    ]

    st.write("Programs aligned with typical municipal priorities:")
    # Compute numeric match% (simple: weight Buildings/Fleet/Waste shares; Adaptation = constant 0.5)
    rows=[]
    for p in PROGRAMS:
        base = 0
        if "Buildings" in p["focus"]: base += share["Buildings"]
        if "Fleet" in p["focus"]:     base += share["Fleet"]
        if "Waste" in p["focus"]:     base += share["Waste"] * 0.5  # weaker direct fit
        if "Adaptation" in p["focus"] or "Risk" in p["focus"]: base += 0.5*0.2  # small baseline nudge
        match_pct = int(round(min(0.95, max(0.15, base)) * 100))  # clamp 15–95%
        rows.append({
            "Program": p["name"],
            "Amount": p["amount"],
            "Match % (heuristic)": f"{match_pct}%",
            "Deadline": p["deadline"],
            "Link": p["link"]
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Keep clickable list below the table (readable and scannable)
    st.markdown("**Explore program pages:**")
    for p in PROGRAMS:
        st.markdown(f"- [{p['name']}]({p['link']}) — {p['notes']} *(Deadline: {p['deadline']})*")

    # Prefilled template generator
    choice = st.selectbox("Generate a prefilled grant template for:", [p["name"] for p in PROGRAMS])
    template = f"""=== GRANT APPLICATION TEMPLATE (Prefilled) ===
Program: {choice}

1) Applicant
   • Municipality: City of Waterloo
   • Dept: Sustainability Office
   • Contact: [Name, Title, Email, Phone]
   • Address: 100 Regina St S, Waterloo, ON N2J 4A8

2) Project Title
   • Corporate Emissions & Cost Reduction – Phase 1 (Buildings/Fleet/Waste)

3) Summary (150–250 words)
   • Objective: Reduce corporate emissions and operating costs with targeted measures.
   • Baseline (demo): {fmt(bld['tco2e'].sum() + flt['tco2e'].sum() + wst['tco2e'].sum())} tCO₂e; Est. annual cost ${bld['cost'].sum() + flt['cost'].sum() + wst['cost'].sum():,.0f}.
   • Focus: Buildings, Fleet, and Waste.
   • Program Fit: Aligns with {choice} objectives.

4) Activities & Workplan
   • Baseline validation → Measure design → Procurement → Implementation → Monitoring & Verification (M&V).

5) Budget & Sources
   • Total Cost: $[amount]  • Funding Request: $[amount]  • Municipal Match: $[amount]

6) Outcomes & KPIs
   • Emissions reduction (tCO₂e) and cost savings (CAD) from scenarios.
   • Compliance milestones and reporting cadence.

7) Engagement & Equity
   • Tailored communications to Council/Residents/Businesses/Staff.

8) Attachments
   • Dashboard snapshots, Scenario results (tCO₂e & $), Compliance one-pager, Support letters.
=== END ===
"""
    st.download_button("Download Prefilled Template (.txt)", template.encode("utf-8"),
                       file_name="Grant_Application_Template.txt", mime="text/plain")

# =========================================================
# ENGAGEMENT — dropdowns (stakeholder + program) → side card with tailored message
# =========================================================
elif st.session_state.page=="Engagement":
    st.subheader("Stakeholder Engagement")

    stakeholders = ["Council","Residents","Businesses","City Staff"]
    programs = ["Buildings Retrofit","Fleet Electrification","Waste Diversion","Compliance Update","Pilot Invitation"]

    c1, c2 = st.columns(2)
    with c1:
        who = st.selectbox("Stakeholder", stakeholders)
    with c2:
        topic = st.selectbox("Program / Topic", programs)

    # Simple tone + content matrix
    base = {
        ("Council","Buildings Retrofit"): "Targeted building retrofits reduce utility spend and emissions. Scenario results indicate material savings with short paybacks when paired with grants.",
        ("Council","Fleet Electrification"): "Phasing in EVs for high-usage units lowers fuel and maintenance costs while improving compliance readiness.",
        ("Council","Waste Diversion"): "Expanded diversion reduces landfill fees and stabilizes costs. Pilot options are low-risk and quick to implement.",
        ("Council","Compliance Update"): "Dashboards consolidate evidence for reporting—fewer manual hours, clearer audit trails, and better readiness for regulatory change.",
        ("Council","Pilot Invitation"): "A 3–4 month pilot focuses on one area with measurable outcomes and grant-ready documentation at the end.",

        ("Residents","Buildings Retrofit"): "Improving energy efficiency in public buildings reduces operating costs and emissions—savings that support community services.",
        ("Residents","Fleet Electrification"): "Transitioning select vehicles to electric cuts noise and emissions in neighbourhoods while saving fuel costs.",
        ("Residents","Waste Diversion"): "More recycling and organics keeps materials out of landfill, lowering costs and emissions.",
        ("Residents","Compliance Update"): "The city is tracking progress in a transparent way, with simple summaries that anyone can understand.",
        ("Residents","Pilot Invitation"): "We’re testing practical steps that lower bills and emissions. Your feedback helps shape what comes next.",

        ("Businesses","Buildings Retrofit"): "Data identifies best-return retrofits. Programs can offset upfront costs, reducing total cost of ownership.",
        ("Businesses","Fleet Electrification"): "EV pilots for duty cycles with predictable routes can reduce fuel risk and maintenance downtime.",
        ("Businesses","Waste Diversion"): "Better sorting and organics programs improve operational efficiency and reduce fees.",
        ("Businesses","Compliance Update"): "Clear reporting supports supply-chain and lender requests with investor-grade summaries.",
        ("Businesses","Pilot Invitation"): "A focused pilot de-risks adoption and shows concrete value quickly.",

        ("City Staff","Buildings Retrofit"): "Upload, track, and visualize facility data in one place—faster reporting, fewer spreadsheets, grant-ready outputs.",
        ("City Staff","Fleet Electrification"): "Target high-use units first. Scenario sliders quantify emissions and cost impacts instantly.",
        ("City Staff","Waste Diversion"): "Track waste streams, quantify landfill fees, and estimate savings from diversion.",
        ("City Staff","Compliance Update"): "Dashboards map metrics to reporting needs, creating an audit trail for submissions.",
        ("City Staff","Pilot Invitation"): "Pilot scope is co-designed. You choose the focus; we provide the tooling and templates."
    }

    message = base.get((who, topic),
        "Data and dashboards make progress visible, reduce manual work, and support funding applications.")
    # Side card layout
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(f"**To:** {who}  \n**Subject:** {topic}")
    st.write(message)

    # Share & copy
    q = urllib.parse.quote(message)
    st.markdown(
        f"[LinkedIn](https://linkedin.com/shareArticle?mini=true&url=https://thedataleaf.com&summary={q}) | "
        f"[𝕏](https://twitter.com/intent/tweet?text={q}) | "
        f"[Facebook](https://facebook.com/sharer/sharer.php?u=https://thedataleaf.com&quote={q}) | "
        f"[Email](mailto:?subject={urllib.parse.quote(topic)}&body={q})"
    )
    st.caption("Tip: click in the box above and press ⌘/Ctrl+C to copy.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
st.caption("Demo data only. Units indicated on every chart. Costs in CAD. Data Leaf © 2025")
