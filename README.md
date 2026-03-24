# MindTune EEG Logger

Logs MindTune EEG data from a serial port into `mindtune_full_eeg_data.csv`.

Created for Toshiba Mindtune px3809N-1ETC bluetooth based brainwave recording headphones.

## Logged features:
```
Timestamp,Signal_Quality,Attention,Meditation,Delta,Theta,Low_Alpha,High_Alpha,Low_Beta,High_Beta,Low_Gamma,Mid_Gamma
```

## Initial set up
1. Install mindtune bluetooth driver from the set up folder provided in the cd
2. Connect the dongle and connect the headphones (click power button then media button for 3-5 secs until it flashes red-blue which means its in pairing mode)
3. Confirm the COM_PORT used by the bluetooth connection (through device manger or bluetooth devices)


## Run
1. Set `COM_PORT` in `main.py` (example: `COM1`).
2. Install deps: `uv sync`
3. Start logger: `uv run .\main.py` for only raw data
    `uv run collector_ui.py` for tkinter ui based data collection


