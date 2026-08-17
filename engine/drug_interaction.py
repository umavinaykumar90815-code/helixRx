import json
import os

# Polypharmacy and Drug-Drug-Gene Interaction Rules Matrix
DRUG_INTERACTION_MATRIX = {
    ("Clopidogrel", "Simvastatin"): {
        "severity": "Moderate / Caution Required",
        "mechanism": "Potential CYP3A4 / OATP1B1 competitive transport inhibition.",
        "clinical_guidance": "Monitor for increased statin exposure and muscle toxicity (myopathy) if hepatic clearance is impaired."
    },
    ("Codeine", "Clopidogrel"): {
        "severity": "High / Major Interaction",
        "mechanism": "P2Y12 inhibitors may delay gastric emptying and reduce exposure to active opioid metabolites.",
        "clinical_guidance": "Monitor analgesic efficacy closely; consider alternative non-opioid pain management."
    },
    ("Warfarin", "Simvastatin"): {
        "severity": "High / Major Interaction",
        "mechanism": "Simvastatin can displace Warfarin from plasma proteins and inhibit CYP2C9 metabolism.",
        "clinical_guidance": "Enhance INR monitoring frequency upon initiation or dose adjustment of Simvastatin."
    }
}

def analyze_polypharmacy(selected_drugs, patient_phenotypes, organ_status):
    """
    Evaluates multi-drug combinations for pharmacokinetic and pharmacodynamic interactions.
    """
    interactions = []
    
    # Check all pairwise combinations of selected drugs
    for i in range(len(selected_drugs)):
        for j in range(i + 1, len(selected_drugs)):
            drug1 = selected_drugs[i]
            drug2 = selected_drugs[j]
            
            pair = (drug1, drug2) if (drug1, drug2) in DRUG_INTERACTION_MATRIX else (drug2, drug1)
            
            if pair in DRUG_INTERACTION_MATRIX:
                rule = DRUG_INTERACTION_MATRIX[pair]
                
                # Check for gene-exacerbated polypharmacy risk
                gene_compounding = False
                for p in patient_phenotypes:
                    if p.get("phenotype") in ["Poor Metabolizer", "Intermediate Metabolizer"]:
                        gene_compounding = True
                        
                interactions.append({
                    "drug_pair": f"{drug1} + {drug2}",
                    "severity": rule["severity"],
                    "mechanism": rule["mechanism"],
                    "clinical_guidance": rule["clinical_guidance"],
                    "gene_compounding_risk": gene_compounding
                })
                
    return interactions

if __name__ == "__main__":
    sample_drugs = ["Clopidogrel", "Simvastatin"]
    sample_phenotypes = [{"gene": "CYP2C19", "phenotype": "Poor Metabolizer"}]
    sample_organ = {"egfr": 45, "alt": 30}
    
    results = analyze_polypharmacy(sample_drugs, sample_phenotypes, sample_organ)
    print("\n--- POLYPHARMACY ANALYSIS ---")
    for res in results:
        print(f"Pair: {res['drug_pair']} | Severity: {res['severity']}")
        print(f"Mechanism: {res['mechanism']}")
        print(f"Guidance: {res['clinical_guidance']}\n")