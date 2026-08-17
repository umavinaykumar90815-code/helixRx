import re
from pypdf import PdfReader

def extract_text_from_file(file_path):
    """Extracts raw text from .txt or .pdf lab report files."""
    ext = file_path.split('.')[-1].lower()
    text = ""
    
    if ext == "pdf":
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            print(f"PDF extraction error: {e}")
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            
    return text

def parse_medical_report(file_path):
    """
    Scans lab report text for organ clearance and diabetes glycemic markers.
    """
    report_text = extract_text_from_file(file_path)
    
    # Organ function regex
    egfr_pattern = r'(?:eGFR|GFR|Glomerular\s*Filtration\s*Rate)[\s:=]*([0-9]+(?:\.[0-9]+)?)'
    alt_pattern = r'(?:ALT|SGPT|Alanine\s*Aminotransferase)[\s:=]*([0-9]+(?:\.[0-9]+)?)'
    creatinine_pattern = r'(?:Creatinine|Serum\s*Creatinine)[\s:=]*([0-9]+(?:\.[0-9]+)?)'
    
    # Glycemic markers regex
    fbs_pattern = r'(?:FBS|Fasting\s*Blood\s*Sugar|Fasting\s*Glucose)[\s:=]*([0-9]+(?:\.[0-9]+)?)'
    ppbs_pattern = r'(?:PPBS|PP\s*Glucose|Postprandial\s*Blood\s*Sugar|Post\s*Prandial)[\s:=]*([0-9]+(?:\.[0-9]+)?)'
    hba1c_pattern = r'(?:HbA1c|Glycated\s*Hemoglobin|A1C)[\s:=]*([0-9]+(?:\.[0-9]+)?)'
    
    egfr_m = re.search(egfr_pattern, report_text, re.IGNORECASE)
    alt_m = re.search(alt_pattern, report_text, re.IGNORECASE)
    creat_m = re.search(creatinine_pattern, report_text, re.IGNORECASE)
    
    fbs_m = re.search(fbs_pattern, report_text, re.IGNORECASE)
    ppbs_m = re.search(ppbs_pattern, report_text, re.IGNORECASE)
    hba1c_m = re.search(hba1c_pattern, report_text, re.IGNORECASE)
    
    return {
        "egfr": float(egfr_m.group(1)) if egfr_m else None,
        "alt": float(alt_m.group(1)) if alt_m else None,
        "creatinine": float(creat_m.group(1)) if creat_m else None,
        "fbs": float(fbs_m.group(1)) if fbs_m else None,
        "ppbs": float(ppbs_m.group(1)) if ppbs_m else None,
        "hba1c": float(hba1c_m.group(1)) if hba1c_m else None,
        "raw_text_snippet": report_text[:300] + "..." if len(report_text) > 300 else report_text
    }