# HMP4040 PyVISA Controller + Examples

This repository contains a Python controller for the Rohde & Schwarz HMP4040 power supply using PyVISA (@py backend),
plus example scripts for single- and multi-channel pulsed electrolysis experiments and ARB helpers.

## Repository contents
- `hmp4040_pyvisa_arb.py` — Main controller module (includes ARB helpers, robust single- and multi-channel pulsed experiment routines).
- `example_single_pulse.py` — Minimal single-channel galvanostatic pulsed experiment example.
- `run_multi_short.py` — Quick multi-channel short test (good for verifying behavior).
- `run_multi_long.py` — Long-run (8h-oriented) multi-channel example with autosave and signal handling.
- `test_multi_enable_debug.py` — Short debug runner that prints enable/diagnostics (use during initial verification).
- `README.md` — This file.

## Requirements
- macOS (tested on macOS Monterey)
- Python 3.8+
- `pyvisa`, `pyvisa-py`
- `pandas`, `matplotlib`
- USB connection to HMP4040 (via built-in VISA interface)
- (Optional) `zeroconf` if using HISLIP/TCPIP discovery.

Install dependencies with pip:
```bash
pip install pyvisa pyvisa-py pandas matplotlib
pip install zeroconf  # if needed for TCPIP discovery
pip install -r requirements.txt
```

## Quick start (macOS)
1. Ensure the PSU is connected via USB or LAN.
```bash
ls /dev | grep -i usb
```
you should see something like:
```bash
cu.usbmodemVCP1094011
tty.usbmodemVCP1094011
```

3. Verify device presence:
```python
import pyvisa
rm = pyvisa.ResourceManager('@py')
print(rm.list_resources())
```
or
```python
import pyvisa

rm = pyvisa.ResourceManager('@py')
inst = rm.open_resource('ASRL/dev/cu.usbmodemVCP1094011::INSTR')
inst.read_termination = '\n'
inst.write_termination = '\n'
inst.timeout = 5000

print(inst.query('*IDN?'))  # should print ROHDE&SCHWARZ,HMP4040,...
```

If `list_resources()` returns nothing on macOS, use the ASRL device path (e.g. `ASRL/dev/cu.usbmodemVCP1094011::INSTR`).

## 🔌 Run Electrolysis 

## Quick Start
  - Example scripts are in the [examples/](examples/) folder:
  - `example_single_pulse.py`: Single-channel pulsed electrolysis  
  - `run_multi_short.py`: Quick multi-channel test  
  - `run_multi_long.py`: Long autonomous multi-channel run  
  - `test_multi_enable_debug.py`: Output verification test

1. Run single-channel example:
```bash
python3 example_single_pulse.py
```

2. Run a short multi-channel test (inspect LEDs and CSV output):
```bash
python3 run_multi_short.py
```

3. For long runs, tweak `run_multi_long.py` params (dt, autosave_interval_s) and test with inert loads first.

## 🛟 Safety notes
- ALWAYS test with an inert resistive load before connecting electrochemical cells.
- Set conservative compliance values (voltage or current limits) before enabling outputs.
- Use small `dt` only for short tests; for long runs prefer `dt >= 0.5 s` to avoid USB overload.
- Enable `verbose_enable_debug=True` for initial verification (it prints OUTP?/SYST:ERR? diagnostics).

## File format
Logged CSVs include a small metadata header (lines starting with `#`) followed by CSV columns:
`channel, time_s, voltage_V, current_A, charge_C, phase`

## Contributing
Contributions welcome — open a PR or issue with improvements, bug reports, or device-specific command tweaks.

## License
Place your preferred license here (e.g., MIT).
