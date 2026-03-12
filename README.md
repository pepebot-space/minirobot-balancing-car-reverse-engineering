# MiniRobot Balancing Car Reverse Engineering

Reverse engineering toolkit for controlling MiniRobot balancing car over BLE.

## Target App

- Android App ID: `com.loby.balance.car.google`

## Files

- `minirobot_ble_control.py` - Python BLE controller (raw/write/light/drive/remote/session/autotest/move)
- `MINIROBOT_BLE_PI.md` - Full Raspberry Pi setup and usage guide

## Quick Start (Raspberry Pi)

```bash
python3 -m venv ~/minirobot-venv
~/minirobot-venv/bin/python -m pip install --upgrade pip bleak
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --duration 1.5
```

## Simple Movement Commands

```bash
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --duration 1.5
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move backward --duration 1.5
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move left --duration 1.0
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move right --duration 1.0
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move stop --duration 0.4
```

## Notes

- Existing advanced commands remain available in `minirobot_ble_control.py`.
- Current tested unit control works with XOR key `55` (already defaulted in `move` mode).
