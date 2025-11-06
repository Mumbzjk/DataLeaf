# =========================
# Data Leaf MVP – Streamlit
# End-to-end demo + pilot (no scrolling main sections)
# =========================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os, requests, json, urllib.parse, time, math

# ----------------- BRAND / PAGE -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"

st.set_page_config(
    page_title="Data Leaf – City of Waterloo Pilot MVP",
    page_icon=LOGO_URL,
    layout="wide"
)

# Minimal CSS for compact layout and subtle polish
st.markdown("""
<style>
/* tighter top padding */
.block-container { padding-top: 0.8rem; padding-bottom: 1rem; }
/* compact radio & sliders */
.stRadio > div { gap: 0.75rem; }
.stSlider { margin-top: -0.25rem; }
/* small badge row */
.badge { display:inline-block; padding:4px 8px; border-radius:14px; background:#eef6ff; color:#1e6c93; margin-right:6px; font-size:0.85rem; }
.headerbar { display:flex; align-items:center; gap:12px; margin:6px 0 10px 0; }
.headerbar img { width:36px; height:36px; border-radius:6px; object-fit:contain; }
.headerbar h2 { margin:0; font-weight:800; }
.pulse { width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 6px rgba(34,197,94,.15); display:inline-block; }
.smallcap { color:#6b7280; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# Header (Data Leaf logo only; no emoji leaf)
st.markdown(
    f"""<div class="headerbar">
        <img src="{LOGO_URL}" alt="Data Leaf logo">
        <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
    </div>""",
    unsafe_allow_html=True
)

# ----------------- AI (PRIVATE / ADMIN) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)

def call_openai(prompt, max_tokens=140, temperature=0.3):
    """Direct HTTPS call that works with project-scoped keys; provider hidden from UI."""
    if not OPENAI_API_KEY:
        return None
    try:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
        data = {"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],
                "max_tokens":max_tokens,"temperature":temperature}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, data=json.dumps(data), timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return f"⚠️ OpenAI error {r.status_code}: {r.text}"
    except Exception as e:
        return f"❌ Request failed: {e}"

with st.expander("Admin • Smart Assist status (hidden in demos)", expanded=False):
    st.caption("Keep AI private. Use this check pre-demo.")
    if st.button("Test connection"):
        if not USE_AI:
            st.error("No API key detected. Add it under Streamlit → Settings → Secrets.")
        else:
            res = call_openai("Reply only with: Connected.")
            if res and "Connected" in res:
                st.success("Connected")
            else:
                st.error(f"Connection issue: {res}")
    st.caption("Tip: collapse this during live demos.")

# ----------------- MODE -----------------
mode = st.radio("Mode", ["Demo", "Pilot (upload your data)"], horizontal=True)
demo = mode == "Demo"
st.caption("Pilot mode enables secure uploads; Demo uses Jan–Jun 2025 sample data.")

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
    fleet = pd.DataFrame({
        "vehicle":["Waste Truck 1","Waste Truck 2","By-law Car 3","Facilities Van 7"],
        "fuel_type":["Diesel","Diesel","Gasoline","Diesel"],
        "liters":[1800,1700,350,900]
    })
    waste = pd.DataFrame({
        "stream":["Municipal Solid Waste","Recycling","Organics"],
        "amount_tonnes":[42,30,18]
    })
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ----------------- UPLOADS (PILOT) -----------------
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    c_up_a, c_up_b, c_up_c = st.columns(3)
    with c_up_a:
        ub = st.file_uploader("Buildings CSV", type=["csv"],
                              help="Columns: facility,month,year,kwh,natural_gas_m3")
    with c_up_b:
        uf = st.file_uploader("Fleet CSV", type=["csv"],
                              help="Columns: vehicle,fuel_type,liters")
    with c_up_c:
        uw = st.file_uploader("Waste CSV", type=["csv"],
                              help="Columns: stream,amount_tonnes")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet     = pd.read_csv(uf) if uf else demo_fleet
    waste     = pd.read_csv(uw) if uw else demo_waste

# ----------------- COST SETTINGS (your request) -----------------
with st.expander("Cost Settings (CAD) – used everywhere", expanded=False):
    colc1, colc2, colc3, colc4 = st.columns(4)
    with colc1:
        elec_rate = st.number_input("Electricity ($/kWh)", value=0.17, min_value=0.0, step=0.01)
    with colc2:
        gas_rate  = st.number_input("Natural gas ($/m³)", value=0.45, min_value=0.0, step=0.01)
    with colc3:
        diesel_rate = st.number_input("Diesel ($/L)", value=1.80, min_value=0.0, step=0.01)
    with colc4:
        gasoline_rate = st.number_input("Gasoline ($/L)", value=1.65, min_value=0.0, step=0.01)
    colc5, _ = st.columns([1,3])
    with colc5:
        landfill_rate = st.number_input("Landfill tipping ($/tonne)", value=125.0, min_value=0.0, step=1.0)

# Emission factors (illustrative; adjust in pilot if desired)
emission_factors = {
    "kwh": 0.00003,           # tCO2e per kWh
    "natural_gas_m3": 0.00189,# tCO2e per m3
    "diesel_l": 0.00268,      # tCO2e per L
    "gasoline_l": 0.00231,    # tCO2e per L
    "msw_tonne": 0.45         # tCO2e per tonne (landfilled)
}

# ----------------- CALCULATIONS -----------------
def calc_buildings(df, elec_rate, gas_rate):
    df = df.copy()
    df["tco2e_elec"] = df["kwh"] * emission_factors["kwh"]
    df["tco2e_gas"]  = df["natural_gas_m3"] * emission_factors["natural_gas_m3"]
    df["tco2e"]      = df["tco2e_elec"] + df["tco2e_gas"]
    df["cost_elec"]  = df["kwh"] * elec_rate
    df["cost_gas"]   = df["natural_gas_m3"] * gas_rate
    df["cost_$"]     = df["cost_elec"] + df["cost_gas"]
    return df

def calc_fleet(df, diesel_rate, gasoline_rate):
    df = df.copy()
    df["tco2e"] = np.where(df["fuel_type"].str.lower().str.contains("diesel"),
                           df["liters"]*emission_factors["diesel_l"],
                           df["liters"]*emission_factors["gasoline_l"])
    df["cost_$"] = np.where(df["fuel_type"].str.lower().str.contains("diesel"),
                            df["liters"]*diesel_rate,
                            df["liters"]*gasoline_rate)
    return df

def calc_waste(df, landfill_rate):
    df = df.copy()
    df["tco2e"] = np.where(df["stream"].str.contains("Municipal"),
                           df["amount_tonnes"]*emission_factors["msw_tonne"], 0)
    df["cost_$"] = np.where(df["stream"].str.contains("Municipal"),
                            df["amount_tonnes"]*landfill_rate, 0)
    return df

bld = calc_buildings(buildings, elec_rate, gas_rate)
flt = calc_fleet(fleet, diesel_rate, gasoline_rate)
wst = calc_waste(waste, landfill_rate)

fmt = lambda n: f"{n:,.1f}"
bld_t, flt_t, wst_t = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
bld_$, flt_$, wst_$ = bld["cost_$"].sum(), flt["cost_$"].sum(), wst["cost_$"].sum()
grand_t = bld_t + flt_t + wst_t
grand_$ = bld_$ + flt_$ + wst_$

# ----------------- TOP KPIs (single row) -----------------
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Total (tCO₂e)", fmt(grand_t))
k2.metric("Buildings (tCO₂e)", fmt(bld_t))
k3.metric("Fleet (tCO₂e)", fmt(flt_t))
k4.metric("Waste (tCO₂e)", fmt(wst_t))
k5.metric("Estimated Annual Cost (CAD)", f"${grand_$:,.0f}")

# ----------------- TABS (no-scroll main sections) -----------------
tabs = st.tabs([
    "Overview • live",
    "Policy Scenarios",
    "Funding & Templates",
    "Engagement"
])

# ================= OVERVIEW =================
with tabs[0]:
    # “live” demo toggle — adds a small time-based wobble to values for visual movement
    live_demo = st.toggle("Live (demo)", value=True, help="Adds subtle motion so charts feel alive.")
    wobble = 1.0
    if live_demo:
        t = time.time()
        wobble = 1.0 + 0.02*math.sin(t/2.0)  # ±2% gentle oscillation

    st.markdown(
        """<div class="smallcap"><span class="pulse"></span> Overview (tCO₂e + $). Tooltips show both.</div>""",
        unsafe_allow_html=True
    )

    ca, cb, cc = st.columns(3)
    order = ["Jan","Feb","Mar","Apr","May","Jun"]

    # Buildings trend (stacked by facility) – with wobble
    with ca:
        st.caption("Buildings – Monthly trend (tCO₂e)")
        chart_b = bld.groupby(["month","facility"],as_index=False).agg(
            tco2e=("tco2e","sum"), cost_$=("cost_$","sum"))
        if "month" in chart_b.columns:
            chart_b["month"] = pd.Categorical(chart_b["month"], categories=order, ordered=True)
        chart_b["tco2e"] = chart_b["tco2e"] * wobble
        st.altair_chart(
            alt.Chart(chart_b).mark_area(opacity=0.75, interpolate="monotone").encode(
                x=alt.X("month", title="Month"),
                y=alt.Y("tco2e:Q", title="tCO₂e"),
                color=alt.Color("facility:N", title="Facility",
                                scale=alt.Scale(range=["#1e6c93","#3aa6d0","#89c2d9","#a8dadc","#457b9d"])),
                tooltip=[alt.Tooltip("facility"), alt.Tooltip("month"),
                         alt.Tooltip("tco2e:Q", title="tCO₂e", format=".1f"),
                         alt.Tooltip("cost_$:Q", title="$", format="$.0f")]
            ).properties(height=260), use_container_width=True
        )

    # Fleet bar – with wobble
    with cb:
        st.caption("Fleet – By vehicle (tCO₂e)")
        flt_show = flt.copy()
        flt_show["tco2e"] *= wobble
        st.altair_chart(
            alt.Chart(flt_show).mark_bar(color="#2a9d8f").encode(
                x=alt.X("vehicle:N", sort="-y", title="Vehicle"),
                y=alt.Y("tco2e:Q", title="tCO₂e"),
                tooltip=[alt.Tooltip("vehicle"), alt.Tooltip("fuel_type"),
                         alt.Tooltip("tco2e:Q", title="tCO₂e", format=".1f"),
                         alt.Tooltip("cost_$:Q", title="$", format="$.0f")]
            ).properties(height=260), use_container_width=True
        )

    # Waste bar – with wobble
    with cc:
        st.caption("Waste – By stream (tCO₂e)")
        wst_show = wst.copy()
        wst_show["tco2e"] *= wobble
        st.altair_chart(
            alt.Chart(wst_show).mark_bar(color="#8a5a44").encode(
                x=alt.X("stream:N", sort="-y", title="Stream"),
                y=alt.Y("tco2e:Q", title="tCO₂e"),
                tooltip=[alt.Tooltip("stream"),
                         alt.Tooltip("tco2e:Q", title="tCO₂e", format=".1f"),
                         alt.Tooltip("cost_$:Q", title="$", format="$.0f")]
            ).properties(height=260), use_container_width=True
        )

# ================= POLICY SCENARIOS (side-by-side) =================
with tabs[1]:
    st.subheader("Policy Scenario Builder – Side-by-Side (tCO₂e & $)")
    sA, sB, sC = st.columns(3)

    # Buildings
    with sA:
        st.markdown("**Buildings**")
        retro = st.slider("Retrofit (%)", 0, 30, 15, key="retro")
        grid  = st.slider("Grid change (%)", -50, 50, -10, key="grid",
                          help="Adjusts electricity emissions factor (cleaner/dirty grid).")
        # scenario recompute
        f_elec = emission_factors["kwh"]*(1+grid/100)
        f_gas  = emission_factors["natural_gas_m3"]
        bld_sc_em = ((bld["kwh"]*f_elec + bld["natural_gas_m3"]*f_gas) * (1-retro/100)).sum()
        bld_sc_$  = ((bld["kwh"]*elec_rate + bld["natural_gas_m3"]*gas_rate) * (1-retro/100)).sum()
        comp = pd.DataFrame({"Case":["Current","Scenario"],
                             "tCO2e":[bld_t,bld_sc_em],
                             "Cost_$":[bld_$,bld_sc_$]})
        st.altair_chart(
            alt.Chart(comp.melt("Case", var_name="Metric", value_name="Value")).mark_bar().encode(
                x=alt.X("Case:N", title=""),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Metric:N", scale=alt.Scale(range=["#1e6c93","#9ecae1"])),
                column=alt.Column("Metric:N", title="")
            ).properties(height=210), use_container_width=True
        )
        st.caption(f"Savings: **{fmt(bld_t - bld_sc_em)} tCO₂e**, **${(bld_$ - bld_sc_$):,.0f}**")

    # Fleet
    with sB:
        st.markdown("**Fleet**")
        ev = st.slider("EV adoption (%)", 0, 50, 20, key="ev")
        flt_sc_em = flt_t*(1-ev/100)
        flt_sc_$  = flt_$*(1-ev/100)  # proportional demo assumption
        comp = pd.DataFrame({"Case":["Current","Scenario"],
                             "tCO2e":[flt_t,flt_sc_em],
                             "Cost_$":[flt_$,flt_sc_$]})
        st.altair_chart(
            alt.Chart(comp.melt("Case", var_name="Metric", value_name="Value")).mark_bar().encode(
                x=alt.X("Case:N", title=""),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Metric:N", scale=alt.Scale(range=["#2a9d8f","#9fdacb"])),
                column=alt.Column("Metric:N", title="")
            ).properties(height=210), use_container_width=True
        )
        st.caption(f"Savings: **{fmt(flt_t - flt_sc_em)} tCO₂e**, **${(flt_$ - flt_sc_$):,.0f}**")

    # Waste
    with sC:
        st.markdown("**Waste**")
        div = st.slider("Diversion (+%)", 0, 50, 10, key="div")
        msw_t = wst[wst["stream"].str.contains("Municipal")]["tco2e"].sum()
        msw_$ = wst[wst["stream"].str.contains("Municipal")]["cost_$"].sum()
        wst_sc_em = wst_t - msw_t*(div/100)
        wst_sc_$  = wst_$ - msw_$*(div/100)
        comp = pd.DataFrame({"Case":["Current","Scenario"],
                             "tCO2e":[wst_t,wst_sc_em],
                             "Cost_$":[wst_$,wst_sc_$]})
        st.altair_chart(
            alt.Chart(comp.melt("Case", var_name="Metric", value_name="Value")).mark_bar().encode(
                x=alt.X("Case:N", title=""),
                y=alt.Y("Value:Q", title="Value"),
                color=alt.Color("Metric:N", scale=alt.Scale(range=["#8a5a44","#d6b7a6"])),
                column=alt.Column("Metric:N", title="")
            ).properties(height=210), use_container_width=True
        )
        st.caption(f"Savings: **{fmt(wst_t - wst_sc_em)} tCO₂e**, **${(wst_$ - wst_sc_$):,.0f}**")

# Track simple engagement badges
if "ran_scenario" not in st.session_state:
    st.session_state.ran_scenario = False
if any([st.session_state.get("retro"), st.session_state.get("ev"), st.session_state.get("div")]):
    st.session_state.ran_scenario = True

# ================= FUNDING & TEMPLATES (two columns; no scroll) =================
with tabs[2]:
    left, right = st.columns([1.1, 1.9])
    with left:
        st.subheader("Funding Navigator")
        st.caption("Pick jurisdiction → program.")
        ON_programs = [
            ("Ontario – Community Reduction Fund (example)","https://www.ontario.ca/page/climate-change-funding"),
            ("Ontario – EV Chargers Municipal Stream (example)","https://www.ontario.ca/page/transportation-electric-vehicles")
        ]
        CA_programs = [
            ("Infrastructure Canada – Green & Inclusive Community Buildings (GICB)","https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html"),
            ("NRCan – Green Infrastructure (example)","https://natural-resources.canada.ca/science-and-data/funding-partnerships/funding-opportunities")
        ]
        FCM_programs = [
            ("FCM GMF – Community Buildings Retrofit","https://greenmunicipalfund.ca/community-buildings-retrofit-initiative"),
            ("FCM GMF – Fleet Electrification","https://greenmunicipalfund.ca/funding/fleet-electrification"),
            ("FCM GMF – Climate Adaptation","https://greenmunicipalfund.ca/funding/adaptation")
        ]
        juris = st.selectbox("Jurisdiction", ["Ontario","Government of Canada","FCM – Green Municipal Fund"])
        if juris=="Ontario":
            choices = ON_programs
        elif juris=="Government of Canada":
            choices = CA_programs
        else:
            choices = FCM_programs
        prog_label = st.selectbox("Program", [c[0] for c in choices], key="prog")
        prog_link = dict(choices)[prog_label]
        st.markdown(f"👉 **Program link:** [{prog_link}]({prog_link})")

    with right:
        st.subheader("Prefilled Application Template (.txt)")
        template = f"""=== GRANT APPLICATION TEMPLATE (Prefilled) ===
Program: {prog_label}
Official Link: {prog_link}

1) Applicant
   • Municipality: City of Waterloo
   • Dept: Sustainability Office
   • Contact: [Name, Title, Email, Phone]
   • Address: 100 Regina St S, Waterloo, ON N2J 4A8

2) Project Title
   • Corporate Emissions & Cost Reduction – Phase 1 (Buildings/Fleet/Waste)

3) Summary (150–250 words)
   • Objective: Reduce corporate emissions and operating costs with targeted measures.
   • Current (demo): {fmt(grand_t)} tCO₂e; Est. annual cost ${grand_$:,.0f}.
   • Focus: Priority facilities, EV transition, and waste diversion.
   • Program Fit: Aligns with {prog_label} objectives.

4) Need & Rationale
   • Regulatory readiness; cost exposure; data fragmentation; limited staff capacity.

5) Outcomes & KPIs
   • Emissions reduction (tCO₂e) and cost savings (CAD) from scenarios.
   • Compliance milestones achieved; reporting cadence.

6) Activities & Workplan
   • Baseline validation → Measure design → Procurement → Implementation → M&V.

7) Budget & Sources
   • Total Cost: $[amount]  • Funding Request: $[amount]  • Municipal Match: $[amount]
   • In-kind/partners: [if any]

8) Timeline & Milestones
   • Start [date] → Substantial completion [date]

9) Risk & Mitigation
   • Procurement, Data gaps, Cost overruns; with mitigations.

10) Engagement & Equity
   • Tailored communications to Council/Residents/Businesses/Staff.

11) Attachments
   • Dashboard snapshots, Scenario results (tCO₂e & $), Compliance one-pager, Support letters.
=== END ===
"""
        st.text_area("Preview", template, height=360)
        st.download_button("Download Template (.txt)", template.encode("utf-8"),
                           file_name="Grant_Application_Template.txt", mime="text/plain")

# ================= ENGAGEMENT (two-column tailored; copy & share) =================
with tabs[3]:
    st.subheader("Stakeholder Engagement – Tailored Messages")
    topA, topB, topC = st.columns([1.4, 1.4, 1.2])
    with topA:
        stakeholders = st.multiselect(
            "Audience(s)",
            ["Council","Residents","Businesses","City Staff"],
            default=["Council","Residents","Businesses","City Staff"]
        )
    with topB:
        topic = st.selectbox(
            "Topic",
            ["Quarterly progress","Budget impact","Compliance update","Pilot invitation","Climate risk & resilience"]
        )
    with topC:
        st.caption("Badges unlock as you engage:")
        unlocked = []
        if not demo: unlocked.append("✅ Data Uploader")
        if st.session_state.get("ran_scenario"): unlocked.append("🏷️ Scenario Explorer")
        if unlocked:
            st.markdown(" ".join([f"<span class='badge'>{b}</span>" for b in unlocked]), unsafe_allow_html=True)
        else:
            st.caption("Upload, run a scenario, or share to unlock badges.")

    # Base context (used for tailored copy)
    base_ctx = (
        f"Corporate estimate (demo) ≈ {fmt(grand_t)} tCO2e with ≈ ${grand_$:,.0f} annual operating costs. "
        f"Scenarios show clear pathways to reduce emissions and costs while improving compliance readiness."
    )
    tones = {
        "Council":"actionable, funding-savvy, concise",
        "Residents":"plain-language, community benefits, supportive",
        "Businesses":"cost-focused, compliance-ready, pragmatic",
        "City Staff":"operational clarity, next steps, collaborative"
    }
    def make_msg(aud, topic):
        prompt = (f"Write a short, 2–3 sentence update for {aud} on '{topic}'. "
                  f"Tone: {tones[aud]}. Include high-level tCO2e and $ implications. "
                  f"Base: {base_ctx}")
        if USE_AI:
            out = call_openai(prompt, max_tokens=120, temperature=0.25)
            if out and not out.startswith(("⚠️","❌")):
                return out
        return (f"{aud}: {topic}. We’re prioritizing actions that lower emissions and costs. "
                f"Estimated footprint: {fmt(grand_t)} tCO₂e; major savings from retrofits, EVs, and diversion.")

    def share_links(text):
        q = urllib.parse.quote(text)
        li = f"https://www.linkedin.com/sharing/share-offsite/?url=https://thedataleaf.com&summary={q}"
        xt = f"https://twitter.com/intent/tweet?text={q}"
        return f"[Share on LinkedIn]({li}) | [Share on X]({xt})"

    # Render in two columns to avoid page scroll
    left, right = st.columns(2)
    half = (len(stakeholders)+1)//2
    left_au = stakeholders[:half]
    right_au = stakeholders[half:]

    for col, group in [(left,left_au),(right,right_au)]:
        with col:
            for aud in group:
                st.markdown(f"**{aud}**")
                txt = make_msg(aud, topic)
                key = f"msg_{aud}"
                st.text_area("Message", value=txt, height=130, key=key)
                st.markdown(share_links(txt))
                st.caption("Copy: click into box → ⌘/Ctrl+A → ⌘/Ctrl+C")
                st.divider()

# --------------- FOOTER ---------------
st.caption("Demo unless Pilot uploads used. Charts show tCO₂e and CAD. Costs are configurable above; funding links are clickable; templates populate post-selection.")
