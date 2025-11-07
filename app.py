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
with st.spinner("Loading Data Leaf Dashboard — analyzing municipal emissions, costs, and funding insights..."):
    time.sleep(1.8)

# ----------------- PAGE CONFIG -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
st.set_page_config(page_title="Data Leaf – City of Waterloo Pilot MVP",
                   page_icon=LOGO_URL, layout="wide")

# ----------------- HEADER (fixed logo visibility & layout) -----------------
st.markdown("""
<style>
/* Keep top padding modest so header/logo stay visible */
.block-container { padding-top: 0.8rem !important; }

/* Ensure Streamlit header area remains visible */
header, .stApp header { 
    visibility: visible !important;
    height: auto !important;
}

/* Force logo to display clearly and align nicely with title */
header img, .stApp header img {
    height: 68px !important;
    display: inline-block !important;
    visibility: visible !important;
    margin-right: 0.5rem !important;
    vertical-align: middle !important;
}

/* Hide dev toolbar only, keep normal header */
div[data-testid="stToolbar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# --- Explicit header content (logo + title) ---
# --- Refined header (large logo + compact title) ---
st.markdown(f"""
<div style='display:flex; align-items:center; justify-content:flex-start;
            gap:18px; padding:0.4rem 0 0.8rem 0;'>
    <img src="{LOGO_URL}" style='height:95px; width:auto; flex-shrink:0;
             border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.15);'>
    <h3 style='margin:0; color:#1e6c93; font-size:1.25rem; font-weight:600;
               line-height:1.3; white-space:normal; max-width:500px;'>
        Data Leaf — City of Waterloo Pilot MVP
    </h3>
</div>
""", unsafe_allow_html=True)

# ----------------- SMART ASSIST (Developer only) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)
if USE_AI:
    with st.expander(" Smart Assist Connection ", expanded=False):
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
# OVERVIEW — AI-Assisted Snapshot (Final Revision)
# =========================================================
# =========================================================
# OVERVIEW — Scenario-specific System + AI Summaries
# =========================================================
if nav=="Overview":
    # --- reduce top whitespace ---
    st.markdown(
        "<style>.block-container{padding-top:1rem!important;}</style>",
        unsafe_allow_html=True)

    st.markdown("### AI-Assisted Overview — City of Waterloo Climate Snapshot")
    st.caption("Instantly see where emissions and costs stand. Updated from your data for smarter, faster decisions.")

    # --- Monthly / Annual toggle ---
    view_mode = st.radio("View Mode", ["Monthly", "Annual"], horizontal=True, index=0)
    is_monthly = (view_mode == "Monthly")

    import pandas as pd, numpy as np, altair as alt
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

    # --- synthetic demo data ---
    b_em = np.random.uniform(80,120,12)
    f_em = np.random.uniform(35,60,12)
    w_em = np.random.uniform(5,12,12)
    df_b = pd.DataFrame({"Month":months,"tCO2e":b_em,"Cost_CAD":b_em*650})
    df_f = pd.DataFrame({"Month":months,"tCO2e":f_em,"Cost_CAD":f_em*720})
    df_w = pd.DataFrame({"Month":months,"tCO2e":w_em,"Cost_CAD":w_em*400})

    # --- totals & KPIs ---
    b_t, f_t, w_t = df_b["tCO2e"].sum(), df_f["tCO2e"].sum(), df_w["tCO2e"].sum()
    total_em = b_t + f_t + w_t
    total_cost = df_b["Cost_CAD"].sum() + df_f["Cost_CAD"].sum() + df_w["Cost_CAD"].sum()
    period_label = "Monthly" if is_monthly else "Annual"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total Emissions (tCO₂e) — {period_label}", f"{total_em:,.1f}")
    c2.metric(f"Buildings ({period_label})", f"{b_t:,.1f} tCO₂e")
    c3.metric(f"Fleet ({period_label})", f"{f_t:,.1f} tCO₂e")
    c4.metric(f"Waste ({period_label})", f"{w_t:,.1f} tCO₂e")

    st.markdown("---")

    # --- helper to build each scenario panel ---
    import requests
    def scenario_panel(title, df, color):
        em_t, cost_t = df["tCO2e"].sum(), df["Cost_CAD"].sum()
        chart = alt.Chart(df).mark_line(interpolate="monotone", point=True, color=color).encode(
            x=alt.X("Month", sort=months),
            y=alt.Y("tCO2e", title="Emissions (tCO₂e)"),
            tooltip=["Month","tCO2e","Cost_CAD"]).properties(width=300,height=180)
        bars = alt.Chart(df).mark_bar(opacity=0.25,color=color).encode(
            x=alt.X("Month", sort=months),
            y=alt.Y("Cost_CAD", title="Cost ($CAD)"))
        st.markdown(f"#### {title}")
        st.altair_chart(alt.layer(bars,chart).resolve_scale(y="independent"),use_container_width=True)
        st.caption(f"Total: {em_t:,.1f} tCO₂e | ${cost_t:,.0f} CAD")

        # --- system summary ---
        sys_text = (f"System-Generated Summary: {title} accounts for {(em_t/total_em)*100:.1f}% "
                    f"of total emissions with annual cost ≈ ${cost_t:,.0f} CAD.")
        st.markdown(
            f"<div style='background:#E3F2FD;border-left:6px solid {color};"
            "padding:10px;border-radius:6px;margin-top:8px;'>"
            f"<strong style='color:{color};'>🧮 {sys_text}</strong></div>",
            unsafe_allow_html=True)

        # --- AI summary ---
        key=f"ai_summary_{title}"
        if key not in st.session_state: st.session_state[key]=None
        if st.button(f"Generate AI Summary – {title}", key=f"btn_{title}"):
            prompt=(f"Write a 3-sentence plain summary for {title.lower()} "
                    f"showing {em_t:,.1f} tCO₂e and ${cost_t:,.0f} CAD cost this {period_label.lower()}. "
                    "Mention trends and improvement opportunities.")
            try:
                r=requests.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization":f"Bearer {OPENAI_API_KEY}",
                             "Content-Type":"application/json"},
                    json={"model":"gpt-4o-mini",
                          "messages":[{"role":"user","content":prompt}]})
                st.session_state[key]=r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                st.error(f"AI summary failed: {e}")

        if st.session_state[key]:
            st.markdown(
                f"<div style='background:#E8F5E9;border-left:6px solid #2E7D32;"
                "padding:10px;border-radius:6px;margin-top:6px;'>"
                f"<strong style='color:#2E7D32;'>🤖 AI-Generated Summary:</strong><br>"
                f"{st.session_state[key]}</div>",
                unsafe_allow_html=True)

    # --- display three scenarios horizontally ---
    col_b,col_f,col_w=st.columns(3)
    with col_b: scenario_panel("🏢 Buildings", df_b, "#1e6c93")
    with col_f: scenario_panel("🚗 Fleet", df_f, "#2a9d8f")
    with col_w: scenario_panel("♻️ Waste", df_w, "#8a5a44")



# =========================================================
# SCENARIO BUILDER
# =========================================================
elif nav=="Scenario Builder":
 
    st.subheader("Scenario Builder")
    st.caption("Simulate how retrofits, EV adoption, and waste diversion affect Waterloo’s emissions and annual operating costs in real time.")

    # --- Sliders ---
    sA, sB, sC = st.columns(3)
    with sA: retrofit = st.slider("Buildings retrofit (%)", 0, 30, 15)
    with sB: ev = st.slider("Fleet EV adoption (%)", 0, 50, 20)
    with sC: diversion = st.slider("Waste diversion (%)", 0, 50, 10)

    # --- Baseline + Scenario calculations ---
    b_em, f_em, w_em = 840, 420, 30
    b_cost, f_cost, w_cost = 480000, 370000, 27000

    b_em_s = b_em * (1 - retrofit / 100)
    f_em_s = f_em * (1 - ev / 100)
    w_em_s = w_em * (1 - diversion / 100)

    b_cost_s = b_cost * (1 - retrofit / 100)
    f_cost_s = f_cost * (1 - ev / 100)
    w_cost_s = w_cost * (1 - diversion / 100)

    import pandas as pd, altair as alt

    # --- Dual-metric chart + summary block ---
    def scenario_block(title, em_now, em_new, cost_now, cost_new, color, bg_color):
        df = pd.DataFrame({
            "Metric": ["Baseline Emissions", "Scenario Emissions",
                       "Baseline Cost ($000)", "Scenario Cost ($000)"],
            "Value": [em_now, em_new, cost_now/1000, cost_new/1000],
            "Category": ["Emissions", "Emissions", "Cost", "Cost"]
        })

        chart = (
            alt.Chart(df)
            .mark_bar(size=40)
            .encode(
                x=alt.X("Metric:N", sort=None, title=None),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Category:N",
                                scale=alt.Scale(domain=["Emissions", "Cost"],
                                                range=[color, "#b0bec5"]),
                                legend=alt.Legend(title="Category")),
                tooltip=["Metric", "Value"]
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)

        diff_em = em_now - em_new
        diff_cost = cost_now - cost_new
        st.markdown(f"""
            <div style='background:{bg_color}; border-left:4px solid {color};
            padding:10px; border-radius:6px; font-size:0.9em;'>
            <b>System-Calculated Summary</b><br>
            • Emission reduction: {diff_em:.1f} tCO₂e <br>
            • Estimated cost savings: ${diff_cost:,.0f}<br>
            <i>Live values update automatically with each slider.</i>
            </div>
        """, unsafe_allow_html=True)

    # --- 3-column layout (no scrolling) ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🏢 Buildings")
        scenario_block("Buildings", b_em, b_em_s, b_cost, b_cost_s, "#1e6c93", "#e3f2fd")
    with col2:
        st.markdown("### 🚗 Fleet")
        scenario_block("Fleet", f_em, f_em_s, f_cost, f_cost_s, "#2e7d32", "#e8f5e9")
    with col3:
        st.markdown("### ♻️ Waste")
        scenario_block("Waste", w_em, w_em_s, w_cost, w_cost_s, "#8a5a44", "#f5f0eb")

    # --- AI Summary + PDF Export ---
    st.divider()
    st.markdown("### 🤖 AI-Generated Scenario Summary")

    if "ai_summary" not in st.session_state:
        st.session_state.ai_summary = None

    if st.button("Generate AI Summary"):
        if OPENAI_API_KEY:
            import requests
            prompt = f"""
            The City of Waterloo scenario includes:
            - Buildings retrofit: {retrofit}%
            - Fleet EV adoption: {ev}%
            - Waste diversion: {diversion}%
            Current total: {b_em + f_em + w_em:.1f} tCO₂e, ${b_cost + f_cost + w_cost:,.0f}.
            Scenario total: {b_em_s + f_em_s + w_em_s:.1f} tCO₂e, ${b_cost_s + f_cost_s + w_cost_s:,.0f}.
            Write a concise plain-language summary (3–5 sentences) including savings and policy relevance.
            """
            try:
                r = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini",
                          "messages": [{"role": "user", "content": prompt}]})
                st.session_state.ai_summary = r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                st.error(f"AI summary request failed: {e}")
        else:
            st.warning("OpenAI key not found – showing fallback summary only.")

    if st.session_state.ai_summary:
        st.markdown("""
            <div style='background:#e8f5e9; border-left:6px solid #2e7d32;
            padding:14px; border-radius:8px; margin-bottom:10px;'>
            <strong style='color:#2e7d32;'>AI-Generated Insight:</strong><br>
        """, unsafe_allow_html=True)
        st.write(st.session_state.ai_summary)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- Fallback summary always visible ---
    reduction = (1 - (b_em_s + f_em_s + w_em_s) / (b_em + f_em + w_em)) * 100
    savings = (b_cost + f_cost + w_cost) - (b_cost_s + f_cost_s + w_cost_s)
    fallback_text = (
        f"Estimated emissions reduction {reduction:.1f}% and cost savings ${savings:,.0f}. "
        "Supports Waterloo’s compliance readiness and demonstrates measurable progress."
    )

    st.markdown(f"""
        <div style='background:#e3f2fd; border-left:6px solid #1e6c93;
        padding:14px; border-radius:8px;'>
        <strong style='color:#1e6c93;'>System-Calculated Summary:</strong><br>
        {fallback_text}
        </div>
    """, unsafe_allow_html=True)

    # --- PDF Export ---
                 # --- PDF Export (Clean Scaling + Option for Charts) ---
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from textwrap import wrap
    import tempfile, os, math

    st.markdown("#### 📄 Download Scenario Summary")

    # --- Helper function for chart scaling ---
    def draw_chart_centered(c, path, y, page_width, page_height, max_width=170):
        """Draws chart proportionally centered on the PDF."""
        try:
            img = ImageReader(path)
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            new_height = max_width * aspect
            if y - new_height < 100:
                c.showPage()
                y = page_height - 70
            x_center = (page_width - max_width) / 2
            c.drawImage(img, x_center, y - new_height,
                        width=max_width, height=new_height)
            y -= new_height + 20
            return y
        except Exception as e:
            print(f"Chart draw failed: {e}")
            return y - 20

    # --- Radio button for report type ---
    include_charts = st.radio(
        "Include charts in download?",
        ["✅ Yes (Full Report with Charts)", "📝 No (Text-Only Summary)"],
        horizontal=True
    )

    if st.button("Generate PDF"):
        temp_dir = tempfile.mkdtemp()

        # --- Chart export helper (only if selected) ---
        def save_chart_as_png(chart, filename, scale=2):
            path = os.path.join(temp_dir, filename)
            chart.save(path, format="png", scale_factor=scale)
            return path

        chart_paths = []
        if "Yes" in include_charts:
            chart_paths = [
                save_chart_as_png(
                    alt.Chart(pd.DataFrame({
                        "Metric": ["Baseline Emissions", "Scenario Emissions", "Baseline Cost ($000)", "Scenario Cost ($000)"],
                        "Value": [b_em, b_em_s, b_cost/1000, b_cost_s/1000],
                        "Category": ["Emissions", "Emissions", "Cost", "Cost"]
                    }))
                    .mark_bar(size=40)
                    .encode(x="Metric", y="Value",
                            color=alt.Color("Category:N",
                                            scale=alt.Scale(domain=["Emissions", "Cost"],
                                                            range=["#1e6c93", "#b0bec5"]))),
                    "buildings_chart.png"),

                save_chart_as_png(
                    alt.Chart(pd.DataFrame({
                        "Metric": ["Baseline Emissions", "Scenario Emissions", "Baseline Cost ($000)", "Scenario Cost ($000)"],
                        "Value": [f_em, f_em_s, f_cost/1000, f_cost_s/1000],
                        "Category": ["Emissions", "Emissions", "Cost", "Cost"]
                    }))
                    .mark_bar(size=40)
                    .encode(x="Metric", y="Value",
                            color=alt.Color("Category:N",
                                            scale=alt.Scale(domain=["Emissions", "Cost"],
                                                            range=["#2e7d32", "#b0bec5"]))),
                    "fleet_chart.png"),

                save_chart_as_png(
                    alt.Chart(pd.DataFrame({
                        "Metric": ["Baseline Emissions", "Scenario Emissions", "Baseline Cost ($000)", "Scenario Cost ($000)"],
                        "Value": [w_em, w_em_s, w_cost/1000, w_cost_s/1000],
                        "Category": ["Emissions", "Emissions", "Cost", "Cost"]
                    }))
                    .mark_bar(size=40)
                    .encode(x="Metric", y="Value",
                            color=alt.Color("Category:N",
                                            scale=alt.Scale(domain=["Emissions", "Cost"],
                                                            range=["#8a5a44", "#b0bec5"]))),
                    "waste_chart.png")
            ]

        # --- PDF setup ---
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 60

        # Logo + Title
        try:
            logo_url = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
            logo_img = ImageReader(logo_url)
            c.drawImage(logo_img, 50, y - 40, width=120, height=40, mask='auto')
        except Exception:
            pass
        c.setFont("Helvetica-Bold", 14)
        c.drawString(190, y - 20, "City of Waterloo – Scenario Summary")
        y -= 70

        # Slider summary
        c.setFont("Helvetica", 11)
        for line in [
            f"Buildings retrofit: {retrofit}%",
            f"Fleet EV adoption: {ev}%",
            f"Waste diversion: {diversion}%"
        ]:
            c.drawString(50, y, line)
            y -= 15
        y -= 10

        # Scenario sections
        scenarios = [
            ("Buildings", b_em, b_em_s, b_cost, b_cost_s, "#1e6c93"),
            ("Fleet", f_em, f_em_s, f_cost, f_cost_s, "#2e7d32"),
            ("Waste", w_em, w_em_s, w_cost, w_cost_s, "#8a5a44")
        ]

        for idx, (name, em_now, em_new, cost_now, cost_new, color) in enumerate(scenarios):
            diff_em = em_now - em_new
            diff_cost = cost_now - cost_new

            c.setFont("Helvetica-Bold", 12)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(50, y, f"{name} Scenario")
            y -= 10

            # Draw chart proportionally centered
            if chart_paths:
                y = draw_chart_centered(c, chart_paths[idx], y, width, height, max_width=340)

            c.setFont("Helvetica", 10)
            lines = [
                f"• Emission reduction: {diff_em:.1f} tCO₂e",
                f"• Estimated cost savings: ${diff_cost:,.0f}"
            ]
            for line in lines:
                c.drawString(60, y, line)
                y -= 13
            y -= 10

            if y < 150:
                c.showPage()
                y = height - 70

        # AI summary
        if st.session_state.ai_summary:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "AI-Generated Insight:")
            y -= 15
            c.setFont("Helvetica", 10)
            for line in wrap(st.session_state.ai_summary, 90):
                if y < 100:
                    c.showPage()
                    y = height - 70
                    c.setFont("Helvetica", 10)
                c.drawString(60, y, line)
                y -= 13
            y -= 10

        # Overall system summary
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Overall System-Calculated Summary:")
        y -= 15
        c.setFont("Helvetica", 10)
        for line in wrap(fallback_text, 90):
            if y < 100:
                c.showPage()
                y = height - 70
                c.setFont("Helvetica", 10)
            c.drawString(60, y, line)
            y -= 13

        # Footer
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(50, 40, "Generated by Data Leaf – AI-assisted Sustainability Dashboard")
        c.save()

        pdf = buffer.getvalue()
        buffer.close()

        st.download_button(
            "📥 Download Scenario Summary PDF",
            data=pdf,
            file_name="Waterloo_Scenario_Summary.pdf",
            mime="application/pdf"
        )

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
