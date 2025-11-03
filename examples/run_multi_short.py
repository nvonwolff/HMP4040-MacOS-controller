#!/usr/bin/env python3
"""run_multi_short.py

Quick multi-channel short test (uses run_pulsed_experiment_multi).
"""
from hmp4040_pyvisa_v3_arb import HMP4040PyVISA
import time

RESOURCE = "ASRL/dev/cu.usbmodemVCP1094011::INSTR"
psu = HMP4040PyVISA(RESOURCE, timeout_ms=15000)

channels_cfg = {
    1: {"mode":"current","pulse_level":0.02,"pulse_duration":10,"rest_level":0.0,"rest_duration":5,"target_charge_C":0.01,"pulse_voltage_compliance":5.0},
    2: {"mode":"current","pulse_level":0.03,"pulse_duration":8,"rest_level":0.0,"rest_duration":4,"target_charge_C":0.01,"pulse_voltage_compliance":5.0}
}

try:
    df = psu.run_pulsed_experiment_multi(
        channels=channels_cfg,
        dt=0.5,
        autosave_interval_s=None,
        experiment_name="multi_short_test",
        verbose_enable_debug=True
    )
    print("Multi short test finished. Rows:", len(df))
finally:
    psu.close()
