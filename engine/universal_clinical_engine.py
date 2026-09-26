"""
HelixRx Universal Clinical Engine
Comprehensive clinical decision support across 11 chronic conditions.
Handles dynamic auto-titration, renal/hepatic safety thresholds,
and meal-by-meal administration schedule generation.
"""

def generate_meal_titration_instruction(drug_name, current_dose, recommended_dose):
    """
    Translates raw dose titration numbers into practical, meal-by-meal instructions
    (Breakfast, Lunch, Dinner) along with explicit administration guidance.
    """
    d_name = str(drug_name).lower()
    current_dose = float(current_dose)
    recommended_dose = float(recommended_dose)
    
    # 1. Metformin
    if "metformin" in d_name:
        if recommended_dose > current_dose:
            action_text = f"🔺 Dose Increase Recommended: Step up from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        elif recommended_dose < current_dose:
            action_text = f"🔻 Dose Reduction Required: Reduce from {current_dose:.0f} mg down to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Maintain Current Dose: Keep taking {recommended_dose:.0f} mg/day."

        if recommended_dose <= 0:
            split_plan = "• Morning (Breakfast): Discontinue\n• Afternoon (Lunch): Discontinue\n• Night (Dinner): Discontinue"
            clinical_note = "Medication held due to organ safety or clinical contraindication."
        elif recommended_dose <= 500:
            split_plan = "• Morning (Breakfast): None\n• Afternoon (Lunch): None\n• Night (Dinner): 500 mg (with meal)"
            clinical_note = "Always take with or immediately after meals to reduce gastrointestinal side effects."
        elif recommended_dose <= 1000:
            split_plan = "• Morning (Breakfast): 500 mg (with meal)\n• Afternoon (Lunch): None\n• Night (Dinner): 500 mg (with meal)"
            clinical_note = "Split evenly across breakfast and dinner to maintain steady glycemic control."
        elif recommended_dose <= 1500:
            split_plan = "• Morning (Breakfast): 500 mg (with meal)\n• Afternoon (Lunch): 500 mg (with meal)\n• Night (Dinner): 500 mg (with meal)"
            clinical_note = "Take 500 mg with each of your three main meals."
        else:  # 2000 mg max
            split_plan = "• Morning (Breakfast): 1000 mg (with meal)\n• Afternoon (Lunch): None\n• Night (Dinner): 1000 mg (with meal)"
            clinical_note = "Take 1000 mg with breakfast and 1000 mg with dinner. Maximum daily dose reached."

    # 2. Glimepiride / Gliclazide (Sulfonylureas)
    elif "glimepiride" in d_name or "gliclazide" in d_name:
        if recommended_dose > current_dose:
            action_text = f"🔺 Titration Recommended: Increase from {current_dose:.1f} mg to {recommended_dose:.1f} mg/day."
        elif recommended_dose < current_dose:
            action_text = f"🔻 Dose Lowered: Reduce from {current_dose:.1f} mg down to {recommended_dose:.1f} mg/day."
        else:
            action_text = f"✅ Maintain Current Dose: Continue {recommended_dose:.1f} mg/day."

        if recommended_dose <= 0:
            split_plan = "• Morning (Breakfast): Discontinue\n• Afternoon (Lunch): Discontinue\n• Night (Dinner): Discontinue"
            clinical_note = "Discontinued due to hypoglycemia risk or contraindication."
        elif recommended_dose <= 2:
            split_plan = f"• Morning (Breakfast): None\n• Afternoon (Lunch): {recommended_dose:.1f} mg (15-30 mins before food)\n• Night (Dinner): None"
            clinical_note = "Take before your main meal. Never skip a meal after taking a sulfonylurea."
        else:
            half = recommended_dose / 2.0
            split_plan = f"• Morning (Breakfast): {half:.1f} mg (before breakfast)\n• Afternoon (Lunch): {half:.1f} mg (before lunch)\n• Night (Dinner): None"
            clinical_note = "Split before breakfast and lunch. Avoid taking at night to prevent nocturnal hypoglycemia."

    # 3. Insulin
    elif "insulin" in d_name:
        if recommended_dose > current_dose:
            action_text = f"🔺 Titration: Adjust from {current_dose:.0f} Units to {recommended_dose:.0f} Units/day."
        elif recommended_dose < current_dose:
            action_text = f"🔻 Reduction: Step down from {current_dose:.0f} Units to {recommended_dose:.0f} Units/day."
        else:
            action_text = f"✅ Maintain: Continue {recommended_dose:.0f} Units/day."

        morning_units = round(recommended_dose * 0.6)
        night_units = round(recommended_dose * 0.4)
        split_plan = f"• Morning (Breakfast): {morning_units} Units (subcutaneous before meal)\n• Afternoon (Lunch): None\n• Night (Dinner): {night_units} Units (subcutaneous before dinner)"
        clinical_note = "Rotate injection sites daily. Keep fast-acting carbohydrates nearby in case of hypoglycemia."

    # 4. Antihypertensives (Amlodipine, Telmisartan, Lisinopril)
    elif "amlodipine" in d_name or "telmisartan" in d_name or "lisinopril" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Dosage Adjusted: Change from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mg/day."
            
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg once daily\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take in the morning with a full glass of water. Maintain consistent hydration."

    # 5. Thyroid (Levothyroxine, Methimazole)
    elif "levothyroxine" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Levothyroxine Titration: Adjust from {current_dose:.0f} mcg to {recommended_dose:.0f} mcg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mcg/day."

        split_plan = f"• Morning (Waking Up): {recommended_dose:.0f} mcg on an empty stomach\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take strictly 30-60 minutes before breakfast with plain water. Avoid calcium or iron supplements within 4 hours."

    elif "methimazole" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Antithyroid Adjustment: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Maintain: Continue {recommended_dose:.0f} mg/day."

        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg with food\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take with meals to prevent gastrointestinal upset."

    # 6. Lipid Lowering (Statins & Fibrates)
    elif "atorvastatin" in d_name or "rosuvastatin" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Statin Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mg/day."

        split_plan = f"• Morning (Breakfast): None\n• Afternoon (Lunch): None\n• Night (Bedtime): {recommended_dose:.0f} mg once daily"
        clinical_note = "Take at bedtime. The liver produces the vast majority of cholesterol while sleeping."

    elif "fenofibrate" in d_name:
        action_text = f"🔄 Dose: {recommended_dose:.0f} mg/day."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg with meal\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take with your morning meal for optimal absorption."

    # 7. Anticoagulants (Warfarin, Apixaban, Rivaroxaban)
    elif "warfarin" in d_name:
        if recommended_dose != current_dose:
            action_text = f"⚠️ Warfarin Titration: Adjust dose from {current_dose:.1f} mg to {recommended_dose:.1f} mg/day based on INR."
        else:
            action_text = f"✅ INR Therapeutic: Maintain {recommended_dose:.1f} mg/day."

        split_plan = f"• Morning (Breakfast): None\n• Afternoon (Lunch): None\n• Night (Dinner/Bedtime): {recommended_dose:.1f} mg once daily"
        clinical_note = "Take at the exact same time every evening. Maintain consistent dietary Vitamin K intake."

    elif "apixaban" in d_name:
        action_text = f"✅ DOAC Schedule: {recommended_dose:.1f} mg twice daily."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.1f} mg\n• Afternoon (Lunch): None\n• Night (Dinner): {recommended_dose:.1f} mg"
        clinical_note = "Take roughly 12 hours apart, with or without food."

    elif "rivaroxaban" in d_name:
        action_text = f"✅ DOAC Schedule: {recommended_dose:.0f} mg once daily."
        split_plan = f"• Morning (Breakfast): None\n• Afternoon (Lunch): None\n• Night (Dinner): {recommended_dose:.0f} mg (must be taken with food)"
        clinical_note = "Take with your evening meal. Food is required for adequate absorption."

    # 8. Heart Failure & Diuretics (Furosemide, Spironolactone)
    elif "furosemide" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Diuretic Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Maintain: Continue {recommended_dose:.0f} mg/day."

        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg\n• Afternoon (Lunch): None\n• Night (Dinner): Avoid"
        clinical_note = "Take early in the day to prevent nighttime urination from disrupting sleep."

    elif "spironolactone" in d_name:
        action_text = f"🔄 Aldosterone Antagonist: {recommended_dose:.0f} mg/day."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg with food\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take with morning food. Regularly monitor serum potassium levels."

    # 9. Gout & Hyperuricemia (Allopurinol, Febuxostat, Colchicine)
    elif "allopurinol" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Urate-Lowering Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Target Reached: Maintain {recommended_dose:.0f} mg/day."

        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg after meal\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take immediately after meals with plenty of fluid (2-3 liters of water daily)."

    elif "febuxostat" in d_name:
        action_text = f"🔄 Dose: {recommended_dose:.0f} mg/day."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Can be taken with or without food."

    elif "colchicine" in d_name:
        action_text = f"🔄 Dose: {recommended_dose:.1f} mg/day."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.1f} mg\n• Afternoon (Lunch): None\n• Night (Dinner): None"
        clinical_note = "Take as prescribed. If severe diarrhea or vomiting occurs, contact your doctor."

    # 10. Respiratory (Salbutamol, Budesonide)
    elif "salbutamol" in d_name or "albuterol" in d_name:
        action_text = f"💨 Bronchodilator: {recommended_dose:.0f} mcg as needed."
        split_plan = "• Morning: 1-2 puffs if symptoms occur\n• Afternoon: 1-2 puffs if symptoms occur\n• Night: 1-2 puffs if symptoms occur"
        clinical_note = "Rescue inhaler. Use prior to strenuous activity or during acute shortness of breath."

    elif "budenoside" in d_name or "budesonide" in d_name:
        action_text = f"💨 Inhaled Corticosteroid: {recommended_dose:.0f} mcg twice daily."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mcg inhaler\n• Afternoon: None\n• Night (Bedtime): {recommended_dose:.0f} mcg inhaler"
        clinical_note = "Always rinse mouth thoroughly with water and spit it out after inhalation to prevent oral thrush."

    # 11. Depression & Anxiety (Sertraline, Escitalopram, Venlafaxine)
    elif "sertraline" in d_name or "escitalopram" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 SSRI Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mg/day."

        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg with food\n• Afternoon: None\n• Night: None"
        clinical_note = "Take in the morning with food to minimize nausea. Do not discontinue abruptly."

    elif "venlafaxine" in d_name:
        action_text = f"🔄 SNRI Titration: Adjust to {recommended_dose:.0f} mg/day."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg with food\n• Afternoon: None\n• Night: None"
        clinical_note = "Take with food at approximately the same time each morning."

    # 12. Rheumatoid Arthritis (Methotrexate, Hydroxychloroquine)
    elif "methotrexate" in d_name:
        action_text = f"⚠️ WEEKLY Dosing: {recommended_dose:.0f} mg ONCE PER WEEK ONLY."
        split_plan = f"• Designated Day: {recommended_dose:.0f} mg once a week (e.g., every Sunday morning)\n• All Other Days: DO NOT TAKE METHOTREXATE"
        clinical_note = "CRITICAL WARNING: Methotrexate is taken once weekly, NOT daily. Folic acid is usually prescribed on off-days."

    elif "hydroxychloroquine" in d_name:
        action_text = f"🔄 DMARD: {recommended_dose:.0f} mg/day."
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg with food\n• Afternoon: None\n• Night: None"
        clinical_note = "Take with food or a glass of milk. Requires annual ophthalmology exams."

    # Generic Fallback
    else:
        action_text = f"Recommended Daily Dose: {recommended_dose:.0f} mg (Current: {current_dose:.0f} mg)"
        split_plan = f"• Morning (Breakfast): {recommended_dose:.0f} mg\n• Afternoon: None\n• Night: None"
        clinical_note = "Take strictly according to your physician's schedule."

    return {
        "action_text": action_text,
        "split_plan": split_plan,
        "clinical_note": clinical_note
    }


def evaluate_disease_management(condition, drug_name, current_dose, vitals, egfr=90, alt=25):
    """
    Evaluates condition-specific vitals and computes titration changes,
    renal/hepatic safety cutoffs, and therapeutic target concordances.
    """
    reasons = []
    recommended_dose = float(current_dose)
    status = "Optimal"
    dose_correct = True
    d_lower = str(drug_name).lower()
    egfr = float(egfr)
    alt = float(alt)

    # -------------------------------------------------------------
    # 1. TYPE 2 DIABETES
    # -------------------------------------------------------------
    if condition == "Diabetes":
        fbs = vitals.get("fbs", 110)
        ppbs = vitals.get("ppbs", 140)
        hba1c = vitals.get("hba1c", 6.5)

        if "metformin" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated / Renal Risk"
                dose_correct = False
                reasons.append(f"CRITICAL: eGFR is {egfr} mL/min (<30). Metformin is contraindicated due to severe lactic acidosis risk.")
            elif egfr < 45:
                if current_dose > 1000:
                    recommended_dose = 1000.0
                    status = "Renal Dose Reduction"
                    dose_correct = False
                    reasons.append(f"Renal Impairment (eGFR {egfr} mL/min): Metformin dosage capped at 1000 mg/day max.")
            else:
                if hba1c > 7.0 or fbs > 130 or ppbs > 180:
                    if current_dose < 2000:
                        recommended_dose = min(current_dose + 500, 2000)
                        status = "Titration Up Recommended"
                        dose_correct = False
                        reasons.append(f"Uncontrolled Glycemia (HbA1c: {hba1c}%, FBS: {fbs} mg/dL). Step up dose toward 2000 mg ceiling.")
                    else:
                        reasons.append("Max therapeutic Metformin dose (2000 mg) reached. Consider adding dual-agent therapy (SGLT2i or DPP-4i).")
                else:
                    reasons.append(f"Glycemic metrics well controlled (HbA1c {hba1c}%, FBS {fbs} mg/dL). Current dose is optimal.")

        elif "glimepiride" in d_lower or "gliclazide" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated / Hypoglycemia Risk"
                dose_correct = False
                reasons.append(f"Severe renal impairment (eGFR {egfr} mL/min). Discontinue sulfonylureas due to prolonged half-life and lethal hypoglycemia risk.")
            elif fbs < 70 or ppbs < 90:
                recommended_dose = max(current_dose - 1.0, 0.0)
                status = "Hypoglycemia Alert"
                dose_correct = False
                reasons.append(f"Hypoglycemia flagged (FBS {fbs} mg/dL). Dose reduction or discontinuation advised.")
            elif hba1c > 7.5 or fbs > 140:
                max_ceiling = 4.0 if "glimepiride" in d_lower else 160.0
                step = 1.0 if "glimepiride" in d_lower else 40.0
                if current_dose < max_ceiling:
                    recommended_dose = min(current_dose + step, max_ceiling)
                    status = "Titration Up"
                    dose_correct = False
                    reasons.append(f"HbA1c elevated at {hba1c}%. Increase dose by {step} mg.")
                else:
                    reasons.append(f"Sulfonylurea maximum ceiling ({max_ceiling} mg) reached.")
            else:
                reasons.append("Sulfonylurea dose maintains stable blood glucose targets.")

        elif "insulin" in d_lower:
            if fbs < 70:
                recommended_dose = max(current_dose - 4.0, 4.0)
                status = "Hypoglycemia Reduction"
                dose_correct = False
                reasons.append(f"Hypoglycemia detected (FBS {fbs} mg/dL). Reduce total daily insulin by 10-20% immediately.")
            elif fbs > 180 or hba1c > 8.0:
                recommended_dose = current_dose + 4.0
                status = "Titration Up"
                dose_correct = False
                reasons.append(f"Persistent fasting hyperglycemia (FBS {fbs} mg/dL). Increase daily basal dose by 2-4 Units.")
            else:
                reasons.append("Insulin dosing maintains target fasting glucose.")

    # -------------------------------------------------------------
    # 2. HYPERTENSION
    # -------------------------------------------------------------
    elif condition == "Hypertension":
        sbp = vitals.get("systolic_bp", 120)
        dbp = vitals.get("diastolic_bp", 80)

        if sbp >= 140 or dbp >= 90:
            status = "Uncontrolled Hypertension"
            dose_correct = False
            if "amlodipine" in d_lower:
                if current_dose < 10.0:
                    recommended_dose = 10.0
                    reasons.append(f"BP elevated ({sbp}/{dbp} mmHg). Titrate Amlodipine from 5 mg to 10 mg daily.")
                else:
                    reasons.append(f"BP uncontrolled at max Amlodipine (10 mg). Recommend adding an ARB (Telmisartan) or ACEi.")
            elif "telmisartan" in d_lower:
                if current_dose < 80.0:
                    recommended_dose = min(current_dose + 40.0, 80.0)
                    reasons.append(f"BP elevated ({sbp}/{dbp} mmHg). Increase Telmisartan to {recommended_dose} mg.")
                else:
                    reasons.append("Max Telmisartan (80 mg) reached. Recommend combination therapy with Amlodipine or Chlorthalidone.")
            elif "lisinopril" in d_lower:
                if current_dose < 40.0:
                    recommended_dose = min(current_dose + 10.0, 40.0)
                    reasons.append(f"BP elevated ({sbp}/{dbp} mmHg). Increase Lisinopril to {recommended_dose} mg.")
        elif sbp < 95 or dbp < 60:
            status = "Hypotension Warning"
            dose_correct = False
            recommended_dose = max(current_dose / 2.0, 2.5)
            reasons.append(f"Hypotension risk flagged (BP {sbp}/{dbp} mmHg). Reduce dosage to prevent orthostatic dizziness.")
        else:
            reasons.append(f"Blood pressure is within clinical target (<130/80 mmHg). Maintain current dosage.")

    # -------------------------------------------------------------
    # 3. THYROID DISORDERS
    # -------------------------------------------------------------
    elif condition == "Thyroid Disorders":
        tsh = vitals.get("tsh", 2.0)
        free_t4 = vitals.get("free_t4", 1.2)

        if "levothyroxine" in d_lower:
            if tsh > 4.5:
                status = "Hypothyroidism / Under-replaced"
                dose_correct = False
                recommended_dose = current_dose + 25.0
                reasons.append(f"TSH elevated at {tsh} mIU/L (Target: 0.4-4.0). Increase Levothyroxine by 25 mcg/day.")
            elif tsh < 0.3:
                status = "Hyperthyroidism / Over-replaced"
                dose_correct = False
                recommended_dose = max(current_dose - 25.0, 25.0)
                reasons.append(f"TSH suppressed at {tsh} mIU/L. Reduce Levothyroxine by 25 mcg/day to prevent cardiac arrhythmias.")
            else:
                reasons.append(f"TSH ({tsh} mIU/L) is euthyroid. Maintain current Levothyroxine dose.")

        elif "methimazole" in d_lower:
            if tsh < 0.1 and free_t4 > 1.8:
                status = "Active Hyperthyroidism"
                dose_correct = False
                recommended_dose = min(current_dose + 5.0, 30.0)
                reasons.append(f"Free T4 elevated ({free_t4} ng/dL). Increase Methimazole to control thyrotoxicosis.")
            elif tsh > 4.0:
                status = "Overtreatment Hypothyroidism"
                dose_correct = False
                recommended_dose = max(current_dose - 5.0, 2.5)
                reasons.append("TSH rising above normal. Titrate down Methimazole dose.")
            else:
                reasons.append("Thyroid function tests well controlled on current Methimazole.")

    # -------------------------------------------------------------
    # 4. HYPERLIPIDEMIA
    # -------------------------------------------------------------
    elif condition == "Hyperlipidemia":
        ldl = vitals.get("ldl_cholesterol", 110)
        tg = vitals.get("triglycerides", 160)

        if "atorvastatin" in d_lower:
            if alt > 120:
                recommended_dose = 0.0
                status = "Hepatic Safety Hold"
                dose_correct = False
                reasons.append(f"Liver ALT is {alt} U/L (>3x ULN). Suspend statin therapy until transaminases normalize.")
            elif ldl > 100:
                status = "Suboptimal LDL Control"
                dose_correct = False
                recommended_dose = min(current_dose * 2.0, 80.0)
                reasons.append(f"LDL elevated at {ldl} mg/dL (Goal <70-100). Step up statin intensity to {recommended_dose:.0f} mg.")
            else:
                reasons.append(f"LDL cholesterol ({ldl} mg/dL) meets cardioprotective target.")

        elif "rosuvastatin" in d_lower:
            if alt > 120:
                recommended_dose = 0.0
                status = "Hepatic Hold"
                dose_correct = False
                reasons.append(f"Elevated ALT ({alt} U/L). Discontinue Rosuvastatin temporarily.")
            elif ldl > 100:
                status = "Suboptimal LDL"
                dose_correct = False
                recommended_dose = min(current_dose + 10.0, 40.0)
                reasons.append(f"LDL is {ldl} mg/dL. Increase Rosuvastatin to {recommended_dose:.0f} mg.")
            else:
                reasons.append("Lipid targets optimal on Rosuvastatin.")

        elif "fenofibrate" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated in CKD"
                dose_correct = False
                reasons.append(f"eGFR {egfr} mL/min (<30). Fenofibrate contraindicated due to acute renal decline risk.")
            elif tg > 200:
                reasons.append(f"Triglycerides elevated ({tg} mg/dL). Maintain or consider lifestyle modifications.")

    # -------------------------------------------------------------
    # 5. CHRONIC KIDNEY DISEASE (CKD)
    # -------------------------------------------------------------
    elif condition == "Chronic Kidney Disease":
        ckd_egfr = vitals.get("egfr", egfr)
        uacr = vitals.get("uacr", 50)

        if "allopurinol" in d_lower:
            if ckd_egfr < 30:
                recommended_dose = min(current_dose, 100.0)
                if current_dose > 100.0:
                    status = "Renal Capped Dose"
                    dose_correct = False
                    reasons.append(f"Severe CKD (eGFR {ckd_egfr}). Allopurinol capped at 100 mg/day max to prevent DRESS/Stevens-Johnson syndrome.")
            elif ckd_egfr < 60:
                recommended_dose = min(current_dose, 200.0)
                if current_dose > 200.0:
                    status = "Renal Dose Adjusted"
                    dose_correct = False
                    reasons.append(f"Moderate CKD (eGFR {ckd_egfr}). Allopurinol capped at 200 mg/day.")
            else:
                reasons.append("Kidney function supports standard Allopurinol clearance.")

        elif "dapagliflozin" in d_lower:
            if ckd_egfr < 20:
                recommended_dose = 0.0
                status = "Contraindicated"
                dose_correct = False
                reasons.append(f"eGFR {ckd_egfr} mL/min is below initiation cutoff (<20). Hold SGLT2 inhibitor.")
            else:
                reasons.append(f"eGFR ({ckd_egfr} mL/min) meets nephroprotective criteria for Dapagliflozin 10 mg.")

    # -------------------------------------------------------------
    # 6. ASTHMA / COPD
    # -------------------------------------------------------------
    elif condition == "Asthma / COPD":
        fev1 = vitals.get("fev1_percent", 75)
        peak_flow = vitals.get("peak_flow", 350)

        if fev1 < 60:
            status = "Poor Respiratory Control"
            dose_correct = False
            if "budenoside" in d_lower or "budesonide" in d_lower:
                recommended_dose = min(current_dose * 2.0, 800.0)
                reasons.append(f"FEV1 markedly reduced ({fev1}%). Step up inhaled corticosteroid to {recommended_dose:.0f} mcg twice daily.")
            elif "salbutamol" in d_lower or "albuterol" in d_lower:
                reasons.append("Frequent rescue inhaler need indicates poor disease control. Add daily controller ICS therapy.")
        else:
            reasons.append(f"FEV1 ({fev1}%) and peak flow indicate stable airway mechanics.")

    # -------------------------------------------------------------
    # 7. HEART FAILURE
    # -------------------------------------------------------------
    elif condition == "Heart Failure":
        ef = vitals.get("ejection_fraction", 45)
        bnp = vitals.get("bnp", 150)

        if "furosemide" in d_lower:
            if bnp > 400:
                status = "Volume Overload / Congestion"
                dose_correct = False
                recommended_dose = min(current_dose + 20.0, 160.0)
                reasons.append(f"Elevated BNP ({bnp} pg/mL) indicates fluid retention. Titrate Furosemide up to {recommended_dose:.0f} mg.")
            elif bnp < 100 and egfr < 45:
                status = "Dehydration / Over-diuresis"
                dose_correct = False
                recommended_dose = max(current_dose - 20.0, 20.0)
                reasons.append("Low BNP with worsening renal function suggests over-diuresis. Reduce loop diuretic.")
            else:
                reasons.append(f"Ejection fraction ({ef}%) and BNP ({bnp} pg/mL) stable on current regimen.")

        elif "spironolactone" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Hyperkalemia Safety Hold"
                dose_correct = False
                reasons.append(f"eGFR {egfr} mL/min (<30). Discontinue Spironolactone due to fatal hyperkalemia risk.")
            else:
                reasons.append("Aldosterone antagonist well tolerated at current renal status.")

    # -------------------------------------------------------------
    # 8. DEPRESSION / ANXIETY
    # -------------------------------------------------------------
    elif condition == "Depression / Anxiety":
        phq9 = vitals.get("phq9", 8)
        gad7 = vitals.get("gad7", 6)

        if "sertraline" in d_lower:
            if phq9 >= 15:
                status = "Inadequate Symptom Remission"
                dose_correct = False
                recommended_dose = min(current_dose + 50.0, 200.0)
                reasons.append(f"PHQ-9 score {phq9} indicates moderate-to-severe depression. Titrate Sertraline toward {recommended_dose:.0f} mg.")
            elif phq9 < 5:
                reasons.append(f"PHQ-9 score {phq9} indicates clinical remission. Maintain current dosage.")
        elif "escitalopram" in d_lower:
            if phq9 >= 15 or gad7 >= 12:
                status = "Inadequate Response"
                dose_correct = False
                recommended_dose = min(current_dose + 5.0, 20.0)
                reasons.append(f"High depression/anxiety scores (PHQ-9: {phq9}, GAD-7: {gad7}). Increase Escitalopram to {recommended_dose:.0f} mg.")
        elif "venlafaxine" in d_lower:
            if phq9 >= 15:
                recommended_dose = min(current_dose + 37.5, 225.0)
                status = "Titration Up"
                dose_correct = False
                reasons.append(f"Elevated PHQ-9 ({phq9}). Step up Venlafaxine to {recommended_dose:.1f} mg.")

    # -------------------------------------------------------------
    # 9. GOUT / HYPERURICEMIA
    # -------------------------------------------------------------
    elif condition == "Gout / Hyperuricemia":
        uric_acid = vitals.get("uric_acid", 6.0)
        flares = vitals.get("flares_per_year", 0)

        if "allopurinol" in d_lower:
            if egfr < 30:
                recommended_dose = min(current_dose, 100.0)
                if current_dose > 100.0:
                    status = "Renal Dose Reduction"
                    dose_correct = False
                    reasons.append(f"CKD Stage 4 (eGFR {egfr}). Allopurinol capped at 100 mg daily.")
            elif uric_acid > 6.0:
                status = "Target Not Achieved"
                dose_correct = False
                recommended_dose = min(current_dose + 100.0, 800.0)
                reasons.append(f"Serum uric acid is {uric_acid} mg/dL (Goal <6.0 mg/dL). Titrate Allopurinol to {recommended_dose:.0f} mg/day.")
            else:
                reasons.append(f"Serum uric acid ({uric_acid} mg/dL) meets therapeutic target.")

        elif "febuxostat" in d_lower:
            if uric_acid > 6.0 and current_dose < 80.0:
                recommended_dose = 80.0
                status = "Titrate Up"
                dose_correct = False
                reasons.append(f"Uric acid elevated ({uric_acid} mg/dL). Increase Febuxostat to 80 mg.")
            else:
                reasons.append("Uric acid controlled on Febuxostat.")

        elif "colchicine" in d_lower:
            if egfr < 30:
                recommended_dose = 0.3
                status = "Renal Dose Reduction"
                dose_correct = False
                reasons.append(f"Severe renal impairment (eGFR {egfr}). Reduce Colchicine to 0.3 mg or alternative days to avoid neuro-myopathy.")

    # -------------------------------------------------------------
    # 10. ATRIAL FIBRILLATION
    # -------------------------------------------------------------
    elif condition == "Atrial Fibrillation":
        inr = vitals.get("inr", 2.5)

        if "warfarin" in d_lower:
            if inr > 3.5:
                status = "Supratherapeutic INR / Major Bleed Risk"
                dose_correct = False
                recommended_dose = max(current_dose * 0.8, 1.0)
                reasons.append(f"CRITICAL: INR is {inr} (>3.0 target). Hold 1 dose and reduce weekly Warfarin by 15-20%.")
            elif inr < 2.0:
                status = "Subtherapeutic INR / Thromboembolism Risk"
                dose_correct = False
                recommended_dose = current_dose * 1.15
                reasons.append(f"INR is {inr} (<2.0 target). Increase weekly Warfarin dose by 10-15%.")
            else:
                reasons.append(f"INR is within therapeutic window (2.0 - 3.0). Dosing is optimal.")

        elif "apixaban" in d_lower:
            if egfr < 25:
                recommended_dose = 2.5
                status = "Renal Dose Adjustment"
                dose_correct = False
                reasons.append(f"Reduced eGFR ({egfr} mL/min). Reduce Apixaban to 2.5 mg twice daily.")
            else:
                reasons.append("Standard Apixaban 5 mg BID dosing safe at current renal function.")

        elif "rivaroxaban" in d_lower:
            if egfr < 50:
                recommended_dose = 15.0
                status = "Renal Dose Adjustment"
                dose_correct = False
                reasons.append(f"Moderate renal impairment (eGFR {egfr} mL/min). Reduce Rivaroxaban to 15 mg once daily.")
            else:
                reasons.append("Standard Rivaroxaban 20 mg once daily is appropriate.")

    # -------------------------------------------------------------
    # 11. RHEUMATOID ARTHRITIS
    # -------------------------------------------------------------
    elif condition == "Rheumatoid Arthritis":
        crp = vitals.get("crp", 3.0)
        esr = vitals.get("esr", 15)

        if "methotrexate" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated in Severe CKD"
                dose_correct = False
                reasons.append(f"eGFR {egfr} mL/min (<30). Methotrexate is contraindicated due to toxic bone marrow suppression.")
            elif alt > 80:
                recommended_dose = 0.0
                status = "Hepatotoxicity Hold"
                dose_correct = False
                reasons.append(f"ALT elevated at {alt} U/L (>2x ULN). Suspend Methotrexate and re-evaluate transaminases.")
            elif crp > 10.0 or esr > 30:
                if current_dose < 25.0:
                    recommended_dose = min(current_dose + 2.5, 25.0)
                    status = "Titrate Up (Weekly)"
                    dose_correct = False
                    reasons.append(f"Elevated inflammatory markers (CRP: {crp} mg/L, ESR: {esr} mm/hr). Increase weekly dose toward 20-25 mg.")
                else:
                    reasons.append("Maximum tolerated weekly Methotrexate dose reached. Consider biologic DMARD addition.")
            else:
                reasons.append(f"Inflammatory biomarkers normalized (CRP {crp} mg/L, ESR {esr} mm/hr).")

        elif "hydroxychloroquine" in d_lower:
            if egfr < 30:
                recommended_dose = min(current_dose * 0.75, 200.0)
                status = "Renal Dose Reduction"
                dose_correct = False
                reasons.append(f"eGFR {egfr} mL/min. Reduce Hydroxychloroquine to prevent ocular and systemic accumulation.")
            else:
                reasons.append("Standard Hydroxychloroquine dosing maintains disease stability.")

    return {
        "condition": condition,
        "drug": drug_name,
        "current_dose_mg": float(current_dose),
        "recommended_dose_mg": round(float(recommended_dose), 1),
        "dose_correct": dose_correct,
        "status": status,
        "reasons": reasons
    }