#!/usr/bin/env python3
"""example_single_pulse.py

Single-channel galvanostatic pulse example using HMP4040_pyvisa_v3_arb.
"""
from hmp4040_pyvisa_v3_arb import HMP4040PyVISA
import time

RESOURCE = "ASRL/dev/cu.usbmodemVCP1094011::INSTR"  # <- change to your resource
psu = HMP4040PyVISA(RESOURCE, timeout_ms=15000)

single_channel_config = {
    "channel": 1,
    "mode": "current",       # "current" or "voltage"
    "pulse_level": 0.05,     # A in current mode, V in voltage mode
    "pulse_duration": 10,    # seconds
    "rest_level": 0.01,      # A in current mode, V in voltage mode
    "rest_duration": 5,      # seconds
    "target_charge_C": 0.5,  # stop after this amount of charge passed
    "pulse_current_limit": 0.1, # optional compliance
    "rest_current_limit": 0.02  # optional compliance
}

try:
    print("Starting single-channel pulsed experiment...")
    df_single = psu.run_pulsed_experiment(**single_channel_config)
    print("Single-channel experiment complete. Rows recorded:", len(df_single))
    print(df_single.tail())
finally:
    psu.close()
