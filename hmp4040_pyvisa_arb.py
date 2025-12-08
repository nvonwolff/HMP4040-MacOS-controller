import time, os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import pyvisa

class HMP4040PyVISA:
    """HMP4040 PyVISA controller with pulsed experiments and ARB support."""

    def __init__(self, resource: str, timeout_ms: int = 5000):
        self.rm = pyvisa.ResourceManager('@py')
        self.inst = self.rm.open_resource(resource)
        self.inst.read_termination = '\n'
        self.inst.write_termination = '\n'
        self.inst.timeout = timeout_ms
        print("Connected to:", self.query("*IDN?"))

    def write(self, cmd: str): self.inst.write(cmd)
    def query(self, cmd: str) -> str: return self.inst.query(cmd).strip()
    def select_channel(self, ch: int): self.write(f"INST OUT{ch}")
    def set_voltage(self, ch: int, v: float): self.select_channel(ch); self.write(f"VOLT {v}")
    def set_current_limit(self, ch: int, i: float): self.select_channel(ch); self.write(f"CURR {i}")
    def output_on(self, ch: int): self.select_channel(ch); self.write("OUTP ON")
    def output_off(self, ch: int): self.select_channel(ch); self.write("OUTP OFF")
    def measure_voltage(self, ch: int) -> float: self.select_channel(ch); return float(self.query("MEAS:VOLT?"))
    def measure_current(self, ch: int) -> float: self.select_channel(ch); return float(self.query("MEAS:CURR?"))

    # ---------------- ARB helpers ----------------
    def arb_clear(self, channel: int): self.select_channel(channel); self.write("ARB:CLEAR 1")
    def arb_start(self, channel: int): self.select_channel(channel); self.write("ARB:STAR 1")
    def arb_stop(self, channel: int): self.select_channel(channel); self.write("ARB:STOP 1")
    def arb_send_sequence(self, channel: int, sequence: list, repeat: int = 1):
        self.select_channel(channel)
        seq_str = ",".join(str(x) for x in sequence)
        self.write(f"ARB:DATA {seq_str}")
        self.write(f"ARB:REP {repeat}")
        self.write(f"ARB:TRAN 1")

    def _verify_and_enable_channel(self, ch: int, retries: int = 4, settle_short: float = 0.08, settle_long: float = 0.25, verbose: bool = False):
        """
        Try to enable channel `ch` (OUTP ON), verify with OUTP? and MEAS:VOLT?/MEAS:CURR?,
        retry a few times, and if OUTP is ON but measured V/I are zero, perform an OFF->ON toggle
        and reapply setpoints, with a longer settle. Returns (ok: bool, info: dict).
        info contains last replies and measurements for debugging.
        """
        info = {"last_resp": None, "syst_err": None, "meas_v": None, "meas_i": None, "attempts": 0}
        for attempt in range(1, retries + 1):
            info["attempts"] = attempt
            try:
                # ensure we are on the right channel
                self.select_channel(ch)
    
                # Request ON
                self.write("OUTP ON")
                time.sleep(settle_short)
    
                # Query OUTP state (try several names)
                resp = None
                for qcmd in ("OUTP?", "OUTP:STAT?", "OUTP:STATE?"):
                    try:
                        r = self.query(qcmd)
                        if r is None:
                            continue
                        resp = str(r).strip()
                        info["last_resp"] = f"{qcmd} -> {resp}"
                        # canonicalize
                        if resp.upper() in ("1", "ON", "TRUE"):
                            break
                    except Exception:
                        continue
    
                # Read measured V/I
                try:
                    v = float(self.query("MEAS:VOLT?"))
                except Exception:
                    v = None
                try:
                    i = float(self.query("MEAS:CURR?"))
                except Exception:
                    i = None
                info["meas_v"] = v
                info["meas_i"] = i
    
                # If OUTP reported ON and measurements look non-zero (or as expected), success
                if resp and resp.upper() in ("1", "ON", "TRUE"):
                    # determine if channel is actually sourcing: if either V or I is reasonably non-zero
                    sourcing = False
                    if v is not None and abs(v) > 1e-6: sourcing = True
                    if i is not None and abs(i) > 1e-6: sourcing = True
    
                    if sourcing:
                        if verbose:
                            print(f"ch{ch} enabled and sourcing (resp={resp}, V={v}, I={i})")
                        # clear any SYST:ERR? into info
                        try:
                            info["syst_err"] = self.query("SYST:ERR?")
                        except Exception:
                            info["syst_err"] = None
                        return True, info
    
                    # If OUTP says ON but no sourcing -> try OFF->ON + reapply setpoints (toggle recovery)
                    if verbose:
                        print(f"ch{ch} reported ON but V/I are near zero (V={v}, I={i}) -> attempting toggle/reapply (attempt {attempt}).")
    
                    # Save current setpoints if possible (best-effort)
                    try:
                        prev_v = self.query("VOLT?")
                    except Exception:
                        prev_v = None
                    try:
                        prev_i = self.query("CURR?")
                    except Exception:
                        prev_i = None
    
                    # toggle: OFF, short wait, reapply setpoints, ON, longer settle
                    try:
                        self.write("OUTP OFF")
                        time.sleep(0.05)
                        # reapply setpoints that were likely set earlier (best-effort restore)
                        if prev_v is not None:
                            try:
                                self.write(f"VOLT {prev_v}")
                            except Exception:
                                pass
                        if prev_i is not None:
                            try:
                                self.write(f"CURR {prev_i}")
                            except Exception:
                                pass
                        # re-ON and wait longer
                        self.write("OUTP ON")
                        time.sleep(settle_long)
                    except Exception as exc_toggle:
                        if verbose:
                            print(f"ch{ch} toggle attempt raised: {exc_toggle}")
                        time.sleep(0.1)
    
                    # read measurements again and loop (will retry)
                    try:
                        v2 = float(self.query("MEAS:VOLT?"))
                    except Exception:
                        v2 = None
                    try:
                        i2 = float(self.query("MEAS:CURR?"))
                    except Exception:
                        i2 = None
                    info["meas_v_after_toggle"] = v2
                    info["meas_i_after_toggle"] = i2
    
                    # check for errors
                    try:
                        info["syst_err"] = self.query("SYST:ERR?")
                    except Exception:
                        info["syst_err"] = None
    
                    # if now sourcing, return success
                    if (v2 is not None and abs(v2) > 1e-6) or (i2 is not None and abs(i2) > 1e-6):
                        if verbose:
                            print(f"ch{ch} now sourcing after toggle: V={v2}, I={i2}")
                        return True, info
    
                    # otherwise keep retrying
                else:
                    # If OUTP query didn't return ON, check SYST:ERR?
                    try:
                        serr = self.query("SYST:ERR?")
                        info["syst_err"] = serr
                        if verbose:
                            print(f"ch{ch} OUTP query returned '{resp}', SYST:ERR? -> {serr}")
                    except Exception:
                        pass
    
                # small backoff before next attempt
                time.sleep(0.2)
            except Exception as exc:
                info["last_exc"] = str(exc)
                if verbose:
                    print(f"ch{ch} verification attempt exception: {exc}")
                time.sleep(0.2)
    
        # final: not ok after all retries
        if verbose:
            print(f"Warning: channel {ch} did not start sourcing after {retries} attempts. Info: {info}")
        return False, info




    # ---------------- CSV helpers ----------------
    def _save_with_metadata(self, df, filename, metadata):
        meta_lines = [f"# {k}: {v}" for k, v in metadata.items()]
        with open(filename, "w") as f:
            f.write("\n".join(meta_lines) + "\n")
            df.to_csv(f, index=False)

    # ---------------- Pulsed experiment ----------------
    def run_pulsed_experiment_multi(
        self,
        channels: dict,
        dt: float = 0.5,
        autosave_interval_s: float = 600,
        experiment_name: str = "multi_pulse",
        plot: bool = True,
        out_dir: str = ".",
        verbose_enable_debug: bool = False,
        stop_flag=None
    ):
        """
        Multi-channel pulsed experiment (simultaneous, interleaved polling).
        stop_flag: callable returning True to request safe stop (e.g., from SIGINT)
        """
        import os, pandas as pd, matplotlib.pyplot as plt, time
        from datetime import datetime
    
        # --- validate input ---
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
    
        # --- initialize per-channel state ---
        state = {}
        for ch, cfg in channels.items():
            state[ch] = {
                "cfg": cfg,
                "charge": 0.0,
                "phase": "pulse",
                "phase_start": time.time(),
                "enabled": False,
                "last_enable_resp": None,
            }
            try: self.output_off(ch)
            except Exception: pass
    
        data = []
        t0 = time.time()
        last_autosave = time.time()
    
        print(f"Starting multi-channel pulsed experiment ({experiment_name}) channels={list(channels.keys())}")
    
        try:
            while True:
    
                if stop_flag is not None and stop_flag():
                    print("\n🔚 Stop requested — exiting experiment loop safely.")
                    break
    
                all_done = True
    
                # ==============================
                # 🔧 Apply Pulse or Rest Setpoints
                # ==============================
                for ch, s in state.items():
                    cfg = s["cfg"]
    
                    if s["charge"] >= cfg["target_charge_C"]:
                        try: self.output_off(ch)
                        except Exception: pass
                        s["enabled"] = False
                        continue
    
                    all_done = False
                    mode = cfg["mode"].lower()
    
                    # --------- PULSE PHASE ----------
                    if s["phase"] == "pulse":
                        if mode == "current":
                            if cfg.get("pulse_voltage_compliance") is not None:
                                self.set_voltage(ch, cfg["pulse_voltage_compliance"])
                            self.set_current_limit(ch, cfg["pulse_level"])
                        else:
                            if cfg.get("pulse_current_limit") is not None:
                                self.set_current_limit(ch, cfg["pulse_current_limit"])
                            self.set_voltage(ch, cfg["pulse_level"])
    
                    # --------- REST PHASE ----------
                    else:
                        if mode == "current":
                            if cfg["rest_level"] < 0.001:  # < 1 mA → FLOAT MODE
                                self.set_voltage(ch, 0.0)
    
                                clamp = cfg.get(
                                    "rest_current_limit",
                                    cfg.get("pulse_voltage_compliance", 0.05)
                                )
                                self.set_current_limit(ch, clamp)
    
                                if verbose_enable_debug:
                                    print(f"[CH{ch}] REST → FLOAT MODE (0V, CC clamp {clamp} A)")
                            else:
                                self.set_current_limit(ch, cfg["rest_level"])
                        else:
                            if cfg.get("rest_current_limit") is not None:
                                self.set_current_limit(ch, cfg["rest_current_limit"])
                            self.set_voltage(ch, cfg["rest_level"])
    
                # Enable channels
                for ch, s in state.items():
                    if s["charge"] >= s["cfg"]["target_charge_C"]:
                        continue
                    ok, resp = self._verify_and_enable_channel(
                        ch, retries=4, settle_short=0.08, verbose=verbose_enable_debug
                    )
                    s["enabled"] = ok
                    s["last_enable_resp"] = resp
    
                time.sleep(dt)
    
                # --- measurement loop ---
                for ch, s in state.items():
                    if s["charge"] >= s["cfg"]["target_charge_C"]:
                        continue
    
                    t_rel = time.time() - t0
    
                    try:
                        v_meas = self.measure_voltage(ch)
                        i_meas = self.measure_current(ch)
                    except:
                        v_meas = float("nan")
                        i_meas = float("nan")
    
                    if not (i_meas != i_meas):
                        s["charge"] += float(i_meas) * dt
    
                    data.append([ch, t_rel, v_meas, i_meas, s["charge"], s["phase"]])
                    print(f"CH{ch} {s['phase']:5s} t={t_rel:.1f}s  V={v_meas:.3f}  I={i_meas:.4f}  Q={s['charge']:.4f}")
    
                    elapsed = time.time() - s["phase_start"]
                    if s["phase"] == "pulse" and elapsed >= cfg["pulse_duration"]:
                        s["phase"] = "rest"; s["phase_start"] = time.time()
                    elif s["phase"] == "rest" and elapsed >= cfg["rest_duration"]:
                        s["phase"] = "pulse"; s["phase_start"] = time.time()
    
                if autosave_interval_s and (time.time() - last_autosave) >= autosave_interval_s:
                    df_temp = pd.DataFrame(data, columns=["channel", "time_s", "voltage_V", "current_A", "charge_C", "phase"])
                    self._save_with_metadata(df_temp, filename, {"timestamp": timestamp, "partial_save": True})
                    print(f"Autosaved intermediate data → {filename}")
                    last_autosave = time.time()
    
                if all_done:
                    break
    
        finally:
            print("\n🧹 Final cleanup...")
            try: self.disable_all_outputs()
            except: pass
    
            df = pd.DataFrame(data, columns=["channel", "time_s", "voltage_V", "current_A", "charge_C", "phase"])
            self._save_with_metadata(df, filename, {"timestamp": timestamp, "experiment_name": experiment_name})
            print(f"💾 Saved final data → {filename}")
    
            if plot and len(df):
                import matplotlib.pyplot as plt
                for ch in sorted(channels.keys()):
                    sub = df[df.channel == ch]
                    plt.figure(figsize=(10,4))
                    plt.title(f"Channel {ch}")
                    plt.plot(sub.time_s, sub.voltage_V, label="Voltage")
                    plt.plot(sub.time_s, sub.current_A, "--", label="Current")
                    plt.legend(); plt.xlabel("Time (s)")
                    plt.show()
    
        return df

        
    # ---------------- SHUTDOWN POWERSUPPLY ----------------    
    def disable_all_outputs(self):
        """
        Safely disables all outputs on the HMP4040.
    
        Uses a generic approach assuming max 4 channels (HMP4040 spec).
        Silently ignores errors if a channel is unavailable or already off.
        """
        print("🔌 Disabling all PSU outputs...")
    
        try:
            for ch in range(1, 5):  # HMP4040 supports up to 4 channels
                try:
                    self.select_channel(ch)
                    self.write("OUTP OFF")
                    time.sleep(0.1)  # Prevent command flooding
                except Exception:
                    # Ignore channels that may not exist or errors caused by state
                    pass
    
            print("✅ All outputs switched OFF.")
        except Exception as e:
            print(f"⚠️ Error while disabling outputs: {e}")



    # ---------------- Close ----------------
    def close(self):
        try: self.inst.close()
        except Exception: pass
        try: self.rm.close()
        except Exception: pass
        print("Connection closed.")
