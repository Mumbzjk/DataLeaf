import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import os

# ================= Optional AI =================
USE_AI = False
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
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

# --- AI status pill ---
ai_status = "🟢 AI: Connected" if USE_AI else "🔴 AI: Not connected"
st.caption(ai_status + " · Set OPENAI_API_KEY in Streamlit → Settings → Secrets")

# ------------------ MODE SWITCH ------------------
mode = st.radio("Select Mode", ["Demo Mode", "Pilot Mode"], horizontal=True)
demo = mode == "Demo Mode"
st.caption("🌿 *Pilot Mode lets you upload your data; Demo Mode uses sample figures (Jan–Jun 2025).*")

# ================= Demo data ===================
def load_demo():
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
                "kwh":int(base_kwh*mult),"natural_gas_m3":int(base_gas*mult)
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
    return buildings,fleet,waste

demo_buildings, demo_fleet, demo_waste = load_demo()

# ================= Pilot uploads =================
if demo:
    buildings, fleet, waste = demo_buildings, demo_fleet, demo_waste
else:
    st.info("🔹 Upload CSVs to populate the dashboard with your data.")
    ub = st.file_uploader("Upload Buildings CSV", type=["csv"],
                          help="Columns required: facility,month,year,kwh,natural_gas_m3")
    uf = st.file_uploader("Upload Fleet CSV", type=["csv"],
                          help="Columns required: vehicle,fuel_type,liters")
    uw = st.file_uploader("Upload Waste CSV", type=["csv"],
                          help="Columns required: stream,amount (tonnes)")
    buildings = pd.read_csv(ub) if ub else demo_buildings
    fleet     = pd.read_csv(uf) if uf else demo_fleet
    waste     = pd.read_csv(uw) if uw else demo_waste

# ================= Factors & grants =============
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

m1,m2,m3,m4 = st.columns(4)
m1.metric("Total (tCO₂e)", fmt(grand_total))
m2.metric("Buildings (tCO₂e)", fmt(bld_total))
m3.metric("Fleet (tCO₂e)", fmt(flt_total))
m4.metric("Waste (tCO₂e)", fmt(wst_total))

tabs = st.tabs(["Overview","Policy Scenarios","Funding","Engagement"])

# ================= Overview (three charts) =====
with tabs[0]:
    st.subheader("Overview – Three Key Views (tCO₂e)")

    cA,cB,cC = st.columns(3)

    # Buildings trend (area chart)
    with cA:
        st.markdown("**Buildings – Monthly trend (tCO₂e)**")
        order = ["Jan","Feb","Mar","Apr","May","Jun"]
        chart_b = bld.groupby(["month","facility"],as_index=False)["tco2e"].sum()
        if "month" in chart_b.columns:
            chart_b["month"] = pd.Categorical(chart_b["month"], categories=order, ordered=True)
        st.altair_chart(
            alt.Chart(chart_b).mark_area(opacity=0.7).encode(
                x=alt.X("month", title="Month"),
                y=alt.Y("tco2e", title="tCO₂e"),
                color="facility",
                tooltip=["facility","month","tco2e"]
            ).properties(height=280),
            use_container_width=True
        )

    # Fleet bar
    with cB:
        st.markdown("**Fleet – By vehicle (tCO₂e)**")
        chart_f = flt.copy()
        st.altair_chart(
            alt.Chart(chart_f).mark_bar().encode(
                x=alt.X("vehicle", sort="-y", title="Vehicle"),
                y=alt.Y("tco2e", title="tCO₂e"),
                tooltip=["vehicle","fuel_type","tco2e"]
            ).properties(height=280),
            use_container_width=True
        )

    # Waste bar
    with cC:
        st.markdown("**Waste – By stream (tCO₂e)**")
        chart_w = wst.copy()
        st.altair_chart(
            alt.Chart(chart_w).mark_bar().encode(
                x=alt.X("stream", sort="-y", title="Stream"),
                y=alt.Y("tco2e", title="tCO₂e"),
                tooltip=["stream","tco2e"]
            ).properties(height=280),
            use_container_width=True
        )

    st.caption("All figures update automatically when you upload your data in Pilot Mode.")

# ============== Policy Scenarios (three charts) =============
with tabs[1]:
    st.subheader("Policy Scenario Builder – Per Category (tCO₂e)")

    # ---------- Buildings scenario ----------
    st.markdown("### Buildings")
    colA, colB = st.columns([1,2])
    with colA:
        retro = st.slider("Retrofit savings (%)", 0, 30, 15,
                          help="Uniform savings on electricity & natural gas emissions.")
        grid = st.slider("Grid intensity change (%)", -50, 50, -10,
                         help="Changes electricity factor to simulate cleaner/dirter grid.")
        f_elec = factors.loc[factors["source"]=="kwh","tco2e_per_unit"].values[0]*(1+grid/100)
        f_gas  = factors.loc[factors["source"]=="natural_gas_m3","tco2e_per_unit"].values[0]
        bld_sc_vals = (bld["kwh"]*f_elec + bld["natural_gas_m3"]*f_gas)*(1-retro/100)
        bld_sc_total = bld_sc_vals.sum()
        delta_abs_b = bld_total - bld_sc_total
        delta_pct_b = 0 if bld_total==0 else delta_abs_b/bld_total*100
        st.metric("Scenario (tCO₂e)", fmt(bld_sc_total), f"-{fmt(delta_abs_b)} ({delta_pct_b:.1f}%)")
        if USE_AI and st.button("Explain Buildings (AI)"):
            try:
                msg = f"Buildings scenario: retrofit {retro}%, grid change {grid}%. Current {fmt(bld_total)} tCO2e; scenario {fmt(bld_sc_total)}."
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"One-sentence plain summary for city staff: {msg}"}],
                    temperature=0.2, max_tokens=70
                )
                st.success(out.choices[0].message.content.strip())
            except Exception:
                st.info("AI unavailable; values above reflect the scenario.")
    with colB:
        comp_b = pd.DataFrame({"Case":["Current","Scenario"],"tCO2e":[bld_total,bld_sc_total]})
        st.altair_chart(
            alt.Chart(comp_b).mark_bar().encode(
                x=alt.X("Case", title=""),
                y=alt.Y("tCO2e", title="tCO₂e"),
                tooltip=["Case","tCO2e"]
            ).properties(height=220),
            use_container_width=True
        )

    st.divider()

    # ---------- Fleet scenario ----------
    st.markdown("### Fleet")
    colC, colD = st.columns([1,2])
    with colC:
        ev = st.slider("EV adoption (%)", 0, 50, 20,
                       help="Reduces tailpipe emissions proportionally (demo assumption).")
        flt_sc_total = flt_total*(1-ev/100)
        delta_abs_f = flt_total - flt_sc_total
        delta_pct_f = 0 if flt_total==0 else delta_abs_f/flt_total*100
        st.metric("Scenario (tCO₂e)", fmt(flt_sc_total), f"-{fmt(delta_abs_f)} ({delta_pct_f:.1f}%)")
        if USE_AI and st.button("Explain Fleet (AI)"):
            try:
                msg = f"Fleet scenario: EV adoption {ev}%. Current {fmt(flt_total)} tCO2e; scenario {fmt(flt_sc_total)}."
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"One-sentence plain summary for city staff: {msg}"}],
                    temperature=0.2, max_tokens=60
                )
                st.success(out.choices[0].message.content.strip())
            except Exception:
                st.info("AI unavailable; values above reflect the scenario.")
    with colD:
        comp_f = pd.DataFrame({"Case":["Current","Scenario"],"tCO2e":[flt_total,flt_sc_total]})
        st.altair_chart(
            alt.Chart(comp_f).mark_bar().encode(
                x=alt.X("Case", title=""),
                y=alt.Y("tCO2e", title="tCO₂e"),
                tooltip=["Case","tCO2e"]
            ).properties(height=220),
            use_container_width=True
        )

    st.divider()

    # ---------- Waste scenario ----------
    st.markdown("### Waste")
    colE, colF = st.columns([1,2])
    with colE:
        div = st.slider("Diversion increase (%)", 0, 50, 10,
                        help="Shifts a portion of MSW away from landfill (demo).")
        msw = wst[wst["stream"].str.contains("Municipal")]["tco2e"].sum()
        wst_sc_total = wst_total - msw*(div/100)
        delta_abs_w = wst_total - wst_sc_total
        delta_pct_w = 0 if wst_total==0 else delta_abs_w/wst_total*100
        st.metric("Scenario (tCO₂e)", fmt(wst_sc_total), f"-{fmt(delta_abs_w)} ({delta_pct_w:.1f}%)")
        if USE_AI and st.button("Explain Waste (AI)"):
            try:
                msg = f"Waste scenario: diversion +{div}%. Current {fmt(wst_total)} tCO2e; scenario {fmt(wst_sc_total)}."
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":f"One-sentence plain summary for city staff: {msg}"}],
                    temperature=0.2, max_tokens=60
                )
                st.success(out.choices[0].message.content.strip())
            except Exception:
                st.info("AI unavailable; values above reflect the scenario.")
    with colF:
        comp_w = pd.DataFrame({"Case":["Current","Scenario"],"tCO2e":[wst_total,wst_sc_total]})
        st.altair_chart(
            alt.Chart(comp_w).mark_bar().encode(
                x=alt.X("Case", title=""),
                y=alt.Y("tCO2e", title="tCO₂e"),
                tooltip=["Case","tCO2e"]
            ).properties(height=220),
            use_container_width=True
        )

# ================= Funding (clickable + template) =========
with tabs[2]:
    st.subheader("Relevant Funding (click to open)")
    for _, r in grants.iterrows():
        st.markdown(
            f"- **{r['program']}** – *{r['match_pct']}* – {r['deadline']}  \n"
            f"  {r['notes']}  \n"
            f"  👉 [{r['link']}]({r['link']})"
        )
    st.divider()
    st.subheader("Generate Prefilled Grant Template (.txt)")
    sel = st.selectbox("Choose a program", grants["program"])
    gr = grants[grants["program"]==sel].iloc[0]
    top_src = bld.groupby("facility",as_index=False)["tco2e"].sum().sort_values("tco2e",ascending=False).iloc[0]["facility"]
    key_cat = gr["categories"].split(",")[0]
    template = f"""PROGRAM: {gr['program']}
Deadline: {gr['deadline']}
Match: {gr['match_pct']} (Max {gr['max_amount']})
Link: {gr['link']}

Project Summary:
The City of Waterloo aims to reduce emissions in {key_cat}, focusing on {top_src}.
Current corporate footprint ≈ {fmt(grand_total)} tCO₂e (Buildings {fmt(bld_total)}, Fleet {fmt(flt_total)}, Waste {fmt(wst_total)}).

Outcomes:
• Emissions reduction in priority sources (see Policy Scenarios)
• Cost savings from energy/fuel efficiency
• Readiness for regulatory and grant reporting
"""
    st.text_area("Preview", template, height=220)
    st.download_button("Download Template (.txt)", template.encode("utf-8"),
                       file_name="Grant_Template.txt", mime="text/plain")

# ================= Engagement (group or independent) ======
with tabs[3]:
    st.subheader("Stakeholder Engagement – Targeted Messages")

    audiences = st.multiselect(
        "Select audience(s)",
        ["Council","Residents","Businesses","City Staff"],
        default=["Council","Residents"]
    )

    def gen_msg(aud):
        base = (f"In 2025 (demo), Waterloo’s estimated corporate emissions ≈ {fmt(grand_total)} tCO₂e. "
                f"Top sources are Buildings and Fleet. We’re prioritizing retrofits, EV transition, and better diversion.")
        tone = {
            "Council":"Clear, action-focused update with funding angle.",
            "Residents":"Short, supportive tone with community benefits.",
            "Businesses":"Practical benefits and cost-savings emphasis.",
            "City Staff":"Operational clarity and next steps."
        }[aud]
        if USE_AI:
            try:
                prompt = (f"Write a two-sentence update for {aud}. Tone: {tone}. "
                          f"Include the tCO2e figure and mention retrofits/EV/diversion. "
                          f"Data context: {base}")
                out = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role":"user","content":prompt}],
                    temperature=0.2, max_tokens=110
                )
                return out.choices[0].message.content.strip()
            except Exception:
                return base + f" [AI unavailable]"
        else:
            return base

    for aud in audiences:
        st.markdown(f"**{aud}**")
        st.text_area(f"Message for {aud}", gen_msg(aud), height=120, key=f"msg_{aud}")

st.caption("Demo unless Pilot uploads used. All charts labeled in tCO₂e. Funding examples reflect 2025 programs.")
