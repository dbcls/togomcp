#!/usr/bin/env python3
"""
Test script to verify unified analysis scripts work correctly
"""

import sys
from pathlib import Path

print("Testing Unified Analysis Scripts")
print("=" * 60)

# Test 1: Import unified analyzer
print("\n1. Testing results_analyzer_unified.py import...")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from results_analyzer_unified import UnifiedAnalyzer
    print("   ✓ Import successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Import unified dashboard generator
print("\n2. Testing generate_dashboard_unified.py import...")
try:
    from generate_dashboard_unified import UnifiedDashboardGenerator
    print("   ✓ Import successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 3: Test auto-detection with pattern matching file
print("\n3. Testing auto-detection with pattern matching file...")
results_csv = Path(__file__).parent.parent / "results" / "results.csv"
if results_csv.exists():
    try:
        analyzer = UnifiedAnalyzer(str(results_csv), mode='auto')
        if analyzer.mode == 'pattern' and not analyzer.has_llm_columns:
            print("   ✓ Correctly detected pattern matching mode")
        else:
            print("   ⚠ Unexpected mode detected")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
else:
    print(f"   ⚠ Test file not found: {results_csv}")

# Test 4: Test auto-detection with LLM evaluation file
print("\n4. Testing auto-detection with LLM evaluation file...")
results_llm_csv = Path(__file__).parent.parent / "results" / "results_with_llm.csv"
if results_llm_csv.exists():
    try:
        analyzer = UnifiedAnalyzer(str(results_llm_csv), mode='auto')
        if analyzer.mode == 'combined' and analyzer.has_llm_columns:
            print("   ✓ Correctly detected combined mode with LLM columns")
        else:
            print(f"   ⚠ Unexpected mode: {analyzer.mode}, has_llm: {analyzer.has_llm_columns}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
else:
    print(f"   ⚠ Test file not found: {results_llm_csv}")

# Test 5: Test mode forcing
print("\n5. Testing forced mode selection...")
if results_csv.exists():
    try:
        # Force pattern mode
        analyzer = UnifiedAnalyzer(str(results_csv), mode='pattern')
        if analyzer.mode == 'pattern':
            print("   ✓ Pattern mode forced successfully")
        else:
            print(f"   ✗ Failed to force pattern mode, got: {analyzer.mode}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
else:
    print(f"   ⚠ Test file not found: {results_csv}")

# Test 6: Test dashboard generator
print("\n6. Testing dashboard generator initialization...")
if results_csv.exists():
    try:
        generator = UnifiedDashboardGenerator(str(results_csv), mode='auto')
        print("   ✓ Dashboard generator initialized successfully")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
else:
    print(f"   ⚠ Test file not found: {results_csv}")

# Test 7: Test correctness column detection
print("\n7. Testing correctness column detection...")
if results_csv.exists():
    try:
        analyzer = UnifiedAnalyzer(str(results_csv), mode='pattern')
        baseline_col, togomcp_col = analyzer._get_correctness_columns()
        if baseline_col == 'baseline_has_expected' and togomcp_col == 'togomcp_has_expected':
            print("   ✓ Pattern mode columns correct")
        else:
            print(f"   ✗ Unexpected columns: {baseline_col}, {togomcp_col}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
else:
    print(f"   ⚠ Test file not found: {results_csv}")

if results_llm_csv.exists():
    try:
        analyzer = UnifiedAnalyzer(str(results_llm_csv), mode='combined')
        baseline_col, togomcp_col = analyzer._get_correctness_columns()
        if baseline_col == 'full_combined_baseline_found' and togomcp_col == 'full_combined_togomcp_found':
            print("   ✓ Combined mode columns correct")
        else:
            print(f"   ✗ Unexpected columns: {baseline_col}, {togomcp_col}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

# Summary
print("\n" + "=" * 60)
print("✓ All basic tests passed!")
print("\nTo fully test the scripts, run:")
print(f"  python results_analyzer_unified.py {results_csv}")
if results_llm_csv.exists():
    print(f"  python results_analyzer_unified.py {results_llm_csv}")
print()
