import pandas as pd
import numpy as np
import joblib
import time
from collections import deque
from pathlib import Path


class MindTunePredictor:
    def __init__(self, model_path, scaler_path, window_size=5, needs_scaling=False):
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.needs_scaling = needs_scaling

        self.history = deque(maxlen=window_size)
        self.window_size = window_size

        self.label_map = {0: "calm", 1: "neutral", 2: "stressed"}

        # EXACT column order from your training dataframe
        # Normalize feature names to plain str so sklearn feature-name validation stays consistent.
        self.expected_features = [str(col) for col in self.model.feature_names_in_]

    def _preprocess(self, raw_data):
        # 1. Calculate Percentages
        bands = [
            "delta",
            "theta",
            "low_alpha",
            "high_alpha",
            "low_beta",
            "high_beta",
            "low_gamma",
            "mid_gamma",
        ]
        total_power = sum([raw_data.get(b, 0) for b in bands]) + 1e-6
        feat = {f"{b}_pct": raw_data.get(b, 0) / total_power for b in bands}

        # 2. Add base metrics (session_time_sec removed - model retrained without it)
        feat["attention"] = float(raw_data.get("attention", 0))
        feat["meditation"] = float(raw_data.get("meditation", 0))
        feat["signal_quality"] = float(raw_data.get("signal_quality", 0))

        # 3. Markers
        marker_cols = [c for c in self.expected_features if "marker_ev" in c]
        for col in marker_cols:
            feat[col] = float(raw_data.get(col, 0))

        # 4. Ratios
        eps = 1e-6
        feat["theta_beta_ratio"] = feat["theta_pct"] / (
            feat["low_beta_pct"] + feat["high_beta_pct"] + eps
        )
        feat["alpha_beta_ratio"] = (feat["low_alpha_pct"] + feat["high_alpha_pct"]) / (
            feat["low_beta_pct"] + feat["high_beta_pct"] + eps
        )
        feat["slow_fast_ratio"] = (feat["delta_pct"] + feat["theta_pct"]) / (
            feat["low_beta_pct"]
            + feat["high_beta_pct"]
            + feat["low_gamma_pct"]
            + feat["mid_gamma_pct"]
            + eps
        )

        return feat

    def predict(self, raw_data_dict):
        current_feat = self._preprocess(raw_data_dict)
        self.history.append(current_feat)

        if len(self.history) < self.window_size:
            return "Initializing buffer..."

        df_history = pd.DataFrame(list(self.history))
        final_features = current_feat.copy()

        # Rolling stats
        rolling_base = [
            "delta_pct",
            "theta_pct",
            "low_alpha_pct",
            "high_alpha_pct",
            "low_beta_pct",
            "high_beta_pct",
            "attention",
            "meditation",
        ]

        for col in rolling_base:
            final_features[f"{col}_roll_mean_5"] = df_history[col].mean()
            final_features[f"{col}_roll_std_5"] = df_history[col].std()

        # Convert to DF and force columns to match training EXACTLY
        X_input = pd.DataFrame([final_features])

        # Reorder columns to match the model's training order
        X_input = X_input[self.expected_features]

        # Only scale if the model requires it (e.g., KNN, SVM, LogReg, MLP)
        # Tree-based models (Random Forest, Extra Trees, etc.) don't need scaling
        if self.needs_scaling:
            scaled_data = self.scaler.transform(X_input)
            X_final = pd.DataFrame(scaled_data, columns=self.expected_features)
        else:
            X_final = X_input

        # Predict
        prediction_idx = self.model.predict(X_final)[0]

        return self.label_map.get(prediction_idx, "Unknown")


# --- TEST ---
if __name__ == "__main__":
    # LightGBM doesn't need scaling (tree-based model)
    predictor = MindTunePredictor("lightgbm.pkl", "scaler_2.pkl", needs_scaling=False)

    csv_path = Path(__file__).resolve().parent / "all_sessions_eeg_with_markers.csv"
    df = pd.read_csv(csv_path)

    signal_cols = [
        "delta",
        "theta",
        "low_alpha",
        "high_alpha",
        "low_beta",
        "high_beta",
        "low_gamma",
        "mid_gamma",
        "attention",
        "meditation",
        "signal_quality",
    ]
    marker_cols = [c for c in df.columns if c.startswith("marker_ev_")]

    stressed_mask = (
        df["marker_emotion"].fillna("").astype(str).str.lower().eq("stressed")
    )

    start_idx = None
    run_len = 0
    for idx, is_stressed in enumerate(stressed_mask.tolist()):
        if is_stressed:
            run_len += 1
            if run_len == 50:
                start_idx = idx - 49
                break
        else:
            run_len = 0

    if start_idx is None:
        raise ValueError(
            "Could not find 50 consecutive unknown rows in all_sessions_eeg_with_markers.csv"
        )

    segment = df.iloc[start_idx : start_idx + 50]

    for i, (_, row) in enumerate(segment.iterrows(), start=1):
        raw_sample = {col: float(row[col]) for col in signal_cols}
        raw_sample.update({col: float(row[col]) for col in marker_cols})
        print(f"Point {i}: {predictor.predict(raw_sample)}")
