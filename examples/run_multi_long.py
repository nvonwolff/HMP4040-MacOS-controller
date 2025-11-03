#!/usr/bin/env python3
"""run_multi_long.py

Long (8h-oriented) multi-channel pulsed experiment example.
Use conservative settings and test with inert load before running cells.
"""
from hmp4040_pyvisa_v3_arb import HMP4040PyVISA
import time, signal, sys

RESOURCE = "ASRL/dev/cu.usbmodemVCP1094011::INSTR"
psu = HMP4040PyVISA(RESOURCE, timeout_ms=20000)

channels_cfg = {
    1: {
        "mode": "current",
        "pulse_level": 0.05,
        "pulse_duration": 600.0,
        "rest_level": 0.01,
        "rest_duration": 300.0,
        "target_charge_C": 360.0,
        "pulse_voltage_compliance": 8.0
    },
    2: {
        "mode": "voltage",
        "pulse_level": 2.0,
        "pulse_duration": 300.0,
        "rest_level": 0.5,
        "rest_duration": 300.0,
        "target_charge_C": 300.0,
        "pulse_current_limit": 0.05
    }
}

def sigint_handler(sig, frame):
    print("\nSIGINT received — switching outputs off and exiting.")
    try:
        for ch in channels_cfg.keys():
            psu.select_channel(ch)
            psu.write("OUTP OFF")
    except Exception:
        pass
    psu.close()
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)

try:
    df = psu.run_pulsed_experiment_multi(
        channels=channels_cfg,
        dt=1.0,
        autosave_interval_s=600,
        experiment_name="multi_long_run",
        plot=False,
        verbose_enable_debug=False
    )
    print("Multi-channel long run finished. Rows:", len(df))
finally:
    psu.close()
