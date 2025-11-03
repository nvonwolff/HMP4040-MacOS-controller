#!/usr/bin/env python3
# test_multi_enable_debug.py - small quick debug to verify enable logic
from hmp4040_pyvisa_arb import HMP4040PyVISA
psu = HMP4040PyVISA("ASRL/dev/cu.usbmodemVCP1094011::INSTR", timeout_ms=15000)
channels_cfg = {
    1: {"mode":"current","pulse_level":0.02,"pulse_duration":5,"rest_level":0.0,"rest_duration":3,"target_charge_C":0.001},
    2: {"mode":"current","pulse_level":0.03,"pulse_duration":4,"rest_level":0.0,"rest_duration":3,"target_charge_C":0.001}
}
try:
    df = psu.run_pulsed_experiment_multi(channels=channels_cfg, dt=0.5, autosave_interval_s=None, verbose_enable_debug=True, experiment_name="test_multi_debug")
    print("Test run finished, rows:", len(df))
finally:
    psu.close()
