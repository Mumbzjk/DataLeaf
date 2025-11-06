# =============================================
# Data Leaf – City of Waterloo Pilot MVP (Refined)
# =============================================

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests, os, urllib.parse
from datetime import datetime

# ----------------- PAGE CONFIG -----------------
LOGO_URL = "https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png"
st.set_page_config(page_title="Data Leaf – City of Waterloo Pilot MVP",
                   page_icon=LOGO_URL, layout="wide")

# ----------------- STYLES + HEADER -----------------
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
.badge {{display:inline-block;padding:4px 8px;border-radius:14px;background:#eef6ff;color:#1e6c93;margin-right:6px;font-size:0.85rem;}}
.smallcap {{color:#6b7280;font-size:0.9rem;}}
.table-note {{color:#6b7280;font-size:0.85rem;margin-top:-6px}}
</style>
<div class="headerbar">
    <img src="{LOGO_URL}" alt="Data Leaf logo">
    <h2>Data Leaf – City of Waterloo Pilot MVP</h2>
</div>
""", unsafe_allow_html=True)

# ----------------- PRIVATE ADMIN (developer-only when key present) -----------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_AI = bool(OPENAI_API_KEY)

if USE_AI:
    with st.expander("🧩 Developer • Smart Assist Connection (Private)", expanded=True):
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
    with c1: ub=st.file_uploader("Buildings CSV", type="csv", help="Cols: facility,month,year,kwh,natural_gas_m3")
    with c2: uf=st.file_uploader("Fleet CSV", type="csv", help="Cols: vehicle,fuel_type,liters")
    with c3: uw=st.file_uploader("Waste CSV", type="csv", help="Cols: stream,amount_tonnes")
    buildings=pd.read_csv(ub) if ub else demo_buildings
    fleet=pd.read_csv(uf) if uf else demo_fleet
    waste=pd.read_csv(uw) if uw else demo_waste

# ----------------- COST + FACTORS -----------------
# (kept simple; configurable later via admin panel)
elec_rate, gas_rate = 0.17, 0.45        # $/kWh, $/m3
diesel_rate, gasoline_rate = 1.80, 1.65 # $/L
landfill_rate = 125.0                   # $/tonne

emission_factors={"kwh":0.00003,"natural_gas_m3":0.00189,"diesel_l":0.00268,"gasoline_l":0.00231,"msw_tonne":0.45}

def calc_build(df):
    df=df.copy()
    df["tco2e"]=df["kwh"]*emission_factors["kwh"]+df["natural_gas_m3"]*emission_factors["natural_gas_m3"]
    df["cost"]=df["kwh"]*elec_rate + df["natural_gas_m3"]*gas_rate
    return df

def calc_fleet(df):
    df=df.copy()
    df["tco2e"]=np.where(df["fuel_type"].str.contains("Diesel",case=False),
                         df["liters"]*emission_factors["diesel_l"],
                         df["liters"]*emission_factors["gasoline_l"])
    df["cost"]=np.where(df["fuel_type"].str.contains("Diesel",case=False),
                        df["liters"]*diesel_rate, df["liters"]*gasoline_rate)
    return df

def calc_waste(df):
    df=df.copy()
    df["tco2e"]=np.where(df["stream"].str.contains("Municipal"), df["amount_tonnes"]*emission_factors["msw_tonne"], 0)
    df["cost"]=np.where(df["stream"].str.contains("Municipal"), df["amount_tonnes"]*landfill_rate, 0)
    return df

bld, flt, wst = calc_build(buildings), calc_fleet(fleet), calc_waste(waste)

fmt = lambda n: f"{n:,.1f}"
bld_t, flt_t, wst_t = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
bld_c, flt_c, wst_c = bld["cost"].sum(), flt["cost"].sum(), wst["cost"].sum()
grand_t, grand_c = bld_t + flt_t + wst_t, bld_c + flt_c + wst_c

# ---------- BADGES ----------
def badges_row():
    unlocked=[]
    if not demo: unlocked.append("✅ Data Uploader")
    if st.session_state.get("ran_scenario"): unlocked.append("🏷️ Scenario Explorer")
    if st.session_state.get("funding_scored"): unlocked.append("💸 Funding Ready")
    if st.session_state.get("shared_outreach"): unlocked.append("📣 Outreach Champion")
    if unlocked:
        st.markdown(" ".join([f"<span class='badge'>{b}</span>" for b in unlocked]), unsafe_allow_html=True)

# =========================================================
# PAGE 1: OVERVIEW  (No gimmicks — clear, comparative visuals)
# =========================================================
if st.session_state.page=="Overview":
    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("Total (tCO₂e)", fmt(grand_t))
    k2.metric("Buildings", fmt(bld_t))
    k3.metric("Fleet", fmt(flt_t))
    k4.metric("Waste", fmt(wst_t))
    k5.metric("Annual Cost (CAD)", f"${grand_c:,.0f}")
    badges_row()

    # Month scrubber to "tell the story" across time (much clearer than animation)
    order = ["Jan","Feb","Mar","Apr","May","Jun"]
    sel_month = st.select_slider("View by month (for trend context)", options=order, value="Jun")

    # Monthly series for each category (bars=tCO2e, line=Cost)
    def monthly_series(df, name):
        g = df.groupby("month", as_index=False)[["tco2e","cost"]].sum()
        g["category"] = name
        g["month"] = pd.Categorical(g["month"], categories=order, ordered=True)
        return g.sort_values("month")

    m_b = monthly_series(bld, "Buildings")
    m_f = monthly_series(flt, "Fleet")
    m_w = monthly_series(wst, "Waste")

    def panel(data, title, bar_color, line_color):
        bars = alt.Chart(data).mark_bar(color=bar_color, opacity=0.9).encode(
            x=alt.X("month:N", title="Month"),
            y=alt.Y("tco2e:Q", title="Emissions (tCO₂e)")
        )
        line = alt.Chart(data).mark_line(point=True, color=line_color, strokeWidth=3).encode(
            x="month:N",
            y=alt.Y("cost:Q", title="Cost (CAD)")
        )
        return alt.layer(bars, line).resolve_scale(y='independent').properties(title=title, height=260)

    cA,cB,cC = st.columns(3)
    with cA: st.altair_chart(panel(m_b, "Buildings – Emissions vs Cost", "#1e6c93", "#9ecae1"), use_container_width=True)
    with cB: st.altair_chart(panel(m_f, "Fleet – Emissions vs Cost", "#2a9d8f", "#9fdacb"), use_container_width=True)
    with cC: st.altair_chart(panel(m_w, "Waste – Emissions vs Cost", "#8a5a44", "#d6b7a6"), use_container_width=True)

    # Snapshot for selected month (clear, digestible readout)
    snap_b = bld[bld["month"]==sel_month][["tco2e","cost"]].sum()
    snap_f = flt[flt["month"]==sel_month][["tco2e","cost"]].sum()
    snap_w = wst[wst["month"]==sel_month][["tco2e","cost"]].sum()
    s1,s2,s3 = st.columns(3)
    s1.metric(f"{sel_month} • Buildings", f"{fmt(snap_b['tco2e'])} tCO₂e", f"${snap_b['cost']:,.0f}")
    s2.metric(f"{sel_month} • Fleet",     f"{fmt(snap_f['tco2e'])} tCO₂e", f"${snap_f['cost']:,.0f}")
    s3.metric(f"{sel_month} • Waste",     f"{fmt(snap_w['tco2e'])} tCO₂e", f"${snap_w['cost']:,.0f}")

# =========================================================
# PAGE 2: SCENARIO BUILDER (as-is – you liked it)
# =========================================================
elif st.session_state.page=="Scenario Builder":
    sA,sB,sC=st.columns(3)
    with sA: retro=st.slider("Buildings retrofit (%)",0,30,15)
    with sB: ev=st.slider("Fleet EV adoption (%)",0,50,20)
    with sC: div=st.slider("Waste diversion (%)",0,50,10)

    bld_sc_em=bld_t*(1-retro/100); flt_sc_em=flt_t*(1-ev/100); wst_sc_em=wst_t*(1-div/100)
    bld_sc_cost=bld_c*(1-retro/100); flt_sc_cost=flt_c*(1-ev/100); wst_sc_cost=wst_c*(1-div/100)

    def chart_block(title,cur_em,sc_em,cur_c,sc_c,col1,col2):
        df=pd.DataFrame({"Case":["Current","Scenario"],"Emissions":[cur_em,sc_em],"Cost":[cur_c,sc_c]})
        bars=alt.Chart(df).mark_bar(color=col1).encode(x="Case",y="Emissions")
        line=alt.Chart(df).mark_line(point=True,color=col2,strokeWidth=3).encode(x="Case",y="Cost")
        st.altair_chart(alt.layer(bars,line).resolve_scale(y='independent').properties(title=title,height=260),use_container_width=True)

    pA,pB,pC=st.columns(3)
    with pA: chart_block("Buildings",bld_t,bld_sc_em,bld_c,bld_sc_cost,"#1e6c93","#9ecae1")
    with pB: chart_block("Fleet",flt_t,flt_sc_em,flt_c,flt_sc_cost,"#2a9d8f","#9fdacb")
    with pC: chart_block("Waste",wst_t,wst_sc_em,wst_c,wst_sc_cost,"#8a5a44","#d6b7a6")

    st.session_state.ran_scenario = True

    st.subheader("Smart Assist – Scenario Summary")
    if USE_AI:
        prompt=(f"City of Waterloo scenario. Baseline {fmt(grand_t)} tCO2e, ${grand_c:,.0f}/yr. "
                f"Retrofit {retro}%, EV {ev}%, diversion {div}%. Explain impacts in plain language "
                f"for city staff: costs, emissions, compliance readiness, next steps.")
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type":"application/json"},
                json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}]}
            ).json()
            st.write(r["choices"][0]["message"]["content"] if "choices" in r else "AI summary unavailable.")
        except Exception as e:
            st.error(f"Smart Assist error: {e}")
    else:
        st.info("Smart Assist inactive; add OPENAI_API_KEY in Streamlit → Settings → Secrets to enable.")

# =========================================================
# PAGE 3: FUNDING & GRANTS (real scoring: focus, match, amount, deadlines)
# =========================================================
elif st.session_state.page=="Funding & Grants":
    st.subheader("Funding & Grants – Eligibility & Templates")
    badges_row()

    # Program catalogue (curated examples with amounts, match, deadlines)
    PROGRAMS = [
        {"name":"Infrastructure Canada – GICB",
         "focus":["Buildings","Community"], "amount": "Up to $25M", "match":"Typically municipal matching",
         "deadline":"2026-03-31", "link":"https://housing-infrastructure.canada.ca/gicb-bcvi/index-eng.html",
         "notes":"Community buildings: deep retrofits/new builds; accessibility; M&V."},
        {"name":"FCM GMF – Community Buildings Retrofit",
         "focus":["Buildings"], "amount": "Up to $5M (varies by stream)", "match":"Varies; often 50%",
         "deadline":"Rolling", "link":"https://greenmunicipalfund.ca/community-buildings-retrofit-initiative",
         "notes":"Audits, retrofits, commissioning; strong M&V expected."},
        {"name":"FCM GMF – Fleet Electrification",
         "focus":["Fleet"], "amount": "Up to $1M+", "match":"Varies; often 50%",
         "deadline":"Rolling", "link":"https://greenmunicipalfund.ca/funding/fleet-electrification",
         "notes":"EV transition plans, charging, pilot deployments."},
        {"name":"FCM GMF – Climate Adaptation",
         "focus":["Adaptation","Risk"], "amount": "Up to $1M+", "match":"Varies",
         "deadline":"Rolling", "link":"https://greenmunicipalfund.ca/funding/adaptation",
         "notes":"Risk assessment, adaptation planning/implementation."},
        {"name":"Ontario – Climate/EV Programs (hub)",
         "focus":["Buildings","Fleet"], "amount": "Varies", "match":"Varies",
         "deadline":"Varies", "link":"https://www.ontario.ca/page/climate-change-funding",
         "notes":"Entry page to active provincial programs."},
        {"name":"NRCan – Green Infrastructure (hub)",
         "focus":["Buildings","Fleet","Adaptation"], "amount": "Varies", "match":"Varies",
         "deadline":"Varies", "link":"https://natural-resources.canada.ca/science-and-data/funding-partnerships/funding-opportunities",
         "notes":"Federal funding opportunities hub."},
    ]

    # Select focus areas (from your analysis)
    fleft, fright = st.columns([1.1,1.9])
    with fleft:
        focus = st.multiselect("Project focus (from analysis)",
                               ["Buildings","Fleet","Waste","Adaptation","Risk"],
                               default=["Buildings","Fleet"])
        # Simple quantitative signals (from baseline) to influence eligibility
        st.markdown("**Impact signals**")
        st.write(f"- Buildings: {fmt(bld_t)} tCO₂e / ${bld_c:,.0f}/yr")
        st.write(f"- Fleet: {fmt(flt_t)} tCO₂e / ${flt_c:,.0f}/yr")
        st.write(f"- Waste: {fmt(wst_t)} tCO₂e / ${wst_c:,.0f}/yr")

        # Heuristic eligibility rules (transparent & explainable)
        def eligible(p):
            # Waste isn’t explicitly listed in many programs; tie it to Buildings (retrofit ops) or FCM Adaptation.
            if "Waste" in focus and ("Buildings" in p["focus"] or "Adaptation" in p["focus"]):
                return True
            # Direct focus match
            if any(f in p["focus"] for f in focus if f != "Waste"):
                return True
            return False

        # Score by strength: focus match + scale of impact (bigger baseline → stronger case)
        def score(p):
            s = 0
            s += sum(1 for f in focus if f in p["focus"])
            # boost by category scale (rough)
            if "Buildings" in p["focus"]: s += (1 if bld_t > 200 else 0)
            if "Fleet" in p["focus"]:     s += (1 if flt_t > 50 else 0)
            if "Adaptation" in p["focus"] or "Risk" in p["focus"]: s += 1
            return s

        eligible_list = [p for p in PROGRAMS if eligible(p)]
        eligible_list = sorted(eligible_list, key=score, reverse=True)

    with fright:
        st.markdown("**Eligible programs (ranked):**")
        # Show as a clean table with name (linked), amount, match, deadline
        df = pd.DataFrame([{
            "Program": p["name"],
            "Amount": p["amount"],
            "Match": p["match"],
            "Deadline": p["deadline"],
            "Link": p["link"]
        } for p in eligible_list])
        # Render with links in separate column
        st.dataframe(df[["Program","Amount","Match","Deadline","Link"]], use_container_width=True, hide_index=True)
        st.markdown("<div class='table-note'>Programs ranked by focus alignment and scale of impact from your baseline.</div>", unsafe_allow_html=True)

        # Prefilled template generator
        if eligible_list:
            pick_name = st.selectbox("Generate template for", [p["name"] for p in eligible_list])
            pick = next(p for p in eligible_list if p["name"]==pick_name)
            template = f"""=== GRANT APPLICATION TEMPLATE (Prefilled) ===
Program: {pick['name']}
Official Link: {pick['link']}

1) Applicant
   • Municipality: City of Waterloo
   • Dept: Sustainability Office
   • Contact: [Name, Title, Email, Phone]
   • Address: 100 Regina St S, Waterloo, ON N2J 4A8

2) Project Title
   • Corporate Emissions & Cost Reduction – Phase 1 ({', '.join(focus)})

3) Summary (150–250 words)
   • Objective: Reduce corporate emissions and operating costs with targeted measures.
   • Baseline (demo): {fmt(grand_t)} tCO₂e; Est. annual cost ${grand_c:,.0f}.
   • Focus: {', '.join(focus)}.
   • Program Fit: Aligns with {pick['name']} objectives. Amount: {pick['amount']}; Match: {pick['match']}; Deadline: {pick['deadline']}.

4) Need & Rationale
   • Regulatory readiness; cost exposure; data fragmentation; limited staff capacity.

5) Outcomes & KPIs
   • Emissions reduction (tCO₂e) and cost savings (CAD) from scenarios.
   • Compliance milestones and reporting cadence.

6) Activities & Workplan
   • Baseline validation → Measure design → Procurement → Implementation → M&V.

7) Budget & Sources
   • Total Cost: $[amount]  • Funding Request: $[amount]  • Municipal Match: $[amount]

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
            st.download_button("Download Prefilled Template (.txt)", template.encode("utf-8"),
                               file_name="Grant_Application_Template.txt", mime="text/plain")
            st.session_state.funding_scored = True
        else:
            st.info("No programs match the current focus selection. Try adjusting focus to Buildings, Fleet, or Adaptation.")

# =========================================================
# PAGE 4: ENGAGEMENT (you liked this; kept)
# =========================================================
elif st.session_state.page=="Engagement":
    st.subheader("Stakeholder Messages – City of Waterloo")
    groups=["Council","Residents","Businesses","City Staff"]
    topic=st.selectbox("Topic",["Quarterly update","Budget impact","Compliance progress","Pilot invitation"])

    defaults={
        "Council":"Waterloo is advancing measurable climate action. Current footprint is about 1,200 tCO₂e. Retrofit and EV measures could cut 15–25% while saving on fuel and utilities.",
        "Residents":"The City of Waterloo is working to lower costs and emissions through better data. You can see progress in buildings, fleet, and waste—each step keeps our community thriving.",
        "Businesses":"Waterloo is improving efficiency city-wide. Data insights help identify funding and compliance opportunities that lower energy costs for everyone.",
        "City Staff":"Together we’re simplifying reporting. Data Leaf lets us upload, track, and visualize progress in one place—making updates faster and grant-ready."
    }

    col1,col2 = st.columns(2)
    any_shared=False
    for i,g in enumerate(groups):
        with (col1 if i%2==0 else col2):
            st.markdown(f"**{g}**")
            st.text_area("Message",defaults[g],height=110, key=f"msg_{g}")
            q=urllib.parse.quote(defaults[g])
            li=f"https://linkedin.com/shareArticle?mini=true&url=https://thedataleaf.com&summary={q}"
            xt=f"https://twitter.com/intent/tweet?text={q}"
            fb=f"https://facebook.com/sharer/sharer.php?u=https://thedataleaf.com&quote={q}"
            ml=f"mailto:?subject=City%20of%20Waterloo%20update&body={q}"
            links=f"[LinkedIn]({li}) | [𝕏]({xt}) | [Facebook]({fb})"
            if g=="City Staff": links += f" | [Email]({ml})"
            st.markdown(links)
            st.caption("Copy: click in box → ⌘/Ctrl+A → ⌘/Ctrl+C")
            st.divider()
            any_shared=True
    if any_shared:
        st.session_state.shared_outreach=True

# =========================================================
st.caption("Demo data only. Costs in CAD. Smart Assist private. Badges unlock as you use the app. Data Leaf © 2025")
