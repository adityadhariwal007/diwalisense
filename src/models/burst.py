"""Residual model; inputs must come from leakage-free baseline predictions."""
from src.models.baseline import train_quantiles


def train_burst(X_event, observed_pm25, baseline_oof_p50):
    if not observed_pm25.index.equals(baseline_oof_p50.index):
        raise ValueError("Observed and out-of-time baseline indices must match")
    residual = observed_pm25 - baseline_oof_p50
    # TODO: pooled event rows, policy features, rolling out-of-time baseline predictions.
    # TODO: calibrate TOTAL forecast ranges; do not add component quantiles blindly.
    return train_quantiles(X_event, residual)
