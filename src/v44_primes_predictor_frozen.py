#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V44_primes_predictor_frozen
===========================

Frozen parametric predictor based on the equation validated up to V44b.

IMPORTANT
---------
This script does NOT prove RH, twin primes or Goldbach. It is an
experimental/reproducible tool to:
  - evaluate the E0 + U + R45 conjecture on new batches,
  - audit M0/M3/R45,
  - rank gap pairs,
  - generate out-of-sample evidence,
  - measure error terms.

Model
-----
For consecutive gaps g1, g2:

    S = g1 + g2
    D = g2 - g1
    t = loglog(p_center)

    Delta(S,D;p) =
        E0(S)
        + U(S,D;t)
        + R45(S,D;t)

with:

    E0(S) =
        c0 + c1*sqrt(S) + c2*log(1+S) + c3/sqrt(S)

    U(S,D;t) =
        u0(t) + u1(t)*(S-Sbar) + u2*(D^2-D2bar)

    R45(S,D;t) =
        cos(pi*D/45) * [ a45(t)*sin(pi*S/45) + b45(t)*cos(pi*S/45) ]

Frozen coefficients
-------------------
Calibrated on:
  base = V15_CAUSAL
  target = resid_log
  blocks = B04..B10
  dataset = v24_corrected_residuals_long.csv

The coefficients should be treated as a "laboratory calibration".
For extrapolations far from the calibrated range, the script returns
a trust_score and may emit warnings.

CLI usage
---------
Show formula/constants:

    python V44_primes_predictor_frozen.py --show-formula

Predict from a CSV:

    python V44_primes_predictor_frozen.py \
      --input new_pairs.csv \
      --output predictions_v44.csv \
      --p-col p_center \
      --g1-col g1 \
      --g2-col g2 \
      --center-mode fixed

If an observed target is available:

    python V44_primes_predictor_frozen.py \
      --input batch.csv \
      --target-col resid_log \
      --output audit.csv \
      --summary-output audit_summary.csv

Quick API:

    from V44_primes_predictor_frozen import FrozenV44Predictor
    pred = FrozenV44Predictor()
    delta = pred.predict_delta(p_center=10**9, g1=12, g2=18)
    factor = pred.predict_weight_correction(10**9, 12, 18)
"""

from __future__ import annotations

import argparse
import math
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, Union

import numpy as np
import pandas as pd


Number = Union[int, float, np.integer, np.floating]


# =============================================================================
# Safe log/loglog for huge integers
# =============================================================================

def safe_log(x: Union[int, float, str]) -> float:
    """Compute log(x) robustly for huge Python ints or decimal strings."""
    if isinstance(x, str):
        x = x.strip()
        if not x:
            return float("nan")
        # Avoid constructing a huge float.
        try:
            if len(x) < 300:
                return math.log(float(x))
            # decimal approximation: x = leading * 10^(n-d)
            d = min(18, len(x))
            leading = float(x[:d])
            return math.log(leading) + (len(x) - d) * math.log(10.0)
        except Exception:
            try:
                return safe_log(int(x))
            except Exception:
                return float("nan")

    if isinstance(x, (int, np.integer)):
        x_int = int(x)
        if x_int <= 0:
            return float("nan")
        bits = x_int.bit_length()
        if bits < 900:
            return math.log(float(x_int))
        # Use top 53 bits as mantissa.
        shift = bits - 53
        mant = x_int >> shift
        return math.log(float(mant)) + shift * math.log(2.0)

    try:
        xf = float(x)
    except Exception:
        return float("nan")
    if not math.isfinite(xf) or xf <= 0:
        return float("nan")
    return math.log(xf)


def safe_loglog(x: Union[int, float, str]) -> float:
    lp = safe_log(x)
    if not math.isfinite(lp) or lp <= 0:
        return float("nan")
    return math.log(max(lp, math.e))


# =============================================================================
# Calibration
# =============================================================================

@dataclass(frozen=True)
class V44Calibration:
    # E0(S) = c0 + c_sqrt*sqrtS + c_log*log1pS + c_inv*inv_sqrtS
    c0: float = -0.03114180
    c_sqrt: float = 0.04098501
    c_log1p: float = -0.05334537
    c_inv_sqrt: float = -0.12132411

    # Parametric laws vs t = loglog(p)
    # u0(t) = u0_m*t + u0_b
    u0_m: float = 1.15901518
    u0_b: float = -3.52340837

    # u1(t) = u1_m*t + u1_b
    u1_m: float = 0.05119857
    u1_b: float = -0.15564373

    # u2 constant
    u2_const: float = -1.3985706067124188e-05

    # a45(t) = a45_m*t + a45_b, clipped
    a45_m: float = -0.45487620
    a45_b: float = 1.38952873

    # b45(t) = b45_m*t + b45_b with cooling clips
    b45_m: float = 1.20270108
    b45_b: float = -3.69017588

    # Training/reference ranges
    t_min: float = 3.011131766253543
    t_max: float = 3.061634162310919
    b45_min_observed: float = -0.066857
    b45_last_observed: float = -0.007588

    # Fixed reference centers from V15_CAUSAL/resid_log grid
    Sbar_fixed: float = 60.0
    D2bar_fixed: float = 549.3915756630265

    # Safety caps
    a45_min: float = -0.08
    a45_max: float = 0.08
    b45_min_cap_factor: float = 1.25
    b45_max: float = 0.0

    # Beyond this many t-units from calibration, warn.
    trust_radius_t: float = 0.25

    calibration_label: str = "V44b frozen calibration | V15_CAUSAL/resid_log | B04-B10"


# =============================================================================
# Predictor
# =============================================================================

class FrozenV44Predictor:
    def __init__(self, calibration: V44Calibration = V44Calibration(), center_mode: str = "fixed"):
        self.cal = calibration
        if center_mode not in {"fixed", "support", "custom"}:
            raise ValueError("center_mode must be 'fixed', 'support' or 'custom'")
        self.center_mode = center_mode

    # -----------------------------
    # Parameter laws
    # -----------------------------

    def u0(self, t: float) -> float:
        return self.cal.u0_m * t + self.cal.u0_b

    def u1(self, t: float) -> float:
        return self.cal.u1_m * t + self.cal.u1_b

    def u2(self, t: float) -> float:
        return self.cal.u2_const

    def a45(self, t: float) -> float:
        raw = self.cal.a45_m * t + self.cal.a45_b
        return float(np.clip(raw, self.cal.a45_min, self.cal.a45_max))

    def b45(self, t: float) -> float:
        raw = self.cal.b45_m * t + self.cal.b45_b

        # Physical contract:
        # b45 remains non-positive and should not become more negative
        # than a conservative lower cap estimated from calibration.
        b_min = self.cal.b45_min_cap_factor * self.cal.b45_min_observed
        b_max = self.cal.b45_max

        # For extrapolation beyond calibration, never allow b to become
        # more negative than the last observed b45; it may cool towards zero.
        if t >= self.cal.t_max:
            b_min = self.cal.b45_last_observed

        return float(np.clip(raw, b_min, b_max))

    def trust_score(self, t: float) -> float:
        """1 near calibration range; decays outside trust_radius_t."""
        if not math.isfinite(t):
            return 0.0
        if self.cal.t_min <= t <= self.cal.t_max:
            return 1.0
        dist = min(abs(t - self.cal.t_min), abs(t - self.cal.t_max))
        return float(math.exp(-dist / max(self.cal.trust_radius_t, 1e-12)))

    # -----------------------------
    # Core formula
    # -----------------------------

    @staticmethod
    def _arrays(p_center, g1, g2):
        p = np.asarray(p_center if np.ndim(p_center) else [p_center], dtype=object)
        g1a = np.asarray(g1 if np.ndim(g1) else [g1], dtype=float)
        g2a = np.asarray(g2 if np.ndim(g2) else [g2], dtype=float)
        if len(p) == 1 and len(g1a) > 1:
            p = np.array([p[0]] * len(g1a), dtype=object)
        return p, g1a, g2a

    def E0(self, S: np.ndarray) -> np.ndarray:
        S = np.asarray(S, dtype=float)
        sqrtS = np.sqrt(np.maximum(S, 0.0))
        log1pS = np.log1p(np.maximum(S, 0.0))
        inv = 1.0 / np.sqrt(np.maximum(S, 1.0))
        return (
            self.cal.c0
            + self.cal.c_sqrt * sqrtS
            + self.cal.c_log1p * log1pS
            + self.cal.c_inv_sqrt * inv
        )

    def compute_centers(
        self,
        S: np.ndarray,
        D: np.ndarray,
        center_mode: Optional[str] = None,
        weights: Optional[np.ndarray] = None,
        Sbar: Optional[float] = None,
        D2bar: Optional[float] = None,
    ) -> Tuple[float, float]:
        mode = center_mode or self.center_mode

        if mode == "custom":
            if Sbar is None or D2bar is None:
                raise ValueError("center_mode='custom' requires Sbar and D2bar")
            return float(Sbar), float(D2bar)

        if mode == "support":
            S = np.asarray(S, dtype=float)
            D2 = np.asarray(D, dtype=float) ** 2
            if weights is None:
                w = np.ones_like(S, dtype=float)
            else:
                w = np.asarray(weights, dtype=float)
                w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
            z = np.sum(w)
            if z > 0:
                return float(np.sum(w * S) / z), float(np.sum(w * D2) / z)

        # fixed fallback
        return self.cal.Sbar_fixed, self.cal.D2bar_fixed

    def U(self, S: np.ndarray, D: np.ndarray, t: np.ndarray, Sbar: float, D2bar: float) -> np.ndarray:
        S = np.asarray(S, dtype=float)
        D = np.asarray(D, dtype=float)
        t = np.asarray(t, dtype=float)
        # vectorize laws
        u0v = self.cal.u0_m * t + self.cal.u0_b
        u1v = self.cal.u1_m * t + self.cal.u1_b
        u2v = self.cal.u2_const
        return u0v + u1v * (S - Sbar) + u2v * (D * D - D2bar)

    def R45(self, S: np.ndarray, D: np.ndarray, t: np.ndarray) -> np.ndarray:
        S = np.asarray(S, dtype=float)
        D = np.asarray(D, dtype=float)
        t = np.asarray(t, dtype=float)

        a = np.vectorize(self.a45)(t)
        b = np.vectorize(self.b45)(t)

        return np.cos(np.pi * D / 45.0) * (
            a * np.sin(np.pi * S / 45.0)
            + b * np.cos(np.pi * S / 45.0)
        )

    def predict_components(
        self,
        p_center,
        g1,
        g2,
        center_mode: Optional[str] = None,
        weights: Optional[np.ndarray] = None,
        Sbar: Optional[float] = None,
        D2bar: Optional[float] = None,
    ) -> pd.DataFrame:
        p, g1a, g2a = self._arrays(p_center, g1, g2)
        n = max(len(p), len(g1a), len(g2a))
        if len(p) != n:
            p = np.array([p[0]] * n, dtype=object)
        if len(g1a) != n or len(g2a) != n:
            raise ValueError("p_center, g1, g2 must have the same length, or p_center must be scalar")

        S = g1a + g2a
        D = g2a - g1a
        t = np.array([safe_loglog(x) for x in p], dtype=float)

        Sbar_eff, D2bar_eff = self.compute_centers(
            S, D, center_mode=center_mode, weights=weights, Sbar=Sbar, D2bar=D2bar
        )

        e0 = self.E0(S)
        u = self.U(S, D, t, Sbar_eff, D2bar_eff)
        r45 = self.R45(S, D, t)
        delta = e0 + u + r45
        trust = np.array([self.trust_score(tt) for tt in t], dtype=float)

        out = pd.DataFrame({
            "p_center": list(p),
            "g1": g1a,
            "g2": g2a,
            "S": S,
            "D": D,
            "t_loglog": t,
            "Sbar_used": Sbar_eff,
            "D2bar_used": D2bar_eff,
            "E0": e0,
            "U": u,
            "R45": r45,
            "delta_v44": delta,
            "correction_factor_exp_delta": np.exp(np.clip(delta, -50, 50)),
            "a45": np.vectorize(self.a45)(t),
            "b45": np.vectorize(self.b45)(t),
            "trust_score": trust,
            "center_mode": center_mode or self.center_mode,
            "calibration_label": self.cal.calibration_label,
        })
        return out

    def predict_delta(self, p_center, g1, g2, **kwargs):
        out = self.predict_components(p_center, g1, g2, **kwargs)
        vals = out["delta_v44"].to_numpy()
        return float(vals[0]) if len(vals) == 1 else vals

    def predict_weight_correction(self, p_center, g1, g2, **kwargs):
        delta = self.predict_delta(p_center, g1, g2, **kwargs)
        return np.exp(delta)

    def score_gap_pair(self, p_center, g1, g2, **kwargs):
        """Alias for correction factor; higher means the pair is favored by V44."""
        return self.predict_weight_correction(p_center, g1, g2, **kwargs)

    # -----------------------------
    # Batch/audit
    # -----------------------------

    def predict_dataframe(
        self,
        df: pd.DataFrame,
        p_col: str = "p_center",
        g1_col: str = "g1",
        g2_col: str = "g2",
        weight_col: Optional[str] = None,
        center_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        if p_col not in df.columns or g1_col not in df.columns or g2_col not in df.columns:
            raise KeyError(f"Missing columns {p_col}, {g1_col}, {g2_col}")
        weights = df[weight_col].to_numpy(float) if weight_col and weight_col in df.columns else None

        pred = self.predict_components(
            df[p_col].to_numpy(dtype=object),
            df[g1_col].to_numpy(dtype=float),
            df[g2_col].to_numpy(dtype=float),
            center_mode=center_mode,
            weights=weights,
        )
        return pd.concat([df.reset_index(drop=True), pred.add_prefix("v44_")], axis=1)

    def audit_dataframe(
        self,
        df: pd.DataFrame,
        target_col: str,
        p_col: str = "p_center",
        g1_col: str = "g1",
        g2_col: str = "g2",
        weight_col: Optional[str] = None,
        center_mode: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        out = self.predict_dataframe(df, p_col, g1_col, g2_col, weight_col, center_mode)
        if target_col not in out.columns:
            raise KeyError(f"target_col={target_col} does not exist")

        y = pd.to_numeric(out[target_col], errors="coerce").to_numpy(float)
        pred_cols = ["v44_E0", "v44_E0_plus_U", "v44_delta_v44"]
        out["v44_E0_plus_U"] = out["v44_E0"] + out["v44_U"]

        rows = []
        base_rms = _rms(y)
        for label, col in [
            ("M0_E0", "v44_E0"),
            ("M3_E0_plus_U", "v44_E0_plus_U"),
            ("M3_plus_R45", "v44_delta_v44"),
        ]:
            p = out[col].to_numpy(float)
            residual = y - p
            r = _rms(residual)
            imp = 100.0 * (base_rms - r) / base_rms if base_rms and np.isfinite(base_rms) else np.nan
            rows.append({
                "model": label,
                "target_col": target_col,
                "rms_target": base_rms,
                "rms_after": r,
                "improvement_pct_vs_zero": imp,
                "corr_pred_target": _corr(p, y),
                "n": len(out),
                "center_mode": center_mode or self.center_mode,
            })

        summary = pd.DataFrame(rows)
        return out, summary


def _rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return float("nan")
    return float(np.sqrt(np.mean(x*x)))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return float("nan")
    aa = a[m] - a[m].mean()
    bb = b[m] - b[m].mean()
    den = np.sqrt(np.sum(aa*aa) * np.sum(bb*bb))
    if den <= 0:
        return float("nan")
    return float(np.sum(aa*bb) / den)


# =============================================================================
# CLI
# =============================================================================

def print_formula(pred: FrozenV44Predictor) -> None:
    c = pred.cal
    print("=" * 88)
    print("V44_primes_predicor_frozen")
    print("=" * 88)
    print("Formula:")
    print("  Delta(S,D;p) = E0(S) + U(S,D;t) + R45(S,D;t)")
    print("  t = loglog(p)")
    print("  E0(S) = c0 + c1*sqrt(S) + c2*log(1+S) + c3/sqrt(S)")
    print("  U = u0(t) + u1(t)*(S-Sbar) + u2*(D^2-D2bar)")
    print("  R45 = cos(pi*D/45) * [a(t)*sin(pi*S/45) + b(t)*cos(pi*S/45)]")
    print("")
    print("Calibration constants:")
    for k, v in asdict(c).items():
        print(f"  {k}: {v}")
    print("")
    print("Caveat:")
    print("  This is an empirical frozen predictor, not a proof of RH/twin primes/Goldbach.")


def parse_args():
    ap = argparse.ArgumentParser(description="Frozen V44 prime gap residual predictor")
    ap.add_argument("--input", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=Path("v44_predictions.csv"))
    ap.add_argument("--summary-output", type=Path, default=Path("v44_audit_summary.csv"))
    ap.add_argument("--p-col", default="p_center")
    ap.add_argument("--g1-col", default="g1")
    ap.add_argument("--g2-col", default="g2")
    ap.add_argument("--target-col", default=None)
    ap.add_argument("--weight-col", default=None)
    ap.add_argument("--center-mode", choices=["fixed", "support"], default="fixed")
    ap.add_argument("--show-formula", action="store_true")
    ap.add_argument("--demo", action="store_true")
    return ap.parse_args()


def main():
    args = parse_args()
    pred = FrozenV44Predictor(center_mode=args.center_mode)

    if args.show_formula or args.input is None:
        print_formula(pred)

    if args.demo:
        demo = pred.predict_components(
            p_center=[10**9, 10**12],
            g1=[12, 30],
            g2=[18, 42],
            center_mode=args.center_mode,
        )
        print("\nDemo predictions:")
        print(demo.to_string(index=False))

    if args.input is None:
        return

    df = pd.read_csv(args.input)
    if args.target_col:
        out, summary = pred.audit_dataframe(
            df,
            target_col=args.target_col,
            p_col=args.p_col,
            g1_col=args.g1_col,
            g2_col=args.g2_col,
            weight_col=args.weight_col,
            center_mode=args.center_mode,
        )
        summary.to_csv(args.summary_output, index=False)
        print(f"Audit summary saved to: {args.summary_output}")
        print(summary.to_string(index=False))
    else:
        out = pred.predict_dataframe(
            df,
            p_col=args.p_col,
            g1_col=args.g1_col,
            g2_col=args.g2_col,
            weight_col=args.weight_col,
            center_mode=args.center_mode,
        )

    out.to_csv(args.output, index=False)
    print(f"Predictions saved to: {args.output}")


if __name__ == "__main__":
    main()
