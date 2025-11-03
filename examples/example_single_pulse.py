"""
example_single_pulse.py
-----------------------
Minimal example for running a single-channel pulsed electrolysis experiment
on the Rohde & Schwarz HMP4040 using the HMP4040_pyvisa_v3_arb class.

This script demonstrates how to:
 - connect to the instrument via USB on macOS
 - run a short pulsed current experiment on one channel
 - log data to a CSV file with metadata
"""

from hmp4040_pyvisa_arb import HMP4040PyVISA
import time

# --- USER SETTINGS ---
resource = "ASRL/dev/cu.usbmodemVCP1094011::INSTR"  # adjust if needed
channel = 1
mode = "current"  # or "voltage"

# Define a simple pulse sequence
# Each step = {'current_A': value, 'duration_s': seconds}
pulse_sequence = [
    {"current_A": 0.2, "duration_s": 5},  # 200 mA for 5 s
    {"current_A": 0.0, "duration_s": 5},  # rest for 5 s
    {"current_A": 0.3, "duration_s": 5},  # 300 mA for 5 s
    {"current_A": 0.0, "duration_s": 5},  # rest for 5 s
]

# --- CONNECT TO INSTRUMENT ---
print("Connecting to HMP4040...")
psu = HMP4040PyVISA(resource)

# --- RUN EXPERIMENT ---
print("Starting single-channel pulsed experiment...")
psu.run_pulsed_experiment_single(
    channel=channel,
    mode=mode,
    pulse_sequence=pulse_sequence,
    filename_prefix="single_pulse_test",
    verbose=True,
)

print("Experiment complete. Data saved to CSV.")

# Optionally disconnect (closes VISA session)
psu.close()
