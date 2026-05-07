#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_v44b.py
=============
Official script to reproduce the causal validation (V44b) for the paper.
Takes the test data, runs the frozen model and exports the summary.
"""

import pandas as pd
import os
from v44_primes_predictor_frozen import FrozenV44Predictor  # Assuming the class name from the other AI

def main():
    print("Starting V44b causal-validation audit...")

    # Relative paths assuming execution from the repo root
    input_data_path = "data/sample_consecutive_gaps.csv"
    output_summary_path = "data/aggregated_v44b_audit.csv"

    if not os.path.exists(input_data_path):
        print(f"❌ Error: cannot find {input_data_path}. Make sure to run from the repository root.")
        return

    # Load data
    df = pd.read_csv(input_data_path)

    # Initialize the frozen predictor
    # (Configured in "geometric support" mode for leakage-free centering)
    predictor = FrozenV44Predictor()

# Run audit (M3 vs R45 vs Smooth vs Null)
    print("Computing residual metrics and geometric null controls...")
    _, summary = predictor.audit_dataframe(
        df,
        target_col="resid_log"
    )

    # Save results
    summary.to_csv(output_summary_path, index=False)
    print(f"✅ Audit completed. Results table exported to: {output_summary_path}")
    print("\nSummary:")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()