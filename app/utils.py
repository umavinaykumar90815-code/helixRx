import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf_report(filename, drug_name, patient_filename, harmonized_data, organ_data):
    """
    Generates a structured, professional 1-page PDF clinical summary report.
    """
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    # Title & Header
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E3A8A'))
    story.append(Paragraph("Clinical Pharmacogenomics (PGx) Safety Report", title_style))
    story.append(Spacer(1, 10))

    # Patient & Drug Meta Table
    meta_data = [
        [Paragraph("<b>Patient File:</b>", styles['Normal']), Paragraph(patient_filename, styles['Normal'])],
        [Paragraph("<b>Proposed Medication:</b>", styles['Normal']), Paragraph(drug_name, styles['Normal'])],
        [Paragraph("<b>Analysis Type:</b>", styles['Normal']), Paragraph("Tri-Domain PGx & Organ Clearance Safety Check", styles['Normal'])]
    ]
    meta_table = Table(meta_data, colWidths=[150, 350])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1'))
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Findings Section
    story.append(Paragraph("<b>Genomic & Guideline Findings</b>", styles['Heading2']))
    story.append(Spacer(1, 5))

    for item in harmonized_data:
        story.append(Paragraph(f"• <b>Gene Evaluated:</b> {item['gene']}", styles['Normal']))
        story.append(Paragraph(f"• <b>Assessed Phenotype:</b> {item['phenotype']}", styles['Normal']))
        story.append(Paragraph(f"• <b>CPIC Recommendation:</b> {item['cpic_recommendation']}", styles['Normal']))
        story.append(Paragraph(f"• <b>FDA Note:</b> {item['fda_recommendation']}", styles['Normal']))
        story.append(Spacer(1, 10))

    # Organ Clearance Section
    story.append(Paragraph("<b>Organ Clearance & Physiological Parameters</b>", styles['Heading2']))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"• <b>Kidney eGFR:</b> {organ_data['egfr_status']} (Value: {organ_data.get('egfr_val', 'N/A')} mL/min)", styles['Normal']))
    story.append(Paragraph(f"• <b>Liver ALT:</b> {organ_data['alt_status']} (Value: {organ_data.get('alt_val', 'N/A')} U/L)", styles['Normal']))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Anatomical Warnings:</b>", styles['Normal']))
    for warn in organ_data['organ_warnings']:
        story.append(Paragraph(f"  - {warn}", styles['Normal']))

    story.append(Spacer(1, 20))
    
    # Final Verdict Card
    final_risk = organ_data['final_risk_level']
    card_color = colors.HexColor('#FECACA') if final_risk in ["High Risk", "Toxic Risk"] else colors.HexColor('#D1FAE5')
    
    verdict_text = Paragraph(f"<b>FINAL CLINICAL VERDICT: {final_risk.upper()}</b>", styles['Heading2'])
    verdict_table = Table([[verdict_text]], colWidths=[500])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), card_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(verdict_table)

    doc.build(story)