"""
HelixRx Medical Report & Optical Ingestion Engine
Parses unstructured electronic medical records, laboratory PDFs, plain text,
and dual-camera mobile snaps (prescriptions and tablet strips) into
structured clinical parameters.
"""

import os
import re
import json

# Safe imports with fallback to prevent container boot failure
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from google import genai
except ImportError:
    genai = None


def parse_medical_report(file_path: str) -> dict:
    """
    Extracts laboratory biomarkers (eGFR, ALT, Creatinine, Bilirubin, Blood Sugars)
    from uploaded text files or PDF medical reports.
    """
    extracted_text = ""
    
    if not os.path.exists(file_path):
        return {"egfr": 90.0, "alt": 25.0, "notes": "File not found; defaulted to baseline."}

    # Extract text based on file format
    if file_path.lower().endswith(".pdf") and PdfReader is not None:
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
        except Exception:
            extracted_text = ""
    else:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                extracted_text = f.read()
        except Exception:
            extracted_text = ""

    results = {
        "egfr": None,
        "alt": None,
        "creatinine": None,
        "ast": None,
        "fbs": None,
        "ppbs": None,
        "hba1c": None,
        "raw_snippet": extracted_text[:300] if extracted_text else ""
    }

    if not extracted_text:
        results["egfr"] = 90.0
        results["alt"] = 25.0
        return results

    # Regex patterns for clinical parameters
    egfr_match = re.search(r"(?:eGFR|GFR)[\s:=]+([0-9]{1,3}(?:\.[0-9]+)?)", extracted_text, re.IGNORECASE)
    if egfr_match:
        try:
            results["egfr"] = float(egfr_match.group(1))
        except ValueError:
            pass

    alt_match = re.search(r"(?:ALT|SGPT)[\s:=]+([0-9]{1,3}(?:\.[0-9]+)?)", extracted_text, re.IGNORECASE)
    if alt_match:
        try:
            results["alt"] = float(alt_match.group(1))
        except ValueError:
            pass

    creat_match = re.search(r"(?:Creatinine|Serum Creatinine)[\s:=]+([0-9]{1,2}(?:\.[0-9]+)?)", extracted_text, re.IGNORECASE)
    if creat_match:
        try:
            results["creatinine"] = float(creat_match.group(1))
        except ValueError:
            pass

    hba1c_match = re.search(r"(?:HbA1c|A1C)[\s:=]+([0-9]{1,2}(?:\.[0-9]+)?)", extracted_text, re.IGNORECASE)
    if hba1c_match:
        try:
            results["hba1c"] = float(hba1c_match.group(1))
        except ValueError:
            pass

    fbs_match = re.search(r"(?:FBS|Fasting Blood Sugar)[\s:=]+([0-9]{2,3}(?:\.[0-9]+)?)", extracted_text, re.IGNORECASE)
    if fbs_match:
        try:
            results["fbs"] = float(fbs_match.group(1))
        except ValueError:
            pass

    if results["egfr"] is None:
        results["egfr"] = 90.0
    if results["alt"] is None:
        results["alt"] = 25.0

    return results


def analyze_prescription_and_report_images(report_img=None, meds_img=None, api_key: str = "") -> dict:
    """
    Multimodal Vision Engine: Analyzes camera snaps of paper lab reports and
    medicine blister packaging to auto-extract biomarkers, diagnosed condition,
    active generic molecules, and dose strengths.
    """
    if not api_key:
        return {"error": "Gemini API key is not configured in secrets."}

    if genai is None:
        return {"error": "google-genai package is not installed."}

    if report_img is None and meds_img is None:
        return {"error": "No images provided for analysis."}

    client = genai.Client(api_key=api_key)

    prompt = (
        "You are an expert clinical pharmacogenomics assistant, lab diagnostic reader, and pharmaceutical package analyst.\n"
        "Analyze the provided image(s). One may be a printed or handwritten patient lab test report, "
        "and the other may be a photograph of medicine blister strips, boxes, or bottles.\n\n"
        "Extract the clinical readings and active medications, returning STRICTLY valid JSON with no markdown formatting or backticks:\n"
        "{\n"
        '  "detected_condition": "Diabetes" | "Hypertension" | "Thyroid Disorders" | "Hyperlipidemia" | "Chronic Kidney Disease" | "Asthma / COPD" | "Heart Failure" | "Depression / Anxiety" | "Gout / Hyperuricemia" | "Atrial Fibrillation" | "Rheumatoid Arthritis",\n'
        '  "vitals": {\n'
        '    "fbs": null,\n'
        '    "ppbs": null,\n'
        '    "hba1c": null,\n'
        '    "systolic_bp": null,\n'
        '    "diastolic_bp": null,\n'
        '    "egfr": 90,\n'
        '    "alt": 25,\n'
        '    "tsh": null,\n'
        '    "free_t4": null,\n'
        '    "ldl_cholesterol": null,\n'
        '    "triglycerides": null,\n'
        '    "uric_acid": null,\n'
        '    "inr": null,\n'
        '    "crp": null\n'
        "  },\n"
        '  "detected_medicines": [\n'
        "    {\n"
        '      "name": "Metformin",\n'
        '      "strength_mg": 500.0\n'
        "    }\n"
        "  ],\n"
        '  "doctor_instructions_summary": "Concise 1-sentence clinical summary of prescribed drugs or test highlights."\n'
        "}\n\n"
        "Rules:\n"
        "1. Map trade/brand names (e.g. Glycomet, Reclimet, Diamicron, Glizid, Telma, Amlopres, Eltroxin, Lipitor, Storvas) to their active chemical molecules (Metformin, Gliclazide, Glimepiride, Telmisartan, Amlodipine, Levothyroxine, Atorvastatin).\n"
        "2. Accurately detect milligram strength from tablet foil imprint (e.g. 500mg, 40mg, 80mg, 2mg, 5mg).\n"
        "3. Set missing numerical readings to null (keep egfr at 90 and alt at 25 if not explicitly mentioned).\n"
        "4. Output purely the JSON object without wrapping it in ```json code fences."
    )

    contents = [prompt]
    if report_img is not None:
        contents.append("LAB REPORT PHOTOGRAPH:")
        contents.append(report_img)
    if meds_img is not None:
        contents.append("MEDICINE STRIP / PRESCRIPTION PHOTOGRAPH:")
        contents.append(meds_img)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )
        raw_text = response.text.strip()
        
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed_json = json.loads(raw_text.strip())
        return parsed_json
    except Exception as e:
        return {"error": f"Image parsing failure: {str(e)}"}