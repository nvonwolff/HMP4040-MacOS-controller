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
```bash
pip install -r requirements.txt
