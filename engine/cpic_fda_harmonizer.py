import json
import os

def load_json_data(filepath):
    """Utility to safely load local JSON files."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r') as f:
        return json.load(f)

def harmonize_guidelines(selected_drug, patient_phenotypes):
    """
    Cross-references patient phenotypes against CPIC and FDA databases.
    Handles case-insensitive drug name matching for custom tablet inputs.
    """
    cpic_db = load_json_data("data/guidelines/cpic_rules.json")
    fda_db = load_json_data("data/guidelines/fda_table.json")
    
    # Case-insensitive lookup matching
    matched_cpic_drug = next((k for k in cpic_db if k.lower() == selected_drug.lower()), selected_drug)
    matched_fda_drug = next((k for k in fda_db if k.lower() == selected_drug.lower()), selected_drug)

    analysis_results = []
    
    for item in patient_phenotypes:
        gene = item.get("gene")
        phenotype = item.get("phenotype")
        
        cpic_rule = cpic_db.get(matched_cpic_drug, {}).get(gene, {}).get(phenotype, None)
        fda_rule = fda_db.get(matched_fda_drug, {}).get(gene, {}).get(phenotype, None)
        
        # Determine guideline discrepancies
        discrepancy_flag = False
        if cpic_rule and not fda_rule:
            discrepancy_flag = True
            discrepancy_note = "Actionable CPIC guideline available; not explicitly detailed in FDA Table."
        elif fda_rule and not cpic_rule:
            discrepancy_flag = True
            discrepancy_note = "FDA labeling available; not explicitly detailed in CPIC guideline."
        elif not cpic_rule and not fda_rule:
            discrepancy_note = f"No specific CPIC/FDA rule found for {selected_drug} with gene {gene} ({phenotype})."
        else:
            discrepancy_note = "CPIC and FDA guidelines are aligned."
            
        risk = "Safe / Normal"
        if cpic_rule:
            risk = cpic_rule.get("risk_level", "Safe / Normal")
        elif fda_rule:
            risk = "High Risk" if fda_rule.get("fda_boxed_warning") else "Moderate Risk"
            
        analysis_results.append({
            "drug": selected_drug,
            "gene": gene,
            "phenotype": phenotype,
            "risk_level": risk,
            "cpic_recommendation": cpic_rule.get("recommendation") if cpic_rule else "No specific CPIC rule found for this variant.",
            "fda_recommendation": fda_rule.get("recommendation") if fda_rule else "No specific FDA table entry found for this variant.",
            "discrepancy_flag": discrepancy_flag,
            "discrepancy_note": discrepancy_note
        })
        
    return analysis_results

if __name__ == "__main__":
    from vcf_parser import parse_vcf
    from phenotype_mapper import map_patient_variants
    
    sample_vcf = "data/raw_vcf/patient_sample2.vcf"
    if os.path.exists(sample_vcf):
        variants = parse_vcf(sample_vcf)
        phenotypes = map_patient_variants(variants)
        
        harmonized = harmonize_guidelines("Abacavir", phenotypes)
        print("\n--- HARMONIZED CLINICAL ADVICE FOR ABACAVIR ---")
        for res in harmonized:
            print(f"Drug: {res['drug']} | Gene: {res['gene']} ({res['phenotype']})")
            print(f"Risk Level: {res['risk_level']}")
            print(f"CPIC Guidance: {res['cpic_recommendation']}")
            print(f"FDA Note:     {res['fda_recommendation']}\n")
    else:
        print(f"Sample VCF missing at {sample_vcf}")