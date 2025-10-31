
# hmp4040_pyvisa_v3_arb.py
# Updated HMP4040 controller with ARB helper methods added.
# Save this file and import HMP4040PyVISA from it.

import time
from datetime import datetime
import os
import pandas as pd
import matplotlib.pyplot as plt
import pyvisa


class HMP4040PyVISA:
    """
    PyVISA controller for Rohde & Schwarz HMP4040 with ARB helpers.

    This file extends the previous hmp4040_pyvisa_v3 with helper methods to
    upload, transfer, start, stop, save and query arbitrary (ARB) sequences
    on the instrument. Use ARB for autonomous, timing-accurate sequences.
    """

    def __init__(self, resource: str, timeout_ms: int = 5000):
        self.rm = pyvisa.ResourceManager('@py')
        self.resource = resource
        self.inst = self.rm.open_resource(resource)
        self.inst.read_termination = '\\n'
        self.inst.write_termination = '\\n'
        self.inst.timeout = timeout_ms
        idn = self.query('*IDN?')
        print(f"Connected to: {idn}")

    # -------------------------
    # Low-level API
    # -------------------------
    def write(self, cmd: str):
        self.inst.write(cmd)

    def query(self, cmd: str) -> str:
        return self.inst.query(cmd).strip()

    # -------------------------
    # Channel / basic controls
    # -------------------------
    def select_channel(self, channel: int):
        if channel not in (1, 2, 3, 4):
            raise ValueError("channel must be 1..4")
        self.write(f"INST OUT{channel}")

    def set_voltage(self, channel: int, voltage: float):
        self.select_channel(channel)
        self.write(f"VOLT {voltage}")

    def set_current_limit(self, channel: int, current: float):
        self.select_channel(channel)
        self.write(f"CURR {current}")

    def output_on(self, channel: int):
        self.select_channel(channel)
        self.write("OUTP ON")

    def output_off(self, channel: int):
        self.select_channel(channel)
        self.write("OUTP OFF")

    # -------------------------
    # ARB helper methods
    # -------------------------
    def arb_upload(self, channel: int, data_str: str, wait: float = 0.2):
        """
        Upload ARB data string to the currently selected channel memory.
        data_str: string in the exact format expected by the HMP4040 ARB:DATA command.
        Example: '1,1,1,2,2,1,3,3,1'  (check manual for correct format)
        """
        self.select_channel(channel)
        self.write(f"ARB:DATA {data_str}")
        # wait for operation to complete if possible
        try:
            self.query("*OPC?")
        except Exception:
            # fallback short wait
            time.sleep(wait)

    def arb_transfer(self, channel: int, wait: float = 0.5):
        """Transfer uploaded ARB points into the channel's ARB memory (ARB:TRAN 1)."""
        self.select_channel(channel)
        self.write("ARB:TRAN 1")
        try:
            self.query("*OPC?")
        except Exception:
            time.sleep(wait)

    def arb_start(self, channel: int):
        """Start the ARB sequence on the selected channel (ARB:STAR 1)."""
        self.select_channel(channel)
        # some firmwares use ARB:START or ARB:STAR; try both conservatively
        try:
            self.write("ARB:STAR 1")
        except Exception:
            try:
                self.write("ARB:START 1")
            except Exception:
                # still attempt generic command
                self.write("ARB:STAR 1")

    def arb_stop(self, channel: int):
        """Stop the ARB sequence on the selected channel (ARB:STOP 1)."""
        self.select_channel(channel)
        try:
            self.write("ARB:STOP 1")
        except Exception:
            # try alternative
            try:
                self.write("ARB:PAUSE 1")
            except Exception:
                pass

    def arb_save(self, channel: int):
        """Save current ARB in instrument memory (ARB:SAVE 1)."""
        self.select_channel(channel)
        self.write("ARB:SAVE 1")
        try:
            self.query("*OPC?")
        except Exception:
            time.sleep(0.2)

    def arb_recall(self, channel: int):
        """Recall a previously saved ARB from instrument memory (ARB:REST or ARB:RECALL)."""
        self.select_channel(channel)
        # try typical commands
        for cmd in ("ARB:REST", "ARB:RECALL", "ARB:LOAD"):
            try:
                self.write(cmd)
                try:
                    self.query("*OPC?")
                except Exception:
                    time.sleep(0.2)
                return
            except Exception:
                continue
        raise RuntimeError("ARB recall/save command unsuccessful on this firmware. Check manual.")

    def arb_clear(self, channel: int):
        """Clear ARB data for the channel (ARB:CLEAR 1)."""
        self.select_channel(channel)
        try:
            self.write("ARB:CLEAR 1")
        except Exception:
            # ignore if device doesn't support
            pass

    def arb_status(self, channel: int) -> str:
        """
        Query an ARB status string if supported. Returns raw reply or None.
        Example queries that may be supported: 'ARB:STAT?', 'ARB:RUN?', 'ARB:ERR?'.
        """
        self.select_channel(channel)
        for qcmd in ("ARB:STAT?", "ARB:RUN?", "ARB:ERR?", "ARB:STATE?"):
            try:
                return self.query(qcmd)
            except Exception:
                continue
        return None

    # -------------------------
    # Measurements
    # -------------------------
    def measure_voltage(self, channel: int) -> float:
        self.select_channel(channel)
        return float(self.query("MEAS:VOLT?"))

    def measure_current(self, channel: int) -> float:
        self.select_channel(channel)
        return float(self.query("MEAS:CURR?"))

    # -------------------------
    # CSV + metadata helper
    # -------------------------
    def _save_with_metadata(self, df: pd.DataFrame, filename: str, metadata: dict):
        meta_lines = [f"# {k}: {v}" for k, v in metadata.items()]
        meta_str = "\\n".join(meta_lines) + "\\n"
        with open(filename, "w") as f:
            f.write(meta_str)
            df.to_csv(f, index=False)

    # -------------------------
    # Logging (single-channel)
    # -------------------------
    def log_data(
        self,
        channel: int,
        duration: float,
        interval: float = 0.5,
        experiment_name: str = "experiment",
        plot: bool = True,
        additional_metadata: dict = None,
        out_dir: str = ".",
    ) -> pd.DataFrame:
        if interval <= 0:
            raise ValueError("interval must be > 0")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(out_dir, f"{experiment_name}_{timestamp}.csv")

        print(f"Starting logging on channel {channel} for {duration}s (interval={interval}s)")
        self.output_on(channel)
        data = []
        t0 = time.time()
        try:
            while time.time() - t0 < duration:
                t_rel = time.time() - t0
                v = self.measure_voltage(channel)
                i = self.measure_current(channel)
                data.append([t_rel, v, i])
                print(f"{t_rel:.2f}s: V={v:.6f} V, I={i:.6f} A")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Logging interrupted by user — saving partial data.")
        finally:
            self.output_off(channel)

        df = pd.DataFrame(data, columns=["time_s", "voltage_V", "current_A"])
        metadata = {
            "timestamp": timestamp,
            "experiment_name": experiment_name,
            "channel": channel,
            "duration_s_requested": duration,
            "interval_s": interval,
        }
        if additional_metadata:
            metadata.update(additional_metadata)

        self._save_with_metadata(df, filename, metadata)
        print(f"Saved log to: {filename}")

        # Plot with twin axes
        if plot and len(df):
            fig, ax_v = plt.subplots(figsize=(9, 4.5))
            ax_i = ax_v.twinx()
            ax_v.plot(df["time_s"], df["voltage_V"], label="Voltage (V)")
            ax_i.plot(df["time_s"], df["current_A"], label="Current (A)", linestyle="--")
            ax_v.set_xlabel("Time (s)")
            ax_v.set_ylabel("Voltage (V)")
            ax_i.set_ylabel("Current (A)")
            ax_v.legend(loc="upper left")
            ax_i.legend(loc="upper right")
            plt.tight_layout()
            plt.show()

        return df

    # -------------------------
    # Single-channel pulsed experiment (mode: 'current' or 'voltage')
    # -------------------------
    def run_pulsed_experiment(
        self,
        channel: int,
        mode: str,
        pulse_level: float,
        pulse_duration: float,
        rest_level: float,
        rest_duration: float,
        target_charge_C: float,
        experiment_name: str = "pulsed",
        dt: float = 0.1,
        autosave_interval_s: float = None,
        plot: bool = True,
        out_dir: str = ".",
        # compliance/current-limit options
        pulse_voltage_compliance: float = None,
        pulse_current_limit: float = None,
        rest_current_limit: float = None,
    ) -> pd.DataFrame:
        mode = mode.lower()
        if mode not in ("current", "voltage"):
            raise ValueError("mode must be 'current' or 'voltage'")
        if dt <= 0:
            raise ValueError("dt must be > 0")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(out_dir, f"{experiment_name}_{timestamp}.csv")
        print(f"Starting pulsed experiment (mode={mode}) on channel {channel} (target {target_charge_C} C)")

        data = []
        total_charge = 0.0
        t0 = time.time()
        last_autosave = time.time()

        try:
            while total_charge < target_charge_C:
                # PULSE
                if mode == "current":
                    if pulse_voltage_compliance is not None:
                        self.set_voltage(channel, pulse_voltage_compliance)
                    self.set_current_limit(channel, pulse_level)
                    self.output_on(channel)
                    phase = "pulse"
                    t_start = time.time()
                    while time.time() - t_start < pulse_duration and total_charge < target_charge_C:
                        t_rel = time.time() - t0
                        v_meas = self.measure_voltage(channel)
                        i_meas = self.measure_current(channel)
                        total_charge += i_meas * dt
                        data.append([t_rel, v_meas, i_meas, total_charge, phase])
                        print(f"{t_rel:.2f}s: [PULSE] I_set={pulse_level:.4f}A V={v_meas:.4f}V I={i_meas:.4f}A Q={total_charge:.4f}C")
                        time.sleep(dt)
                        if autosave_interval_s and (time.time() - last_autosave) >= autosave_interval_s:
                            df_temp = pd.DataFrame(data, columns=["time_s", "voltage_V", "current_A", "charge_C", "phase"])
                            metadata = {"timestamp": timestamp, "experiment": experiment_name, "channel": channel, "partial_save": True}
                            self._save_with_metadata(df_temp, filename, metadata)
                            last_autosave = time.time()
                    self.output_off(channel)
                else:
                    # mode == 'voltage'
                    if pulse_current_limit is not None:
                        self.set_current_limit(channel, pulse_current_limit)
                    self.set_voltage(channel, pulse_level)
                    self.output_on(channel)
                    phase = "pulse"
                    t_start = time.time()
                    while time.time() - t_start < pulse_duration and total_charge < target_charge_C:
                        t_rel = time.time() - t0
                        v_meas = self.measure_voltage(channel)
                        i_meas = self.measure_current(channel)
                        total_charge += i_meas * dt
                        data.append([t_rel, v_meas, i_meas, total_charge, phase])
                        print(f"{t_rel:.2f}s: [PULSE] V_set={pulse_level:.4f}V V={v_meas:.4f}V I={i_meas:.4f}A Q={total_charge:.4f}C")
                        time.sleep(dt)
                        if autosave_interval_s and (time.time() - last_autosave) >= autosave_interval_s:
                            df_temp = pd.DataFrame(data, columns=["time_s", "voltage_V", "current_A", "charge_C", "phase"])
                            metadata = {"timestamp": timestamp, "experiment": experiment_name, "channel": channel, "partial_save": True}
                            self._save_with_metadata(df_temp, filename, metadata)
                            last_autosave = time.time()
                    self.output_off(channel)

                if total_charge >= target_charge_C:
                    break

                # REST
                if mode == "current":
                    self.set_current_limit(channel, rest_level)
                    self.output_on(channel)
                    phase = "rest"
                    t_start = time.time()
                    while time.time() - t_start < rest_duration and total_charge < target_charge_C:
                        t_rel = time.time() - t0
                        v_meas = self.measure_voltage(channel)
                        i_meas = self.measure_current(channel)
                        total_charge += i_meas * dt
                        data.append([t_rel, v_meas, i_meas, total_charge, phase])
                        print(f"{t_rel:.2f}s: [REST] I_set={rest_level:.4f}A V={v_meas:.4f}V I={i_meas:.4f}A Q={total_charge:.4f}C")
                        time.sleep(dt)
                    self.output_off(channel)
                else:
                    if rest_current_limit is not None:
                        self.set_current_limit(channel, rest_current_limit)
                    self.set_voltage(channel, rest_level)
                    self.output_on(channel)
                    phase = "rest"
                    t_start = time.time()
                    while time.time() - t_start < rest_duration and total_charge < target_charge_C:
                        t_rel = time.time() - t0
                        v_meas = self.measure_voltage(channel)
                        i_meas = self.measure_current(channel)
                        total_charge += i_meas * dt
                        data.append([t_rel, v_meas, i_meas, total_charge, phase])
                        print(f"{t_rel:.2f}s: [REST] V_set={rest_level:.4f}V V={v_meas:.4f}V I={i_meas:.4f}A Q={total_charge:.4f}C")
                        time.sleep(dt)
                    self.output_off(channel)

        except KeyboardInterrupt:
            print("Experiment interrupted by user — saving partial data.")
        finally:
            try:
                self.output_off(channel)
            except Exception:
                pass

        df = pd.DataFrame(data, columns=["time_s", "voltage_V", "current_A", "charge_C", "phase"])
        metadata = {
            "timestamp": timestamp,
            "experiment_name": experiment_name,
            "channel": channel,
            "mode": mode,
            "pulse_level": pulse_level,
            "pulse_duration_s": pulse_duration,
            "rest_level": rest_level,
            "rest_duration_s": rest_duration,
            "target_charge_C": target_charge_C,
            "dt_s": dt,
            "pulse_voltage_compliance": pulse_voltage_compliance,
            "pulse_current_limit": pulse_current_limit,
            "rest_current_limit": rest_current_limit,
        }
        self._save_with_metadata(df, filename, metadata)
        print(f"Saved pulsed experiment log to: {filename}")

        # Plot: voltage left, current right
        if plot and len(df):
            fig, ax_v = plt.subplots(figsize=(10, 4.5))
            ax_i = ax_v.twinx()
            ax_v.plot(df["time_s"], df["voltage_V"], label="Voltage (V)", color="tab:blue")
            ax_i.plot(df["time_s"], df["current_A"], label="Current (A)", color="tab:orange", linestyle="--")
            # shade phases
            try:
                cur_phase = None
                start_t = None
                for _, row in df.iterrows():
                    if row["phase"] != cur_phase:
                        if cur_phase is not None:
                            ax_v.axvspan(start_t, row["time_s"], alpha=0.06,
                                         color="tab:green" if cur_phase == "pulse" else "tab:gray")
                        cur_phase = row["phase"]
                        start_t = row["time_s"]
                if cur_phase is not None and start_t is not None:
                    ax_v.axvspan(start_t, df["time_s"].iloc[-1], alpha=0.06,
                                 color="tab:green" if cur_phase == "pulse" else "tab:gray")
            except Exception:
                pass

            ax_v.set_xlabel("Time (s)")
            ax_v.set_ylabel("Voltage (V)")
            ax_i.set_ylabel("Current (A)")
            lines_v, labels_v = ax_v.get_legend_handles_labels()
            lines_i, labels_i = ax_i.get_legend_handles_labels()
            ax_v.legend(lines_v + lines_i, labels_v + labels_i, loc="upper right")
            plt.title(f"{experiment_name}  (Q={df['charge_C'].iloc[-1]:.4f} C)")
            plt.tight_layout()
            plt.show()

        return df

    # -------------------------
    # Multi-channel pulsed experiment (interleaved)
    # -------------------------
    def run_pulsed_experiment_multi(
        self,
        channels: dict,
        dt: float = 0.1,
        autosave_interval_s: float = None,
        experiment_name: str = "multi_pulse",
        plot: bool = True,
        out_dir: str = ".",
    ) -> pd.DataFrame:
        # (This is the fixed replacement method provided earlier; it preserves signature)
        if not isinstance(channels, dict) or not channels:
            raise ValueError("channels must be a non-empty dict keyed by channel number")
        for ch, cfg in channels.items():
            if ch not in (1, 2, 3, 4):
                raise ValueError(f"invalid channel: {ch}")
            if "mode" not in cfg or cfg["mode"] not in ("current", "voltage"):
                raise ValueError(f"channel {ch}: mode must be 'current' or 'voltage'")
            for key in ("pulse_level", "pulse_duration", "rest_level", "rest_duration", "target_charge_C"):
                if key not in cfg:
                    raise ValueError(f"channel {ch}: missing required param '{key}'")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(out_dir, f"{experiment_name}_{timestamp}.csv")

        # per-channel state
        state = {}
        for ch, cfg in channels.items():
            state[ch] = {
                "cfg": cfg,
                "charge": 0.0,
                "phase": "pulse",
                "phase_start": time.time(),
                "last_measured_i": 0.0,
                "est_time_s": float("inf"),
            }
            try:
                self.output_off(ch)
            except Exception:
                pass

        data = []
        t0 = time.time()
        last_autosave = time.time()

        print(f"Starting multi-channel pulsed experiment ({experiment_name}) with channels: {list(channels.keys())}")
        try:
            while True:
                all_done = True

                # configure all channels according to their current phase
                for ch, s in state.items():
                    cfg = s["cfg"]
                    if s["charge"] >= cfg["target_charge_C"]:
                        try:
                            self.output_off(ch)
                        except Exception:
                            pass
                        continue
                    all_done = False
                    phase = s["phase"]

                    if cfg["mode"] == "current":
                        if phase == "pulse":
                            if cfg.get("pulse_voltage_compliance") is not None:
                                self.set_voltage(ch, cfg["pulse_voltage_compliance"])
                            self.set_current_limit(ch, cfg["pulse_level"])
                        else:
                            self.set_current_limit(ch, cfg["rest_level"])
                    else:
                        if phase == "pulse":
                            if cfg.get("pulse_current_limit") is not None:
                                self.set_current_limit(ch, cfg["pulse_current_limit"])
                            self.set_voltage(ch, cfg["pulse_level"])
                        else:
                            if cfg.get("rest_current_limit") is not None:
                                self.set_current_limit(ch, cfg["rest_current_limit"])
                            self.set_voltage(ch, cfg["rest_level"])

                # enable outputs for all active channels
                for ch, s in state.items():
                    cfg = s["cfg"]
                    if s["charge"] >= cfg["target_charge_C"]:
                        continue
                    try:
                        self.output_on(ch)
                    except Exception:
                        pass

                # measure each channel once and update state
                for ch, s in state.items():
                    cfg = s["cfg"]
                    if s["charge"] >= cfg["target_charge_C"]:
                        continue

                    v_meas = self.measure_voltage(ch)
                    i_meas = self.measure_current(ch)
                    s["last_measured_i"] = i_meas
                    s["charge"] += i_meas * dt
                    t_rel = time.time() - t0
                    data.append([ch, t_rel, v_meas, i_meas, s["charge"], s["phase"]])
                    print(f"ch{ch} {s['phase']:5s} t={t_rel:.1f}s V={v_meas:.3f} V I={i_meas:.3f} A Q={s['charge']:.4f} C")

                    now = time.time()
                    elapsed = now - s["phase_start"]
                    if s["phase"] == "pulse":
                        if elapsed >= cfg["pulse_duration"]:
                            s["phase"] = "rest"
                            s["phase_start"] = now
                    else:
                        if elapsed >= cfg["rest_duration"]:
                            s["phase"] = "pulse"
                            s["phase_start"] = now

                    time.sleep(max(0.0, dt))

                # autosave
                if autosave_interval_s and (time.time() - last_autosave) >= autosave_interval_s:
                    df_temp = pd.DataFrame(data, columns=["channel", "time_s", "voltage_V", "current_A", "charge_C", "phase"])
                    metadata = {"timestamp": timestamp, "experiment_name": experiment_name, "partial_save": True}
                    self._save_with_metadata(df_temp, filename, metadata)
                    print(f"Autosaved intermediate data to {filename}")
                    last_autosave = time.time()

                # status estimates
                est_lines = []
                for ch, s in state.items():
                    cfg = s["cfg"]
                    rem = max(0.0, cfg["target_charge_C"] - s["charge"])
                    measured = abs(s["last_measured_i"])
                    if cfg["mode"] == "current":
                        fallback = abs(cfg.get("pulse_level", 0.0))
                    else:
                        fallback = abs(cfg.get("pulse_current_limit") or cfg.get("rest_current_limit") or 0.0)
                    estimate_current = measured if measured > 1e-6 else (fallback if fallback > 1e-9 else None)
                    if estimate_current:
                        t_est = rem / estimate_current
                        est_str = f"{t_est:.1f}s remaining"
                    else:
                        est_str = "estimate: unknown"
                    est_lines.append(f"ch{ch}: Q={s['charge']:.4f}/{cfg['target_charge_C']:.4f} C, {est_str}")
                print(" | ".join(est_lines))

                if all_done:
                    break

        except KeyboardInterrupt:
            print("Experiment interrupted by user — saving partial data.")
        finally:
            for ch in state.keys():
                try:
                    self.output_off(ch)
                except Exception:
                    pass

        df = pd.DataFrame(data, columns=["channel", "time_s", "voltage_V", "current_A", "charge_C", "phase"])
        metadata = {
            "timestamp": timestamp,
            "experiment_name": experiment_name,
            "channels": channels,
            "dt_s": dt,
        }
        self._save_with_metadata(df, filename, metadata)
        print(f"Saved multi-channel pulsed experiment to: {filename}")

        # final summary
        for ch, s in state.items():
            cfg = s["cfg"]
            rem = max(0.0, cfg["target_charge_C"] - s["charge"])
            t_est = s.get("est_time_s", None)
            t_est_str = "unknown" if (t_est is None or t_est == float("inf")) else f"{t_est:.1f} s"
            print(f" ch{ch}: Q={s['charge']:.6f}/{cfg['target_charge_C']:.6f} C  |  time estimate: {t_est_str}")

        if plot and len(df):
            channels_list = sorted(channels.keys())
            n_ch = len(channels_list)
            fig, axes = plt.subplots(n_ch, 1, figsize=(10, 3 * n_ch), sharex=True)
            if n_ch == 1:
                axes = [axes]
            for ax, ch in zip(axes, channels_list):
                subdf = df[df["channel"] == ch]
                ax_v = ax
                ax_i = ax_v.twinx()
                ax_v.plot(subdf["time_s"], subdf["voltage_V"], label="Voltage (V)", color="tab:blue")
                ax_i.plot(subdf["time_s"], subdf["current_A"], label="Current (A)", color="tab:orange", linestyle="--")
                ax_v.set_ylabel("Voltage (V)")
                ax_i.set_ylabel("Current (A)")
                ax.set_title(f"Channel {ch}")
                l1, lab1 = ax_v.get_legend_handles_labels()
                l2, lab2 = ax_i.get_legend_handles_labels()
                ax_v.legend(l1 + l2, lab1 + lab2, loc="upper right")
            axes[-1].set_xlabel("Time (s)")
            plt.tight_layout()
            plt.show()

        return df

    def pulsed_until_charge(self, *args, **kwargs):
        return self.run_pulsed_experiment(*args, **kwargs)

    def close(self):
        try:
            self.inst.close()
        except Exception:
            pass
        try:
            self.rm.close()
        except Exception:
            pass
        print("Connection closed.")
