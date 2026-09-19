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
    },
    "Depression / Anxiety": {
        "biomarkers": ["phq9", "gad7"],
        "targets": {"phq9": {"max": 9}, "gad7": {"max": 7}},
        "drugs": {
            "Sertraline": {"standard_dose": 50.0, "max_dose": 200.0, "titration_step": 50.0},
            "Escitalopram": {"standard_dose": 10.0, "max_dose": 20.0, "titration_step": 10.0},
            "Venlafaxine": {"standard_dose": 75.0, "max_dose": 225.0, "titration_step": 75.0}
        }
    },
    "Gout / Hyperuricemia": {
        "biomarkers": ["uric_acid", "flares_per_year"],
        "targets": {"uric_acid": {"max": 6.0}, "flares_per_year": {"max": 0}},
        "drugs": {
            "Allopurinol": {"standard_dose": 100.0, "max_dose": 600.0, "titration_step": 100.0, "renal_cutoff_egfr": 30, "adjusted_dose": 50.0},
            "Febuxostat": {"standard_dose": 40.0, "max_dose": 80.0, "titration_step": 40.0, "renal_cutoff_egfr": 30, "adjusted_dose": 40.0},
            "Colchicine": {"standard_dose": 0.5, "max_dose": 1.0, "titration_step": 0.5, "renal_cutoff_egfr": 30, "adjusted_dose": 0.3}
        }
    },
    "Atrial Fibrillation": {
        "biomarkers": ["inr", "cha2ds2_vasc"],
        "targets": {"inr": {"min": 2.0, "max": 3.0}},
        "drugs": {
            "Warfarin": {"standard_dose": 5.0, "max_dose": 15.0, "titration_step": 1.0},
            "Apixaban": {"standard_dose": 5.0, "max_dose": 5.0, "renal_cutoff_egfr": 30, "adjusted_dose": 2.5},
            "Rivaroxaban": {"standard_dose": 20.0, "max_dose": 20.0, "renal_cutoff_egfr": 50, "adjusted_dose": 15.0}
        }
    },
    "Rheumatoid Arthritis": {
        "biomarkers": ["crp", "esr"],
        "targets": {"crp": {"max": 5.0}, "esr": {"max": 20}},
        "drugs": {
            "Methotrexate": {"standard_dose": 15.0, "max_dose": 25.0, "titration_step": 2.5, "renal_cutoff_egfr": 30, "adjusted_dose": 0.0},
            "Hydroxychloroquine": {"standard_dose": 200.0, "max_dose": 400.0, "titration_step": 100.0}
        }
    }
}

def ensure_protocols_exist():
    os.makedirs(os.path.dirname(PROTOCOLS_FILEPATH), exist_ok=True)
    # Always update or write the file so newly introduced protocols persist
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

    # Special handling: Atrial Fibrillation with Warfarin titrations
    if condition == "Atrial Fibrillation" and medication == "Warfarin":
        inr_val = lab_vitals.get("inr")
        if inr_val is not None:
            if inr_val < 2.0:
                dose_correct = False
                status = "Sub-Optimal Control / Adjustment Recommended"
                recommended_dose = round(current_dose_mg * 1.15, 1)
                reasons.append(f"• INR ({inr_val}) is sub-therapeutic (< 2.0). Increase dose by ~15% to prevent stroke.")
            elif inr_val > 3.0:
                dose_correct = False
                status = "Supratherapeutic Bleeding Risk"
                recommended_dose = round(current_dose_mg * 0.85, 1)
                reasons.append(f"• INR ({inr_val}) exceeds target (> 3.0). High bleeding danger. Reduce dose by ~15%.")
            else:
                reasons.append(f"• INR ({inr_val}) is in the optimal therapeutic window (2.0 - 3.0).")
    else:
        # 1. Biomarker Control Evaluation
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
                reasons.append(f"• {medication} is at maximum dosage ceiling ({max_dose} mg/mcg/Units). Evaluate multi-drug combination therapy.")

    # 3. Renal Clearance Safety Cutoffs
    if "renal_cutoff_egfr" in drug_data and egfr < drug_data["renal_cutoff_egfr"]:
        dose_correct = False
        status = "Renal Clearance Safety Risk"
        recommended_dose = drug_data.get("adjusted_dose", current_dose_mg * 0.5)
        if recommended_dose == 0.0:
            reasons.append(f"• CONTRAINDICATED: eGFR ({egfr} mL/min) is below safety threshold ({drug_data['renal_cutoff_egfr']} mL/min). Discontinue {medication}.")
        else:
            reasons.append(f"• eGFR ({egfr} mL/min) is below safety threshold ({drug_data['renal_cutoff_egfr']} mL/min). Dose reduced to {recommended_dose} mg.")

    # 4. Hepatic Safety Cutoff Check
    if alt > 120.0 and medication in ["Methotrexate", "Atorvastatin"]:
        dose_correct = False
        status = "Hepatic Safety Warning"
        recommended_dose = 0.0
        reasons.append(f"• Hepatotoxicity alert: Serum ALT is markedly elevated ({alt} U/L). Withhold or stop {medication}.")

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