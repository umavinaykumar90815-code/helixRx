import streamlit as st
import os
import sys
import numpy as np
import plotly.graph_objects as go
from google import genai
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

# MUST be the first Streamlit command called in the script
st.set_page_config(
    page_title="HelixRx | Precision PGx & Clinical AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Global Styling
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
# LIVE GEMINI CLINICAL AI ASSISTANT (PERSISTENT MODAL)
# -------------------------------------------------------------
@st.dialog("💬 HelixRx Clinical AI Assistant", width="large")
def show_ai_assistant_dialog():
    st.caption("HelixRx Real-Time Precision AI. Ask any clinical, dosage, or genomic questions freely.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": "Hello! I am your HelixRx Clinical Assistant. Ask me anything about medications, genetic markers, renal/hepatic thresholds, or drug-drug interactions in your preferred language."
            }
        ]

    chat_container = st.container(height=380)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    user_prompt = st.chat_input("Type your question here...")
    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with chat_container:
            with st.chat_message("user"):
                st.write(user_prompt)

        system_instruction = (
            "You are HelixRx AI, an expert multilingual clinical pharmacogenomics (PGx) and medication safety assistant. "
            "Respond naturally in whatever language the user asks their question in (e.g., English, Telugu, Hindi, Spanish). "
            "Provide clear, clinically accurate answers regarding medications, dosages, organ clearance (eGFR, ALT), "
            "and genetic guidelines (CPIC, FDA). Keep explanations practical and easy to understand for patients, "
            "while maintaining strict medical accuracy. Always include a brief reminder to consult their healthcare provider."
        )

        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if not api_key:
                reply = "⚠️ API Key not configured. Please add `GEMINI_API_KEY` to your Streamlit Cloud Secrets."
            else:
                client = genai.Client(api_key=api_key)
                full_prompt = f"{system_instruction}\n\nUser Question: {user_prompt}"
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=full_prompt,
                )
                reply = response.text

        except Exception as e:
            reply = f"⚠️ Clinical engine connection error: {str(e)}"

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with chat_container:
            with st.chat_message("assistant"):
                st.write(reply)

# =============================================================
# 1. LOGIN GATEWAY (UNAUTHENTICATED VIEW)
# =============================================================
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

# =============================================================
# 2. AUTHENTICATED PORTALS
# =============================================================
else:
    # Sidebar Header & Profile Branding
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <h1 style="color: #00ADB5; margin-bottom: 0px;">🧬 HelixRx</h1>
                <p style="color: #888888; font-size: 0.85rem; margin-top: 0px;">
                    Pharmacogenomic Clinical Intelligence
                </p>
            </div>
            <hr style="margin-top: 5px; margin-bottom: 15px;">
            """,
            unsafe_allow_html=True
        )
        st.markdown(f"**Logged In:** `{st.session_state.user_name}`")
        st.markdown(f"**Active Portal:** `{st.session_state.user_role}`")
        
        if st.button("🚪 Log Out", use_container_width=True):
            logout()
            
        st.divider()

        # Conversational AI Assistant Trigger Button
        if st.button("💬 Open HelixRx AI Assistant", use_container_width=True):
            show_ai_assistant_dialog()

        st.divider()

    # =========================================================
    # A. PATIENT PORTAL (MULTI-DISEASE & MULTILINGUAL ASSISTER)
    # =========================================================
    if st.session_state.user_role == "Patient":
        selected_lang = st.sidebar.selectbox("🌐 Choose Language / భాష / भाषा", ["English", "Telugu", "Hindi", "Spanish"])

        TRANSLATIONS = {
            "English": {
                "portal_title": "Universal Multi-Disease & Medication Assister",
                "portal_sub": "Verify treatment safety, target ranges, and personalized dosage adjustments against your latest test reports.",
                "col1_title": "1️⃣ Select Disease & Enter Vitals",
                "disease_label": "Clinical Diagnosis",
                "col2_title": "2️⃣ Current Prescribed Medication",
                "med_label": "Current Prescribed Drug",
                "dose_label": "Current Prescribed Dosage",
                "egfr_label": "Patient eGFR Metric (mL/min, default: 90)",
                "eval_btn": "🔍 Evaluate Protocol & Dosage Efficacy",
                "results_header": "📊 Evaluation Assessment",
                "safe_badge": "✅ CURRENT DOSE IS OPTIMAL & SAFE",
                "warn_badge": "⚠️ ADJUSTMENT / TITRATION RECOMMENDED",
                "contra_badge": "⛔ CONTRAINDICATED / KIDNEY SAFETY WARNING",
                "curr_dose": "Current Dose:",
                "rec_dose": "Target-Adjusted Dose:",
                "details_title": "Clinical Evaluation Details:",
                "safety_note": "💡 **Patient Safety Note:** Please consult your healthcare provider prior to changing your prescribed dosage.",
                "explain_btn": "🗣️ Explain in Plain Language",
                "generating": "Generating patient explanation..."
            },
            "Telugu": {
                "portal_title": "సార్వత్రిక బహుళ-వ్యాధులు & ఔషధ సహాయకం",
                "portal_sub": "మీ తాజా పరీక్ష నివేదికలతో చికిత్స భద్రత మరియు సరైన మోతాదును ధృవీకరించండి.",
                "col1_title": "1️⃣ వ్యాధిని ఎంచుకుని వివరాలను నమోదు చేయండి",
                "disease_label": "క్లినికల్ రోగనిర్ధారణ",
                "col2_title": "2️⃣ ప్రస్తుత సూచించిన మందు",
                "med_label": "ప్రస్తుతం వాడుతున్న మందు",
                "dose_label": "ప్రస్తుత మోతాదు (Dosage)",
                "egfr_label": "రోగి eGFR విలువ (mL/min, సాధారణం: 90)",
                "eval_btn": "🔍 ప్రోటోకాల్ & మోతాదు సామర్థ్యాన్ని అంచనా వేయండి",
                "results_header": "📊 మూల్యాంకన ఫలితాలు",
                "safe_badge": "✅ ప్రస్తుత మోతాదు సురక్షితమైనది మరియు సరైనది",
                "warn_badge": "⚠️ మోతాదు సర్దుబాటు సిఫార్సు చేయబడింది",
                "contra_badge": "⛔ తీవ్రమైన ప్రమాదం / కిడ్నీ భద్రతా హెచ్చరిక",
                "curr_dose": "ప్రస్తుత మోతాదు:",
                "rec_dose": "సిఫార్సు చేసిన సరైన మోతాదు:",
                "details_title": "క్లినికల్ మూల్యాంకన వివరాలు:",
                "safety_note": "💡 **గమనిక:** మీ మోతాదును మార్చడానికి ముందు దయచేసి మీ వైద్యుడిని సంప్రదించండి.",
                "explain_btn": "🗣️ సులభమైన తెలుగులో వివరణ పొందండి",
                "generating": "తెలుగులో వివరణ రూపొందించబడుతోంది..."
            },
            "Hindi": {
                "portal_title": "सार्वभौमिक बहु-रोग और दवा सहायक",
                "portal_sub": "अपनी नवीनतम परीक्षण रिपोर्टों के विरुद्ध उपचार सुरक्षा और व्यक्तिगत खुराक समायोजन की जाँच करें।",
                "col1_title": "1️⃣ रोग चुनें और स्वास्थ्य विवरण दर्ज करें",
                "disease_label": "चिकित्सीय निदान (Diagnosis)",
                "col2_title": "2️⃣ वर्तमान निर्धारित दवा",
                "med_label": "वर्तमान निर्धारित दवा",
                "dose_label": "वर्तमान खुराक (Dosage)",
                "egfr_label": "मरीज का eGFR स्तर (mL/min, डिफ़ॉल्ट: 90)",
                "eval_btn": "🔍 प्रोटोकॉल और खुराक प्रभावशीलता का मूल्यांकन करें",
                "results_header": "📊 मूल्यांकन परिणाम",
                "safe_badge": "✅ वर्तमान खुराक इष्टतम और सुरक्षित है",
                "warn_badge": "⚠️ खुराक समायोजन की सिफारिश की गई है",
                "contra_badge": "⛔ गंभीर चेतावनी / किडनी सुरक्षा जोखिम",
                "curr_dose": "वर्तमान खुराक:",
                "rec_dose": "अनुशंसित समायोजित खुराक:",
                "details_title": "चिकित्सीय मूल्यांकन विवरण:",
                "safety_note": "💡 **सुरक्षा नोट:** कृपया अपनी निर्धारित खुराक बदलने से पहले अपने डॉक्टर से परामर्श लें।",
                "explain_btn": "🗣️ सरल हिंदी में स्पष्टीकरण प्राप्त करें",
                "generating": "हिंदी में विवरण तैयार किया जा रहा है..."
            },
            "Spanish": {
                "portal_title": "Asistente Universal de Enfermedades y Medicamentos",
                "portal_sub": "Verifique la seguridad del tratamiento y los ajustes de dosis personalizados con sus últimos análisis.",
                "col1_title": "1️⃣ Seleccione Enfermedad e Ingrese Parámetros",
                "disease_label": "Diagnóstico Clínico",
                "col2_title": "2️⃣ Medicamento Prescrito Actual",
                "med_label": "Medicamento Actual",
                "dose_label": "Dosis Actual Prescrita",
                "egfr_label": "Métrica eGFR del Paciente (mL/min, default: 90)",
                "eval_btn": "🔍 Evaluar Eficacia de Protocolo y Dosis",
                "results_header": "📊 Evaluación Clínica",
                "safe_badge": "✅ LA DOSIS ACTUAL ES ÓPTIMA Y SEGURA",
                "warn_badge": "⚠️ SE RECOMIENDA AJUSTE / TITULACIÓN",
                "contra_badge": "⛔ CONTRAINDICADO / ADVERTENCIA DE SEGURIDAD RENAL",
                "curr_dose": "Dosis Actual:",
                "rec_dose": "Dosis Recomendada Ajustada:",
                "details_title": "Detalles de la Evaluación Clínica:",
                "safety_note": "💡 **Nota:** Consulte a su proveedor de atención médica antes de cambiar su dosis.",
                "explain_btn": "🗣️ Explicar en Español Sencillo",
                "generating": "Generando explicación en español..."
            }
        }

        t = TRANSLATIONS[selected_lang]

        st.markdown(f"""
        <div class="header-banner">
            <h2 style="margin:0;">🏥 {t['portal_title']}</h2>
            <p style="margin:5px 0 0 0; opacity:0.9;">{t['portal_sub']}</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(t["col1_title"])
            condition = st.selectbox(
                t["disease_label"],
                [
                    "Diabetes", "Hypertension", "Thyroid Disorders", 
                    "Hyperlipidemia", "Chronic Kidney Disease", "Asthma / COPD", 
                    "Heart Failure", "Depression / Anxiety", "Gout / Hyperuricemia", 
                    "Atrial Fibrillation", "Rheumatoid Arthritis"
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
            elif condition == "Heart Failure":
                vitals_payload["ejection_fraction"] = st.number_input("Left Ventricular Ejection Fraction (%)", 10, 75, 38)
                vitals_payload["bnp"] = st.number_input("BNP Biomarker (pg/mL)", 0, 5000, 420)
                med_options = ["Furosemide", "Spironolactone"]
            elif condition == "Depression / Anxiety":
                vitals_payload["phq9"] = st.slider("PHQ-9 Depression Severity Score (0-27)", 0, 27, 14)
                vitals_payload["gad7"] = st.slider("GAD-7 Anxiety Score (0-21)", 0, 21, 10)
                med_options = ["Sertraline", "Escitalopram", "Venlafaxine"]
            elif condition == "Gout / Hyperuricemia":
                vitals_payload["uric_acid"] = st.number_input("Serum Uric Acid (mg/dL)", 2.0, 16.0, 8.4, step=0.1)
                vitals_payload["flares_per_year"] = st.number_input("Acute Attacks in Last 12 Mos", 0, 20, 3)
                med_options = ["Allopurinol", "Febuxostat", "Colchicine"]
            elif condition == "Atrial Fibrillation":
                vitals_payload["inr"] = st.number_input("International Normalized Ratio (INR)", 0.8, 6.0, 1.8, step=0.1)
                vitals_payload["cha2ds2_vasc"] = st.slider("CHA2DS2-VASc Stroke Risk Score", 0, 9, 3)
                med_options = ["Apixaban", "Rivaroxaban", "Warfarin"]
            else:  # Rheumatoid Arthritis
                vitals_payload["crp"] = st.number_input("C-Reactive Protein - CRP (mg/L)", 0.0, 100.0, 18.5, step=0.1)
                vitals_payload["esr"] = st.number_input("Erythrocyte Sedimentation Rate - ESR (mm/hr)", 0, 120, 35)
                med_options = ["Methotrexate", "Hydroxychloroquine"]

        with col2:
            st.subheader(t["col2_title"])
            selected_med = st.selectbox(t["med_label"], med_options, key="pat_med_choice")
            
            default_map = {
                "Metformin": 1000.0, "Glimepiride": 2.0, "Gliclazide": 80.0, "Insulin": 20.0,
                "Amlodipine": 5.0, "Telmisartan": 40.0, "Lisinopril": 10.0,
                "Levothyroxine": 50.0, "Methimazole": 10.0,
                "Atorvastatin": 20.0, "Rosuvastatin": 10.0, "Fenofibrate": 145.0,
                "Allopurinol": 100.0, "Febuxostat": 40.0, "Colchicine": 0.5,
                "Dapagliflozin": 10.0, "Salbutamol / Albuterol": 100.0, "Budenoside": 200.0,
                "Furosemide": 40.0, "Spironolactone": 25.0,
                "Sertraline": 50.0, "Escitalopram": 10.0, "Venlafaxine": 75.0,
                "Apixaban": 5.0, "Rivaroxaban": 20.0, "Warfarin": 5.0,
                "Methotrexate": 15.0, "Hydroxychloroquine": 200.0
            }
            default_val = default_map.get(selected_med, 10.0)
            current_dose_input = st.number_input(t["dose_label"], 0.0, 3000.0, default_val)
            patient_egfr_val = st.number_input(t["egfr_label"], 0, 150, 90)

        st.write("---")
        if st.button(t["eval_btn"], type="primary"):
            res = evaluate_disease_management(
                condition, selected_med, current_dose_input, vitals_payload, egfr=patient_egfr_val
            )

            st.session_state.last_patient_res = res
            st.session_state.last_patient_condition = condition
            st.session_state.last_patient_med = selected_med

        if "last_patient_res" in st.session_state:
            res = st.session_state.last_patient_res
            st.subheader(t["results_header"])
            if res["dose_correct"]:
                st.markdown(f'<span class="badge-green">{t["safe_badge"]}</span>', unsafe_allow_html=True)
            else:
                if "Renal" in res["status"] or "Contraindicated" in res["status"]:
                    st.markdown(f'<span class="badge-red">{t["contra_badge"]}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="badge-yellow">{t["warn_badge"]}</span>', unsafe_allow_html=True)

            r1, r2 = st.columns(2)
            with r1:
                st.write(f"**{t['curr_dose']}** {res['current_dose_mg']} mg/mcg/Units")
                st.write(f"**{t['rec_dose']}** **{res['recommended_dose_mg']} mg/mcg/Units**")
            with r2:
                st.write(f"**{t['details_title']}**")
                for r in res["reasons"]:
                    st.write(r)

            st.info(t["safety_note"])

            # Multilingual Clinical Explanation via Gemini
            if st.button(t["explain_btn"]):
                with st.spinner(t["generating"]):
                    try:
                        api_key = st.secrets.get("GEMINI_API_KEY", "")
                        if api_key:
                            client = genai.Client(api_key=api_key)
                            explain_prompt = f"""
                            You are a friendly, compassionate clinical doctor explaining a test evaluation directly to a patient.
                            Explain this clinical assessment result clearly in {selected_lang}.
                            Avoid dense medical jargon. Use simple, conversational words.

                            Details:
                            - Diagnosis / Condition: {st.session_state.last_patient_condition}
                            - Medication: {st.session_state.last_patient_med}
                            - Current Dose: {res['current_dose_mg']} mg/mcg/Units
                            - Recommended Dose: {res['recommended_dose_mg']} mg/mcg/Units
                            - Clinical Findings: {' '.join(res['reasons'])}

                            Provide a 3-4 sentence reassurance and instructions on what they should ask their doctor at their next appointment.
                            """
                            exp_res = client.models.generate_content(
                                model="gemini-3.6-flash",
                                contents=explain_prompt
                            )
                            st.success(exp_res.text)
                        else:
                            st.warning("GEMINI_API_KEY not configured for dynamic explanations.")
                    except Exception as e:
                        st.error(f"Explanation engine error: {str(e)}")

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

        # Sidebar Ingestion for Clinicians
        with st.sidebar:
            st.header("📥 Diagnostic & Genomic Ingestion")
            report_file = st.file_uploader("Upload Lab Report (PDF / TXT)", type=["pdf", "txt"], key="c_pdf_up")

            parsed_egfr, parsed_alt = 90.0, 25.0
            if report_file is not None:
                report_temp_path = os.path.join("data", "raw_reports", report_file.name)
                os.makedirs(os.path.dirname(report_temp_path), exist_ok=True)
                with open(report_temp_path, "wb") as f:
                    f.write(report_file.getbuffer())
                extracted_data = parse_medical_report(report_temp_path)
                if extracted_data.get("egfr") is not None: 
                    parsed_egfr = extracted_data["egfr"]
                if extracted_data.get("alt") is not None: 
                    parsed_alt = extracted_data["alt"]
                st.success("Lab file scanned.")

            available_drugs = [
                "Clopidogrel", "Codeine", "Warfarin", "Simvastatin", 
                "Fluorouracil", "Abacavir", "Metformin", "Atorvastatin", "Other (Custom Tablet Name)"
            ]
            selected_options = st.multiselect(
                "Select Active Prescription(s)",
                options=available_drugs,
                default=["Clopidogrel"],
                key="c_drug_select"
            )

            selected_drugs = []
            for drug in selected_options:
                if drug == "Other (Custom Tablet Name)":
                    custom_drug_name = st.text_input("Enter Custom Drug Name:", value="Aspirin", key="c_custom_drug")
                    if custom_drug_name.strip():
                        selected_drugs.append(custom_drug_name.strip())
                else:
                    selected_drugs.append(drug)

            egfr = st.number_input("Kidney eGFR (mL/min/1.73m²)", 0, 150, int(parsed_egfr), key="c_egfr_val")
            alt = st.number_input("Liver ALT Transaminase (U/L)", 0, 500, int(parsed_alt), key="c_alt_val")
            uploaded_vcf = st.file_uploader("Upload Patient Genomic Sequence (.VCF)", type=["vcf"], key="c_vcf_up")

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

                        # PDF Report Generation
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