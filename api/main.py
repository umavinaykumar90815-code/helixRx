from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.phenotype_mapper import determine_phenotype
from engine.cpic_fda_harmonizer import harmonize_guidelines
from engine.organ_clearance import evaluate_organ_clearance
from engine.drug_interaction import analyze_polypharmacy
from engine.ml_predictor import VariantImpactPredictor

app = FastAPI(
    title="Clinical Pharmacogenomics (PGx) Enterprise API",
    version="2.0.0",
    description="Tri-Domain Clinical Decision Support REST Service"
)

ml_engine = VariantImpactPredictor()

class AnalysisRequest(BaseModel):
    selected_drugs: List[str]
    target_gene: str
    star_allele: str
    egfr: float
    alt: float

class NovelVariantRequest(BaseModel):
    cadd_score: float
    polyphen_score: float
    sift_score: float
    phylop_score: float

@app.get("/")
def health_check():
    return {"status": "Active", "system": "PGx Enterprise Engine v2.0"}

@app.post("/api/v1/analyze")
def run_pgx_analysis(req: AnalysisRequest):
    phenotype = determine_phenotype(req.target_gene, req.star_allele)
    patient_phenotype = [{"gene": req.target_gene, "phenotype": phenotype}]
    
    primary_drug = req.selected_drugs[0]
    harmonized = harmonize_guidelines(primary_drug, patient_phenotype)
    
    organ_eval = evaluate_organ_clearance(
        req.egfr, req.alt, 
        harmonized[0]["risk_level"] if harmonized else "Safe / Normal", 
        primary_drug
    )
    
    polypharmacy = []
    if len(req.selected_drugs) > 1:
        polypharmacy = analyze_polypharmacy(req.selected_drugs, patient_phenotype, {"egfr": req.egfr, "alt": req.alt})
        
    return {
        "primary_drug": primary_drug,
        "genomic_assessment": patient_phenotype[0],
        "guideline_harmonization": harmonized,
        "organ_clearance": organ_eval,
        "polypharmacy_alerts": polypharmacy
    }

@app.post("/api/v1/predict-novel-variant")
def predict_variant(req: NovelVariantRequest):
    return ml_engine.predict_variant_impact(
        req.cadd_score, req.polyphen_score, req.sift_score, req.phylop_score
    )