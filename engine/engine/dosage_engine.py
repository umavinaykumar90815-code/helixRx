def calculate_dosage_adjustment(drug_name, egfr, alt, standard_dose_mg=100.0):
    """
    Determines if drug dosage requires adjustment, reduction, or discontinuation
    based on renal (eGFR) and hepatic (ALT) clearance.
    """
    drug = drug_name.capitalize()
    adjustment_recommended = False
    recommended_dose = standard_dose_mg
    reasons = []
    status = "Standard Dose Safe"

    # Renal Dosing Rules
    if egfr is not None:
        if egfr < 15:
            status = "Contraindicated / High Danger"
            adjustment_recommended = True
            recommended_dose = 0.0
            reasons.append("End-stage renal disease (eGFR < 15 mL/min). Discontinue drug or switch to dialysis-cleared alternative.")
        elif egfr < 30:
            status = "Dose Reduction Required"
            adjustment_recommended = True
            recommended_dose = standard_dose_mg * 0.5
            reasons.append("Severe renal impairment (eGFR 15-29 mL/min). Reduce dose by 50%.")
        elif egfr < 60:
            if drug in ["Codeine", "Simvastatin"]:
                status = "Dose Reduction Required"
                adjustment_recommended = True
                recommended_dose = standard_dose_mg * 0.75
                reasons.append("Moderate renal impairment (eGFR 30-59 mL/min). Reduce dose by 25%.")

    # Hepatic Dosing Rules
    if alt is not None and alt > 120:  # > 3x Upper Limit of Normal
        status = "Hepatic Warning / Dose Reduction"
        adjustment_recommended = True
        recommended_dose = min(recommended_dose, standard_dose_mg * 0.5)
        reasons.append("Severe hepatic transaminase elevation (ALT > 120 U/L). High risk of drug accumulation.")

    if not reasons:
        reasons.append("Extracted organ vitals are within safe operating thresholds for standard dosing.")

    return {
        "drug": drug,
        "standard_dose_mg": standard_dose_mg,
        "recommended_dose_mg": recommended_dose,
        "adjustment_required": adjustment_recommended,
        "status": status,
        "clinical_reasons": reasons
    }