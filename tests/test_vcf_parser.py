import unittest
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.vcf_parser import parse_vcf

class TestVCFParser(unittest.TestCase):
    def test_parse_vcf_valid(self):
        sample_path = "data/raw_vcf/patient_sample1.vcf"
        if os.path.exists(sample_path):
            variants = parse_vcf(sample_path)
            self.assertIsInstance(variants, list)
            self.assertGreater(len(variants), 0)

if __name__ == '__main__':
    unittest.main()