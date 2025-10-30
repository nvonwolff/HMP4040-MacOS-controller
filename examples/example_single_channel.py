from hmp4040_pyvisa_v3 import HMP4040PyVISA

RESOURCE = "ASRL/dev/cu.usbmodemVCP1094011::INSTR"

def main():
    psu = HMP4040PyVISA(RESOURCE)
    try:
        df = psu.run_pulsed_experiment(
            channel=1, mode="current", pulse_level=0.2, pulse_duration=5.0,
            rest_level=0.0, rest_duration=2.0, target_charge_C=0.5,
            dt=0.1, autosave_interval_s=30, experiment_name="example_single"
        )
        print(df.head())
    finally:
        psu.close()

if __name__ == "__main__":
    main()
