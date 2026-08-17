import streamlit as st
import os
import sys
import numpy as np
import plotly.graph_objects as go

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

st.set_page_config(page_title="Enterprise PGx & Clinical Safety Engine", layout="wide", page_icon="🧬")

st.title("🧬 Enterprise Clinical Pharmacogenomics (PGx) & Universal Safety Engine")
st.markdown("**Tri-Domain Clinical Decision Support System:** Bioinformatics | Multi-Disease Dosage Rules | Machine Learning | Anatomy")

# Multi-Tab Architecture
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Patient PGx & Polypharmacy Dashboard", 
    "🏥 Universal Multi-Disease & Medication Assister", 
    "🤖 ML Novel Variant Predictor", 
    "📈 Pharmacokinetics Analytics"
])

ml_predictor = VariantImpactPredictor()

# --- TAB 1: PGX & POLYPHARMACY DASHBOARD ---
with tab1:
    st.sidebar.header("📋 Clinical & Lab Report Inputs")
    
    # 1. Optional Lab Report Scanner
    st.sidebar.subheader("📄 Medical Lab Report Scanner")
    report_file = st.sidebar.file_uploader("Upload Medical Lab Report (PDF / TXT)", type=["pdf", "txt"], key="lab_report_uploader")

    parsed_egfr = 90.0
    parsed_alt = 25.0

    if report_file is not None:
        report_temp_path = os.path.join("data", "raw_reports", report_file.name)
        os.makedirs(os.path.dirname(report_temp_path), exist_ok=True)
        with open(report_temp_path, "wb") as f:
            f.write(report_file.getbuffer())
            
        extracted_data = parse_medical_report(report_temp_path)
        st.sidebar.success("Lab report scanned successfully!")
        
        if extracted_data["egfr"] is not None:
            parsed_egfr = extracted_data["egfr"]
            st.sidebar.info(f"Auto-detected eGFR: **{parsed_egfr} mL/min**")
        if extracted_data["alt"] is not None:
            parsed_alt = extracted_data["alt"]
            st.sidebar.info(f"Auto-detected ALT: **{parsed_alt} U/L**")

    # 2. Medication Selection
    available_drugs = ["Clopidogrel", "Codeine", "Warfarin", "Simvastatin", "Fluorouracil", "Abacavir", "Other (Custom Tablet Name)"]
    selected_options = st.sidebar.multiselect(
        "Select Proposed Medication / Regimen",
        options=available_drugs,
        default=["Clopidogrel"],
        key="pgx_drug_select"
    )

    selected_drugs = []
    for drug in selected_options:
        if drug == "Other (Custom Tablet Name)":
            custom_drug_name = st.sidebar.text_input("Enter Custom Tablet Name:", value="Aspirin", key="custom_drug_in")
            if custom_drug_name.strip():
                selected_drugs.append(custom_drug_name.strip())
        else:
            selected_drugs.append(drug)

    # 3. Organ Clearance Parameters
    st.sidebar.subheader("🫀 Organ Clearance Parameters")
    egfr = st.sidebar.number_input("Kidney eGFR (mL/min/1.73m²)", min_value=0, max_value=150, value=int(parsed_egfr), key="pgx_egfr_in")
    alt = st.sidebar.number_input("Liver ALT (U/L)", min_value=0, max_value=500, value=int(parsed_alt), key="pgx_alt_in")

    # 4. Optional VCF File Upload
    st.sidebar.subheader("🧬 Genomic Profile (Optional)")
    uploaded_vcf = st.sidebar.file_uploader("Upload Patient VCF File", type=["vcf"], key="pgx_vcf_uploader")

    # Patient Genotype Resolver (VCF or Population Baseline)
    if uploaded_vcf is not None:
        vcf_path = os.path.join("data", "raw_vcf", uploaded_vcf.name)
        os.makedirs(os.path.dirname(vcf_path), exist_ok=True)
        with open(vcf_path, "wb") as f:
            f.write(uploaded_vcf.getbuffer())

        raw_variants = parse_vcf(vcf_path)
        phenotypes = map_patient_variants(raw_variants)
        st.success(f"Loaded genomic profile from **{uploaded_vcf.name}**.")
    else:
        phenotypes = [
            {"gene": "CYP2C19", "phenotype": "Normal Metabolizer"},
            {"gene": "CYP2D6", "phenotype": "Normal Metabolizer"},
            {"gene": "HLAB", "phenotype": "Normal Metabolizer"},
            {"gene": "SLCO1B1", "phenotype": "Normal Metabolizer"}
        ]
        st.info("ℹ️ No VCF uploaded. Evaluating using **General Population Baseline (Normal Metabolizer)** and Organ Clearance Vitals.")

    if len(selected_drugs) > 0:
        st.subheader("💊 Medication & Clinical Clearance Evaluations")
        
        for idx, drug in enumerate(selected_drugs):
            harmonized = harmonize_guidelines(drug, phenotypes)
            for h_idx, item in enumerate(harmonized):
                organ_eval = evaluate_organ_clearance(egfr, alt, item['risk_level'], drug)
                final_risk = organ_eval['final_risk_level']

                with st.expander(f"Tablet Evaluation: {drug} (Risk Level: {final_risk})", expanded=True):
                    if final_risk in ["High Risk", "Toxic Risk"]:
                        st.error(f"🚨 **RISK LEVEL: {final_risk.upper()}**")
                    elif final_risk == "Moderate Risk":
                        st.warning(f"⚠️ **RISK LEVEL: {final_risk.upper()}**")
                    else:
                        st.success("✅ **RISK LEVEL: SAFE / NORMAL METABOLISM**")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("##### 🧬 Genomic Assessment")
                        st.write(f"**Target Gene:** {item['gene']}")
                        st.write(f"**Assessed Phenotype:** {item['phenotype']}")
                        st.write(f"**CPIC Advice:** {item['cpic_recommendation']}")
                        st.write(f"**FDA Table Note:** {item['fda_recommendation']}")
                        if item['discrepancy_flag']:
                            st.info(f"💡 **Guideline Note:** {item['discrepancy_note']}")

                    with c2:
                        st.markdown("##### 🫀 Physiological Clearance & Dosage")
                        st.write(f"**Kidney eGFR:** {egfr} mL/min ({organ_eval['egfr_status']})")
                        st.write(f"**Liver ALT:** {alt} U/L ({organ_eval['alt_status']})")
                        st.write("**Anatomical Warnings:**")
                        for w in organ_eval['organ_warnings']:
                            st.caption(f"• {w}")

                        # Calculate Organ-Based Dosage Adjustment
                        dose_eval = calculate_dosage_adjustment(drug, egfr, alt, standard_dose_mg=100.0)
                        st.write(f"**Organ-Adjusted Dose:** **{dose_eval['recommended_dose_mg']} mg** (Standard: {dose_eval['standard_dose_mg']} mg)")

                # PDF Clinical Report Export Trigger
                vcf_filename_str = uploaded_vcf.name if uploaded_vcf else "Population_Baseline.vcf"
                pdf_filename = f"PGx_Report_{drug}_{idx}_{vcf_filename_str}.pdf"
                organ_eval['egfr_val'] = egfr
                organ_eval['alt_val'] = alt
                
                generate_pdf_report(pdf_filename, drug, vcf_filename_str, harmonized, organ_eval)
                
                if os.path.exists(pdf_filename):
                    with open(pdf_filename, "rb") as pdf_file:
                        st.download_button(
                            label=f"📄 Download Clinical PDF Report for {drug}",
                            data=pdf_file,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            key=f"download_btn_{idx}_{drug}_{h_idx}"
                        )

        # Polypharmacy Section
        if len(selected_drugs) > 1:
            st.divider()
            st.subheader("⚠️ Polypharmacy & Multi-Tablet Interactions")
            poly_results = analyze_polypharmacy(selected_drugs, phenotypes, {"egfr": egfr, "alt": alt})
            if poly_results:
                for poly in poly_results:
                    st.warning(f"**Interaction:** {poly['drug_pair']} | **Severity:** {poly['severity']}")
                    st.write(f"• **Mechanism:** {poly['mechanism']}")
                    st.write(f"• **Guidance:** {poly['clinical_guidance']}")
            else:
                st.info("No severe drug-drug interactions flagged in the rules matrix for this specific combination.")

# --- TAB 2: UNIVERSAL MULTI-DISEASE & MEDICATION ASSISTER ---
with tab2:
    st.subheader("🏥 Universal Multi-Disease Clinical & Dosage Assister")
    st.caption("Verifies treatment efficacy and dosage correctness across major medical conditions based on lab biomarkers.")

    col1, col2 = st.columns(2)

    with col1:
        disease_choice = st.selectbox(
            "Select Diagnosis / Condition", 
            ["Diabetes", "Hypertension", "Thyroid Disorders", "Hyperlipidemia", "Chronic Kidney Disease", "Asthma / COPD", "Heart Failure"],
            key="all_diseases_choice"
        )
        
        vitals_payload = {}
        
        # Render disease-specific inputs dynamically
        if disease_choice == "Diabetes":
            vitals_payload["fbs"] = st.number_input("Fasting Blood Sugar - FBS (mg/dL)", 0, 500, 150, key="diab_fbs")
            vitals_payload["ppbs"] = st.number_input("Postprandial Blood Sugar - PPBS (mg/dL)", 0, 600, 210, key="diab_ppbs")
            vitals_payload["hba1c"] = st.number_input("Glycated Hemoglobin - HbA1c (%)", 3.0, 20.0, 8.1, step=0.1, key="diab_a1c")
            med_options = ["Metformin", "Glimepiride", "Gliclazide", "Insulin"]
            
        elif disease_choice == "Hypertension":
            vitals_payload["systolic_bp"] = st.number_input("Systolic BP (mmHg)", 80, 240, 145, key="htn_sys")
            vitals_payload["diastolic_bp"] = st.number_input("Diastolic BP (mmHg)", 50, 140, 92, key="htn_dia")
            med_options = ["Amlodipine", "Telmisartan", "Lisinopril"]
            
        elif disease_choice == "Thyroid Disorders":
            vitals_payload["tsh"] = st.number_input("Serum TSH (mIU/L)", 0.0, 50.0, 6.8, step=0.1, key="thy_tsh")
            vitals_payload["free_t4"] = st.number_input("Free T4 (ng/dL)", 0.0, 10.0, 0.7, step=0.1, key="thy_t4")
            med_options = ["Levothyroxine", "Methimazole"]
            
        elif disease_choice == "Hyperlipidemia":
            vitals_payload["ldl_cholesterol"] = st.number_input("LDL Cholesterol (mg/dL)", 30, 300, 140, key="lip_ldl")
            vitals_payload["triglycerides"] = st.number_input("Triglycerides (mg/dL)", 30, 1000, 220, key="lip_trig")
            med_options = ["Atorvastatin", "Rosuvastatin", "Fenofibrate"]
            
        elif disease_choice == "Chronic Kidney Disease":
            vitals_payload["egfr"] = st.number_input("Kidney eGFR (mL/min/1.73m²)", 0, 150, 25, key="ckd_egfr")
            vitals_payload["uacr"] = st.number_input("Urine Albumin-to-Creatinine Ratio - UACR (mg/g)", 0, 3000, 150, key="ckd_uacr")
            med_options = ["Allopurinol", "Dapagliflozin"]
            
        elif disease_choice == "Asthma / COPD":
            vitals_payload["fev1_percent"] = st.number_input("FEV1 (% Predicted)", 0, 120, 65, key="resp_fev1")
            vitals_payload["peak_flow"] = st.number_input("Peak Expiratory Flow (L/min)", 0, 800, 250, key="resp_pef")
            med_options = ["Salbutamol / Albuterol", "Budenoside"]
            
        else:  # Heart Failure
            vitals_payload["ejection_fraction"] = st.number_input("Left Ventricular Ejection Fraction - LVEF (%)", 10, 75, 38, key="hf_ef")
            vitals_payload["bnp"] = st.number_input("BNP Biomarker (pg/mL)", 0, 5000, 450, key="hf_bnp")
            med_options = ["Furosemide", "Spironolactone"]

    with col2:
        selected_med = st.selectbox("Current Medication", med_options, key="all_med_choice")
        
        # Set realistic default dose based on drug
        def_dose = 1000.0 if selected_med == "Metformin" else (50.0 if selected_med == "Levothyroxine" else 10.0)
        current_dose_input = st.number_input("Current Prescribed Dosage (mg/mcg/Units)", 0.0, 3000.0, def_dose, key="all_dose_in")
        patient_egfr_val = st.number_input("Renal eGFR Vitals (mL/min)", 0, 150, 90, key="all_egfr_val")

    if st.button("Verify Medication Dosage Correctness", key="all_verify_btn"):
        res = evaluate_disease_management(
            disease_choice, selected_med, current_dose_input, vitals_payload, egfr=patient_egfr_val
        )
        
        st.divider()
        if res["dose_correct"]:
            st.success(f"✅ **STATUS: {res['status'].upper()}**")
        else:
            st.warning(f"⚠️ **STATUS: {res['status'].upper()}**")

        st.write(f"**Current Prescribed Dose:** {res['current_dose_mg']} mg/mcg/Units")
        st.write(f"**Recommended Adjusted Dose:** **{res['recommended_dose_mg']} mg/mcg/Units**")
        st.write("**Clinical Evaluations:**")
        for r in res["reasons"]:
            st.write(r)

# --- TAB 3: ML NOVEL VARIANT PREDICTOR ---
with tab3:
    st.subheader("🤖 Random Forest Functional Impact Predictor for Novel Variants")
    st.caption("Classifies unannotated genetic variants as Pathogenic (Loss-of-Function) or Tolerated using computational scores.")

    c_ml1, c_ml2 = st.columns(2)
    with c_ml1:
        cadd = st.slider("CADD Score (Phred Scale)", 0.0, 60.0, 32.5, key="cadd_slider")
        polyphen = st.slider("PolyPhen-2 Score", 0.0, 1.0, 0.88, key="polyphen_slider")
    with c_ml2:
        sift = st.slider("SIFT Score (Inverted: <0.05 = Harmful)", 0.0, 1.0, 0.02, key="sift_slider")
        phylop = st.slider("PhyloP Conservation Score", -2.0, 10.0, 6.5, key="phylop_slider")

    if st.button("Run ML Classification Model", key="run_ml_btn"):
        res = ml_predictor.predict_variant_impact(cadd, polyphen, sift, phylop)
        if res['is_loss_of_function']:
            st.error(f"**Predicted Impact:** {res['prediction']} (Confidence: {res['confidence']})")
        else:
            st.success(f"**Predicted Impact:** {res['prediction']} (Confidence: {res['confidence']})")

# --- TAB 4: PHARMACOKINETICS ANALYTICS ---
with tab4:
    st.subheader("📈 Dynamic Pharmacokinetic (PK) Concentration Curves")
    st.caption("Simulates plasma drug exposure over time based on patient organ clearance capacity.")

    time_hrs = np.linspace(0, 24, 100)
    ke_normal = 0.2
    ke_impaired = 0.08 if egfr < 60 or alt > 40 else 0.2

    conc_normal = 100 * (np.exp(-ke_normal * time_hrs) - np.exp(-1.0 * time_hrs))
    conc_patient = 100 * (np.exp(-ke_impaired * time_hrs) - np.exp(-1.0 * time_hrs))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=time_hrs, y=conc_normal, mode='lines', name='Normal Clearance Profile', line=dict(color='green', dash='dash')))
    fig.add_trace(go.Scatter(x=time_hrs, y=conc_patient, mode='lines', name='Current Patient Profile (Adjusted)', line=dict(color='red', width=3)))

    fig.update_layout(title="Plasma Concentration vs. Time Post-Dose", xaxis_title="Time (Hours)", yaxis_title="Plasma Concentration (ng/mL)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)