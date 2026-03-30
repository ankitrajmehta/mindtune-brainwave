import tkinter as tk
from tkinter import messagebox
import threading
import queue
import serial
import time
from datetime import datetime
from prediction import MindTunePredictor
from typing import Optional

try:
    Serial = serial.Serial
    SerialException = serial.SerialException
except AttributeError as exc:
    raise SystemExit(
        "PySerial is not available. Uninstall 'serial' and install 'pyserial' (e.g. 'uv add pyserial')."
    ) from exc


class EmotionDetectorUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MindTune - Live Emotion Detection")
        self.root.geometry("1100x700")
        self.root.minsize(960, 640)

        # Configuration
        self.com_var = tk.StringVar(value="COM1")
        self.baud_var = tk.StringVar(value="57600")

        # Threading
        self.lock = threading.Lock()
        self.ui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.reader_thread: Optional[threading.Thread] = None
        self.ser: Optional[Serial] = None

        # State
        self.running = False
        self.serial_connected = False
        self.packet_count = 0
        self.model_loaded = False

        # Current data
        self.current_emotion = "N/A"
        self.current_data = {
            "signal_quality": 0,
            "attention": 0,
            "meditation": 0,
            "delta": 0,
            "theta": 0,
            "low_alpha": 0,
            "high_alpha": 0,
            "low_beta": 0,
            "high_beta": 0,
            "low_gamma": 0,
            "mid_gamma": 0,
        }

        # UI elements
        self.signal_label: Optional[tk.Label] = None
        self.serial_label: Optional[tk.Label] = None
        self.packet_label: Optional[tk.Label] = None
        self.model_status_label: Optional[tk.Label] = None
        self.emotion_label: Optional[tk.Label] = None
        self.log_listbox: Optional[tk.Listbox] = None
        self.start_button: Optional[tk.Button] = None
        self.stop_button: Optional[tk.Button] = None

        # Initialize predictor
        self.predictor = None
        print("=" * 60)
        print("MindTune Emotion Detector - Initializing")
        print("=" * 60)
        self._load_model()

        self._build_ui()
        self.root.after(200, self._refresh_ui)

    def _load_model(self) -> None:
        """Load the ML model and scaler"""
        print("\n[INIT] Loading machine learning model...")
        try:
            # LightGBM is a tree-based model, doesn't need scaling
            self.predictor = MindTunePredictor(
                "lightgbm.pkl", "scaler_2.pkl", needs_scaling=False
            )
            self.model_loaded = True
            print("[OK] ✓ Model loaded successfully (LightGBM)")
            print(
                f"[INFO] Model expects {len(self.predictor.expected_features)} features"
            )
            print(f"[INFO] Emotion classes: {list(self.predictor.label_map.values())}")
        except Exception as e:
            print(f"[ERROR] ✗ Failed to load model: {e}")
            self.model_loaded = False
            messagebox.showerror(
                "Model Error",
                f"Failed to load model:\n{e}\n\nThe app will start but predictions will not work.",
            )
        print("-" * 60)

    def _build_ui(self) -> None:
        """Build the UI matching collector_ui.py style"""
        # Top configuration frame
        top = tk.Frame(self.root, padx=12, pady=10)
        top.pack(fill="x")

        # COM Port and Baud Rate
        tk.Label(top, text="COM Port").grid(row=0, column=0, padx=4, pady=4, sticky="e")
        com_entry = tk.Entry(top, textvariable=self.com_var, width=18)
        com_entry.grid(row=0, column=1, padx=4, pady=4, sticky="w")

        tk.Label(top, text="Baud Rate").grid(
            row=0, column=2, padx=4, pady=4, sticky="e"
        )
        baud_entry = tk.Entry(top, textvariable=self.baud_var, width=18)
        baud_entry.grid(row=0, column=3, padx=4, pady=4, sticky="w")

        # Model Status
        tk.Label(top, text="Model Status").grid(
            row=1, column=0, padx=4, pady=4, sticky="e"
        )
        model_status_text = "LOADED" if self.model_loaded else "FAILED"
        model_status_color = "#1f7a1f" if self.model_loaded else "#a00000"
        self.model_status_label = tk.Label(
            top,
            text=model_status_text,
            fg=model_status_color,
            font=("Segoe UI", 10, "bold"),
        )
        self.model_status_label.grid(row=1, column=1, padx=4, pady=4, sticky="w")

        # Start/Stop buttons
        self.start_button = tk.Button(
            top, text="Start Detection", width=18, command=self.start_detection
        )
        self.start_button.grid(row=0, column=4, rowspan=1, padx=8, pady=4, sticky="ew")

        self.stop_button = tk.Button(
            top,
            text="Stop Detection",
            width=18,
            command=self.stop_detection,
            state="disabled",
        )
        self.stop_button.grid(row=1, column=4, rowspan=1, padx=8, pady=4, sticky="ew")

        # Status frame
        status_frame = tk.Frame(self.root, padx=12, pady=8)
        status_frame.pack(fill="x")

        self.running_label = tk.Label(
            status_frame,
            text="Detection: OFF",
            fg="#a00000",
            font=("Segoe UI", 12, "bold"),
        )
        self.running_label.pack(side="left", padx=(0, 20))

        self.serial_label = tk.Label(
            status_frame,
            text="Serial: DISCONNECTED",
            fg="#a00000",
            font=("Segoe UI", 11, "bold"),
        )
        self.serial_label.pack(side="left", padx=(0, 20))

        self.packet_label = tk.Label(
            status_frame, text="Packets: 0", font=("Segoe UI", 11)
        )
        self.packet_label.pack(side="left", padx=(0, 20))

        self.signal_label = tk.Label(
            status_frame, text="Signal: N/A", font=("Segoe UI", 11)
        )
        self.signal_label.pack(side="left")

        # Content frame
        content = tk.Frame(self.root, padx=12, pady=8)
        content.pack(fill="both", expand=True)

        # Left side - Emotion display and metrics
        left = tk.Frame(content)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Emotion display
        emotion_frame = tk.LabelFrame(left, text="Current Emotion", padx=10, pady=10)
        emotion_frame.pack(fill="x", pady=(0, 8))

        self.emotion_label = tk.Label(
            emotion_frame, text="N/A", font=("Segoe UI", 48, "bold"), fg="#555555"
        )
        self.emotion_label.pack(pady=20)

        # Core metrics
        metrics_frame = tk.LabelFrame(left, text="Core Metrics", padx=10, pady=10)
        metrics_frame.pack(fill="x", pady=(0, 8))

        self.attention_label = tk.Label(
            metrics_frame, text="Attention: --", font=("Segoe UI", 11), anchor="w"
        )
        self.attention_label.pack(fill="x", pady=2)

        self.meditation_label = tk.Label(
            metrics_frame, text="Meditation: --", font=("Segoe UI", 11), anchor="w"
        )
        self.meditation_label.pack(fill="x", pady=2)

        # Brainwave bands
        bands_frame = tk.LabelFrame(left, text="Brainwave Bands (K)", padx=10, pady=10)
        bands_frame.pack(fill="both", expand=True)

        self.delta_label = tk.Label(
            bands_frame, text="Delta: --", font=("Segoe UI", 10), anchor="w"
        )
        self.delta_label.pack(fill="x", pady=1)

        self.theta_label = tk.Label(
            bands_frame, text="Theta: --", font=("Segoe UI", 10), anchor="w"
        )
        self.theta_label.pack(fill="x", pady=1)

        self.alpha_label = tk.Label(
            bands_frame, text="Alpha (L/H): --/--", font=("Segoe UI", 10), anchor="w"
        )
        self.alpha_label.pack(fill="x", pady=1)

        self.beta_label = tk.Label(
            bands_frame, text="Beta (L/H): --/--", font=("Segoe UI", 10), anchor="w"
        )
        self.beta_label.pack(fill="x", pady=1)

        self.gamma_label = tk.Label(
            bands_frame, text="Gamma (L/M): --/--", font=("Segoe UI", 10), anchor="w"
        )
        self.gamma_label.pack(fill="x", pady=1)

        # Right side - Activity log
        right = tk.Frame(content)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        log_frame = tk.LabelFrame(right, text="Activity Log", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True)

        self.log_listbox = tk.Listbox(log_frame, height=30)
        self.log_listbox.pack(fill="both", expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Log initial message
        self._append_log("System initialized")
        if self.model_loaded:
            self._append_log("Model loaded successfully")
        else:
            self._append_log("WARNING: Model failed to load")

    def _append_log(self, text: str) -> None:
        """Append message to activity log"""
        if self.log_listbox is None:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_listbox.insert(0, f"[{ts}] {text}")
        if self.log_listbox.size() > 100:
            self.log_listbox.delete(100, tk.END)

    def _queue_log(self, text: str) -> None:
        """Queue a log message from a thread"""
        self.ui_queue.put(text)

    def _refresh_ui(self) -> None:
        """Update UI elements periodically"""
        if (
            self.packet_label is None
            or self.serial_label is None
            or self.signal_label is None
            or self.emotion_label is None
        ):
            self.root.after(200, self._refresh_ui)
            return

        # Process queued log messages
        while not self.ui_queue.empty():
            try:
                log_text = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(log_text)

        with self.lock:
            signal_quality = self.current_data["signal_quality"]
            packet_count = self.packet_count
            serial_connected = self.serial_connected
            emotion = self.current_emotion
            attention = self.current_data["attention"]
            meditation = self.current_data["meditation"]
            delta = self.current_data["delta"]
            theta = self.current_data["theta"]
            low_alpha = self.current_data["low_alpha"]
            high_alpha = self.current_data["high_alpha"]
            low_beta = self.current_data["low_beta"]
            high_beta = self.current_data["high_beta"]
            low_gamma = self.current_data["low_gamma"]
            mid_gamma = self.current_data["mid_gamma"]

        # Update packet count
        self.packet_label.config(text=f"Packets: {packet_count}")

        # Update serial status
        if serial_connected:
            self.serial_label.config(text="Serial: CONNECTED", fg="#1f7a1f")
        else:
            self.serial_label.config(text="Serial: DISCONNECTED", fg="#a00000")

        # Update signal quality
        if signal_quality == 0:
            text = "Signal: Good (0)"
            color = "#1f7a1f"
        elif signal_quality == 200:
            text = "Signal: Not worn (200)"
            color = "#a00000"
        else:
            text = f"Signal: {signal_quality}"
            color = "#9a6c00"
        self.signal_label.config(text=text, fg=color)

        # Update emotion with color coding
        emotion_colors = {
            "calm": "#1f7a1f",
            "neutral": "#9a6c00",
            "stressed": "#a00000",
            "Initializing buffer...": "#555555",
            "N/A": "#555555",
        }
        self.emotion_label.config(
            text=emotion.upper(), fg=emotion_colors.get(emotion, "#555555")
        )

        # Update metrics
        self.attention_label.config(text=f"Attention: {attention}")
        self.meditation_label.config(text=f"Meditation: {meditation}")

        # Update brainwave bands
        self.delta_label.config(text=f"Delta: {delta // 1000}K")
        self.theta_label.config(text=f"Theta: {theta // 1000}K")
        self.alpha_label.config(
            text=f"Alpha (L/H): {low_alpha // 1000}K/{high_alpha // 1000}K"
        )
        self.beta_label.config(
            text=f"Beta (L/H): {low_beta // 1000}K/{high_beta // 1000}K"
        )
        self.gamma_label.config(
            text=f"Gamma (L/M): {low_gamma // 1000}K/{mid_gamma // 1000}K"
        )

        # Schedule next update
        self.root.after(200, self._refresh_ui)

    def start_detection(self) -> None:
        """Start the detection process"""
        if self.running:
            return

        if not self.model_loaded:
            messagebox.showerror("Model Error", "Cannot start: Model is not loaded")
            return

        try:
            baud_rate = int(self.baud_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Baud rate must be an integer")
            return

        com_port = self.com_var.get().strip()
        if not com_port:
            messagebox.showerror("Missing input", "Please enter a COM port")
            return

        print("\n" + "=" * 60)
        print(f"[START] Initializing detection on {com_port}")
        print("=" * 60)

        self.running = True
        self.stop_event.clear()

        with self.lock:
            self.packet_count = 0
            self.serial_connected = False
            self.current_emotion = "Initializing..."

        if self.running_label is not None:
            self.running_label.config(text="Detection: ON", fg="#1f7a1f")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        self._append_log("Detection STARTED")

        # Start reader thread
        self.reader_thread = threading.Thread(
            target=self._serial_reader_loop, args=(com_port, baud_rate), daemon=True
        )
        self.reader_thread.start()

        self.root.focus_set()

    def stop_detection(self) -> None:
        """Stop the detection process"""
        if not self.running:
            return

        print("\n[STOP] Stopping detection...")

        self.running = False
        self.stop_event.set()

        if self.ser is not None:
            try:
                if self.ser.is_open:
                    self.ser.close()
            except SerialException:
                pass

        if self.reader_thread is not None and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=1.5)

        with self.lock:
            self.serial_connected = False

        if self.running_label is not None:
            self.running_label.config(text="Detection: OFF", fg="#a00000")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

        self._append_log("Detection STOPPED")
        print("[STOP] Detection stopped successfully")

    def _serial_reader_loop(self, com_port: str, baud_rate: int) -> None:
        """Main serial reading loop (runs in thread)"""
        while not self.stop_event.is_set():
            if self.ser is None or not self.ser.is_open:
                try:
                    print(f"[SERIAL] Connecting to {com_port}...")
                    self.ser = Serial(com_port, baud_rate, timeout=1)
                    with self.lock:
                        self.serial_connected = True
                    self._queue_log(f"Serial connected on {com_port}")
                    print(f"[SERIAL] ✓ Connected to {com_port}")
                except SerialException as exc:
                    with self.lock:
                        self.serial_connected = False
                    self._queue_log(f"Serial connection failed: {exc}")
                    print(f"[SERIAL] ✗ Connection failed: {exc}")
                    time.sleep(2)
                    continue

            try:
                self._read_and_parse_packet()
            except SerialException as exc:
                with self.lock:
                    self.serial_connected = False
                self._queue_log(f"Serial error: {exc}")
                print(f"[SERIAL] Error: {exc}")
                try:
                    if self.ser and self.ser.is_open:
                        self.ser.close()
                except SerialException:
                    pass
                self.ser = None
                time.sleep(1)

    def _read_and_parse_packet(self) -> None:
        """Read and parse a single ThinkGear packet"""
        ser = self.ser
        if ser is None:
            return

        # Wait for sync bytes
        if ser.read(1) != b"\xaa":
            return
        if ser.read(1) != b"\xaa":
            return

        # Payload length
        plen_byte = ser.read(1)
        if not plen_byte:
            return
        plen = plen_byte[0]
        if plen > 169:
            return

        # Read payload
        payload = ser.read(plen)
        if len(payload) < plen:
            return

        # Read checksum
        chksum_byte = ser.read(1)
        if not chksum_byte:
            return
        chksum = chksum_byte[0]

        # Verify checksum
        calc_chksum = (~(sum(payload) & 0xFF)) & 0xFF
        if calc_chksum != chksum:
            return

        with self.lock:
            self.packet_count += 1

        # Parse payload
        i = 0
        meditation_updated = False
        while i < plen:
            code = payload[i]
            i += 1

            # Poor Signal (0x02)
            if code == 0x02:
                if i >= plen:
                    break
                with self.lock:
                    self.current_data["signal_quality"] = payload[i]
                i += 1

            # Attention (0x04)
            elif code == 0x04:
                if i >= plen:
                    break
                with self.lock:
                    self.current_data["attention"] = payload[i]
                i += 1

            # Meditation (0x05)
            elif code == 0x05:
                if i >= plen:
                    break
                with self.lock:
                    self.current_data["meditation"] = payload[i]
                i += 1
                meditation_updated = True

            # ASIC EEG Power (0x83)
            elif code == 0x83:
                if i >= plen:
                    break
                vlen = payload[i]
                i += 1
                if vlen == 24 and i + 24 <= plen:
                    bands = [
                        (payload[i] << 16) | (payload[i + 1] << 8) | payload[i + 2],
                        (payload[i + 3] << 16) | (payload[i + 4] << 8) | payload[i + 5],
                        (payload[i + 6] << 16) | (payload[i + 7] << 8) | payload[i + 8],
                        (payload[i + 9] << 16)
                        | (payload[i + 10] << 8)
                        | payload[i + 11],
                        (payload[i + 12] << 16)
                        | (payload[i + 13] << 8)
                        | payload[i + 14],
                        (payload[i + 15] << 16)
                        | (payload[i + 16] << 8)
                        | payload[i + 17],
                        (payload[i + 18] << 16)
                        | (payload[i + 19] << 8)
                        | payload[i + 20],
                        (payload[i + 21] << 16)
                        | (payload[i + 22] << 8)
                        | payload[i + 23],
                    ]
                    with self.lock:
                        self.current_data["delta"] = bands[0]
                        self.current_data["theta"] = bands[1]
                        self.current_data["low_alpha"] = bands[2]
                        self.current_data["high_alpha"] = bands[3]
                        self.current_data["low_beta"] = bands[4]
                        self.current_data["high_beta"] = bands[5]
                        self.current_data["low_gamma"] = bands[6]
                        self.current_data["mid_gamma"] = bands[7]
                    i += 24
                else:
                    i += min(vlen, plen - i)

            # Handle other multi-byte codes
            elif code >= 0x80:
                if i >= plen:
                    break
                vlen = payload[i]
                i += 1
                i += min(vlen, max(0, plen - i))

            # Handle other single-byte codes
            else:
                if i < plen:
                    i += 1

        # Make prediction when meditation updates (once per second)
        if meditation_updated:
            self._make_prediction()

    def _make_prediction(self) -> None:
        """Make emotion prediction from current EEG data"""
        if self.predictor is None:
            return

        with self.lock:
            raw_data = dict(self.current_data)

        try:
            # Make prediction
            emotion = self.predictor.predict(raw_data)

            with self.lock:
                old_emotion = self.current_emotion
                self.current_data = raw_data  # Update to latest
                self.current_emotion = emotion

            # Log prediction
            if emotion != "Initializing buffer...":
                if emotion != old_emotion:
                    print(
                        f"[PREDICT] Emotion: {emotion.upper()} (Att:{raw_data['attention']}, Med:{raw_data['meditation']})"
                    )
                    self._queue_log(f"Emotion: {emotion.upper()}")

        except Exception as e:
            print(f"[ERROR] Prediction failed: {e}")
            with self.lock:
                self.current_emotion = "Error"

    def _on_close(self) -> None:
        """Handle window close event"""
        if self.running:
            self.stop_detection()
        self.root.destroy()


def main() -> None:
    """Main entry point"""
    root = tk.Tk()
    app = EmotionDetectorUI(root)
    print("\n[READY] System ready. Press 'Start Detection' to begin.")
    print("=" * 60 + "\n")
    root.mainloop()


if __name__ == "__main__":
    main()
