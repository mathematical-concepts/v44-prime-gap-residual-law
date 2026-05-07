#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproduce_figures.py
====================
Generates the paper's official figures from the historical exploratory data.
Publication-ready (300 DPI, academic style).
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

# Strict academic style configuration
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.4)
colors = sns.color_palette("Set1")

def ensure_dir(d):
    if not os.path.exists(d): os.makedirs(d)

def plot_lambda_sweep():
    """1. Lambda sweep Λ=30..55: Shows the causal improvement peak at 45."""
    file_path = "data/v41c_sweep_and_nulls.csv"
    if not os.path.exists(file_path):
        print(f"⚠️ Warning: {file_path} is missing. Make sure to put it in the data folder./")
        return

    df = pd.read_csv(file_path, sep=',')

    # Extract columns starting with 'L_' (excluding the ground truth 'L45_actual')
    lambda_cols = [c for c in df.columns if c.startswith('L_') and c != 'L45_actual']

    # Calculate the median improvement for each Lambda across all test blocks
    median_improvements = df[lambda_cols].median()

    # Create a clean DataFrame for the plotting engine
    # We extract the numerical value of Lambda from the column name (e.g., 'L_30.0' -> 30.0)
    lambdas = [float(c.split('_')[1]) for c in lambda_cols]
    plot_df = pd.DataFrame({
        'Lambda': lambdas,
        'Improvement_Pct': median_improvements.values
    })

    plt.figure(figsize=(8, 5))
    sns.lineplot(data=plot_df, x='Lambda', y='Improvement_Pct', marker='o', color=colors[1], linewidth=2)
    plt.axvline(45, color='red', linestyle='--', label='Λ = 45 (S,D Representation)')

    plt.title("Fig 1: Median Causal Improvement vs Lambda")
    plt.xlabel("Wavelength Lambda (Λ)")
    plt.ylabel("Median Improvement over M3 (%)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("figures/fig1_lambda_sweep.png", dpi=300)
    print("✅ Fig 1 generated (Median Causal Improvement vs Lambda).")

def plot_v44b_audit_overview():
    """2. V44b audit bar chart: Muestra el impacto macro (M3) vs micro (R45)."""
    # LEEMOS EL ARCHIVO HISTÓRICO ORIGINAL
    file_path = "data/v44b_patched_audit.csv"
    if not os.path.exists(file_path): return
    
    df = pd.read_csv(file_path)
    plt.figure(figsize=(8, 5))
    
    df_melt = df.melt(id_vars=["block"], value_vars=["M3_vs_M0", "R45_vs_M3"], 
                      var_name="Layer", value_name="Improvement")
    
    sns.barplot(data=df_melt, x="block", y="Improvement", hue="Layer", palette=["#34495e", "#3498db"])
    plt.title("Fig 2: Macroscopic (M3) vs Microscopic (R45) Corrections")
    plt.xlabel("Test Block")
    plt.ylabel("RMS Improvement (%)")
    plt.legend(title="Model Layer")
    plt.tight_layout()
    plt.savefig("figures/fig2_v44b_overview.png", dpi=300)
    print("✅ Fig 2 generated.")

def plot_model_ablation():
    """3. R45 vs Full2D vs SmoothNested: Demuestra la Navaja de Ockham."""
    file_path = "data/v44b_patched_audit.csv"
    if not os.path.exists(file_path): return
    
    df = pd.read_csv(file_path)
    plt.figure(figsize=(8, 5))
    
    df_melt = df.melt(id_vars=["block"], value_vars=["R45_vs_M3", "Full2D_vs_M3", "Smooth_vs_M3"], 
                      var_name="Model", value_name="Improvement")
    
    sns.lineplot(data=df_melt, x="block", y="Improvement", hue="Model", marker='s', linewidth=2.5, palette=["#2ecc71", "#e74c3c", "#95a5a6"])
    plt.title("Fig 3: Structural Orthogonality (Occam's Razor)")
    plt.xlabel("Test Block")
    plt.ylabel("Improvement over M3 (%)")
    plt.axhline(0, color='black', linewidth=1, linestyle='-')
    plt.legend(title="Structural Model")
    plt.tight_layout()
    plt.savefig("figures/fig3_model_ablation.png", dpi=300)
    print("✅ Fig 3 generated.")

def plot_null_control():
    """4. D-shuffle control: Falsación de la geometría espacial."""
    file_path = "data/v44b_patched_audit.csv"
    if not os.path.exists(file_path): return
    
    df = pd.read_csv(file_path)
    plt.figure(figsize=(8, 5))
    
    df_melt = df.melt(id_vars=["block"], value_vars=["R45_vs_M3", "Null_vs_M3"], 
                      var_name="Condition", value_name="Improvement")
    
    sns.barplot(data=df_melt, x="block", y="Improvement", hue="Condition", palette=["#2ecc71", "#e74c3c"])
    plt.title("Fig 4: Geometric Null Control (D-Shuffle Ablation)")
    plt.xlabel("Test Block")
    plt.ylabel("Improvement over M3 (%)")
    plt.axhline(0, color='black', linewidth=1)
    plt.legend(title="Validation Condition")
    plt.tight_layout()
    plt.savefig("figures/fig4_null_control.png", dpi=300)
    print("✅ Fig 4 generated.")

def plot_parameter_evolution():
    """5. Parameter evolution a(t), b(t): El enfriamiento monótono."""
    file_path = "data/v44b_patched_audit.csv"
    if not os.path.exists(file_path): return
    
    df = pd.read_csv(file_path)
    if 'b45_pred' not in df.columns: return

    plt.figure(figsize=(8, 5))
    sns.lineplot(data=df, x="block", y="b45_pred", marker='D', color="#8e44ad", linewidth=2.5)
    
    plt.title("Fig 5: Monotonic Cooling of Resonance Amplitude (b45)")
    plt.xlabel("Test Block")
    plt.ylabel("Predicted Amplitude $b(t)$")
    plt.axhline(0, color='black', linewidth=1, linestyle='--')
    plt.tight_layout()
    plt.savefig("figures/fig5_parameter_evolution.png", dpi=300)
    print("✅ Fig 5 generated.")

def main():
    ensure_dir("figures")
    print("Generando figuras para el Whitepaper...")
    plot_lambda_sweep()
    plot_v44b_audit_overview()
    plot_model_ablation()
    plot_null_control()
    plot_parameter_evolution()
    print("Proceso finalizado. Figuras listas en el directorio /figures.")

if __name__ == "__main__":
    main()