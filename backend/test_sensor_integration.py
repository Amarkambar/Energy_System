"""
Integration test for real sensor data validation and pipeline processing.
Tests the complete flow: CSV upload → validation → pipeline → ML models
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.real_data_ingestion import RealDataIngestor
from data.pipeline import run_pipeline


def create_test_csv(filename: str, scenario: str = "valid"):
    """
    Create test CSV files for different scenarios.
    
    Args:
        filename: Output CSV filename
        scenario: One of "valid", "missing_columns", "outliers", "missing_values", "time_gaps"
    """
    print(f"\n[Test] Creating {scenario} test CSV: {filename}")
    
    # Base valid data
    hours = 168  # 1 week
    start_time = datetime.now() - timedelta(hours=hours)
    timestamps = [start_time + timedelta(hours=i) for i in range(hours)]
    
    base_data = {
        "timestamp": timestamps,
        "consumption_kwh": np.random.uniform(300, 600, hours),
        "voltage_v": np.random.uniform(220, 240, hours),
        "current_a": np.random.uniform(10, 30, hours),
        "power_factor": np.random.uniform(0.85, 0.95, hours),
        "temperature_c": np.random.uniform(20, 30, hours)
    }
    
    df = pd.DataFrame(base_data)
    
    # Apply scenario modifications
    if scenario == "missing_columns":
        # Drop required column to fail validation
        df = df.drop(columns=["consumption_kwh"])  # Required column
    
    elif scenario == "outliers":
        # Add extreme outliers
        df.loc[10, "consumption_kwh"] = 10000  # 10x normal
        df.loc[50, "voltage_v"] = 500  # 2x normal
        df.loc[100, "temperature_c"] = -50  # Impossible value
    
    elif scenario == "missing_values":
        # Add missing values
        df.loc[10:20, "consumption_kwh"] = np.nan
        df.loc[50:60, "voltage_v"] = np.nan
        df.loc[100:110, "temperature_c"] = np.nan
    
    elif scenario == "time_gaps":
        # Remove rows to create gaps
        df = df.drop(df.index[50:70])  # 20-hour gap
        df = df.drop(df.index[120:125])  # 5-hour gap
    
    elif scenario == "negative_values":
        # Add negative values
        df.loc[10:20, "consumption_kwh"] = -50
        df.loc[50:60, "power_factor"] = -0.5
    
    # Save CSV
    df.to_csv(filename, index=False)
    print(f"[Test] ✓ Created {len(df)} rows")
    return filename


def test_validation_only():
    """Test 1: Validation without pipeline execution"""
    print("\n" + "="*70)
    print("TEST 1: Data Validation (No Pipeline Execution)")
    print("="*70)
    
    ingestor = RealDataIngestor()
    
    # Test 1a: Valid data
    csv_path = create_test_csv("test_valid.csv", "valid")
    validation = ingestor.validate_csv(csv_path)
    
    print(f"\n[Test 1a] Valid CSV Validation:")
    print(f"  Is Valid: {validation['is_valid']}")
    print(f"  Errors: {len(validation['errors'])}")
    print(f"  Warnings: {len(validation['warnings'])}")
    
    if validation['stats']:
        print(f"  Stats:")
        print(f"    - Rows: {validation['stats'].get('total_rows', 'N/A')}")
        print(f"    - Columns: {validation['stats'].get('total_columns', 'N/A')}")
        missing_pct = validation['stats'].get('missing_percentage', 0)
        if isinstance(missing_pct, (int, float)):
            print(f"    - Missing %: {missing_pct:.2f}%")
        else:
            print(f"    - Missing %: {missing_pct}")
    
    assert validation['is_valid'], "Valid CSV should pass validation"
    os.remove(csv_path)
    print("[Test 1a] ✓ PASSED")
    
    # Test 1b: Missing columns
    csv_path = create_test_csv("test_missing_cols.csv", "missing_columns")
    validation = ingestor.validate_csv(csv_path)
    
    print(f"\n[Test 1b] Missing Columns Validation:")
    print(f"  Is Valid: {validation['is_valid']}")
    print(f"  Errors: {validation['errors']}")
    
    assert not validation['is_valid'], "Missing columns should fail validation"
    assert any("missing required columns" in err.lower() for err in validation['errors'])
    os.remove(csv_path)
    print("[Test 1b] ✓ PASSED")
    
    # Test 1c: Outliers (should warn but pass)
    csv_path = create_test_csv("test_outliers.csv", "outliers")
    validation = ingestor.validate_csv(csv_path)
    
    print(f"\n[Test 1c] Outliers Validation:")
    print(f"  Is Valid: {validation['is_valid']}")
    print(f"  Warnings: {validation['warnings']}")
    
    assert validation['is_valid'], "Outliers should still pass (with warnings)"
    assert len(validation['warnings']) > 0, "Should have outlier warnings"
    os.remove(csv_path)
    print("[Test 1c] ✓ PASSED")


def test_pipeline_integration():
    """Test 2: Full pipeline integration with validation"""
    print("\n" + "="*70)
    print("TEST 2: Pipeline Integration (Validation + Processing)")
    print("="*70)
    
    # Test 2a: Valid CSV through pipeline
    csv_path = create_test_csv("test_pipeline_valid.csv", "valid")
    
    print(f"\n[Test 2a] Processing valid CSV through pipeline...")
    df = run_pipeline(smart_meter_path=csv_path, use_real_data=True)
    
    print(f"  Result:")
    print(f"    - Rows: {len(df)}")
    print(f"    - Columns: {len(df.columns)}")
    print(f"    - Features: {', '.join(df.columns[:10])}...")
    
    assert len(df) > 0, "Pipeline should return data"
    assert 'consumption_kwh' in df.columns or 'feature_' in ' '.join(df.columns), "Should have features"
    os.remove(csv_path)
    print("[Test 2a] ✓ PASSED")
    
    # Test 2b: Invalid CSV (should fallback to synthetic)
    csv_path = create_test_csv("test_pipeline_invalid.csv", "missing_values")  # Has required columns but with missing data
    
    print(f"\n[Test 2b] Processing CSV with missing values (should clean and continue)...")
    df = run_pipeline(smart_meter_path=csv_path, use_real_data=True)
    
    print(f"  Result:")
    print(f"    - Rows: {len(df)}")
    print(f"    - Columns: {len(df.columns)}")
    print(f"    - Note: Should process with data cleaning")
    
    assert len(df) > 0, "Pipeline should still return data"
    os.remove(csv_path)
    print("[Test 2b] ✓ PASSED")


def test_data_quality_report():
    """Test 3: Data quality report generation"""
    print("\n" + "="*70)
    print("TEST 3: Data Quality Report Generation")
    print("="*70)
    
    ingestor = RealDataIngestor()
    
    # Create CSV with various issues
    csv_path = create_test_csv("test_quality_report.csv", "missing_values")
    
    print(f"\n[Test 3] Generating quality report...")
    # Load and validate the CSV properly
    validation = ingestor.validate_csv(csv_path)
    df = pd.read_csv(csv_path, parse_dates=['timestamp'])
    report = ingestor.generate_data_quality_report(df)
    
    print(f"\n{report[:500]}...")  # Print first 500 chars
    
    assert "Data Quality Report" in report, "Report should have title"
    assert "Dataset Statistics" in report or "Validation Status" in report, "Report should have sections"
    
    os.remove(csv_path)
    print("[Test 3] ✓ PASSED")


def test_pipeline_fallback():
    """Test 4: Fallback behavior when no CSV provided"""
    print("\n" + "="*70)
    print("TEST 4: Pipeline Fallback to Synthetic Data")
    print("="*70)
    
    print(f"\n[Test 4] Running pipeline without CSV (should use synthetic)...")
    df = run_pipeline(smart_meter_path=None, use_real_data=True)
    
    print(f"  Result:")
    print(f"    - Rows: {len(df)}")
    print(f"    - Columns: {len(df.columns)}")
    print(f"    - Data source: Synthetic (no CSV provided)")
    
    assert len(df) > 0, "Pipeline should generate synthetic data"
    assert len(df) >= 100, "Synthetic data should have reasonable size"
    print("[Test 4] ✓ PASSED")


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("REAL SENSOR DATA INTEGRATION TEST SUITE")
    print("="*70)
    print("Testing: Validation → Pipeline → Fallback behavior")
    print("="*70)
    
    tests = [
        ("Validation Only", test_validation_only),
        ("Pipeline Integration", test_pipeline_integration),
        ("Data Quality Report", test_data_quality_report),
        ("Pipeline Fallback", test_pipeline_fallback),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✓ Passed: {passed}/{len(tests)}")
    if failed > 0:
        print(f"✗ Failed: {failed}/{len(tests)}")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Sensor data integration is working correctly.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
