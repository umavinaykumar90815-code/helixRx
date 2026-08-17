import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.phenotype_mapper import determine_phenotype
from engine.organ_clearance import evaluate_organ_clearance

class TestRulesEngine(unittest.TestCase):
    def test_phenotype_mapping(self):
        self.assertEqual(determine_phenotype("CYP2D6", "*4"), "Poor Metabolizer")
        self.assertEqual(determine_phenotype("CYP2C19", "*1"), "Normal Metabolizer")

    def test_organ_clearance(self):
        result = evaluate_organ_clearance(egfr=20, alt=25, current_risk_level="Safe / Normal", drug="Codeine")
        self.assertEqual(result["final_risk_level"], "High Risk")
        self.assertEqual(result["egfr_status"], "Impaired")

if __name__ == '__main__':
    unittest.main()