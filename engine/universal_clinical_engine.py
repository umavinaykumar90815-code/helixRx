"""
HelixRx Universal Clinical Engine
Comprehensive clinical decision support across 11 chronic conditions.
Handles dynamic auto-titration, renal/hepatic safety thresholds,
and meal-by-meal administration schedule generation (Morning, Afternoon, Night).
"""

def generate_meal_titration_instruction(drug_name, current_dose, recommended_dose):
    """
    Translates raw dose titration numbers into structured meal data
    for Breakfast (Morning), Lunch (Afternoon), and Dinner (Night) visual cards.
    """
    d_name = str(drug_name).lower()
    current_dose = float(current_dose)
    recommended_dose = float(recommended_dose)
    
    # Defaults
    morning_dose = "—"
    morning_timing = "None"
    afternoon_dose = "—"
    afternoon_timing = "None"
    night_dose = "—"
    night_timing = "None"
    clinical_note = "Take strictly as prescribed by your treating physician."
    action_text = f"Target Dose: {recommended_dose:.0f} mg/day"

    # 1. Metformin
    if "metformin" in d_name:
        if recommended_dose > current_dose:
            action_text = f"🔺 Dose Increase Recommended: Step up from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        elif recommended_dose < current_dose:
            action_text = f"🔻 Dose Reduction Required: Reduce from {current_dose:.0f} mg down to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Maintain Current Dose: Keep taking {recommended_dose:.0f} mg/day."

        if recommended_dose <= 0:
            clinical_note = "Medication held due to organ safety or clinical contraindication."
        elif recommended_dose <= 500:
            night_dose = "500 mg"
            night_timing = "With dinner meal"
            clinical_note = "Take with dinner to reduce stomach discomfort."
        elif recommended_dose <= 1000:
            morning_dose = "500 mg"
            morning_timing = "With breakfast"
            night_dose = "500 mg"
            night_timing = "With dinner"
            clinical_note = "Split evenly across breakfast and dinner."
        elif recommended_dose <= 1500:
            morning_dose = "500 mg"
            morning_timing = "With breakfast"
            afternoon_dose = "500 mg"
            afternoon_timing = "With lunch"
            night_dose = "500 mg"
            night_timing = "With dinner"
            clinical_note = "Take 500 mg with each of your 3 main meals."
        else:  # 2000 mg max
            morning_dose = "1000 mg"
            morning_timing = "With breakfast"
            night_dose = "1000 mg"
            night_timing = "With dinner"
            clinical_note = "Maximum daily ceiling (2000 mg) reached. Always take with food."

    # 2. Glimepiride / Gliclazide (Sulfonylureas)
    elif "glimepiride" in d_name or "gliclazide" in d_name:
        unit = "mg"
        if recommended_dose > current_dose:
            action_text = f"🔺 Titration Recommended: Increase from {current_dose:.1f} mg to {recommended_dose:.1f} mg/day."
        elif recommended_dose < current_dose:
            action_text = f"🔻 Dose Lowered: Reduce from {current_dose:.1f} mg down to {recommended_dose:.1f} mg/day."
        else:
            action_text = f"✅ Maintain Current Dose: Continue {recommended_dose:.1f} mg/day."

        if recommended_dose <= 0:
            clinical_note = "Discontinued due to hypoglycemia risk or contraindication."
        elif recommended_dose <= 2:
            afternoon_dose = f"{recommended_dose:.1f} {unit}"
            afternoon_timing = "15-30 mins BEFORE lunch"
            clinical_note = "Take strictly before your main meal. Never skip lunch after taking this tablet."
        else:
            half = recommended_dose / 2.0
            morning_dose = f"{half:.1f} {unit}"
            morning_timing = "15-30 mins BEFORE breakfast"
            afternoon_dose = f"{half:.1f} {unit}"
            afternoon_timing = "15-30 mins BEFORE lunch"
            clinical_note = "Split across morning and afternoon meals. Avoid taking at bedtime to prevent nocturnal hypoglycemia."

    # 3. Insulin
    elif "insulin" in d_name:
        if recommended_dose > current_dose:
            action_text = f"🔺 Titration: Adjust from {current_dose:.0f} Units to {recommended_dose:.0f} Units/day."
        elif recommended_dose < current_dose:
            action_text = f"🔻 Reduction: Step down from {current_dose:.0f} Units to {recommended_dose:.0f} Units/day."
        else:
            action_text = f"✅ Maintain: Continue {recommended_dose:.0f} Units/day."

        morning_dose = f"{round(recommended_dose * 0.6)} Units"
        morning_timing = "Subcutaneous injection before breakfast"
        night_dose = f"{round(recommended_dose * 0.4)} Units"
        night_timing = "Subcutaneous injection before dinner"
        clinical_note = "Rotate injection sites daily. Keep fast-acting carbohydrates nearby."

    # 4. Antihypertensives (Amlodipine, Telmisartan, Lisinopril)
    elif "amlodipine" in d_name or "telmisartan" in d_name or "lisinopril" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Dosage Adjusted: Change from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mg/day."
            
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "Every morning with a glass of water"
        clinical_note = "Take consistently at roughly the same time each morning."

    # 5. Thyroid (Levothyroxine, Methimazole)
    elif "levothyroxine" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Levothyroxine Titration: Adjust from {current_dose:.0f} mcg to {recommended_dose:.0f} mcg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mcg/day."

        morning_dose = f"{recommended_dose:.0f} mcg"
        morning_timing = "First thing in morning on empty stomach"
        clinical_note = "Take 30-60 minutes before breakfast with plain water. Avoid calcium or iron supplements within 4 hours."

    elif "methimazole" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Antithyroid Adjustment: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Maintain: Continue {recommended_dose:.0f} mg/day."

        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "With breakfast"
        clinical_note = "Take with food to minimize stomach upset."

    # 6. Lipid Lowering (Statins & Fibrates)
    elif "atorvastatin" in d_name or "rosuvastatin" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Statin Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mg/day."

        night_dose = f"{recommended_dose:.0f} mg"
        night_timing = "Bedtime / After dinner"
        clinical_note = "Take at bedtime because the liver produces most cholesterol overnight."

    elif "fenofibrate" in d_name:
        action_text = f"🔄 Dose: {recommended_dose:.0f} mg/day."
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "With morning meal"
        clinical_note = "Take with your morning meal for optimal absorption."

    # 7. Anticoagulants (Warfarin, Apixaban, Rivaroxaban)
    elif "warfarin" in d_name:
        if recommended_dose != current_dose:
            action_text = f"⚠️ Warfarin Titration: Adjust from {current_dose:.1f} mg to {recommended_dose:.1f} mg/day based on INR."
        else:
            action_text = f"✅ INR Therapeutic: Maintain {recommended_dose:.1f} mg/day."

        night_dose = f"{recommended_dose:.1f} mg"
        night_timing = "Every evening at same time"
        clinical_note = "Maintain consistent dietary Vitamin K intake."

    elif "apixaban" in d_name:
        action_text = f"✅ DOAC Regimen: {recommended_dose:.1f} mg twice daily."
        morning_dose = f"{recommended_dose:.1f} mg"
        morning_timing = "Morning with or without food"
        night_dose = f"{recommended_dose:.1f} mg"
        night_timing = "Night (~12 hours after morning dose)"
        clinical_note = "Take roughly 12 hours apart."

    elif "rivaroxaban" in d_name:
        action_text = f"✅ DOAC Regimen: {recommended_dose:.0f} mg once daily."
        night_dose = f"{recommended_dose:.0f} mg"
        night_timing = "With dinner / evening meal"
        clinical_note = "Must be taken with an evening meal for adequate absorption."

    # 8. Heart Failure & Diuretics (Furosemide, Spironolactone)
    elif "furosemide" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Diuretic Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Maintain: Continue {recommended_dose:.0f} mg/day."

        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "Morning with water"
        clinical_note = "Take early in the morning to prevent frequent nighttime urination."

    elif "spironolactone" in d_name:
        action_text = f"🔄 Aldosterone Antagonist: {recommended_dose:.0f} mg/day."
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "With breakfast"
        clinical_note = "Take with food and monitor serum potassium."

    # 9. Gout & Hyperuricemia (Allopurinol, Febuxostat, Colchicine)
    elif "allopurinol" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 Urate-Lowering Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Target Reached: Maintain {recommended_dose:.0f} mg/day."

        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "Immediately after breakfast"
        clinical_note = "Drink plenty of water (at least 2-3 liters throughout the day)."

    elif "febuxostat" in d_name:
        action_text = f"🔄 Dose: {recommended_dose:.0f} mg/day."
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "Morning with or without food"
        clinical_note = "Can be taken with or without food."

    elif "colchicine" in d_name:
        action_text = f"🔄 Dose: {recommended_dose:.1f} mg/day."
        morning_dose = f"{recommended_dose:.1f} mg"
        morning_timing = "Morning with food"
        clinical_note = "Discontinue if severe diarrhea or abdominal pain develops."

    # 10. Respiratory (Salbutamol, Budesonide)
    elif "salbutamol" in d_name or "albuterol" in d_name:
        action_text = f"💨 Bronchodilator: {recommended_dose:.0f} mcg as needed."
        morning_dose = "1-2 puffs"
        morning_timing = "If symptoms occur"
        afternoon_dose = "1-2 puffs"
        afternoon_timing = "If symptoms occur"
        night_dose = "1-2 puffs"
        night_timing = "If symptoms occur"
        clinical_note = "Rescue inhaler for acute shortness of breath."

    elif "budenoside" in d_name or "budesonide" in d_name:
        action_text = f"💨 Inhaled Corticosteroid: {recommended_dose:.0f} mcg twice daily."
        morning_dose = f"{recommended_dose:.0f} mcg"
        morning_timing = "Inhaler after waking"
        night_dose = f"{recommended_dose:.0f} mcg"
        night_timing = "Inhaler before bedtime"
        clinical_note = "Always rinse mouth with water and spit it out after inhalation."

    # 11. Depression & Anxiety (Sertraline, Escitalopram, Venlafaxine)
    elif "sertraline" in d_name or "escitalopram" in d_name:
        if recommended_dose != current_dose:
            action_text = f"🔄 SSRI Titration: Adjust from {current_dose:.0f} mg to {recommended_dose:.0f} mg/day."
        else:
            action_text = f"✅ Optimal: Maintain {recommended_dose:.0f} mg/day."

        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "With breakfast"
        clinical_note = "Take in the morning with food. Do not stop abruptly."

    elif "venlafaxine" in d_name:
        action_text = f"🔄 SNRI Titration: Adjust to {recommended_dose:.0f} mg/day."
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "With breakfast"
        clinical_note = "Take with food at approximately the same time each morning."

    # 12. Rheumatoid Arthritis (Methotrexate, Hydroxychloroquine)
    elif "methotrexate" in d_name:
        action_text = f"⚠️ WEEKLY Dosing: {recommended_dose:.0f} mg ONCE PER WEEK ONLY."
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "Designated day once weekly (e.g. Sunday morning)"
        clinical_note = "CRITICAL WARNING: Methotrexate is taken once a week, never daily."

    elif "hydroxychloroquine" in d_name:
        action_text = f"🔄 DMARD: {recommended_dose:.0f} mg/day."
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "With breakfast or milk"
        clinical_note = "Take with food or a glass of milk."

    # Fallback
    else:
        morning_dose = f"{recommended_dose:.0f} mg"
        morning_timing = "Morning with water"
        action_text = f"Target Dose: {recommended_dose:.0f} mg/day"
        clinical_note = "Take strictly according to physician instructions."

    split_plan_text = f"• Morning: {morning_dose} ({morning_timing})\n• Afternoon: {afternoon_dose} ({afternoon_timing})\n• Night: {night_dose} ({night_timing})"

    return {
        "action_text": action_text,
        "split_plan": split_plan_text,
        "morning_dose": morning_dose,
        "morning_timing": morning_timing,
        "afternoon_dose": afternoon_dose,
        "afternoon_timing": afternoon_timing,
        "night_dose": night_dose,
        "night_timing": night_timing,
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
        fbs = float(vitals.get("fbs", 110))
        ppbs = float(vitals.get("ppbs", 140))
        hba1c = float(vitals.get("hba1c", 6.5))

        if "metformin" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated / Renal Risk"
                dose_correct = False
                reasons.append(f"CRITICAL: eGFR is {egfr:.0f} mL/min (<30). Metformin is contraindicated due to severe lactic acidosis risk.")
            elif egfr < 45:
                if current_dose > 1000:
                    recommended_dose = 1000.0
                    status = "Renal Dose Reduction"
                    dose_correct = False
                    reasons.append(f"Renal Impairment (eGFR {egfr:.0f} mL/min): Metformin dosage capped at 1000 mg/day max.")
            else:
                if hba1c > 7.0 or fbs > 130 or ppbs > 180:
                    if current_dose < 2000:
                        recommended_dose = min(current_dose + 500, 2000)
                        status = "Titration Up Recommended"
                        dose_correct = False
                        reasons.append(f"Uncontrolled Glycemia (HbA1c: {hba1c}%, FBS: {fbs:.0f} mg/dL). Step up dose toward 2000 mg ceiling.")
                    else:
                        reasons.append("Max therapeutic Metformin dose (2000 mg) reached. Consider adding dual-agent therapy (SGLT2i or DPP-4i).")
                else:
                    reasons.append(f"Glycemic metrics well controlled (HbA1c {hba1c}%, FBS {fbs:.0f} mg/dL). Current dose is optimal.")

        elif "glimepiride" in d_lower or "gliclazide" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated / Hypoglycemia Risk"
                dose_correct = False
                reasons.append(f"Severe renal impairment (eGFR {egfr:.0f} mL/min). Discontinue sulfonylureas due to prolonged half-life and lethal hypoglycemia risk.")
            elif fbs < 70 or ppbs < 90:
                recommended_dose = max(current_dose - 1.0, 0.0)
                status = "Hypoglycemia Alert"
                dose_correct = False
                reasons.append(f"Hypoglycemia flagged (FBS {fbs:.0f} mg/dL). Dose reduction or discontinuation advised.")
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
                reasons.append(f"Hypoglycemia detected (FBS {fbs:.0f} mg/dL). Reduce total daily insulin by 10-20% immediately.")
            elif fbs > 180 or hba1c > 8.0:
                recommended_dose = current_dose + 4.0
                status = "Titration Up"
                dose_correct = False
                reasons.append(f"Persistent fasting hyperglycemia (FBS {fbs:.0f} mg/dL). Increase daily basal dose by 2-4 Units.")
            else:
                reasons.append("Insulin dosing maintains target fasting glucose.")

    # -------------------------------------------------------------
    # 2. HYPERTENSION
    # -------------------------------------------------------------
    elif condition == "Hypertension":
        sbp = float(vitals.get("systolic_bp", 120))
        dbp = float(vitals.get("diastolic_bp", 80))

        if sbp >= 140 or dbp >= 90:
            status = "Uncontrolled Hypertension"
            dose_correct = False
            if "amlodipine" in d_lower:
                if current_dose < 10.0:
                    recommended_dose = 10.0
                    reasons.append(f"BP elevated ({sbp:.0f}/{dbp:.0f} mmHg). Titrate Amlodipine from 5 mg to 10 mg daily.")
                else:
                    reasons.append("BP uncontrolled at max Amlodipine (10 mg). Recommend adding an ARB (Telmisartan) or ACEi.")
            elif "telmisartan" in d_lower:
                if current_dose < 80.0:
                    recommended_dose = min(current_dose + 40.0, 80.0)
                    reasons.append(f"BP elevated ({sbp:.0f}/{dbp:.0f} mmHg). Increase Telmisartan to {recommended_dose:.0f} mg.")
                else:
                    reasons.append("Max Telmisartan (80 mg) reached. Recommend combination therapy with Amlodipine.")
            elif "lisinopril" in d_lower:
                if current_dose < 40.0:
                    recommended_dose = min(current_dose + 10.0, 40.0)
                    reasons.append(f"BP elevated ({sbp:.0f}/{dbp:.0f} mmHg). Increase Lisinopril to {recommended_dose:.0f} mg.")
        elif sbp < 95 or dbp < 60:
            status = "Hypotension Warning"
            dose_correct = False
            recommended_dose = max(current_dose / 2.0, 2.5)
            reasons.append(f"Hypotension risk flagged (BP {sbp:.0f}/{dbp:.0f} mmHg). Reduce dosage to prevent orthostatic dizziness.")
        else:
            reasons.append("Blood pressure is within clinical target (<130/80 mmHg). Maintain current dosage.")

    # -------------------------------------------------------------
    # 3. THYROID DISORDERS
    # -------------------------------------------------------------
    elif condition == "Thyroid Disorders":
        tsh = float(vitals.get("tsh", 2.0))
        free_t4 = float(vitals.get("free_t4", 1.2))

        if "levothyroxine" in d_lower:
            if tsh > 4.5:
                status = "Hypothyroidism / Under-replaced"
                dose_correct = False
                recommended_dose = current_dose + 25.0
                reasons.append(f"TSH elevated at {tsh:.1f} mIU/L (Target: 0.4-4.0). Increase Levothyroxine by 25 mcg/day.")
            elif tsh < 0.3:
                status = "Hyperthyroidism / Over-replaced"
                dose_correct = False
                recommended_dose = max(current_dose - 25.0, 25.0)
                reasons.append(f"TSH suppressed at {tsh:.1f} mIU/L. Reduce Levothyroxine by 25 mcg/day.")
            else:
                reasons.append(f"TSH ({tsh:.1f} mIU/L) is euthyroid. Maintain current Levothyroxine dose.")

        elif "methimazole" in d_lower:
            if tsh < 0.1 and free_t4 > 1.8:
                status = "Active Hyperthyroidism"
                dose_correct = False
                recommended_dose = min(current_dose + 5.0, 30.0)
                reasons.append(f"Free T4 elevated ({free_t4:.1f} ng/dL). Increase Methimazole to control thyrotoxicosis.")
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
        ldl = float(vitals.get("ldl_cholesterol", 110))
        tg = float(vitals.get("triglycerides", 160))

        if "atorvastatin" in d_lower:
            if alt > 120:
                recommended_dose = 0.0
                status = "Hepatic Safety Hold"
                dose_correct = False
                reasons.append(f"Liver ALT is {alt:.0f} U/L (>3x ULN). Suspend statin therapy until transaminases normalize.")
            elif ldl > 100:
                status = "Suboptimal LDL Control"
                dose_correct = False
                recommended_dose = min(current_dose * 2.0, 80.0)
                reasons.append(f"LDL elevated at {ldl:.0f} mg/dL (Goal <70-100). Step up statin intensity to {recommended_dose:.0f} mg.")
            else:
                reasons.append(f"LDL cholesterol ({ldl:.0f} mg/dL) meets cardioprotective target.")

        elif "rosuvastatin" in d_lower:
            if alt > 120:
                recommended_dose = 0.0
                status = "Hepatic Hold"
                dose_correct = False
                reasons.append(f"Elevated ALT ({alt:.0f} U/L). Discontinue Rosuvastatin temporarily.")
            elif ldl > 100:
                status = "Suboptimal LDL"
                dose_correct = False
                recommended_dose = min(current_dose + 10.0, 40.0)
                reasons.append(f"LDL is {ldl:.0f} mg/dL. Increase Rosuvastatin to {recommended_dose:.0f} mg.")
            else:
                reasons.append("Lipid targets optimal on Rosuvastatin.")

        elif "fenofibrate" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated in CKD"
                dose_correct = False
                reasons.append(f"eGFR {egfr:.0f} mL/min (<30). Fenofibrate contraindicated due to acute renal decline risk.")
            elif tg > 200:
                reasons.append(f"Triglycerides elevated ({tg:.0f} mg/dL). Maintain or consider lifestyle modifications.")

    # -------------------------------------------------------------
    # 5. CHRONIC KIDNEY DISEASE (CKD)
    # -------------------------------------------------------------
    elif condition == "Chronic Kidney Disease":
        ckd_egfr = float(vitals.get("egfr", egfr))
        uacr = float(vitals.get("uacr", 50))

        if "allopurinol" in d_lower:
            if ckd_egfr < 30:
                recommended_dose = min(current_dose, 100.0)
                if current_dose > 100.0:
                    status = "Renal Capped Dose"
                    dose_correct = False
                    reasons.append(f"Severe CKD (eGFR {ckd_egfr:.0f}). Allopurinol capped at 100 mg/day max.")
            elif ckd_egfr < 60:
                recommended_dose = min(current_dose, 200.0)
                if current_dose > 200.0:
                    status = "Renal Dose Adjusted"
                    dose_correct = False
                    reasons.append(f"Moderate CKD (eGFR {ckd_egfr:.0f}). Allopurinol capped at 200 mg/day.")
            else:
                reasons.append("Kidney function supports standard Allopurinol clearance.")

        elif "dapagliflozin" in d_lower:
            if ckd_egfr < 20:
                recommended_dose = 0.0
                status = "Contraindicated"
                dose_correct = False
                reasons.append(f"eGFR {ckd_egfr:.0f} mL/min is below initiation cutoff (<20). Hold SGLT2 inhibitor.")
            else:
                reasons.append(f"eGFR ({ckd_egfr:.0f} mL/min) meets nephroprotective criteria for Dapagliflozin 10 mg.")

    # -------------------------------------------------------------
    # 6. ASTHMA / COPD
    # -------------------------------------------------------------
    elif condition == "Asthma / COPD":
        fev1 = float(vitals.get("fev1_percent", 75))
        peak_flow = float(vitals.get("peak_flow", 350))

        if fev1 < 60:
            status = "Poor Respiratory Control"
            dose_correct = False
            if "budenoside" in d_lower or "budesonide" in d_lower:
                recommended_dose = min(current_dose * 2.0, 800.0)
                reasons.append(f"FEV1 markedly reduced ({fev1:.0f}%). Step up inhaled corticosteroid to {recommended_dose:.0f} mcg twice daily.")
            elif "salbutamol" in d_lower or "albuterol" in d_lower:
                reasons.append("Frequent rescue inhaler need indicates poor disease control. Add daily controller ICS therapy.")
        else:
            reasons.append(f"FEV1 ({fev1:.0f}%) and peak flow indicate stable airway mechanics.")

    # -------------------------------------------------------------
    # 7. HEART FAILURE
    # -------------------------------------------------------------
    elif condition == "Heart Failure":
        ef = float(vitals.get("ejection_fraction", 45))
        bnp = float(vitals.get("bnp", 150))

        if "furosemide" in d_lower:
            if bnp > 400:
                status = "Volume Overload / Congestion"
                dose_correct = False
                recommended_dose = min(current_dose + 20.0, 160.0)
                reasons.append(f"Elevated BNP ({bnp:.0f} pg/mL) indicates fluid retention. Titrate Furosemide up to {recommended_dose:.0f} mg.")
            elif bnp < 100 and egfr < 45:
                status = "Dehydration / Over-diuresis"
                dose_correct = False
                recommended_dose = max(current_dose - 20.0, 20.0)
                reasons.append("Low BNP with worsening renal function suggests over-diuresis. Reduce loop diuretic.")
            else:
                reasons.append(f"Ejection fraction ({ef:.0f}%) and BNP ({bnp:.0f} pg/mL) stable on current regimen.")

        elif "spironolactone" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Hyperkalemia Safety Hold"
                dose_correct = False
                reasons.append(f"eGFR {egfr:.0f} mL/min (<30). Discontinue Spironolactone due to fatal hyperkalemia risk.")
            else:
                reasons.append("Aldosterone antagonist well tolerated at current renal status.")

    # -------------------------------------------------------------
    # 8. DEPRESSION / ANXIETY
    # -------------------------------------------------------------
    elif condition == "Depression / Anxiety":
        phq9 = float(vitals.get("phq9", 8))
        gad7 = float(vitals.get("gad7", 6))

        if "sertraline" in d_lower:
            if phq9 >= 15:
                status = "Inadequate Symptom Remission"
                dose_correct = False
                recommended_dose = min(current_dose + 50.0, 200.0)
                reasons.append(f"PHQ-9 score {phq9:.0f} indicates moderate-to-severe depression. Titrate Sertraline toward {recommended_dose:.0f} mg.")
            elif phq9 < 5:
                reasons.append(f"PHQ-9 score {phq9:.0f} indicates clinical remission. Maintain current dosage.")
        elif "escitalopram" in d_lower:
            if phq9 >= 15 or gad7 >= 12:
                status = "Inadequate Response"
                dose_correct = False
                recommended_dose = min(current_dose + 5.0, 20.0)
                reasons.append(f"High depression/anxiety scores (PHQ-9: {phq9:.0f}, GAD-7: {gad7:.0f}). Increase Escitalopram to {recommended_dose:.0f} mg.")
        elif "venlafaxine" in d_lower:
            if phq9 >= 15:
                recommended_dose = min(current_dose + 37.5, 225.0)
                status = "Titration Up"
                dose_correct = False
                reasons.append(f"Elevated PHQ-9 ({phq9:.0f}). Step up Venlafaxine to {recommended_dose:.1f} mg.")

    # -------------------------------------------------------------
    # 9. GOUT / HYPERURICEMIA
    # -------------------------------------------------------------
    elif condition == "Gout / Hyperuricemia":
        uric_acid = float(vitals.get("uric_acid", 6.0))

        if "allopurinol" in d_lower:
            if egfr < 30:
                recommended_dose = min(current_dose, 100.0)
                if current_dose > 100.0:
                    status = "Renal Dose Reduction"
                    dose_correct = False
                    reasons.append(f"CKD Stage 4 (eGFR {egfr:.0f}). Allopurinol capped at 100 mg daily.")
            elif uric_acid > 6.0:
                status = "Target Not Achieved"
                dose_correct = False
                recommended_dose = min(current_dose + 100.0, 800.0)
                reasons.append(f"Serum uric acid is {uric_acid:.1f} mg/dL (Goal <6.0 mg/dL). Titrate Allopurinol to {recommended_dose:.0f} mg/day.")
            else:
                reasons.append(f"Serum uric acid ({uric_acid:.1f} mg/dL) meets therapeutic target.")

        elif "febuxostat" in d_lower:
            if uric_acid > 6.0 and current_dose < 80.0:
                recommended_dose = 80.0
                status = "Titrate Up"
                dose_correct = False
                reasons.append(f"Uric acid elevated ({uric_acid:.1f} mg/dL). Increase Febuxostat to 80 mg.")
            else:
                reasons.append("Uric acid controlled on Febuxostat.")

        elif "colchicine" in d_lower:
            if egfr < 30:
                recommended_dose = 0.3
                status = "Renal Dose Reduction"
                dose_correct = False
                reasons.append(f"Severe renal impairment (eGFR {egfr:.0f}). Reduce Colchicine to 0.3 mg to avoid toxicity.")

    # -------------------------------------------------------------
    # 10. ATRIAL FIBRILLATION
    # -------------------------------------------------------------
    elif condition == "Atrial Fibrillation":
        inr = float(vitals.get("inr", 2.5))

        if "warfarin" in d_lower:
            if inr > 3.5:
                status = "Supratherapeutic INR / Major Bleed Risk"
                dose_correct = False
                recommended_dose = max(current_dose * 0.8, 1.0)
                reasons.append(f"CRITICAL: INR is {inr:.1f} (>3.0 target). Hold 1 dose and reduce weekly Warfarin by 15-20%.")
            elif inr < 2.0:
                status = "Subtherapeutic INR / Thromboembolism Risk"
                dose_correct = False
                recommended_dose = current_dose * 1.15
                reasons.append(f"INR is {inr:.1f} (<2.0 target). Increase weekly Warfarin dose by 10-15%.")
            else:
                reasons.append("INR is within therapeutic window (2.0 - 3.0). Dosing is optimal.")

        elif "apixaban" in d_lower:
            if egfr < 25:
                recommended_dose = 2.5
                status = "Renal Dose Adjustment"
                dose_correct = False
                reasons.append(f"Reduced eGFR ({egfr:.0f} mL/min). Reduce Apixaban to 2.5 mg twice daily.")
            else:
                reasons.append("Standard Apixaban 5 mg BID dosing safe at current renal function.")

        elif "rivaroxaban" in d_lower:
            if egfr < 50:
                recommended_dose = 15.0
                status = "Renal Dose Adjustment"
                dose_correct = False
                reasons.append(f"Moderate renal impairment (eGFR {egfr:.0f} mL/min). Reduce Rivaroxaban to 15 mg once daily.")
            else:
                reasons.append("Standard Rivaroxaban 20 mg once daily is appropriate.")

    # -------------------------------------------------------------
    # 11. RHEUMATOID ARTHRITIS
    # -------------------------------------------------------------
    elif condition == "Rheumatoid Arthritis":
        crp = float(vitals.get("crp", 3.0))
        esr = float(vitals.get("esr", 15))

        if "methotrexate" in d_lower:
            if egfr < 30:
                recommended_dose = 0.0
                status = "Contraindicated in Severe CKD"
                dose_correct = False
                reasons.append(f"eGFR {egfr:.0f} mL/min (<30). Methotrexate is contraindicated due to toxic bone marrow suppression.")
            elif alt > 80:
                recommended_dose = 0.0
                status = "Hepatotoxicity Hold"
                dose_correct = False
                reasons.append(f"ALT elevated at {alt:.0f} U/L (>2x ULN). Suspend Methotrexate and re-evaluate.")
            elif crp > 10.0 or esr > 30:
                if current_dose < 25.0:
                    recommended_dose = min(current_dose + 2.5, 25.0)
                    status = "Titrate Up (Weekly)"
                    dose_correct = False
                    reasons.append(f"Elevated inflammatory markers (CRP: {crp:.1f} mg/L, ESR: {esr:.0f} mm/hr). Increase weekly dose toward 20-25 mg.")
                else:
                    reasons.append("Maximum tolerated weekly Methotrexate dose reached.")
            else:
                reasons.append("Inflammatory biomarkers normalized.")

        elif "hydroxychloroquine" in d_lower:
            if egfr < 30:
                recommended_dose = min(current_dose * 0.75, 200.0)
                status = "Renal Dose Reduction"
                dose_correct = False
                reasons.append(f"eGFR {egfr:.0f} mL/min. Reduce Hydroxychloroquine to prevent systemic accumulation.")
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


