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
    time.sleep(1.8)

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
.smallcap {{color:#6b7280;font-size:0.9rem;}}
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
                st.warning("⚠️ Connection not verified (key OK, but model reply not matched).")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ----------------- NAVIGATION -----------------
nav = st.radio("Navigate", ["Overview", "Scenario Builder", "Funding & Grants", "Engagement"], horizontal=True)

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

# Factors & simple CAD rates
EF = {"kwh":0.00003, "natural_gas_m3":0.00189, "diesel":0.00268, "gasoline":0.00231, "waste":0.45}
RATE = {"kwh":0.17, "natural_gas_m3":0.45, "diesel":1.80, "gasoline":1.65, "waste":125.0}

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

# =========================================================
# OVERVIEW
# =========================================================
if nav=="Overview":
    st.subheader("Overview – Emissions and Cost")
    st.caption("_Demo data period: Jan–Jun 2025. All charts have explicit units._")

    a,b,c,d,e = st.columns(5)
    a.metric("Total (tCO₂e)", fmt(grand_t))
    b.metric("Buildings (tCO₂e)", fmt(bld_t))
    c.metric("Fleet (tCO₂e)", fmt(flt_t))
    d.metric("Waste (tCO₂e)", fmt(wst_t))
    e.metric("Total Cost (CAD)", f"${grand_c:,.0f}")

    view_mode = st.selectbox("View mode:", ["Monthly", "Annual"], index=0)

    def overview_chart(df, title, bar_color, line_color):
        data = df.groupby("month",as_index=False)[["tco2e","cost"]].sum()
        bars = alt.Chart(data).mark_bar(color=bar_color).encode(
            x=alt.X("month:N", title="Month"),
            y=alt.Y("tco2e:Q", title="Emissions (tCO₂e)"),
            tooltip=["month","tco2e","cost"]
        )
        line = alt.Chart(data).mark_line(point=True, color=line_color, strokeWidth=3).encode(
            x="month:N",
            y=alt.Y("cost:Q", title="Cost (CAD)"),
            tooltip=["month","tco2e","cost"]
        )
        st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title=title, height=260),
                        use_container_width=True)

    if view_mode == "Monthly":
        c1,c2,c3 = st.columns(3)
        with c1: overview_chart(bld,"Buildings","#1e6c93","#9ecae1")
        with c2: overview_chart(flt,"Fleet","#2a9d8f","#9fdacb")
        with c3: overview_chart(wst,"Waste","#8a5a44","#d6b7a6")
    else:
        annual = pd.DataFrame({
            "Category":["Buildings","Fleet","Waste"],
            "Emissions":[bld_t, flt_t, wst_t],
            "Cost":[bld_c, flt_c, wst_c]
        })
        c1,c2 = st.columns(2)
        with c1:
            st.altair_chart(
                alt.Chart(annual).mark_bar(color="#1e6c93").encode(
                    x=alt.X("Category:N", title="Category"),
                    y=alt.Y("Emissions:Q", title="Emissions (tCO₂e)"),
                    tooltip=["Category","Emissions"]
                ).properties(title="Annual Emissions by Category", height=320),
                use_container_width=True
            )
        with c2:
            st.altair_chart(
                alt.Chart(annual).mark_bar(color="#9ecae1").encode(
                    x=alt.X("Category:N", title="Category"),
                    y=alt.Y("Cost:Q", title="Cost (CAD)"),
                    tooltip=["Category","Cost"]
                ).properties(title="Annual Cost by Category", height=320),
                use_container_width=True
            )
        st.caption("*Annual totals are aggregated from all facilities and sources.*")

    # --- Overview Report (PDF with fallback to Markdown)
    def build_overview_report_pdf(is_monthly: bool) -> bytes:
        try:
            from reportlab.lib.pagesizes import LETTER
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import inch
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=LETTER)
            title = "Data Leaf – Overview Report"
            sub = f"View mode: {'Monthly' if is_monthly else 'Annual'} • Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            totals = [
                f"Total emissions: {fmt(grand_t)} tCO2e",
                f"Total annualized cost: ${grand_c:,.0f}",
                f"Buildings: {fmt(bld_t)} tCO2e • ${bld_c:,.0f}",
                f"Fleet: {fmt(flt_t)} tCO2e • ${flt_c:,.0f}",
                f"Waste: {fmt(wst_t)} tCO2e • ${wst_c:,.0f}",
            ]
            w,h = LETTER; y = h - 1.0*inch
            c.setFont("Helvetica-Bold", 14); c.drawString(1*inch, y, title); y -= 0.35*inch
            c.setFont("Helvetica", 10); c.drawString(1*inch, y, sub); y -= 0.4*inch
            c.setFont("Helvetica", 11)
            for line in totals:
                c.drawString(1*inch, y, f"• {line}"); y -= 0.24*inch
            if not is_monthly:
                c.setFont("Helvetica-Oblique", 10)
                c.drawString(1*inch, y-0.1*inch, "Annual totals are aggregated from all facilities and sources.")
            c.showPage(); c.save(); buf.seek(0)
            return buf.read()
        except Exception:
            return b""

    def build_overview_report_md(is_monthly: bool) -> bytes:
        md = f"""# Data Leaf – Overview Report

**View mode:** {'Monthly' if is_monthly else 'Annual'}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

**Totals (Demo period: Jan–Jun 2025)**
- Total emissions: {fmt(grand_t)} tCO₂e  
- Total annualized cost: ${grand_c:,.0f}  
- Buildings: {fmt(bld_t)} tCO₂e • ${bld_c:,.0f}  
- Fleet: {fmt(flt_t)} tCO₂e • ${flt_c:,.0f}  
- Waste: {fmt(wst_t)} tCO₂e • ${wst_c:,.0f}

{('*Annual totals are aggregated from all facilities and sources.*' if not is_monthly else '')}
"""
        return md.encode("utf-8")

    st.divider()
    want_pdf = st.checkbox("Download Overview Report as PDF (fallback to Markdown if PDF not available)", value=True)
    monthly_flag = (view_mode == "Monthly")
    pdf_bytes = build_overview_report_pdf(monthly_flag) if want_pdf else b""
    if want_pdf and pdf_bytes:
        st.download_button("Download Overview Report (PDF)", pdf_bytes,
                           file_name="DataLeaf_Overview_Report.pdf",
                           mime="application/pdf", use_container_width=True)
    else:
        md_bytes = build_overview_report_md(monthly_flag)
        st.download_button("Download Overview Report (Markdown)", md_bytes,
                           file_name="DataLeaf_Overview_Report.md",
                           mime="text/markdown", use_container_width=True)

# =========================================================
# SCENARIO BUILDER
# =========================================================
elif nav=="Scenario Builder":
    
   
    st.subheader("Scenario Builder")
    st.caption("Explore how changes in retrofits, EV adoption, or waste diversion affect Waterloo’s emissions and costs in real time.")

    sA, sB, sC = st.columns(3)
    with sA: retrofit = st.slider("Buildings retrofit (%)", 0, 30, 15)
    with sB: ev = st.slider("Fleet EV adoption (%)", 0, 50, 20)
    with sC: diversion = st.slider("Waste diversion (%)", 0, 50, 10)

    # ---------- Baseline and scenario calculations ----------
    b_em, f_em, w_em = 840, 420, 30
    b_cost, f_cost, w_cost = 480000, 370000, 27000

    b_em_s = b_em * (1 - retrofit / 100)
    f_em_s = f_em * (1 - ev / 100)
    w_em_s = w_em * (1 - diversion / 100)

    b_cost_s = b_cost * (1 - retrofit / 100)
    f_cost_s = f_cost * (1 - ev / 100)
    w_cost_s = w_cost * (1 - diversion / 100)

    # ---------- Chart + live summary helper ----------
    def scenario_block(title, em_now, em_new, cost_now, cost_new, color, bg_color):
        st.markdown(f"### {title}")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.bar_chart({
                "Baseline (tCO₂e)": [em_now],
                "Scenario (tCO₂e)": [em_new]
            })
        with col2:
            diff_em = em_now - em_new
            diff_cost = cost_now - cost_new
            st.markdown(f"""
                <div style='background:{bg_color}; border-left:4px solid {color};
                padding:8px; border-radius:6px; font-size:0.9em;'>
                <b>System-Calculated Summary</b><br>
                ↓ Emission reduction: {diff_em:.1f} tCO₂e<br>
                💰 Cost savings: ${diff_cost:,.0f}
                </div>
            """, unsafe_allow_html=True)

    # ---------- Display three scenario sections ----------
    scenario_block("Buildings", b_em, b_em_s, b_cost, b_cost_s, "#1e6c93", "#e3f2fd")   # Blue
    scenario_block("Fleet", f_em, f_em_s, f_cost, f_cost_s, "#2e7d32", "#e8f5e9")       # Green
    scenario_block("Waste", w_em, w_em_s, w_cost, w_cost_s, "#8a5a44", "#f5f0eb")       # Brown

    # ---------- Keep existing AI summary + PDF export exactly as before ----------
    st.divider()
    st.markdown("### 🤖 Scenario Summary")
    # (Leave your existing AI + PDF code here — do not change it)




# =========================================================
# FUNDING & GRANTS — Full Intelligent Funding Centre
# =========================================================
elif nav=="Funding & Grants":
    st.subheader("Funding & Grants – Smart Funding Centre")
    st.markdown("_Discover and apply for the most relevant climate and infrastructure programs._")

    total_em = (bld["tco2e"].sum() + flt["tco2e"].sum() + wst["tco2e"].sum()) or 1.0
    share = {"Buildings": bld["tco2e"].sum()/total_em,
             "Fleet": flt["tco2e"].sum()/total_em,
             "Waste": wst["tco2e"].sum()/total_em}

    PROGRAMS = [
        {
            "name": "Infrastructure Canada – Green and Inclusive Community Buildings (GICB)",
            "amount": "Up to $25M",
            "deadline": "2026-03-31",
            "focus": ["Buildings", "Community"],
            "summary": "Supports retrofits or new builds that cut energy use, improve accessibility, and reduce GHGs in community facilities.",
            "examples": "City of Brampton retrofitted recreation centres and received $7.8M in 2023.",
            "link": "https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html"
        },
        {
            "name": "FCM GMF – Community Buildings Retrofit",
            "amount": "Up to $5M (varies by stream)",
            "deadline": "2025-12-15",
            "focus": ["Buildings"],
            "summary": "Funds audits, retrofits, recommissioning, and capacity building to improve energy performance.",
            "examples": "City of Guelph upgraded HVAC systems in two arenas, receiving $3.4M in 2023.",
            "link": "https://greenmunicipalfund.ca/community-buildings-retrofit-initiative"
        },
        {
            "name": "FCM GMF – Fleet Electrification",
            "amount": "Up to $1M+",
            "deadline": "2025-11-30",
            "focus": ["Fleet"],
            "summary": "Provides grants for electric vehicle feasibility studies, fleet transition planning, and pilot deployments.",
            "examples": "Region of Durham piloted electric waste trucks and received $800k in 2023.",
            "link": "https://greenmunicipalfund.ca/funding/fleet-electrification"
        },
        {
            "name": "FCM GMF – Climate Adaptation",
            "amount": "Up to $1M+",
            "deadline": "2025-12-31",
            "focus": ["Adaptation", "Risk"],
            "summary": "Supports risk assessments, flood mapping, and resilience-building for climate adaptation.",
            "examples": "City of London developed a flood resilience plan funded at $1.2M in 2022.",
            "link": "https://greenmunicipalfund.ca/funding/adaptation"
        },
        {
            "name": "Ontario – Climate & EV Programs (Hub)",
            "amount": "Varies",
            "deadline": "Rolling",
            "focus": ["Buildings", "Fleet"],
            "summary": "Provincial incentives and funding for electric vehicles, energy conservation, and green infrastructure.",
            "examples": "Waterloo Region organizations accessed EV-related rebates through 2024 offerings.",
            "link": "https://www.ontario.ca/page/climate-change-funding"
        },
        {
            "name": "NRCan – Green Infrastructure (Hub)",
            "amount": "Varies",
            "deadline": "Varies",
            "focus": ["Buildings", "Fleet", "Adaptation"],
            "summary": "Federal hub listing multiple open funding streams for efficiency, low-carbon transport, and adaptation.",
            "examples": "Multiple Ontario municipalities used NRCan streams for arena/library retrofits.",
            "link": "https://natural-resources.canada.ca/science-and-data/funding-partnerships/funding-opportunities"
        },
    ]

    # Calculate match % (simple, explainable heuristic)
    rows = []
    for p in PROGRAMS:
        base = 0
        if "Buildings" in p["focus"]: base += share["Buildings"]
        if "Fleet" in p["focus"]: base += share["Fleet"]
        if "Waste" in p["focus"]: base += share["Waste"] * 0.5
        if "Adaptation" in p["focus"] or "Risk" in p["focus"]: base += 0.1
        match_pct = int(round(min(0.95, max(0.15, base)) * 100))
        rows.append({
            "Program": f"[{p['name']}]({p['link']})",  # clickable label
            "Amount": p["amount"],
            "Match %": f"{match_pct}%",
            "Deadline": p["deadline"]
        })

    st.markdown("**Available Programs**")
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


    # Expandable summaries (clean, no duplicate link list)
    st.markdown("### Explore Program Summaries")
    for p in PROGRAMS:
        with st.expander(f"📄 {p['name']}"):
            st.markdown(f"**Funding Amount:** {p['amount']}")
            st.markdown(f"**Deadline:** {p['deadline']}")
            st.markdown(f"**Focus Areas:** {', '.join(p['focus'])}")
            st.markdown(f"**Summary:** {p['summary']}")
            st.markdown(f"**Example:** _{p['examples']}_")
            st.markdown(f"[🔗 View Official Page]({p['link']})")

            # Prefilled template per program
            if st.button(f"Generate Grant Template – {p['name']}", key=f"btn_{p['name']}"):
                prefill = f"""=== GRANT APPLICATION TEMPLATE (Prefilled) ===
Program: {p['name']}

1) Applicant
   • Municipality: City of Waterloo
   • Dept: Sustainability Office
   • Contact: [Name, Title, Email, Phone]

2) Project Title
   • Corporate Emissions & Cost Reduction – {p['focus'][0]} Initiative

3) Summary (150–250 words)
   • Objective: Reduce emissions and costs through {p['focus'][0].lower()} improvements.
   • Baseline (demo): {fmt(grand_t)} tCO₂e; Est. annualized cost ${grand_c:,.0f}.
   • Alignment: Matches {p['name']} objectives and funding criteria.

4) Activities & Workplan
   • Baseline validation → Measure design → Procurement → Implementation → Monitoring & Verification (M&V).

5) Budget & Sources
   • Total Cost: $[amount]  • Funding Request: $[amount]  • Municipal Match: $[amount]

6) Outcomes & KPIs
   • Emissions reduction (tCO₂e) and cost savings (CAD); compliance milestones and reporting cadence.
=== END ===
"""
                st.download_button(
                    label=f"📄 Download Prefilled Template ({p['name']})",
                    data=prefill.encode("utf-8"),
                    file_name=f"Grant_Template_{p['name'].replace(' ', '_')}.txt",
                    mime="text/plain"
                )

    # AI Grant Assist
    st.divider()
    st.markdown("### 🤖 Grant Assist – Find Best Fit Automatically")
    st.caption("Paste your project description below to get AI-powered matches.")
    user_input = st.text_area("Enter project description:", placeholder="e.g., Energy retrofit for municipal facilities with EV charging expansion...")
    if st.button("Analyze & Recommend Grants"):
        if OPENAI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                prompt = f"""
                You are an AI grant advisor. The following programs are available:
                {', '.join([p['name'] for p in PROGRAMS])}.
                Given this project description: {user_input},
                return the top 3 matching programs with short, specific reasons.
                """
                r = requests.post("https://api.openai.com/v1/chat/completions",
                                  headers=headers,
                                  json={"model": "gpt-4o-mini",
                                        "messages": [{"role": "user", "content": prompt}]})
                out = r.json()["choices"][0]["message"]["content"]
                st.success("Top Matches:")
                st.markdown(out)
            except Exception as e:
                st.error(f"AI Grant Assist error: {e}")
        else:
            st.warning("OpenAI API key not detected. (Developer-only feature)")

    # My Funding Tracker
    st.divider()
    st.markdown("### 📊 My Funding Tracker")
    upcoming = sorted([p["deadline"] for p in PROGRAMS if p["deadline"] not in ("Rolling","Varies")])
    next_deadline = upcoming[0] if upcoming else "No fixed deadlines"
    total_open = len(PROGRAMS)
    matched = sum(1 for p in PROGRAMS if "Buildings" in p["focus"] or "Fleet" in p["focus"])
    c1,c2,c3 = st.columns(3)
    c1.metric("Open Programs", total_open)
    c2.metric("Matched to City Priorities", matched)
    c3.metric("Next Deadline", next_deadline)

    if st.button("Generate Next Steps"):
        if OPENAI_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                prompt = ("Based on the current programs and Waterloo’s priorities (automation, compliance, GHG tracking, grants), "
                          "write a 4-step plan for the next 30 days to maximize funding readiness.")
                r = requests.post("https://api.openai.com/v1/chat/completions",
                                  headers=headers,
                                  json={"model": "gpt-4o-mini",
                                        "messages": [{"role": "user", "content": prompt}]})
                st.info(r.json()["choices"][0]["message"]["content"])
            except Exception as e:
                st.error(f"AI Tracker error: {e}")
        else:
            st.warning("Developer-only feature. Add OPENAI_API_KEY to enable Smart Assist.")

# =========================================================
# ENGAGEMENT — dropdowns → tailored message side-card
# =========================================================
elif nav=="Engagement":
    st.subheader("Stakeholder Engagement")

    stakeholders = ["Council","Residents","Businesses","City Staff"]
    topics = ["Buildings Retrofit","Fleet Electrification","Waste Diversion","Compliance Update","Pilot Invitation"]

    c1,c2 = st.columns(2)
    with c1: who = st.selectbox("Stakeholder", stakeholders)
    with c2: topic = st.selectbox("Program / Topic", topics)

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
    st.caption("Tip: click inside the message and press ⌘/Ctrl+C to copy.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
st.caption("Demo data only. Units indicated on every chart. Costs in CAD. Data Leaf © 2025")
