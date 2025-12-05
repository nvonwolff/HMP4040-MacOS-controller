#!/usr/bin/env python3
"""
Long multi-channel pulse electrolysis runner for R&S HMP4040
Safe shutdown, interrupt handling, autosave, and plotting.
"""

import sys
import time
import signal
from hmp4040_pyvisa_arb import HMP4040PyVISA

# -----------------------------
# Connection resource (macOS)
# -----------------------------
RESOURCE = "ASRL/dev/cu.usbmodemVCP1094011::INSTR"

# -----------------------------
# Channel experiment configuration (Example for 2 channels)
# -----------------------------
channels_cfg = {
    2: {
        "mode": "current",
        "pulse_level": 0.003,       # 3 mA pulse
        "pulse_duration": 60.0,     # seconds
        "rest_level": 0.0,
        "rest_duration": 4.0,       # seconds
        "target_charge_C": 10.0,    # Coulombs
        "pulse_voltage_compliance": 32.0
    },
    2: {
        "mode": "voltage",
        "pulse_level": 2.0,          # 2 V pulse
        "pulse_duration": 30.0,
        "rest_level": 0.5,
        "rest_duration": 10.0,
        "target_charge_C": 5.0,
        "pulse_current_limit": 0.005
   }
}

# -----------------------------
# Initialize PSU
# -----------------------------
psu = HMP4040PyVISA(RESOURCE, timeout_ms=20000)

# -----------------------------
# Interrupt handling
# -----------------------------
STOP_REQUESTED = False
def sigint_handler(sig, frame):
    global STOP_REQUESTED
    print("\n⚠️  SIGINT received — experiment will stop safely...")
    STOP_REQUESTED = True

signal.signal(signal.SIGINT, sigint_handler)

# -----------------------------
# Run experiment
# -----------------------------
print("🚀 Starting long multi-channel pulsed experiment")
print("Press CTRL+C at any time to safely stop.\n")

try:
    df = psu.run_pulsed_experiment_multi(
        channels=channels_cfg,
        dt=0.5,
        autosave_interval_s=600,        # autosave every 10 min
        experiment_name="multi_long_run",
        plot=True,                      # Plot data at the end
        verbose_enable_debug=False,
        stop_flag=lambda: STOP_REQUESTED
    )
    print(f"\n🎉 Multi-channel long run finished. Logged rows: {len(df)}")

except Exception as e:
    print(f"\n❌ ERROR during experiment: {e}")
    print("Attempting safe shutdown...")

finally:
    print("\n🧹 Final cleanup: disabling outputs and closing session...")
    try:
        psu.disable_all_outputs()
    except Exception:
        pass

    # Save latest data if available
    try:
        if 'df' in locals() and df is not None:
            final_filename = f"{time.strftime('%Y%m%d_%H%M%S')}_interrupted_run.csv"
            df.to_csv(final_filename, index=False)
            print(f"💾 Data saved: {final_filename}")
    except Exception as e:
        print(f"❌ Failed to save data: {e}")

    psu.close()
    print("🚪 PSU connection closed — script ended safely.")
