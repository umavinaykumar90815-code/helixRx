# Rule table mapping specific star alleles / variants to functional activity scores or phenotypes
ALLELE_FUNCTIONALITY = {
    "CYP2D6": {
        "*1": 1.0,   # Normal function
        "*2": 1.0,   # Normal function
        "*4": 0.0,   # No function (loss-of-function)
        "*10": 0.25, # Decreased function
        "*17": 0.5,  # Decreased function
        "*2xN": 2.0  # Increased function / Gene duplication
    },
    "CYP2C19": {
        "*1": 1.0,   # Normal function
        "*2": 0.0,   # No function
        "*3": 0.0,   # No function
        "*17": 1.5   # Increased function
    },
    "SLCO1B1": {
        "*1": 1.0,   # Normal function
        "*5": 0.0,   # Decreased transport function
        "*15": 0.0   # Decreased transport function
    },
    "HLAB": {
        "*5701": "Positive", # HLA-B*57:01 Carrier (Risk of Abacavir HSR)
        "*1": "Negative"
    }
}

def determine_phenotype(gene, star_allele):
    """
    Translates a star allele mutation into a clinical metabolizer phenotype or risk status.
    """
    gene = gene.upper()
    
    # Specific handling for HLA-B*57:01 risk variant (Abacavir hypersensitivity)
    if gene in ["HLAB", "HLA-B"]:
        if star_allele == "*5701":
            return "Poor Metabolizer"
        return "Normal Metabolizer"

    if gene not in ALLELE_FUNCTIONALITY or star_allele not in ALLELE_FUNCTIONALITY[gene]:
        return "Normal Metabolizer"
    
    activity_score = ALLELE_FUNCTIONALITY[gene][star_allele]
    
    if activity_score == 0.0:
        return "Poor Metabolizer"
    elif 0.0 < activity_score <= 0.5:
        return "Intermediate Metabolizer"
    elif 0.5 < activity_score <= 1.25:
        return "Normal Metabolizer"
    elif activity_score > 1.25:
        return "Ultra-Rapid Metabolizer"
    
    return "Normal Metabolizer"

def map_patient_variants(parsed_variants):
    """
    Takes a list of variant dictionaries from vcf_parser.py 
    and appends phenotype assessments.
    """
    results = []
    for variant in parsed_variants:
        gene = variant.get("gene", "UNKNOWN").upper()
        rsid = variant.get("rsid", "")
        
        # Extract or infer star allele from rsID / VCF info
        star_allele = "*1"
        if "rs2395029" in rsid:
            star_allele = "*5701"
            if gene == "UNKNOWN":
                gene = "HLAB"
        elif "rs28399433" in rsid:
            star_allele = "*4"
            if gene == "UNKNOWN":
                gene = "CYP2D6"
        elif "rs4244285" in rsid:
            star_allele = "*2"
            if gene == "UNKNOWN":
                gene = "CYP2C19"
        elif "rs4149056" in rsid:
            star_allele = "*5"
            if gene == "UNKNOWN":
                gene = "SLCO1B1"
            
        phenotype = determine_phenotype(gene, star_allele)
        
        results.append({
            "gene": gene,
            "rsid": rsid,
            "star_allele": star_allele,
            "phenotype": phenotype
        })
    return results

if __name__ == "__main__":
    from vcf_parser import parse_vcf
    import os
    
    sample_path = "data/raw_vcf/patient_sample2.vcf"
    if os.path.exists(sample_path):
        raw_variants = parse_vcf(sample_path)
        mapped_phenotypes = map_patient_variants(raw_variants)
        
        print("\n--- PATIENT PHENOTYPE MAPPING RESULTS ---")
        for res in mapped_phenotypes:
            print(f"Gene: {res['gene']} | Allele: {res['star_allele']} | Phenotype: {res['phenotype']}")
    else:
        print(f"Sample file not found at {sample_path}")