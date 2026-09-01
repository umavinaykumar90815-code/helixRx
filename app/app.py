import streamlit as st
import os
import sys
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.vcf_parser import parse_vcf
from engine.phenotype_mapper import map_patient_variants
from engine.cpic_fda_harmonizer import harmonize_guidelines
from engine.organ_clearance import evaluate_organ_clearance
from engine.drug_interaction import analyze_polypharmacy
from engine.ml_predictor import VariantImpactPredictor
from engine.report_parser import parse_medical_report
from engine.dosage_engine import calculate_dosage_adjustment
from engine.universal_clinical_engine import evaluate_disease_management
from utils import generate_pdf_report

# Page Configuration
st.set_page_config(
    page_title="HelixRx | Dual Gateway Decision Platform",
    layout="wide",
    page_icon="🧬",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark-Mode & Light-Mode Compatible)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    
    .header-banner {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        padding: 20px 26px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .badge-green {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 16px;
        display: inline-block;
        border: 1px solid #10B981;
    }
    .badge-yellow {
        background-color: rgba(245, 158, 11, 0.15);
        color: #F59E0B;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 16px;
        display: inline-block;
        border: 1px solid #F59E0B;
    }
    .badge-red {
        background-color: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 16px;
        display: inline-block;
        border: 1px solid #EF4444;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SESSION STATE & AUTHENTICATION
# -------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

DOCTOR_LOGINS = {"doctor@helix.org": "doctor123", "admin": "admin123"}
PATIENT_LOGINS = {"patient@gmail.com": "patient123", "user1": "12345"}

def login(role, username):
    st.session_state.authenticated = True
    st.session_state.user_role = role
    st.session_state.user_name = username

def logout():
    st.session_state.authenticated = False
    st.session_state.user_role = None
    st.session_state.user_name = ""
    st.rerun()

# -------------------------------------------------------------
# 1. LOGIN GATEWAY (UNAUTHENTICATED VIEW)
# -------------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown('<h1 style="text-align:center;">🧬 Clinical Pharmacogenomics (PGx) Safety Engine</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#9CA3AF;">Precision Decision Support System • Genomics • Organ Clearance • Multi-Disease Protocols</p>', unsafe_allow_html=True)

    _, mid_col, _ = st.columns([1, 1.8, 1])
    with mid_col:
        with st.container(border=True):
            login_mode = st.radio("Choose Portal Access Type:", ["👤 Patient / Personal Gateway", "🧑‍⚕️ Clinician & Hospital Gateway"], horizontal=True)
            st.write("---")

            if "Patient" in login_mode:
                st.markdown("#### **Patient Login**")
                st.caption("Access the Universal Multi-Disease & Medication Assister.")
                p_id = st.text_input("Patient ID / Email", value="patient@gmail.com")
                p_pw = st.text_input("Password", type="password", value="patient123")
                if st.button("Enter Patient Gateway", type="primary", use_container_width=True):
                    if p_id in PATIENT_LOGINS and PATIENT_LOGINS[p_id] == p_pw:
                        login("Patient", p_id)
                        st.rerun()
                    else:
                        st.error("Invalid credentials. (Demo: `patient@gmail.com` / `patient123`)")
            else:
                st.markdown("#### **Clinician & Hospital Login**")
                st.caption("Access Genomic VCF parsers, CPIC/FDA harmonization, PK curves, and ML predictors.")
                c_id = st.text_input("Physician ID / Email", value="doctor@helix.org")
                c_pw = st.text_input("Password", type="password", value="doctor123")
                if st.button("Authorize Clinician Session", type="primary", use_container_width=True):
                    if c_id in DOCTOR_LOGINS and DOCTOR_LOGINS[c_id] == c_pw:
                        login("Clinician", c_id)
                        st.rerun()
                    else:
                        st.error("Invalid credentials. (Demo: `doctor@helix.org` / `doctor123`)")

# -------------------------------------------------------------
# 2. AUTHENTICATED PORTALS
# -------------------------------------------------------------
else:
    # Sidebar Profile & Session Controls
    st.sidebar.markdown(f"**Logged In:** `{st.session_state.user_name}`")
    st.sidebar.markdown(f"**Active Portal:** `{st.session_state.user_role}`")
    if st.sidebar.button("🚪 Log Out", use_container_width=True):
        logout()
    st.sidebar.divider()

    # =========================================================
    # A. PATIENT PORTAL (ONLY MULTI-DISEASE & MEDICATION ASSISTER)
    # =========================================================
    if st.session_state.user_role == "Patient":
        st.markdown("""
        <div class="header-banner">
            <h2 style="margin:0;">🏥 Universal Multi-Disease & Medication Assister</h2>
            <p style="margin:5px 0 0 0; opacity:0.9;">Verify treatment safety, target ranges, and personalized dosage adjustments against your latest test reports.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("1️⃣ Select Disease & Enter Vitals")
            condition = st.selectbox(
                "Clinical Diagnosis",
                [
                    "Diabetes", "Hypertension", "Thyroid Disorders", 
                    "Hyperlipidemia", "Chronic Kidney Disease", "Asthma / COPD", "Heart Failure"
                ],
                key="pat_disease_sel"
            )

            vitals_payload = {}
            if condition == "Diabetes":
                vitals_payload["fbs"] = st.number_input("Fasting Blood Sugar - FBS (mg/dL)", 0, 500, 145)
                vitals_payload["ppbs"] = st.number_input("Postprandial Blood Sugar - PPBS (mg/dL)", 0, 600, 205)
                vitals_payload["hba1c"] = st.number_input("Glycated Hemoglobin - HbA1c (%)", 3.0, 20.0, 7.8, step=0.1)
                med_options = ["Metformin", "Glimepiride", "Gliclazide", "Insulin"]
            elif condition == "Hypertension":
                vitals_payload["systolic_bp"] = st.number_input("Systolic Blood Pressure (mmHg)", 80, 240, 142)
                vitals_payload["diastolic_bp"] = st.number_input("Diastolic Blood Pressure (mmHg)", 50, 140, 92)
                med_options = ["Amlodipine", "Telmisartan", "Lisinopril"]
            elif condition == "Thyroid Disorders":
                vitals_payload["tsh"] = st.number_input("Thyroid Stimulating Hormone - TSH (mIU/L)", 0.0, 50.0, 6.5, step=0.1)
                vitals_payload["free_t4"] = st.number_input("Free T4 (ng/dL)", 0.0, 10.0, 0.75, step=0.1)
                med_options = ["Levothyroxine", "Methimazole"]
            elif condition == "Hyperlipidemia":
                vitals_payload["ldl_cholesterol"] = st.number_input("LDL Cholesterol (mg/dL)", 30, 300, 140)
                vitals_payload["triglycerides"] = st.number_input("Triglycerides (mg/dL)", 30, 1000, 210)
                med_options = ["Atorvastatin", "Rosuvastatin", "Fenofibrate"]
            elif condition == "Chronic Kidney Disease":
                vitals_payload["egfr"] = st.number_input("Kidney eGFR (mL/min/1.73m²)", 0, 150, 28)
                vitals_payload["uacr"] = st.number_input("Urine Albumin-to-Creatinine Ratio - UACR (mg/g)", 0, 3000, 140)
                med_options = ["Allopurinol", "Dapagliflozin"]
            elif condition == "Asthma / COPD":
                vitals_payload["fev1_percent"] = st.number_input("FEV1 (% Predicted)", 0, 120, 65)
                vitals_payload["peak_flow"] = st.number_input("Peak Expiratory Flow (L/min)", 0, 800, 260)
                med_options = ["Salbutamol / Albuterol", "Budenoside"]
            else:  # Heart Failure
                vitals_payload["ejection_fraction"] = st.number_input("Left Ventricular Ejection Fraction (%)", 10, 75, 38)
                vitals_payload["bnp"] = st.number_input("BNP Biomarker (pg/mL)", 0, 5000, 420)
                med_options = ["Furosemide", "Spironolactone"]

        with col2:
            st.subheader("2️⃣ Current Prescribed Medication")
            selected_med = st.selectbox("Current Prescribed Drug", med_options, key="pat_med_choice")
            default_dose = 1000.0 if selected_med == "Metformin" else (50.0 if selected_med == "Levothyroxine" else 10.0)
            current_dose_input = st.number_input("Current Prescribed Dosage", 0.0, 3000.0, default_dose)
            patient_egfr_val = st.number_input("Patient eGFR Metric (mL/min, default: 90)", 0, 150, 90)

        st.write("---")
        if st.button("🔍 Evaluate Protocol & Dosage Efficacy", type="primary"):
            res = evaluate_disease_management(
                condition, selected_med, current_dose_input, vitals_payload, egfr=patient_egfr_val
            )

            st.subheader("📊 Evaluation Assessment")
            if res["dose_correct"]:
                st.markdown('<span class="badge-green">✅ CURRENT DOSE IS OPTIMAL & SAFE</span>', unsafe_allow_html=True)
            else:
                if "Renal" in res["status"] or "Contraindicated" in res["status"]:
                    st.markdown('<span class="badge-red">⛔ CONTRAINDICATED / KIDNEY SAFETY WARNING</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge-yellow">⚠️ ADJUSTMENT / TITRATION RECOMMENDED</span>', unsafe_allow_html=True)

            r1, r2 = st.columns(2)
            with r1:
                st.write(f"**Current Dose:** {res['current_dose_mg']} mg/mcg/Units")
                st.write(f"**Target-Adjusted Dose:** **{res['recommended_dose_mg']} mg/mcg/Units**")
            with r2:
                st.write("**Clinical Evaluation Details:**")
                for r in res["reasons"]:
                    st.write(r)

            st.info("💡 **Patient Safety Note:** Please consult your healthcare provider prior to changing your prescribed dosage.")

    # =========================================================
    # B. CLINICIAN & HOSPITAL GATEWAY (ALL OTHER ENGINES)
    # =========================================================
    else:
        st.markdown("""
        <div class="header-banner" style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);">
            <h2 style="margin:0;">🧑‍⚕️ Clinical Pharmacogenomics (PGx) Safety Engine</h2>
            <p style="margin:5px 0 0 0; opacity:0.8;">VCF Genomic Parser • CPIC/FDA Harmonization • Organ Clearance Filters • Pharmacokinetics</p>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Patient PGx & Polypharmacy", 
            "🤖 ML Novel Variant Predictor", 
            "📈 Dynamic PK Concentration Curves",
            "📑 Clinical Audit & EHR Summary"
        ])

        ml_predictor = VariantImpactPredictor()

        # Sidebar Ingestion for Doctors
        st.sidebar.header("📥 Diagnostic & Genomic Ingestion")
        report_file = st.sidebar.file_uploader("Upload Lab Report (PDF / TXT)", type=["pdf", "txt"], key="c_pdf_up")

        parsed_egfr, parsed_alt = 90.0, 25.0
        if report_file is not None:
            report_temp_path = os.path.join("data", "raw_reports", report_file.name)
            os.makedirs(os.path.dirname(report_temp_path), exist_ok=True)
            with open(report_temp_path, "wb") as f:
                f.write(report_file.getbuffer())
            extracted_data = parse_medical_report(report_temp_path)
            if extracted_data.get("egfr") is not None: parsed_egfr = extracted_data["egfr"]
            if extracted_data.get("alt") is not None: parsed_alt = extracted_data["alt"]
            st.sidebar.success("Lab file scanned.")

        available_drugs = [
            "Clopidogrel", "Codeine", "Warfarin", "Simvastatin", 
            "Fluorouracil", "Abacavir", "Metformin", "Atorvastatin", "Other (Custom Tablet Name)"
        ]
        selected_options = st.sidebar.multiselect(
            "Select Active Prescription(s)",
            options=available_drugs,
            default=["Clopidogrel"],
            key="c_drug_select"
        )

        selected_drugs = []
        for drug in selected_options:
            if drug == "Other (Custom Tablet Name)":
                custom_drug_name = st.sidebar.text_input("Enter Custom Drug Name:", value="Aspirin", key="c_custom_drug")
                if custom_drug_name.strip():
                    selected_drugs.append(custom_drug_name.strip())
            else:
                selected_drugs.append(drug)

        egfr = st.sidebar.number_input("Kidney eGFR (mL/min/1.73m²)", 0, 150, int(parsed_egfr), key="c_egfr_val")
        alt = st.sidebar.number_input("Liver ALT Transaminase (U/L)", 0, 500, int(parsed_alt), key="c_alt_val")
        uploaded_vcf = st.sidebar.file_uploader("Upload Patient Genomic Sequence (.VCF)", type=["vcf"], key="c_vcf_up")

        # Genomic Resolution
        if uploaded_vcf is not None:
            vcf_path = os.path.join("data", "raw_vcf", uploaded_vcf.name)
            os.makedirs(os.path.dirname(vcf_path), exist_ok=True)
            with open(vcf_path, "wb") as f:
                f.write(uploaded_vcf.getbuffer())
            raw_variants = parse_vcf(vcf_path)
            phenotypes = map_patient_variants(raw_variants)
            st.sidebar.success(f"Loaded VCF: {uploaded_vcf.name}")
        else:
            phenotypes = [
                {"gene": "CYP2C19", "phenotype": "Normal Metabolizer"},
                {"gene": "CYP2D6", "phenotype": "Normal Metabolizer"},
                {"gene": "HLAB", "phenotype": "Normal Metabolizer"},
                {"gene": "SLCO1B1", "phenotype": "Normal Metabolizer"}
            ]

        # Tab 1: PGx & Polypharmacy
        with tab1:
            st.subheader("📋 Precision Prescribing Evaluations")
            if not selected_drugs:
                st.info("Select one or more active prescriptions from the sidebar.")
            else:
                for idx, drug in enumerate(selected_drugs):
                    harmonized = harmonize_guidelines(drug, phenotypes)
                    for h_idx, item in enumerate(harmonized):
                        organ_eval = evaluate_organ_clearance(egfr, alt, item['risk_level'], drug)
                        final_risk = organ_eval['final_risk_level']
                        dose_eval = calculate_dosage_adjustment(drug, egfr, alt, standard_dose_mg=100.0)

                        badge_html = '<span class="badge-green">🟢 SAFE TO PRESCRIBE</span>'
                        if final_risk in ["High Risk", "Toxic Risk"]:
                            badge_html = '<span class="badge-red">🔴 HIGH RISK / CONTRAINDICATED</span>'
                        elif final_risk == "Moderate Risk":
                            badge_html = '<span class="badge-yellow">🟡 CAUTION / DOSE ADJUSTMENT REQUIRED</span>'

                        with st.expander(f"{drug} (Risk: {final_risk})", expanded=True):
                            st.markdown(badge_html, unsafe_allow_html=True)
                            c1, c2 = st.columns(2)
                            with c1:
                                st.markdown("##### 🧬 Pharmacogenetic Profile")
                                st.write(f"**Target Pharmacogene:** `{item['gene']}`")
                                st.write(f"**Assigned Phenotype:** **{item['phenotype']}**")
                                st.write(f"**CPIC Recommendation:** {item['cpic_recommendation']}")
                                st.write(f"**FDA Labeling:** {item['fda_recommendation']}")
                                if item['discrepancy_flag']:
                                    st.warning(f"⚠️ **Guideline Discrepancy:** {item['discrepancy_note']}")

                            with c2:
                                st.markdown("##### 🫀 Organ Clearance & Dosage")
                                st.write(f"**Renal Status:** eGFR {egfr} mL/min (`{organ_eval['egfr_status']}`)")
                                st.write(f"**Hepatic Status:** ALT {alt} U/L (`{organ_eval['alt_status']}`)")
                                st.write(f"**Standard Baseline Dose:** {dose_eval['standard_dose_mg']} mg")
                                st.write(f"**Recommended Adjusted Dose:** **{dose_eval['recommended_dose_mg']} mg**")
                                for w in organ_eval['organ_warnings']:
                                    st.caption(f"• {w}")

                        # PDF Report Download
                        vcf_name = uploaded_vcf.name if uploaded_vcf else "Population_Baseline.vcf"
                        pdf_filename = f"Clinical_PGx_Report_{drug}_{idx}.pdf"
                        organ_eval['egfr_val'] = egfr
                        organ_eval['alt_val'] = alt
                        generate_pdf_report(pdf_filename, drug, vcf_name, harmonized, organ_eval)
                        if os.path.exists(pdf_filename):
                            with open(pdf_filename, "rb") as pdf_file:
                                st.download_button(
                                    label=f"📥 Download Clinical PDF Summary for {drug}",
                                    data=pdf_file,
                                    file_name=pdf_filename,
                                    mime="application/pdf",
                                    key=f"dl_btn_{idx}_{drug}_{h_idx}"
                                )

                # Polypharmacy Checks
                if len(selected_drugs) > 1:
                    st.divider()
                    st.subheader("⚠️ Polypharmacy & Drug-Drug Interactions")
                    poly_results = analyze_polypharmacy(selected_drugs, phenotypes, {"egfr": egfr, "alt": alt})
                    if poly_results:
                        for poly in poly_results:
                            st.error(f"**Interaction Flagged:** {poly['drug_pair']} | **Severity:** {poly['severity']}")
                            st.write(f"• **Pharmacological Mechanism:** {poly['mechanism']}")
                            st.write(f"• **Recommended Action:** {poly['clinical_guidance']}")
                    else:
                        st.success("✅ No critical competitive enzymatic CYP450 interactions detected.")

        # Tab 2: ML Variant Classifier
        with tab2:
            st.subheader("🤖 Random Forest Functional Impact Predictor")
            st.caption("Classifies unannotated, novel genomic variants as Pathogenic (Loss-of-Function) or Tolerated.")

            c_ml1, c_ml2 = st.columns(2)
            with c_ml1:
                cadd = st.slider("CADD Phred Score (Deleteriousness)", 0.0, 60.0, 34.0, key="cadd_val")
                polyphen = st.slider("PolyPhen-2 Structural Impact Score", 0.0, 1.0, 0.91, key="polyphen_val")
            with c_ml2:
                sift = st.slider("SIFT Score (<0.05 indicates deleterious)", 0.0, 1.0, 0.01, key="sift_val")
                phylop = st.slider("PhyloP Evolutionary Conservation Score", -2.0, 10.0, 7.2, key="phylop_val")

            if st.button("Execute Variant Impact Classification", key="btn_run_ml"):
                res = ml_predictor.predict_variant_impact(cadd, polyphen, sift, phylop)
                if res['is_loss_of_function']:
                    st.error(f"🚨 **Prediction:** {res['prediction']} (Confidence: {res['confidence']})")
                    st.write("• **Clinical Implication:** High likelihood of compromised enzymatic catalytic activity.")
                else:
                    st.success(f"✅ **Prediction:** {res['prediction']} (Confidence: {res['confidence']})")
                    st.write("• **Clinical Implication:** Variant predicted to have benign or tolerated functional impact.")

        # Tab 3: Dynamic PK Curves
        with tab3:
            st.subheader("📈 Dynamic Pharmacokinetic (PK) Concentration Modeling")
            st.caption("One-compartment oral absorption and elimination curve adjusted for organ impairment.")

            time_hrs = np.linspace(0, 24, 150)
            ke_normal = 0.22
            ke_patient = 0.08 if egfr < 60 or alt > 40 else 0.22

            conc_normal = 100 * (np.exp(-ke_normal * time_hrs) - np.exp(-1.2 * time_hrs))
            conc_patient = 100 * (np.exp(-ke_patient * time_hrs) - np.exp(-1.2 * time_hrs))

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=time_hrs, y=conc_normal, mode='lines', name='Standard Population Profile', line=dict(color='#10B981', width=2, dash='dash')))
            fig.add_trace(go.Scatter(x=time_hrs, y=conc_patient, mode='lines', name='Patient Specific Profile (Organ-Adjusted)', line=dict(color='#EF4444', width=3)))

            fig.add_hline(y=75, line_dash="dot", line_color="orange", annotation_text="Minimum Toxic Concentration (MTC)")
            fig.add_hline(y=20, line_dash="dot", line_color="cyan", annotation_text="Minimum Effective Concentration (MEC)")

            fig.update_layout(
                xaxis_title="Time Post-Dose (Hours)",
                yaxis_title="Plasma Drug Concentration (ng/mL)",
                template="plotly_white",
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tab 4: EHR Clinical Audit Trail
        with tab4:
            st.subheader("📑 Clinical Audit Trail & EHR Summary")
            st.caption("HL7-FHIR structured summary of the patient's precision pharmacogenomic assessment.")

            summary_text = f"""======================================================================
CLINICAL PHARMACOGENOMICS DECISION SUPPORT RECORD
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
======================================================================
PATIENT ORGAN VITALS:
- eGFR: {egfr} mL/min/1.73m2 (Status: {'Adequate' if egfr >= 60 else 'Impaired'})
- ALT:  {alt} U/L (Status: {'Normal' if alt <= 40 else 'Elevated'})

GENOMIC PROFILE:
- VCF File: {'Uploaded Genomic Sequence' if uploaded_vcf else 'Population Wild-Type Baseline'}

PRESCRIBED MEDICATIONS EVALUATED:
{', '.join(selected_drugs) if selected_drugs else 'None selected'}

REGULATORY GUIDELINE HARMONIZATION:
Harmonized CPIC Level A/B Guidelines with FDA Table of Pharmacogenetic Associations.
======================================================================
"""
            st.code(summary_text, language="text")
            st.download_button(
                "📥 Download Official Clinical Audit Trail",
                data=summary_text,
                file_name="Clinical_PGx_Record.txt",
                mime="text/plain"
            )