import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os
# ================= Optional AI Setup =================
import os
import streamlit as st
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

USE_AI = False
client = None

if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)  # project ID auto-detected
        USE_AI = True
    except Exception as e:
        st.error(f"❌ AI initialization failed: {e}")
        USE_AI = False

# ================= Optional AI =================
USE_AI = False
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        USE_AI = True
    except Exception:
        USE_AI = False

# ================= Page =======================
st.set_page_config(
    page_title="Data Leaf – City of Waterloo Pilot MVP",
    page_icon="https://thedataleaf.com/wp-content/uploads/2025/09/Untitled-design-10-1.png",
    layout="wide"
)

# ---------- AI Connection Check ----------
st.markdown("### 🔍 AI Connection Check")
if st.button("Test AI Connection"):
    if USE_AI and client:
        try:
            ping = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":"Respond with the single word: Connected."}],
                temperature=0.0,
                max_tokens=5
            )
            st.success("✅ " + ping.choices[0].message.content.strip())
        except Exception as e:
            st.error(f"❌ Connection failed: {e}")
    else:
        st.error("❌ No API key detected. Add it at: Streamlit Cloud → App → Settings → Secrets\nOPENAI_API_KEY = \"sk-...\"")

ai_status = "🟢 AI: Connected" if USE_AI else "🔴 AI: Not connected"
st.caption(ai_status + " · Manage at Streamlit → Settings → Secrets")

# ---------- Mode switch ----------
mode = st.radio("Select Mode", ["Demo Mode", "Pilot Mode"], horizontal=True)
demo = mode == "Demo Mode"
st.caption("🌿 Pilot Mode enables secure uploads of your monthly CSVs. Demo Mode uses sample Jan–Jun 2025 data.")

# ================= Demo Data ==================
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
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ================= Pilot Uploads =================
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    st.info("🔹 Upload CSVs below. If a file is not provided, demo data is used as a fallback.")
    ub = st.file_uploader("Upload Buildings CSV", type=["csv"], help="Columns: facility,month,year,kwh,natural_gas_m3")
    uf = st.file_uploader("Upload Fleet CSV", type=["csv"], help="Columns: vehicle,fuel_type,liters")
    uw = st.file_uploader("Upload Waste CSV", type=["csv"], help="Columns: stream,amount (tonnes)")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet     = pd.read_csv(uf) if uf else demo_fleet
    waste     = pd.read_csv(uw) if uw else demo_waste

# ================= Factors & Grants =================
factors = pd.DataFrame({
    "source":["kwh","natural_gas_m3","diesel_l","gasoline_l","tonnes_msw"],
    "tco2e_per_unit":[0.00003,0.00189,0.00268,0.00231,0.45]
})

grants = pd.DataFrame([
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
], columns=["program","deadline","match_pct","max_amount","categories","link","notes"])

# ================= Calculations =================
fmt = lambda n: f"{n:,.1f}"

def calc_buildings(df):
    f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]
    f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
    out = df.copy()
    out["tco2e_elec"] = out["kwh"]*f_elec
    out["tco2e_gas"]  = out["natural_gas_m3"]*f_gas
    out["tco2e"]      = out["tco2e_elec"] + out["tco2e_gas"]
    return out

def calc_fleet(df):
    f_d = factors.loc[factors["source"]=="diesel_l","tco2e_per_unit"].values[0]
    f_g = factors.loc[factors["source"]=="gasoline_l","tco2e_per_unit"].values[0]
    out = df.copy()
    out["tco2e"] = np.where(out["fuel_type"].str.lower().str.contains("diesel"),
                            out["liters"]*f_d, out["liters"]*f_g)
    return out

def calc_waste(df):
    f = factors.loc[factors["source"]=="tonnes_msw","tco2e_per_unit"].values[0]
    out = df.copy()
    out["tco2e"] = np.where(out["stream"].str.contains("Municipal"), out["amount"]*f, 0)
    return out

bld = calc_buildings(buildings)
flt = calc_fleet(fleet)
wst = calc_waste(waste)

bld_total, flt_total, wst_total = bld["tco2e"].sum(), flt["tco2e"].sum(), wst["tco2e"].sum()
grand_total = bld_total + flt_total + wst_total

# ================= Header ======================
st.title("Data Leaf – City of Waterloo Pilot MVP")

k1,k2,k3,k4 = st.columns(4)
k1.metric("Total (tCO₂e)", fmt(grand_total))
k2.metric("Buildings (tCO₂e)", fmt(bld_total))
k3.metric("Fleet (tCO₂e)", fmt(flt_total))
k4.metric("Waste (tCO₂e)", fmt(wst_total))

# Color palettes per section
COLORS_OVERVIEW = {
    "buildings": ["#1e6c93", "#3aa6d0", "#89c2d9", "#a8dadc", "#457b9d"],  # blues
    "fleet":     ["#2a9d8f"],  # teal
    "waste":     ["#8a5a44"]   # brown
}
COLORS_SCENARIOS = {
    "buildings": ["#1e6c93", "#9ecae1"],  # current, scenario
    "fleet":     ["#2a9d8f", "#9fdacb"],
    "waste":     ["#8a5a44", "#d6b7a6"]
}

tabs = st.tabs(["Overview", "Policy Scenarios", "Funding & Templates", "Engagement"])

# ================= Overview (3 charts, diff colors) =================
with tabs[0]:
    st.subheader("Overview – Buildings, Fleet, Waste (tCO₂e)")

    cA,cB,cC = st.columns(3)

    # Buildings (stacked area by facility)
    with cA:
        st.markdown("**Buildings – Monthly trend (tCO₂e)**")
        order = ["Jan","Feb","Mar","Apr","May","Jun"]
        chart_b = bld.groupby(["month","facility"],as_index=False)["tco2e"].sum()
        if "month" in chart_b.columns:
            chart_b["month"] = pd.Categorical(chart_b["month"], categories=order, ordered=True)
        st.altair_chart(
            alt.Chart(chart_b).mark_area(opacity=0.75).encode(
                x=alt.X("month", title="Month"),
                y=alt.Y("tco2e", title="tCO₂e"),
                color=alt.Color("facility", title="Facility",
                                scale=alt.Scale(range=COLORS_OVERVIEW["buildings"])),
                tooltip=["facility","month","tco2e"]
            ).properties(height=280),
            use_container_width=True
        )

    # Fleet (bar by vehicle)
    with cB:
        st.markdown("**Fleet – By vehicle (tCO₂e)**")
        st.altair_chart(
            alt.Chart(flt).mark_bar().encode(
                x=alt.X("vehicle", sort="-y", title="Vehicle"),
                y=alt.Y("tco2e", title="tCO₂e"),
                color=alt.value(COLORS_OVERVIEW["fleet"][0]),
                tooltip=["vehicle","fuel_type","tco2e"]
            ).properties(height=280),
            use_container_width=True
        )

    # Waste (bar by stream)
    with cC:
        st.markdown("**Waste – By stream (tCO₂e)**")
        st.altair_chart(
            alt.Chart(wst).mark_bar().encode(
                x=alt.X("stream", sort="-y", title="Stream"),
                y=alt.Y("tco2e", title="tCO₂e"),
                color=alt.value(COLORS_OVERVIEW["waste"][0]),
                tooltip=["stream","tco2e"]
            ).properties(height=280),
            use_container_width=True
        )

    st.caption("All views update instantly when you upload your data in Pilot Mode.")

# ================= Policy Scenarios (one horizontal row) =============
with tabs[1]:
    st.subheader("Policy Scenario Builder – Side-by-Side (tCO₂e)")

    col1, col2, col3 = st.columns(3)

    # -------- Buildings Scenario --------
    with col1:
        st.markdown("#### Buildings")
        retro = st.slider("Retrofit savings (%)", 0, 30, 15,
                          help="Uniform savings on electricity & natural gas.")
        grid  = st.slider("Grid intensity change (%)", -50, 50, -10,
                          help="Adjusts electricity factor; simulates cleaner/dirter grid.")
        f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]*(1+grid/100)
        f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
        bld_sc_vals  = (bld["kwh"]*f_elec + bld["natural_gas_m3"]*f_gas)*(1-retro/100)
        bld_sc_total = bld_sc_vals.sum()
        delta_abs_b  = bld_total - bld_sc_total
        delta_pct_b  = 0 if bld_total==0 else delta_abs_b/bld_total*100

        comp_b = pd.DataFrame({"Case":["Current","Scenario"],"tCO2e":[bld_total,bld_sc_total]})
        st.altair_chart(
            alt.Chart(comp_b).mark_bar().encode(
                x=alt.X("Case", title=""),
                y=alt.Y("tCO2e", title="tCO₂e"),
                color=alt.Color("Case", scale=alt.Scale(range=COLORS_SCENARIOS["buildings"])),
                tooltip=["Case","tCO2e"]
            ).properties(height=230),
            use_container_width=True
        )
        st.metric("Scenario (tCO₂e)", fmt(bld_sc_total), f"-{fmt(delta_abs_b)} ({delta_pct_b:.1f}%)")
        if USE_AI and st.button("Explain (AI) – Buildings"):
            try:
                msg = f"Buildings scenario: retrofit {retro}%, grid change {grid}%. Current {fmt(bld_total)} tCO2e; scenario {fmt(bld_sc_total)}."
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"One-sentence summary for city staff: {msg}"}],
                    temperature=0.2, max_tokens=70
                )
                st.success(out.choices[0].message.content.strip())
            except Exception as e:
                st.info(f"AI unavailable ({e}). Values shown above.")

    # -------- Fleet Scenario --------
    with col2:
        st.markdown("#### Fleet")
        ev = st.slider("EV adoption (%)", 0, 50, 20,
                       help="Reduces tailpipe emissions proportionally (demo).")
        flt_sc_total = flt_total*(1-ev/100)
        delta_abs_f  = flt_total - flt_sc_total
        delta_pct_f  = 0 if flt_total==0 else delta_abs_f/flt_total*100

        comp_f = pd.DataFrame({"Case":["Current","Scenario"],"tCO2e":[flt_total,flt_sc_total]})
        st.altair_chart(
            alt.Chart(comp_f).mark_bar().encode(
                x=alt.X("Case", title=""),
                y=alt.Y("tCO2e", title="tCO₂e"),
                color=alt.Color("Case", scale=alt.Scale(range=COLORS_SCENARIOS["fleet"])),
                tooltip=["Case","tCO2e"]
            ).properties(height=230),
            use_container_width=True
        )
        st.metric("Scenario (tCO₂e)", fmt(flt_sc_total), f"-{fmt(delta_abs_f)} ({delta_pct_f:.1f}%)")
        if USE_AI and st.button("Explain (AI) – Fleet"):
            try:
                msg = f"Fleet scenario: EV adoption {ev}%. Current {fmt(flt_total)} tCO2e; scenario {fmt(flt_sc_total)}."
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"One-sentence summary for city staff: {msg}"}],
                    temperature=0.2, max_tokens=60
                )
                st.success(out.choices[0].message.content.strip())
            except Exception as e:
                st.info(f"AI unavailable ({e}). Values shown above.")

    # -------- Waste Scenario --------
    with col3:
        st.markdown("#### Waste")
        div = st.slider("Diversion increase (%)", 0, 50, 10,
                        help="Shifts a portion of MSW away from landfill (demo).")
        msw = wst[wst["stream"].str.contains("Municipal")]["tco2e"].sum()
        wst_sc_total = wst_total - msw*(div/100)
        delta_abs_w  = wst_total - wst_sc_total
        delta_pct_w  = 0 if wst_total==0 else delta_abs_w/wst_total*100

        comp_w = pd.DataFrame({"Case":["Current","Scenario"],"tCO2e":[wst_total,wst_sc_total]})
        st.altair_chart(
            alt.Chart(comp_w).mark_bar().encode(
                x=alt.X("Case", title=""),
                y=alt.Y("tCO2e", title="tCO₂e"),
                color=alt.Color("Case", scale=alt.Scale(range=COLORS_SCENARIOS["waste"])),
                tooltip=["Case","tCO2e"]
            ).properties(height=230),
            use_container_width=True
        )
        st.metric("Scenario (tCO₂e)", fmt(wst_sc_total), f"-{fmt(delta_abs_w)} ({delta_pct_w:.1f}%)")
        if USE_AI and st.button("Explain (AI) – Waste"):
            try:
                msg = f"Waste scenario: diversion +{div}%. Current {fmt(wst_total)} tCO2e; scenario {fmt(wst_sc_total)}."
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"One-sentence summary for city staff: {msg}"}],
                    temperature=0.2, max_tokens=60
                )
                st.success(out.choices[0].message.content.strip())
            except Exception as e:
                st.info(f"AI unavailable ({e}). Values shown above.")

# ================= Funding & Templates ====================
with tabs[2]:
    st.subheader("Relevant Funding (click to open)")
    for _, r in grants.iterrows():
        st.markdown(
            f"- **{r['program']}** – *{r['match_pct']}* – {r['deadline']}  \n"
            f"  {r['notes']}  \n"
            f"  👉 [{r['link']}]({r['link']})"
        )

    st.divider()
    st.subheader("Generate Prefilled Grant Application Template (.txt)")

    sel = st.selectbox("Choose a program", grants["program"])
    gr = grants[grants["program"]==sel].iloc[0]
    key_cat = gr["categories"].split(",")[0]

    # quick context
    top_fac = bld.groupby("facility",as_index=False)["tco2e"].sum().sort_values("tco2e",ascending=False).iloc[0]["facility"]

    # Build a comprehensive template with real-life sections
    template = f"""=== GRANT APPLICATION TEMPLATE (Prefilled) ===

Program: {gr['program']}
Deadline: {gr['deadline']}
Cost Share / Match: {gr['match_pct']} (Max: {gr['max_amount']})
Official Link: {gr['link']}

1) Applicant Information
   • Municipality: City of Waterloo
   • Department: Sustainability Office
   • Primary Contact: [Name, Title, Email, Phone]
   • Mailing Address: 100 Regina St S, Waterloo, ON N2J 4A8

2) Project Title
   • {key_cat.title()} Acceleration – Phase 1 ({top_fac})

3) Project Summary (150–250 words)
   • Objective: Reduce corporate emissions in priority area: {key_cat}.
   • Current footprint (demo): {fmt(grand_total)} tCO₂e (Buildings {fmt(bld_total)}, Fleet {fmt(flt_total)}, Waste {fmt(wst_total)}).
   • Focus site(s): {top_fac} (and others as needed).
   • Approach: Targeted measures aligned with {gr['program']}.

4) Statement of Need / Problem Definition
   • Key drivers: Regulatory readiness, cost exposure (energy/fuel), asset lifecycle.
   • Barriers: Limited staff capacity, fragmented data, funding complexity.

5) Objectives & Outcomes (quantified)
   • Emissions reduced (tCO₂e): [insert from scenario results]
   • Energy/fuel cost savings ($): [insert estimate]
   • Co-benefits: comfort, reliability, resilience, equity, accessibility (as applicable).

6) Activities & Workplan
   • Task 1: Data consolidation & baseline validation
   • Task 2: Design measures (e.g., retrofits / EVs / diversion)
   • Task 3: Procurement & implementation
   • Task 4: Monitoring, verification, and reporting (M&V)
   • Responsible parties & milestones listed per task.

7) Budget & Matching Funds
   • Total Project Cost: $[amount]
   • Funding Request: $[amount]
   • Municipal Share: $[amount]  ({gr['match_pct']})
   • In-kind / partner contributions: [if any]

8) Timeline
   • Start: [date]   • Substantial completion: [date]
   • Key milestones aligned to the workplan.

9) Risks & Mitigation
   • Procurement delays → early market sounding; alternate suppliers
   • Data gaps → staged data collection; conservative assumptions
   • Cost overruns → contingency; scope checkpoints

10) Team & Partners
   • City departments: Facilities, Fleet, Finance, Communications
   • External partners: Vendors, utilities, NGOs, consultants (as needed)

11) Equity, Accessibility & Community Benefits
   • Engagement of diverse stakeholders; accessible facilities; community co-benefits.

12) Monitoring & Evaluation (KPIs)
   • KPI 1: Verified tCO₂e reductions vs baseline
   • KPI 2: Energy/fuel savings ($)
   • KPI 3: Progress on compliance milestones and reporting cadence

13) Attachments Checklist
   • KPI snapshot (from dashboard)
   • Scenario results (Current vs Scenario per category)
   • Compliance readiness one-pager
   • Letters of support / council endorsement (if required)
   • Procurement plan / vendor quotes (if available)

=== END TEMPLATE ===
"""

    st.text_area("Preview", value=template, height=420)
    st.download_button("Download Grant Application Template (.txt)",
                       data=template.encode("utf-8"),
                       file_name="Grant_Application_Template_Prefilled.txt",
                       mime="text/plain")

# ================= Engagement ============================
with tabs[3]:
    st.subheader("Stakeholder Engagement – Targeted Messages")

    audiences = st.multiselect(
        "Select audience(s)",
        ["Council","Residents","Businesses","City Staff"],
        default=["Council","Residents"]
    )

    base_context = (f"In 2025 (demo), Waterloo’s estimated corporate emissions ≈ {fmt(grand_total)} tCO₂e. "
                    f"Top sources: Buildings and Fleet. Priorities: retrofits, EV transition, improved diversion.")

    def gen_msg(aud):
        tone = {
            "Council":"Action-focused, funding-savvy, concise.",
            "Residents":"Plain language, community benefits, supportive tone.",
            "Businesses":"Cost-savings, compliance readiness, pragmatic tone.",
            "City Staff":"Operational clarity, next steps, collaboration."
        }[aud]
        if USE_AI:
            try:
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":
                               f"Write a two-sentence update for {aud}. Tone: {tone}. "
                               f"Include the tCO2e figure, and mention retrofits/EV/diversion. "
                               f"Base context: {base_context}"}],
                    temperature=0.2, max_tokens=110
                )
                return out.choices[0].message.content.strip()
            except Exception:
                return base_context + " [AI unavailable]"
        else:
            return base_context

    for aud in audiences:
        st.markdown(f"**{aud}**")
        st.text_area(f"Message for {aud}", gen_msg(aud), height=120, key=f"msg_{aud}")

# Footer note
st.caption("Demo unless Pilot uploads used. All charts labeled in tCO₂e. Funding examples reflect 2025 programs.")
