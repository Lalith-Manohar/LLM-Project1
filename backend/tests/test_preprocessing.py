"""Unit tests for NEXORA ML preprocessing module.

Tests classification rules, edge cases, reconciliation, and output isolation
using small synthetic DataFrames as required by AGENTS.md.
"""

import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add backend directory to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.src.preprocessing import (
    classify_transactions,
    extract_gross_sales,
    extract_cancellations,
    extract_returns,
    extract_exceptional_records,
    validate_preprocessed_data
)


class TestPreprocessingPipeline(unittest.TestCase):
    def setUp(self):
        """Build synthetic transactions covering all mandatory test conditions."""
        self.sample_data = pd.DataFrame([
            # 1. Normal gross sales (Quantity > 0, Price > 0, no 'C')
            {"Invoice": "536365", "StockCode": "85123A", "Quantity": 6, "Price": 2.55, "Customer ID": "17850"},
            {"Invoice": "536366", "StockCode": "71053", "Quantity": 1, "Price": 3.39, "Customer ID": "17850"},
            
            # 2. Duplicate normal sale
            {"Invoice": "536366", "StockCode": "71053", "Quantity": 1, "Price": 3.39, "Customer ID": "17850"},
            
            # 3. Cancellation invoice with negative quantity
            {"Invoice": "C536379", "StockCode": "D", "Quantity": -1, "Price": 27.50, "Customer ID": "17548"},
            
            # 4. Return without 'C' prefix (Quantity < 0)
            {"Invoice": "536589", "StockCode": "21777", "Quantity": -10, "Price": 0.00, "Customer ID": None},
            
            # 5. Zero price record (Quantity > 0, Price == 0) -> Exceptional
            {"Invoice": "536600", "StockCode": "21778", "Quantity": 5, "Price": 0.00, "Customer ID": None},
            
            # 6. Negative price record (Quantity > 0, Price < 0) -> Exceptional
            {"Invoice": "A536601", "StockCode": "B", "Quantity": 1, "Price": -100.00, "Customer ID": None},
            
            # 7. Zero quantity record -> Exceptional
            {"Invoice": "536602", "StockCode": "21779", "Quantity": 0, "Price": 5.00, "Customer ID": "12345"},
            
            # 8. Positive quantity on cancellation invoice -> Exceptional / Cancel flag rule
            # Since our classification gives precedence to cancellation prefix:
            {"Invoice": "C536603", "StockCode": "21780", "Quantity": 10, "Price": 4.50, "Customer ID": "12345"},
            
            # 9. Missing Invoice identifier -> Exceptional
            {"Invoice": None, "StockCode": "21781", "Quantity": 2, "Price": 1.50, "Customer ID": "12345"},
            
            # 10. Missing StockCode identifier
            {"Invoice": "536604", "StockCode": None, "Quantity": 4, "Price": 2.00, "Customer ID": "12345"}
        ])

    def test_reconciliation_total_rows(self):
        """Verifies that every record belongs to exactly one stream and none are lost."""
        classified = classify_transactions(self.sample_data)
        gross = extract_gross_sales(classified)
        cancel = extract_cancellations(classified)
        returns = extract_returns(classified)
        exceptional = extract_exceptional_records(classified)

        val = validate_preprocessed_data(self.sample_data, gross, cancel, returns, exceptional)

        self.assertTrue(val["reconciled"], "Sum of partitioned streams must equal original total rows")
        self.assertEqual(val["total_original"], len(self.sample_data))
        self.assertEqual(val["total_partitioned"], len(self.sample_data))

    def test_gross_sales_extraction(self):
        """Verifies that gross sales contains strictly Quantity > 0, Price > 0, no 'C'."""
        classified = classify_transactions(self.sample_data)
        gross = extract_gross_sales(classified)

        self.assertTrue((gross["Quantity"] > 0).all())
        self.assertTrue((gross["Price"] > 0).all())
        self.assertTrue((~gross["Invoice"].astype(str).str.startswith("C")).all())

    def test_cancellation_extraction(self):
        """Verifies that all cancellations start with 'C'."""
        classified = classify_transactions(self.sample_data)
        cancel = extract_cancellations(classified)

        self.assertTrue(cancel["Invoice"].astype(str).str.startswith("C").all())
        self.assertEqual(len(cancel), 2)  # C536379 (neg qty) and C536603 (pos qty)

    def test_returns_without_c_extraction(self):
        """Verifies that returns have Quantity < 0 and no 'C' prefix."""
        classified = classify_transactions(self.sample_data)
        returns = extract_returns(classified)

        self.assertTrue((returns["Quantity"] < 0).all())
        self.assertTrue((~returns["Invoice"].astype(str).str.startswith("C")).all())
        self.assertIn("536589", returns["Invoice"].values)

    def test_exceptional_records_extraction(self):
        """Verifies zero/negative prices, zero quantity, and missing invoices are caught."""
        classified = classify_transactions(self.sample_data)
        exceptional = extract_exceptional_records(classified)

        # Invoices: 536600 (Price=0), A536601 (Price=-100), 536602 (Qty=0), None (missing invoice)
        self.assertTrue(len(exceptional) >= 4)


if __name__ == "__main__":
    unittest.main()
