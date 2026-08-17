import re

def parse_vcf(file_path):
    """
    Parses a standard genomic .vcf file to extract Single Nucleotide Polymorphisms (SNPs)
    relevant to pharmacogenomic drug metabolism genes.
    """
    variants = []
    
    try:
        with open(file_path, 'r') as file:
            for line in file:
                # Skip VCF metadata header lines
                if line.startswith('#'):
                    continue
                
                parts = line.strip().split('\t')
                if len(parts) >= 8:
                    chrom = parts[0]
                    pos = parts[1]
                    rsid = parts[2]
                    ref = parts[3]
                    alt = parts[4]
                    info = parts[7]
                    
                    # Extract gene symbol if present in INFO field
                    gene_match = re.search(r'GENE=([A-Za-z0-9]+)', info)
                    gene = gene_match.group(1) if gene_match else "UNKNOWN"
                    
                    variants.append({
                        "chromosome": chrom,
                        "position": pos,
                        "rsid": rsid,
                        "ref": ref,
                        "alt": alt,
                        "gene": gene
                    })
        return variants
    except Exception as e:
        print(f"Error reading VCF file: {e}")
        return []

if __name__ == "__main__":
    # Test execution on sample file
    sample_path = "data/raw_vcf/patient_sample1.vcf"
    extracted_variants = parse_vcf(sample_path)
    print(f"Extracted {len(extracted_variants)} variants from sample.")