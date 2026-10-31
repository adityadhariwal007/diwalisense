"""Quantile training helper; caller supplies numeric features and aligned targets."""
from lightgbm import LGBMRegressor


def train_quantiles(X, y):
    if len(X) == 0 or len(X) != len(y) or y.isna().any():
        raise ValueError("Need nonempty aligned X/y with observed targets")
    if not X.index.equals(y.index):
        raise ValueError("X/y indices must match")
    models = {}
    for quantile in (0.1, 0.5, 0.9):
        model = LGBMRegressor(
            objective="quantile", alpha=quantile, n_estimators=100,
            num_leaves=15, random_state=42, n_jobs=1, verbosity=-1,
        )
        models[quantile] = model.fit(X, y)
    return models


def train_baseline(X, y):
    # TODO: select non-event training rows; exclude 2025; tune on earlier time folds.
    # TODO: caller must exclude target-time PM2.5 and unavailable future observations.
    return train_quantiles(X, y)
