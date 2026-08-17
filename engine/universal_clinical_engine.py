import json
import os

PROTOCOLS_FILEPATH = os.path.join("data", "disease_protocols.json")

# Multi-disease protocol database
DEFAULT_DISEASE_PROTOCOLS = {
    "Diabetes": {
        "biomarkers": ["fbs", "ppbs", "hba1c"],
        "targets": {"fbs": {"max": 130}, "ppbs": {"max": 180}, "hba1c": {"max": 7.0}},
        "drugs": {
            "Metformin": {"standard_dose": 1000.0, "max_dose": 2000.0, "titration_step": 500.0, "renal_cutoff_egfr": 30, "adjusted_dose": 0.0},
            "Glimepiride": {"standard_dose": 2.0, "max_dose": 6.0, "titration_step": 1.0},
            "Gliclazide": {"standard_dose": 80.0, "max_dose": 320.0, "titration_step": 40.0},
            "Insulin": {"standard_dose": 10.0, "max_dose": 50.0, "titration_step": 2.0}
        }
    },
    "Hypertension": {
        "biomarkers": ["systolic_bp", "diastolic_bp"],
        "targets": {"systolic_bp": {"max": 130}, "diastolic_bp": {"max": 80}},
        "drugs": {
            "Amlodipine": {"standard_dose": 5.0, "max_dose": 10.0, "titration_step": 2.5},
            "Telmisartan": {"standard_dose": 40.0, "max_dose": 80.0, "titration_step": 40.0},
            "Lisinopril": {"standard_dose": 10.0, "max_dose": 40.0, "titration_step": 10.0}
        }
    },
    "Thyroid Disorders": {
        "biomarkers": ["tsh", "free_t4"],
        "targets": {"tsh": {"min": 0.4, "max": 4.0}, "free_t4": {"min": 0.8, "max": 1.8}},
        "drugs": {
            "Levothyroxine": {"standard_dose": 50.0, "max_dose": 200.0, "titration_step": 12.5},
            "Methimazole": {"standard_dose": 10.0, "max_dose": 40.0, "titration_step": 5.0}
        }
    },
    "Hyperlipidemia": {
        "biomarkers": ["ldl_cholesterol", "triglycerides"],
        "targets": {"ldl_cholesterol": {"max": 100}, "triglycerides": {"max": 150}},
        "drugs": {
            "Atorvastatin": {"standard_dose": 20.0, "max_dose": 80.0, "titration_step": 20.0},
            "Rosuvastatin": {"standard_dose": 10.0, "max_dose": 40.0, "titration_step": 10.0},
            "Fenofibrate": {"standard_dose": 145.0, "max_dose": 145.0, "renal_cutoff_egfr": 30, "adjusted_dose": 48.0}
        }
    },
    "Chronic Kidney Disease": {
        "biomarkers": ["egfr", "creatinine", "uacr"],
        "targets": {"egfr": {"min": 60}, "uacr": {"max": 30}},
        "drugs": {
            "Allopurinol": {"standard_dose": 300.0, "max_dose": 300.0, "renal_cutoff_egfr": 30, "adjusted_dose": 100.0},
            "Dapagliflozin": {"standard_dose": 10.0, "max_dose": 10.0, "renal_cutoff_egfr": 25, "adjusted_dose": 0.0}
        }
    },
    "Asthma / COPD": {
        "biomarkers": ["fev1_percent", "peak_flow"],
        "targets": {"fev1_percent": {"min": 80}, "peak_flow": {"min": 300}},
        "drugs": {
            "Salbutamol / Albuterol": {"standard_dose": 100.0, "max_dose": 400.0, "titration_step": 100.0},
            "Budenoside": {"standard_dose": 200.0, "max_dose": 800.0, "titration_step": 200.0}
        }
    },
    "Heart Failure": {
        "biomarkers": ["ejection_fraction", "bnp"],
        "targets": {"ejection_fraction": {"min": 50}, "bnp": {"max": 100}},
        "drugs": {
            "Furosemide": {"standard_dose": 40.0, "max_dose": 240.0, "titration_step": 20.0},
            "Spironolactone": {"standard_dose": 25.0, "max_dose": 50.0, "renal_cutoff_egfr": 30, "adjusted_dose": 0.0}
        }
    }
}

def ensure_protocols_exist():
    os.makedirs(os.path.dirname(PROTOCOLS_FILEPATH), exist_ok=True)
    with open(PROTOCOLS_FILEPATH, "w") as f:
        json.dump(DEFAULT_DISEASE_PROTOCOLS, f, indent=2)

def load_protocols():
    ensure_protocols_exist()
    try:
        with open(PROTOCOLS_FILEPATH, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_DISEASE_PROTOCOLS

def evaluate_disease_management(condition, medication, current_dose_mg, lab_vitals, egfr=90.0, alt=25.0):
    protocols = load_protocols()
    
    if condition not in protocols:
        return {
            "condition": condition,
            "medication": medication,
            "status": "Condition Not Protocolized",
            "dose_correct": True,
            "current_dose_mg": float(current_dose_mg),
            "recommended_dose_mg": float(current_dose_mg),
            "reasons": ["• Condition relies on specialized monitoring."]
        }

    cond_data = protocols[condition]
    targets = cond_data.get("targets", {})
    drug_data = cond_data.get("drugs", {}).get(medication, {})
    
    reasons = []
    dose_correct = True
    recommended_dose = float(current_dose_mg)
    status = "Therapeutic Target Achieved"

    # 1. Biomarker Control Check
    off_target = False
    for marker, target in targets.items():
        val = lab_vitals.get(marker)
        if val is not None:
            if "max" in target and val > target["max"]:
                off_target = True
                reasons.append(f"• {marker.upper().replace('_', ' ')} level ({val}) exceeds target upper limit ({target['max']}).")
            elif "min" in target and val < target["min"]:
                off_target = True
                reasons.append(f"• {marker.upper().replace('_', ' ')} level ({val}) is below target lower limit ({target['min']}).")

    # 2. Dose Titration Logic
    if off_target:
        dose_correct = False
        status = "Sub-Optimal Control / Adjustment Recommended"
        titration = drug_data.get("titration_step", 0.0)
        max_dose = drug_data.get("max_dose", current_dose_mg)
        
        if current_dose_mg < max_dose and titration > 0:
            recommended_dose = min(max_dose, current_dose_mg + titration)
            reasons.append(f"• Increase {medication} dosage from {current_dose_mg} to {recommended_dose} mg/mcg/Units daily.")
        elif current_dose_mg >= max_dose:
            reasons.append(f"• {medication} is at maximum dosage ceiling ({max_dose} mg/mcg/Units). Evaluate dual-drug combination therapy.")

    # 3. Renal Safety Cutoffs
    if "renal_cutoff_egfr" in drug_data and egfr < drug_data["renal_cutoff_egfr"]:
        dose_correct = False
        status = "Renal Clearance Safety Risk"
        recommended_dose = drug_data.get("adjusted_dose", current_dose_mg * 0.5)
        if recommended_dose == 0.0:
            reasons.append(f"• CONTRAINDICATED: eGFR ({egfr} mL/min) is below safety threshold ({drug_data['renal_cutoff_egfr']} mL/min). Discontinue {medication}.")
        else:
            reasons.append(f"• eGFR ({egfr} mL/min) is below safety threshold ({drug_data['renal_cutoff_egfr']} mL/min). Dose reduced to {recommended_dose} mg.")

    if not reasons:
        reasons.append("• All recorded lab biomarkers are within target clinical ranges. Current dosage is optimal.")

    return {
        "condition": condition,
        "medication": medication,
        "status": status,
        "dose_correct": dose_correct,
        "current_dose_mg": float(current_dose_mg),
        "recommended_dose_mg": float(recommended_dose),
        "reasons": reasons
    }