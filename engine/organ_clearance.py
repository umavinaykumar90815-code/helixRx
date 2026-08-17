def evaluate_organ_clearance(egfr, alt, current_risk_level, drug):
    """
    Adjusts the final drug safety recommendation based on anatomical 
    clearance parameters (Renal eGFR & Hepatic ALT).
    """
    organ_warnings = []
    final_risk_level = current_risk_level
    
    # 1. Evaluate Kidney Clearance (Renal Function)
    if egfr < 30:
        organ_warnings.append("Severe Renal Impairment (eGFR < 30 mL/min). Renal drug clearance severely reduced.")
        if final_risk_level != "High Risk":
            final_risk_level = "High Risk"
    elif egfr < 60:
        organ_warnings.append("Moderate Renal Impairment (eGFR 30-59 mL/min). Dosage adjustment may be needed for renally cleared drugs.")
        if final_risk_level == "Safe / Normal":
            final_risk_level = "Moderate Risk"
            
    # 2. Evaluate Liver Function (Hepatic Clearance)
    # Standard normal ALT threshold is ~40 U/L
    if alt > 120:  # > 3x Upper Limit of Normal
        organ_warnings.append("Severe Hepatic Impairment (Elevated ALT > 3x ULN). Impaired liver metabolism.")
        if final_risk_level != "High Risk":
            final_risk_level = "High Risk"
    elif alt > 40:
        organ_warnings.append("Mild-to-Moderate Hepatic Elevation. Monitor liver enzyme clearance.")
        if final_risk_level == "Safe / Normal":
            final_risk_level = "Moderate Risk"
            
    if not organ_warnings:
        organ_warnings.append("Organ clearance parameters (Kidney & Liver) are within normal physiological ranges.")
        
    return {
        "final_risk_level": final_risk_level,
        "organ_warnings": organ_warnings,
        "egfr_status": "Normal" if egfr >= 60 else "Impaired",
        "alt_status": "Normal" if alt <= 40 else "Elevated"
    }

if __name__ == "__main__":
    # Test execution
    test_result = evaluate_organ_clearance(egfr=25, alt=80, current_risk_level="Safe / Normal", drug="Clopidogrel")
    print("\n--- ORGAN CLEARANCE EVALUATION ---")
    print(f"Final Risk Level: {test_result['final_risk_level']}")
    print("Warnings:", test_result['organ_warnings'])