import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from prediction import MindTunePredictor

# Load the model and training data
model = joblib.load("extra_trees_model.pkl")
featured_df = pd.read_csv("featured_mindtune.csv")

# Get the stressed samples from training data
stressed_train = featured_df[featured_df["label_3class"] == "stressed"]
neutral_train = featured_df[featured_df["label_3class"] == "neutral"]

drop_cols = [
    "session_id",
    "participant_id",
    "timestamp_ms",
    "label_3class",
    "label_encoded",
]
feature_cols = [col for col in featured_df.columns if col not in drop_cols]

print("=== Feature Statistics from TRAINING data ===")
print("\nStressed samples (training):")
print(stressed_train[feature_cols].describe().loc[["mean", "std"]].T.head(20))

print("\n\nNeutral samples (training):")
print(neutral_train[feature_cols].describe().loc[["mean", "std"]].T.head(20))

# Now let's see what the predictor generates
print("\n\n=== Feature Statistics from PREDICTION (test segment) ===")

predictor = MindTunePredictor(
    "extra_trees_model.pkl", "scaler.pkl", needs_scaling=False
)

csv_path = Path("all_sessions_eeg_with_markers.csv")
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

stressed_mask = df["marker_emotion"].fillna("").astype(str).str.lower().eq("stressed")
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

segment = df.iloc[start_idx : start_idx + 50]

# Collect all features generated during prediction
generated_features = []
for i, (_, row) in enumerate(segment.iterrows(), start=1):
    raw_sample = {col: float(row[col]) for col in signal_cols}
    raw_sample.update({col: float(row[col]) for col in marker_cols})

    # Preprocess and collect features
    feat = predictor._preprocess(raw_sample)
    predictor.history.append(feat)

    if len(predictor.history) >= predictor.window_size:
        df_history = pd.DataFrame(list(predictor.history))
        final_features = feat.copy()

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

        generated_features.append(final_features)

generated_df = pd.DataFrame(generated_features)
print("\nGenerated features from test segment (stressed):")
print(generated_df.describe().loc[["mean", "std"]].T.head(20))

# Compare key stress indicators
print("\n\n=== KEY STRESS INDICATORS COMPARISON ===")
key_features = [
    "theta_beta_ratio",
    "alpha_beta_ratio",
    "attention",
    "meditation",
    "theta_pct",
    "low_beta_pct",
    "high_beta_pct",
]

for feat in key_features:
    if feat in generated_df.columns:
        print(f"\n{feat}:")
        print(
            f"  Training (stressed):  mean={stressed_train[feat].mean():.4f}, std={stressed_train[feat].std():.4f}"
        )
        print(
            f"  Training (neutral):   mean={neutral_train[feat].mean():.4f}, std={neutral_train[feat].std():.4f}"
        )
        print(
            f"  Prediction (segment): mean={generated_df[feat].mean():.4f}, std={generated_df[feat].std():.4f}"
        )
