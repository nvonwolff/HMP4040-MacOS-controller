# HMP4040-MacOS-controller

A lightweight, Python-based controller for the **Rohde & Schwarz HMP4040** programmable power supply.  
This project enables full instrument control, live data logging, and pulsed electrolysis experiments directly from **macOS**, using **PyVISA** and **VISA-py** backends — no Windows or LabVIEW drivers required.

---

## 🔧 Features

- Connect and control the **R&S HMP4040** via **USB** (macOS compatible)
- Log **current**, **voltage**, and **charge** with timestamps
- Run **pulsed electrolysis** experiments (constant-current steps)
- Support for **multiple simultaneous channels**
- CSV logging with **metadata headers**
- Real-time **dual-axis plotting** (voltage & current)
- Automatic **experiment time estimation** per channel
- Safe output handling — auto-off after completion or interruption

---

## 🧠 Requirements

- macOS (tested on Ventura / Sonoma)
- Python 3.10+
- USB connection to HMP4040 (via built-in VISA interface)
- No vendor drivers required

Install dependencies:

	bash
	pip install -r requirements.txt

## ⚙️ Setup Instructions
### 1. Connect the HMP4040 via USB

Plug in your instrument and check that it’s visible:
	
	ls /dev | grep -i usb
You should see something like:

	cu.usbmodemVCP1094011
	tty.usbmodemVCP1094011
### 2. Test communication
Launch a Python shell or Jupyter Notebook and run:

	import pyvisa

	rm = pyvisa.ResourceManager('@py')
	print(rm.list_resources())
Expected output (example):

	('ASRL/dev/cu.usbmodemVCP1094011::INSTR',)
### 3. Connect to the instrument

	from hmp4040_controller import HMP4040PyVISA
	inst = HMP4040PyVISA('ASRL/dev/cu.usbmodemVCP1094011::INSTR')
Expected:

	Connected to: ROHDE&SCHWARZ,HMP4040,109401,HW50020003/SW2.70
	
## 🧪 Example: Single-channel logging

	df = inst.log_data(
    channel=1,
    duration=60,          # seconds
    interval=0.5,         # seconds
    experiment_name="test_run"
	)
Output:
- Saves test_run_YYYYMMDD_HHMMSS.csv
- Includes metadata and time series of voltage/current

## ⚡ Example: Pulsed electrolysis
### Constant-current pulses with total charge limit

	df = inst.run_pulsed_experiment(
    channel=1,
    step_current=0.5,       # Amperes
    step_duration=2.0,      # seconds per pulse
    rest_current=0.05,      # Amperes during rest
    rest_duration=1.0,      # seconds
    target_charge_C=50.0,   # Coulombs
    experiment_name="pulse_test"
	)
The program will:
- Alternate between step_current and rest_current
- Log voltage, current, and integrated charge
- Stop automatically once target_charge_C is reached
- Generate a dual-axis plot and a CSV log

## 🔀 Example: Multi-channel experiment

	channels = [
    {"channel": 1, "step_current": 0.5, "rest_current": 0.05, "target_charge_C": 20},
    {"channel": 2, "step_current": 1.0, "rest_current": 0.10, "target_charge_C": 40}
	]

	inst.run_multichannel_pulse(channels)
Each channel runs independently with real-time time estimates printed before the experiment begins.

## 🙌 Acknowledgments

Developed with ❤️ for laboratory automation on macOS.
Inspired by the Rohde & Schwarz SCPI and PyVISA ecosystem.
