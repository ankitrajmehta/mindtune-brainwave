"""
Test script to verify emotion_detector_ui.py predictions match the expected results
by feeding CSV data through the same prediction pipeline that the UI uses.
"""

import pandas as pd
from pathlib import Path
from prediction import MindTunePredictor


def test_ui_predictions():
    """Test predictions using the same data format as emotion_detector_ui.py"""

    print("=" * 70)
    print("Testing emotion_detector_ui.py Prediction Pipeline")
    print("=" * 70)

    # Load predictor (same as UI does)
    print("\n[INIT] Loading model...")
    predictor = MindTunePredictor("lightgbm.pkl", "scaler_2.pkl", needs_scaling=False)
    print("[OK] Model loaded successfully")
    print(f"[INFO] Model expects {len(predictor.expected_features)} features")

    # Load test CSV data
    csv_path = Path(__file__).resolve().parent / "all_sessions_eeg_with_markers.csv"
    df = pd.read_csv(csv_path)

    # Find stressed segment (same as prediction.py test)
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
        raise ValueError("Could not find 50 consecutive stressed rows")

    segment = df.iloc[start_idx : start_idx + 50]

    print(f"\n[TEST] Testing on {len(segment)} samples from stressed segment")
    print("-" * 70)

    # Simulate what emotion_detector_ui.py does
    predictions = []

    for i, (_, row) in enumerate(segment.iterrows(), start=1):
        # Create raw_data dict exactly as emotion_detector_ui.py does
        # (matches the structure of self.current_data in emotion_detector_ui.py:46-58)
        raw_data = {
            "signal_quality": int(row["signal_quality"]),
            "attention": int(row["attention"]),
            "meditation": int(row["meditation"]),
            "delta": int(row["delta"]),
            "theta": int(row["theta"]),
            "low_alpha": int(row["low_alpha"]),
            "high_alpha": int(row["high_alpha"]),
            "low_beta": int(row["low_beta"]),
            "high_beta": int(row["high_beta"]),
            "low_gamma": int(row["low_gamma"]),
            "mid_gamma": int(row["mid_gamma"]),
        }

        # Make prediction (same as UI's _make_prediction method)
        emotion = predictor.predict(raw_data)
        predictions.append(emotion)

        print(
            f"Sample {i:2d}: {emotion:20s} (Att:{raw_data['attention']:3d}, Med:{raw_data['meditation']:3d})"
        )

    # Analyze results
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    # Count predictions
    from collections import Counter

    counts = Counter(predictions)

    print(f"\nTotal samples: {len(predictions)}")
    print(f"\nPrediction breakdown:")
    for emotion, count in counts.most_common():
        percentage = (count / len(predictions)) * 100
        print(f"  {emotion:20s}: {count:3d} samples ({percentage:5.1f}%)")

    # Check if predictions are working
    non_init = [p for p in predictions if p != "Initializing buffer..."]
    stressed_count = sum(1 for p in non_init if p == "stressed")

    print(f"\n[ANALYSIS]")
    print(f"  Samples after initialization: {len(non_init)}")
    print(
        f"  Stressed predictions: {stressed_count}/{len(non_init)} ({stressed_count / len(non_init) * 100:.1f}%)"
    )

    if stressed_count / len(non_init) >= 0.8:  # 80% threshold
        print(f"\n[SUCCESS] ✓ Model is correctly identifying stressed state!")
        print(f"           Expected: stressed samples from CSV")
        print(
            f"           Got: {stressed_count / len(non_init) * 100:.1f}% stressed predictions"
        )
    else:
        print(f"\n[WARNING] Model predictions may not be accurate")
        print(
            f"          Expected mostly 'stressed' but got {stressed_count / len(non_init) * 100:.1f}%"
        )

    print("\n" + "=" * 70)
    print("[COMPLETE] Test finished")
    print("=" * 70)

    return predictions


if __name__ == "__main__":
    test_ui_predictions()
