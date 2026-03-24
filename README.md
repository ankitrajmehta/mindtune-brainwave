# MindTune EEG Logger

Logs MindTune EEG data from a serial port into `mindtune_full_eeg_data.csv`.

Created for Toshiba Mindtune px3809N-1ETC bluetooth based brainwave recording headphones.

## Logged features:
```
Timestamp,Signal_Quality,Attention,Meditation,Delta,Theta,Low_Alpha,High_Alpha,Low_Beta,High_Beta,Low_Gamma,Mid_Gamma
```

## Run
1. Set `COM_PORT` in `main.py` (example: `COM3`).
2. Install deps: `uv sync`
3. Start logger: `uv run .\main.py`
