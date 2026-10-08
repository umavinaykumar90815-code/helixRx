import streamlit as st
import os
import sys
import time
import numpy as np
import plotly.graph_objects as go
from google import genai
from datetime import datetime
from PIL import Image

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.vcf_parser import parse_vcf
from engine.phenotype_mapper import map_patient_variants
from engine.cpic_fda_harmonizer import harmonize_guidelines
from engine.organ_clearance import evaluate_organ_clearance
from engine.drug_interaction import analyze_polypharmacy
from engine.ml_predictor import VariantImpactPredictor
from engine.report_parser import parse_medical_report, analyze_prescription_and_report_images
from engine.dosage_engine import calculate_dosage_adjustment
from engine.universal_clinical_engine import evaluate_disease_management, generate_meal_titration_instruction
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

    .tutorial-pointer {
        background: linear-gradient(90deg, #F59E0B 0%, #D97706 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 8px;
        box-shadow: 0 0 12px rgba(245, 158, 11, 0.6);
        animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.015); }
        100% { transform: scale(1); }
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# MULTI-MODEL FALLBACK CALLER (PROTECTS AGAINST 503 / 404 / 429)
# -------------------------------------------------------------
def call_gemini_with_fallback(client, contents, system_instruction=None):
    """
    Attempts model generation with automated fallback across available models
    to handle 503 (temporary high demand) and 429/404 server spikes.
    """
    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3.8-flash"
    ]

    last_error = None
    for model_name in candidate_models:
        try:
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config if config else None
            )
            if response and response.text:
                return response.text
        except Exception as e:
            err_str = str(e)
            last_error = e
            if "503" in err_str or "UNAVAILABLE" in err_str or "404" in err_str or "429" in err_str:
                time.sleep(0.4)
                continue
            else:
                break

    raise last_error if last_error else RuntimeError("AI generation service is momentarily busy. Please try again.")

# -------------------------------------------------------------
# SESSION STATE, QUERY PARAMETERS & VILLAGE MODE
# -------------------------------------------------------------
query_params = st.query_params
is_village_mode = query_params.get("mode") == "village"

if "authenticated" not in st.session_state:
    if is_village_mode:
        st.session_state.authenticated = True
        st.session_state.user_role = "Patient"
        st.session_state.user_name = "Community Patient / Health Camp"
    else:
        st.session_state.authenticated = False
        st.session_state.user_role = None
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
    if "scanned_data" in st.session_state:
        del st.session_state["scanned_data"]
    if "last_patient_batch" in st.session_state:
        del st.session_state["last_patient_batch"]
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
                "content": "Hello! I am your HelixRx Clinical Assistant. Ask me anything about medications, dosages, meal schedules, renal/hepatic thresholds, or drug interactions in your preferred language."
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
            "Respond naturally in whatever language the user asks their question in (e.g., English, Telugu, Hindi, Swahili). "
            "Provide clear, clinically accurate answers regarding medications, dosages, meal administration timing (Breakfast, Lunch, Dinner), "
            "organ clearance (eGFR, ALT), and genetic guidelines (CPIC, FDA). Keep explanations practical and easy to understand for patients, "
            "while maintaining strict medical accuracy. Always include a brief reminder to consult their healthcare provider."
        )

        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if not api_key:
                reply = "⚠️ API Key not configured. Please add `GEMINI_API_KEY` to your Streamlit Cloud Secrets."
            else:
                client = genai.Client(api_key=api_key)
                reply = call_gemini_with_fallback(client, user_prompt, system_instruction=system_instruction)

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
        
        if is_village_mode:
            st.info("🏕️ **Village Camp / QR Direct Mode Active**")
        
        if st.button("🚪 Log Out", use_container_width=True):
            logout()
            
        st.divider()

        # Conversational AI Assistant Trigger Button
        if st.button("💬 Open HelixRx AI Assistant", use_container_width=True):
            show_ai_assistant_dialog()

        st.divider()

    # =========================================================
    # A. PATIENT PORTAL (CAMERA OCR + MULTI-DRUG PILL BOX SCHEDULE)
    # =========================================================
    if st.session_state.user_role == "Patient":
        default_lang_idx = 1 if is_village_mode else 0  # Default to Telugu if opened via village QR
        selected_lang = st.sidebar.selectbox(
            "🌐 Choose Language / భాష ఎంచుకోండి", 
            ["English", "Telugu", "Hindi", "Swahili (Kiswahili)"],
            index=default_lang_idx
        )

        if "tutorial_active" not in st.session_state:
            st.session_state.tutorial_active = False
        if "tutorial_step" not in st.session_state:
            st.session_state.tutorial_step = 1

        TRANSLATIONS = {
            "English": {
                "portal_title": "Universal Multi-Disease & Medication Assister",
                "portal_sub": "Verify treatment safety, target ranges, and meal-by-meal dosage adjustments against your latest test reports.",
                "start_tour_btn": "🎯 Start Interactive Step-by-Step Tour",
                "stop_tour_btn": "✖ Exit Tour",
                "step1_tip": "👇 STEP 1: Select your chronic condition from this dropdown.",
                "step2_tip": "👇 STEP 2: Enter your latest lab test results here.",
                "step3_tip": "👉 STEP 3: Select all medicines you take and enter each daily dosage.",
                "step4_tip": "👇 STEP 4: Input your kidney eGFR (default 90) and click this button to evaluate!",
                "step5_tip": "👇 STEP 5: Review your visual meal pill box schedule and set reminders below!",
                "next_btn": "Next Step ➡️",
                "prev_btn": "⬅️ Back",
                "finish_tour": "🎉 Finish Tour",
                "col1_title": "1️⃣ Select Disease & Enter Vitals",
                "disease_label": "Clinical Diagnosis",
                "col2_title": "2️⃣ Current Prescribed Medication(s)",
                "med_label": "Select All Medicines You Take for this Condition:",
                "egfr_label": "Patient eGFR Metric (mL/min, default: 90)",
                "eval_btn": "🔍 Evaluate Protocol & Meal-by-Meal Schedule",
                "results_header": "📊 Evaluation Assessment & Meal Administration Schedule",
                "safe_badge": "✅ CURRENT DOSE IS OPTIMAL & SAFE",
                "warn_badge": "⚠️ ADJUSTMENT / TITRATION RECOMMENDED",
                "contra_badge": "⛔ CONTRAINDICATED / KIDNEY SAFETY WARNING",
                "curr_dose": "Current Daily Dose:",
                "rec_dose": "Target-Adjusted Dose:",
                "details_title": "🩺 Clinical Assessment Details:",
                "safety_note": "💡 **Patient Safety Note:** Please consult your healthcare provider prior to changing your prescribed dosage or meal timing.",
                "explain_btn": "🗣️ Explain in Plain Language",
                "generating": "Generating patient explanation..."
            },
            "Telugu": {
                "portal_title": "సార్వత్రిక బహుళ-వ్యాధులు & ఔషధ సహాయకం",
                "portal_sub": "మీ తాజా పరీక్ష నివేదికలతో చికిత్స భద్రత మరియు సరైన భోజన సమయాల మోతాదును ధృవీకరించండి.",
                "start_tour_btn": "🎯 ఇంటరాక్టివ్ గైడెడ్ టూర్ ప్రారంభించండి",
                "stop_tour_btn": "✖ టూర్ ముగించు",
                "step1_tip": "👇 దశ 1: ఇక్కడ మీ వ్యాధిని ఎంచుకోండి.",
                "step2_tip": "👇 దశ 2: మీ తాజా ల్యాబ్ రిపోర్ట్ రీడింగ్‌లను ఇక్కడ నమోదు చేయండి.",
                "step3_tip": "👉 దశ 3: మీరు వాడుతున్న అన్ని మందులను మరియు వాటి మోతాదులను ఇక్కడ నమోదు చేయండి.",
                "step4_tip": "👇 దశ 4: కిడ్నీ eGFR నమోదు చేసి, భోజన సమయాల మోతాదును అంచనా వేయడానికి ఇక్కడ క్లిక్ చేయండి!",
                "step5_tip": "👇 దశ 5: భోజన సమయాల ప్రణాళికను సమీక్షించి, రిమైండర్లను సెట్ చేసుకోండి!",
                "next_btn": "తదుపరి దశ ➡️",
                "prev_btn": "⬅️ వెనుకకు",
                "finish_tour": "🎉 టూర్ పూర్తయింది",
                "col1_title": "1️⃣ వ్యాధిని ఎంచుకుని వివరాలను నమోదు చేయండి",
                "disease_label": "క్లినికల్ రోగనిర్ధారణ",
                "col2_title": "2️⃣ ప్రస్తుతం వాడుతున్న మందు(లు)",
                "med_label": "ఈ సమస్య కోసం మీరు వాడుతున్న అన్ని మందులను ఎంచుకోండి:",
                "egfr_label": "రోగి eGFR విలువ (mL/min, సాధారణం: 90)",
                "eval_btn": "🔍 ప్రోటోకాల్ & భోజన సమయాల మోతాదును అంచనా వేయండి",
                "results_header": "📊 మూల్యాంకన ఫలితాలు & భోజన సమయాల ప్రణాళిక",
                "safe_badge": "✅ ప్రస్తుత మోతాదు సురక్షితమైనది మరియు సరైనది",
                "warn_badge": "⚠️ మోతాదు సర్దుబాటు సిఫార్సు చేయబడింది",
                "contra_badge": "⛔ తీవ్రమైన ప్రమాదం / కిడ్నీ భద్రతా హెచ్చరిక",
                "curr_dose": "ప్రస్తుత రోజువారీ మోతాదు:",
                "rec_dose": "సిఫార్సు చేసిన సరైన మోతాదు:",
                "details_title": "🩺 క్లినికల్ మూల్యాంకన వివరాలు:",
                "safety_note": "💡 **గమనిక:** మీ మోతాదును లేదా సమయాలను మార్చడానికి ముందు దయచేసి మీ వైద్యుడిని సంప్రదించండి.",
                "explain_btn": "🗣️ సులభమైన తెలుగులో వివరణ పొందండి",
                "generating": "తెలుగులో వివరణ రూపొందించబడుతోంది..."
            },
            "Hindi": {
                "portal_title": "सार्वभौमिक बहु-रोग और दवा सहायक",
                "portal_sub": "अपनी नवीनतम परीक्षण रिपोर्टों के विरुद्ध उपचार सुरक्षा और भोजन-वार खुराक समायोजन की जाँच करें।",
                "start_tour_btn": "🎯 इंटरएक्टिव गाइडेड टूर शुरू करें",
                "stop_tour_btn": "✖ टूर बंद करें",
                "step1_tip": "👇 चरण 1: यहाँ अपनी बीमारी का चयन करें।",
                "step2_tip": "👇 चरण 2: अपनी नवीनतम लैब रिपोर्ट का मान यहाँ भरें।",
                "step3_tip": "👉 चरण 3: अपनी सभी दवाएं और उनकी दैनिक खुराक यहाँ दर्ज करें।",
                "step4_tip": "👇 चरण 4: किडनी eGFR दर्ज करें और खुराक तालिका देखने के लिए यहाँ क्लिक करें!",
                "step5_tip": "👇 चरण 5: भोजन-वार खुराक देखें और रिमाइंडर सेट करने के लिए यहाँ क्लिक करें!",
                "next_btn": "अगला कदम ➡️",
                "prev_btn": "⬅ पीछे",
                "finish_tour": "🎉 टूर पूरा हुआ",
                "col1_title": "1️⃣ रोग चुनें और स्वास्थ्य विवरण दर्ज करें",
                "disease_label": "चिकित्सीय निदान (Diagnosis)",
                "col2_title": "2️⃣ वर्तमान निर्धारित दवा(एं)",
                "med_label": "इस बीमारी के लिए ली जाने वाली सभी दवाएं चुनें:",
                "egfr_label": "मरीज का eGFR स्तर (mL/min, डिफ़ॉल्ट: 90)",
                "eval_btn": "🔍 प्रोटोकॉल और भोजन-वार खुराक का मूल्यांकन करें",
                "results_header": "📊 मूल्यांकन परिणाम और भोजन-वार खुराक तालिका",
                "safe_badge": "✅ वर्तमान खुराक इष्टतम और सुरक्षित है",
                "warn_badge": "⚠️ खुराक समायोजन की सिफारिश की गई है",
                "contra_badge": "⛔ गंभीर चेतावनी / किडनी सुरक्षा जोखिम",
                "curr_dose": "वर्तमान दैनिक खुराक:",
                "rec_dose": "अनुशंसित समायोजित खुराक:",
                "details_title": "🩺 चिकित्सीय मूल्यांकन विवरण:",
                "safety_note": "💡 **सुरक्षा नोट:** कृपया अपनी निर्धारित खुराक या समय बदलने से पहले अपने डॉक्टर से परामर्श लें।",
                "explain_btn": "🗣️ सरल हिंदी में स्पष्टीकरण प्राप्त करें",
                "generating": "हिंदी में विवरण तैयार किया जा रहा है..."
            },
            "Swahili (Kiswahili)": {
                "portal_title": "Msaidizi wa Magonjwa Mengi na Dawa za Kudumu",
                "portal_sub": "Thibitisha usalama wa matibabu, vipimo vya afya, na mpango wa kugawa vidonge kulingana na milo.",
                "start_tour_btn": "🎯 Anza Mwongozo wa Hatua kwa Hatua",
                "stop_tour_btn": "✖ Toka Kwenye Mwongozo",
                "step1_tip": "👇 HATUA YA 1: Chagua ugonjwa wako wa kudumu kwenye orodha hii.",
                "step2_tip": "👇 HATUA YA 2: Weka matokeo ya vipimo vyako vya hivi karibuni hapa.",
                "step3_tip": "👉 HATUA YA 3: Chagua dawa zote unazotumia na weka kiwango cha dozi ya kila siku.",
                "step4_tip": "👇 HATUA YA 4: Weka kipimo cha figo (eGFR) na bonyeza kitufe hiki kufanya tathmini!",
                "step5_tip": "👇 HATUA YA 5: Kagua ratiba ya chakula hapa chini na weka vikumbusho!",
                "next_btn": "Hatua Inayofuata ➡️",
                "prev_btn": "⬅️ Nyuma",
                "finish_tour": "🎉 Maliza Mwongozo",
                "col1_title": "1️⃣ Chagua Ugonjwa & Weka Vipimo vya Afya",
                "disease_label": "Uchunguzi wa Kitabibu (Diagnosis)",
                "col2_title": "2️⃣ Dawa Unazotumia Hivi Sasa",
                "med_label": "Chagua dawa zote unazotumia kwa ugonjwa huu:",
                "egfr_label": "Kipimo cha Utendaji Kazi wa Figo - eGFR (mL/min, kawaida: 90)",
                "eval_btn": "🔍 Tathmini Mpango wa Dawa Kulingana na Milo",
                "results_header": "📊 Matokeo ya Tathmini na Ratiba ya Vidonge Kulingana na Milo",
                "safe_badge": "✅ DOZI YA SASA NI SALAMA NA INAFAA",
                "warn_badge": "⚠️ MABADILIKO YA DOZI YANASHAURIWA",
                "contra_badge": "⛔ ONYO KALI: HATARI KWA FIGO / USITUMIE",
                "curr_dose": "Dozi ya Sasa ya Kila Siku:",
                "rec_dose": "Dozi Inayoshauriwa:",
                "details_title": "🩺 Sababu za Kitabibu:",
                "safety_note": "💡 **Ujumbe wa Usalama:** Tafadhali wasiliana na daktari wako kabla ya kubadilisha dozi au ratiba ya kumeza dawa.",
                "explain_btn": "🗣️ Eleza kwa Kiswahili Rahisi",
                "generating": "Maelezo kwa Kiswahili yanatayarishwa..."
            }
        }

        t = TRANSLATIONS[selected_lang]

        # Header Title Banner
        st.markdown(f"""
        <div class="header-banner">
            <h2 style="margin:0;">🏥 {t['portal_title']}</h2>
            <p style="margin:5px 0 0 0; opacity:0.9;">{t['portal_sub']}</p>
        </div>
        """, unsafe_allow_html=True)

        # -------------------------------------------------------------
        # DUAL-CAMERA SNAP ASSISTANT FOR VILLAGE & COMMUNITY TESTING
        # -------------------------------------------------------------
        with st.expander("📸 **Can't read the test numbers or pill names? Snap photos instead!**", expanded=False):
            st.info("💡 Point your phone camera or upload photos of your **Lab Test Paper** and **Medicine Strip/Box**. HelixRx AI will read the numbers and populate your schedule automatically.")

            cam1, cam2 = st.columns(2)
            with cam1:
                st.markdown("##### 📄 1. Lab Test Report Photo")
                report_snap = st.camera_input("Snap lab report", key="cam_report")
                if not report_snap:
                    report_snap = st.file_uploader("Or upload report image", type=["png", "jpg", "jpeg"], key="up_report")

            with cam2:
                st.markdown("##### 💊 2. Medicine Strip / Box Photo")
                meds_snap = st.camera_input("Snap tablet strip", key="cam_meds")
                if not meds_snap:
                    meds_snap = st.file_uploader("Or upload tablet strip image", type=["png", "jpg", "jpeg"], key="up_meds")

            if report_snap or meds_snap:
                if st.button("⚡ Scan Photos & Auto-Fill Schedule", type="primary", use_container_width=True):
                    with st.spinner("Reading lab numbers and tablet packaging..."):
                        img_report = Image.open(report_snap) if report_snap else None
                        img_meds = Image.open(meds_snap) if meds_snap else None
                        api_key = st.secrets.get("GEMINI_API_KEY", "")

                        parsed = analyze_prescription_and_report_images(img_report, img_meds, api_key)

                        if "error" in parsed:
                            st.error(f"Scan issue: {parsed['error']}")
                        else:
                            st.session_state["scanned_data"] = parsed
                            st.success("✅ Prescription & Reports successfully scanned!")
                            st.rerun()

            if "scanned_data" in st.session_state:
                sd = st.session_state["scanned_data"]
                st.markdown(f"**Detected Diagnosis:** `{sd.get('detected_condition', 'Diabetes')}`")
                if sd.get("detected_medicines"):
                    st.markdown("**Detected Medicines:**")
                    for m in sd["detected_medicines"]:
                        st.write(f"• **{m['name']}** — {m.get('strength_mg', '')} mg")
                if sd.get("doctor_instructions_summary"):
                    st.caption(f"📝 *Extracted Summary:* {sd['doctor_instructions_summary']}")
                if st.button("Clear Scanned Data"):
                    del st.session_state["scanned_data"]
                    st.rerun()

        # Tour Toggle Button Bar
        tb_col1, _ = st.columns([2, 1])
        with tb_col1:
            if not st.session_state.tutorial_active:
                if st.button(t["start_tour_btn"], type="primary"):
                    st.session_state.tutorial_active = True
                    st.session_state.tutorial_step = 1
                    st.rerun()
            else:
                if st.button(t["stop_tour_btn"]):
                    st.session_state.tutorial_active = False
                    st.session_state.tutorial_step = 1
                    st.rerun()

        # Step Controller Bar (Shown only during active tour)
        if st.session_state.tutorial_active:
            ctrl_c1, ctrl_c2, ctrl_c3 = st.columns([1, 1, 2])
            with ctrl_c1:
                if st.button(t["prev_btn"], disabled=(st.session_state.tutorial_step == 1)):
                    st.session_state.tutorial_step -= 1
                    st.rerun()
            with ctrl_c2:
                if st.session_state.tutorial_step < 5:
                    if st.button(t["next_btn"], type="primary"):
                        st.session_state.tutorial_step += 1
                        st.rerun()
                else:
                    if st.button(t["finish_tour"], type="primary"):
                        st.session_state.tutorial_active = False
                        st.session_state.tutorial_step = 1
                        st.rerun()
            with ctrl_c3:
                st.info(f"📍 Step {st.session_state.tutorial_step} of 5 Active")

        st.write("---")

        # Resolve Auto-Filled Vitals from Camera Scan (if active)
        auto_v = st.session_state.get("scanned_data", {}).get("vitals", {})
        auto_detected_disease = st.session_state.get("scanned_data", {}).get("detected_condition", "Diabetes")

        condition_list = [
            "Diabetes", "Hypertension", "Thyroid Disorders", 
            "Hyperlipidemia", "Chronic Kidney Disease", "Asthma / COPD", 
            "Heart Failure", "Depression / Anxiety", "Gout / Hyperuricemia", 
            "Atrial Fibrillation", "Rheumatoid Arthritis"
        ]
        disease_default_idx = condition_list.index(auto_detected_disease) if auto_detected_disease in condition_list else 0

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(t["col1_title"])

            # STEP 1 POINTER
            if st.session_state.tutorial_active and st.session_state.tutorial_step == 1:
                st.markdown(f'<div class="tutorial-pointer">{t["step1_tip"]}</div>', unsafe_allow_html=True)

            condition = st.selectbox(
                t["disease_label"],
                condition_list,
                index=disease_default_idx,
                key="pat_disease_sel"
            )

            # STEP 2 POINTER
            if st.session_state.tutorial_active and st.session_state.tutorial_step == 2:
                st.markdown(f'<div class="tutorial-pointer">{t["step2_tip"]}</div>', unsafe_allow_html=True)

            vitals_payload = {}
            if condition == "Diabetes":
                fbs_def = int(auto_v["fbs"]) if auto_v.get("fbs") is not None else 145
                ppbs_def = int(auto_v["ppbs"]) if auto_v.get("ppbs") is not None else 205
                hba1c_def = float(auto_v["hba1c"]) if auto_v.get("hba1c") is not None else 7.8
                vitals_payload["fbs"] = st.number_input("Fasting Blood Sugar - FBS (mg/dL)", 0, 500, fbs_def)
                vitals_payload["ppbs"] = st.number_input("Postprandial Blood Sugar - PPBS (mg/dL)", 0, 600, ppbs_def)
                vitals_payload["hba1c"] = st.number_input("Glycated Hemoglobin - HbA1c (%)", 3.0, 20.0, hba1c_def, step=0.1)
                med_options = ["Metformin", "Glimepiride", "Gliclazide", "Insulin"]
            elif condition == "Hypertension":
                sbp_def = int(auto_v["systolic_bp"]) if auto_v.get("systolic_bp") is not None else 142
                dbp_def = int(auto_v["diastolic_bp"]) if auto_v.get("diastolic_bp") is not None else 92
                vitals_payload["systolic_bp"] = st.number_input("Systolic Blood Pressure (mmHg)", 80, 240, sbp_def)
                vitals_payload["diastolic_bp"] = st.number_input("Diastolic Blood Pressure (mmHg)", 50, 140, dbp_def)
                med_options = ["Amlodipine", "Telmisartan", "Lisinopril"]
            elif condition == "Thyroid Disorders":
                tsh_def = float(auto_v["tsh"]) if auto_v.get("tsh") is not None else 6.5
                ft4_def = float(auto_v["free_t4"]) if auto_v.get("free_t4") is not None else 0.75
                vitals_payload["tsh"] = st.number_input("Thyroid Stimulating Hormone - TSH (mIU/L)", 0.0, 50.0, tsh_def, step=0.1)
                vitals_payload["free_t4"] = st.number_input("Free T4 (ng/dL)", 0.0, 10.0, ft4_def, step=0.1)
                med_options = ["Levothyroxine", "Methimazole"]
            elif condition == "Hyperlipidemia":
                ldl_def = int(auto_v["ldl_cholesterol"]) if auto_v.get("ldl_cholesterol") is not None else 140
                tg_def = int(auto_v["triglycerides"]) if auto_v.get("triglycerides") is not None else 210
                vitals_payload["ldl_cholesterol"] = st.number_input("LDL Cholesterol (mg/dL)", 30, 300, ldl_def)
                vitals_payload["triglycerides"] = st.number_input("Triglycerides (mg/dL)", 30, 1000, tg_def)
                med_options = ["Atorvastatin", "Rosuvastatin", "Fenofibrate"]
            elif condition == "Chronic Kidney Disease":
                ckd_egfr_def = int(auto_v["egfr"]) if auto_v.get("egfr") is not None else 28
                vitals_payload["egfr"] = st.number_input("Kidney eGFR (mL/min/1.73m²)", 0, 150, ckd_egfr_def)
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
                uric_def = float(auto_v["uric_acid"]) if auto_v.get("uric_acid") is not None else 8.4
                vitals_payload["uric_acid"] = st.number_input("Serum Uric Acid (mg/dL)", 2.0, 16.0, uric_def, step=0.1)
                vitals_payload["flares_per_year"] = st.number_input("Acute Attacks in Last 12 Mos", 0, 20, 3)
                med_options = ["Allopurinol", "Febuxostat", "Colchicine"]
            elif condition == "Atrial Fibrillation":
                inr_def = float(auto_v["inr"]) if auto_v.get("inr") is not None else 1.8
                vitals_payload["inr"] = st.number_input("International Normalized Ratio (INR)", 0.8, 6.0, inr_def, step=0.1)
                vitals_payload["cha2ds2_vasc"] = st.slider("CHA2DS2-VASc Stroke Risk Score", 0, 9, 3)
                med_options = ["Apixaban", "Rivaroxaban", "Warfarin"]
            else:  # Rheumatoid Arthritis
                crp_def = float(auto_v["crp"]) if auto_v.get("crp") is not None else 18.5
                vitals_payload["crp"] = st.number_input("C-Reactive Protein - CRP (mg/L)", 0.0, 100.0, crp_def, step=0.1)
                vitals_payload["esr"] = st.number_input("Erythrocyte Sedimentation Rate - ESR (mm/hr)", 0, 120, 35)
                med_options = ["Methotrexate", "Hydroxychloroquine"]

        with col2:
            st.subheader(t["col2_title"])

            # STEP 3 POINTER
            if st.session_state.tutorial_active and st.session_state.tutorial_step == 3:
                st.markdown(f'<div class="tutorial-pointer">{t["step3_tip"]}</div>', unsafe_allow_html=True)

            # Auto-match scanned medicines if available
            auto_detected_meds_list = []
            auto_strengths = {}
            if "scanned_data" in st.session_state:
                for sm in st.session_state["scanned_data"].get("detected_medicines", []):
                    for opt in med_options:
                        if opt.lower() in sm.get("name", "").lower() or sm.get("name", "").lower() in opt.lower():
                            if opt not in auto_detected_meds_list:
                                auto_detected_meds_list.append(opt)
                                if sm.get("strength_mg"):
                                    auto_strengths[opt] = float(sm["strength_mg"])

            default_selection = auto_detected_meds_list if auto_detected_meds_list else ([med_options[0]] if med_options else [])
            selected_meds = st.multiselect(
                t["med_label"], 
                options=med_options, 
                default=default_selection,
                key="pat_multi_med_select"
            )
            
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

            patient_doses = {}
            if selected_meds:
                for med in selected_meds:
                    def_val = auto_strengths.get(med, default_map.get(med, 10.0))
                    patient_doses[med] = st.number_input(
                        f"Current Daily Dose for {med} (mg / mcg / Units):",
                        min_value=0.0,
                        max_value=3000.0,
                        value=def_val,
                        key=f"pat_dose_input_{med}"
                    )
            else:
                st.info("Please select at least one medication from the list above.")

            egfr_default = int(auto_v["egfr"]) if auto_v.get("egfr") is not None else 90
            patient_egfr_val = st.number_input(t["egfr_label"], 0, 150, egfr_default)

        st.write("---")

        # STEP 4 POINTER
        if st.session_state.tutorial_active and st.session_state.tutorial_step == 4:
            st.markdown(f'<div class="tutorial-pointer">{t["step4_tip"]}</div>', unsafe_allow_html=True)

        if st.button(t["eval_btn"], type="primary"):
            if not selected_meds:
                st.warning("Please select at least one medication to evaluate.")
            else:
                batch_evaluations = []
                for med in selected_meds:
                    curr_d = patient_doses.get(med, 0.0)
                    eval_res = evaluate_disease_management(
                        condition, med, curr_d, vitals_payload, egfr=patient_egfr_val
                    )
                    meal_advice = generate_meal_titration_instruction(
                        med, curr_d, eval_res["recommended_dose_mg"]
                    )
                    eval_res["meal_advice"] = meal_advice
                    batch_evaluations.append(eval_res)

                st.session_state.last_patient_batch = batch_evaluations
                st.session_state.last_patient_condition = condition

        # DISPLAY RESULTS WITH VISUAL MEAL PILL BOX CARDS & REMINDERS
        if "last_patient_batch" in st.session_state:
            st.subheader(t["results_header"])

            for res in st.session_state.last_patient_batch:
                med_name = res["drug"]
                adv = res["meal_advice"]

                with st.container(border=True):
                    h1, h2 = st.columns([2.5, 1.5])
                    with h1:
                        st.markdown(f"### 💊 {med_name}")
                        st.markdown(f"**{adv['action_text']}**")
                    with h2:
                        if res["dose_correct"]:
                            st.markdown(f'<span class="badge-green">{t["safe_badge"]}</span>', unsafe_allow_html=True)
                        elif "Renal" in res["status"] or "Contraindicated" in res["status"]:
                            st.markdown(f'<span class="badge-red">{t["contra_badge"]}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="badge-yellow">{t["warn_badge"]}</span>', unsafe_allow_html=True)

                    st.markdown("#### 🍱 Daily Visual Pill Box Schedule")

                    b_col, l_col, d_col = st.columns(3)

                    with b_col:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #78350f 0%, #b45309 100%); padding: 16px; border-radius: 12px; color: white; border: 1px solid #d97706; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                            <div style="font-size: 1.1rem; font-weight: 700;">🌅 Morning (Breakfast)</div>
                            <div style="font-size: 1.6rem; font-weight: 800; margin: 8px 0; color: #fef08a;">{adv.get('morning_dose', '—')}</div>
                            <div style="font-size: 0.85rem; background: rgba(0,0,0,0.25); padding: 6px 8px; border-radius: 6px;">📌 {adv.get('morning_timing', 'None')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with l_col:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #075985 0%, #0284c7 100%); padding: 16px; border-radius: 12px; color: white; border: 1px solid #38bdf8; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                            <div style="font-size: 1.1rem; font-weight: 700;">☀️ Afternoon (Lunch)</div>
                            <div style="font-size: 1.6rem; font-weight: 800; margin: 8px 0; color: #bae6fd;">{adv.get('afternoon_dose', '—')}</div>
                            <div style="font-size: 0.85rem; background: rgba(0,0,0,0.25); padding: 6px 8px; border-radius: 6px;">📌 {adv.get('afternoon_timing', 'None')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with d_col:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #312e81 0%, #4338ca 100%); padding: 16px; border-radius: 12px; color: white; border: 1px solid #818cf8; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                            <div style="font-size: 1.1rem; font-weight: 700;">🌙 Night (Dinner)</div>
                            <div style="font-size: 1.6rem; font-weight: 800; margin: 8px 0; color: #c7d2fe;">{adv.get('night_dose', '—')}</div>
                            <div style="font-size: 0.85rem; background: rgba(0,0,0,0.25); padding: 6px 8px; border-radius: 6px;">📌 {adv.get('night_timing', 'None')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.write("")
                    st.caption(f"💡 **Clinical Administration Rule:** {adv['clinical_note']}")
                    with st.expander("🩺 View Detailed Lab Metric Rationale"):
                        for r in res["reasons"]:
                            st.write(f"• {r}")

            st.write("---")

            # ---------------------------------------------------------
            # 2. POP-UP MEDICATION REMINDER SYSTEM
            # ---------------------------------------------------------
            st.markdown("### ⏰ Set Daily Meal Dose Reminders (Pop-Up & Audio)")
            st.caption("HelixRx can send browser alerts to your phone or laptop at meal times so you never miss a dose.")

            rem_col1, rem_col2, rem_col3 = st.columns(3)
            with rem_col1:
                b_time = st.time_input("🌅 Breakfast Alert Time", value=datetime.strptime("08:30", "%H:%M").time(), key="time_b")
            with rem_col2:
                l_time = st.time_input("☀️ Lunch Alert Time", value=datetime.strptime("13:30", "%H:%M").time(), key="time_l")
            with rem_col3:
                d_time = st.time_input("🌙 Dinner Alert Time", value=datetime.strptime("20:30", "%H:%M").time(), key="time_d")

            btn_rem1, btn_rem2 = st.columns(2)
            
            with btn_rem1:
                if st.button("🧪 Test Instant Reminder Pop-Up", use_container_width=True):
                    med_summary_names = ", ".join([r["drug"] for r in st.session_state.last_patient_batch])
                    test_alert_js = f"""
                    <script>
                        if ("Notification" in window) {{
                            Notification.requestPermission().then(permission => {{
                                if (permission === "granted") {{
                                    new Notification("🔔 HelixRx Medication Reminder", {{
                                        body: "Time for your prescribed meal dose: {med_summary_names}. Check your pill box!",
                                        icon: "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f48a.png"
                                    }});
                                }} else {{
                                    alert("🔔 HelixRx Reminder: Time to take your medication ({med_summary_names}) with your meal!");
                                }}
                            }});
                        }} else {{
                            alert("🔔 HelixRx Reminder: Time to take your medication ({med_summary_names}) with your meal!");
                        }}
                    </script>
                    """
                    st.components.v1.html(test_alert_js, height=0)
                    st.success(f"🔔 Test Alert Triggered for: {med_summary_names}!")

            with btn_rem2:
                if st.button("🔔 Activate Daily Browser Reminders", type="primary", use_container_width=True):
                    med_list_str = ", ".join([r["drug"] for r in st.session_state.last_patient_batch])
                    reminders_active_js = f"""
                    <script>
                        if ("Notification" in window) {{
                            Notification.requestPermission().then(permission => {{
                                if (permission === "granted") {{
                                    new Notification("✅ HelixRx Reminders Activated", {{
                                        body: "Reminders scheduled for Breakfast ({b_time.strftime('%H:%M')}), Lunch ({l_time.strftime('%H:%M')}), and Dinner ({d_time.strftime('%H:%M')}) for {med_list_str}.",
                                        icon: "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2705.png"
                                    }});
                                }} else {{
                                    alert("Please allow notification permissions in your browser bar to receive reminders.");
                                }}
                            }});
                        }}
                    </script>
                    """
                    st.components.v1.html(reminders_active_js, height=0)
                    st.success(f"✅ Daily Reminders active: Breakfast at {b_time.strftime('%H:%M')}, Lunch at {l_time.strftime('%H:%M')}, and Dinner at {d_time.strftime('%H:%M')}.")

            st.info(t["safety_note"])

            # STEP 5 POINTER
            if st.session_state.tutorial_active and st.session_state.tutorial_step == 5:
                st.markdown(f'<div class="tutorial-pointer">{t["step5_tip"]}</div>', unsafe_allow_html=True)

            if st.button(t["explain_btn"]):
                with st.spinner(t["generating"]):
                    try:
                        api_key = st.secrets.get("GEMINI_API_KEY", "")
                        if api_key:
                            client = genai.Client(api_key=api_key)
                            
                            drugs_summary = []
                            for r in st.session_state.last_patient_batch:
                                drugs_summary.append(
                                    f"- Medication: {r['drug']}, Current: {r['current_dose_mg']}, Recommended: {r['recommended_dose_mg']}\n"
                                    f"  Meal Plan: {r['meal_advice']['split_plan']}\n"
                                    f"  Reasons: {' '.join(r['reasons'])}"
                                )
                            
                            explain_prompt = f"""
                            You are a friendly, compassionate clinical doctor explaining a test evaluation directly to a patient.
                            Explain this clinical assessment result clearly in {selected_lang}.
                            Avoid dense medical jargon. Use simple, conversational words.

                            Details:
                            - Diagnosis / Condition: {st.session_state.last_patient_condition}
                            {chr(10).join(drugs_summary)}

                            Explain clearly how they should take their medicines across breakfast, lunch, and dinner, and provide a 3-4 sentence reassurance with questions they should ask their doctor at their next appointment.
                            """
                            exp_text = call_gemini_with_fallback(client, explain_prompt)
                            st.success(exp_text)
                        else:
                            st.warning("GEMINI_API_KEY not configured for dynamic explanations.")
                    except Exception as e:
                        st.error(f"Explanation engine error: {str(e)}")

    # =========================================================
    # B. CLINICIAN & HOSPITAL GATEWAY (GENOMICS & PK MODELING)
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