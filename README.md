# MiniRobot Balancing Car Reverse Engineering

Reverse engineering toolkit for controlling MiniRobot balancing car over BLE.

## Target App

- Android App ID: `com.loby.balance.car.google`

## Files

- `minirobot_ble_control.py` - Python BLE controller (raw/write/light/drive/remote/session/autotest/move)
- `minirobot_web_api.py` - FastAPI Web API server with frontend
- `static/index.html` - Web frontend with Tailwind CSS
- `API_DOCUMENTATION.md` - Full API documentation
- `MINIROBOT_BLE_PI.md` - Full Raspberry Pi setup and usage guide

## Installation

### Using Poetry (Recommended)

```bash
# Install CLI only
poetry install

# Install with web API extras
poetry install --extras "web"

# Install with dev dependencies
poetry install --with dev

# Install everything
poetry install --with dev --extras "web"
```

### Using pip

```bash
# CLI only
pip install bleak

# With web API support
pip install -r requirements-web-api.txt
```

## Quick Start (Web API)

```bash
# Using Poetry
poetry install --extras "web"
poetry run python minirobot_web_api.py

# Or using pip
pip install -r requirements-web-api.txt
python minirobot_web_api.py
```

Open `http://localhost:8000/` in browser for the web interface.

API endpoints are available at `/api/*` (see API_DOCUMENTATION.md).

## Quick Start (CLI)

```bash
# Using Poetry
poetry run minirobot-ble --address CB:F4:C1:BF:F4:79 move forward --duration 1.5

# Or directly
poetry run python minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --duration 1.5

# Using pip/venv
python3 -m venv ~/minirobot-venv
~/minirobot-venv/bin/python -m pip install --upgrade pip bleak
~/minirobot-venv/bin/python ./minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --duration 1.5
```

## Simple Movement Commands

```bash
poetry run minirobot-ble --address CB:F4:C1:BF:F4:79 move forward --duration 1.5
poetry run minirobot-ble --address CB:F4:C1:BF:F4:79 move backward --duration 1.5
poetry run minirobot-ble --address CB:F4:C1:BF:F4:79 move left --duration 1.0
poetry run minirobot-ble --address CB:F4:C1:BF:F4:79 move right --duration 1.0
poetry run minirobot-ble --address CB:F4:C1:BF:F4:79 move stop --duration 0.4
```

## Web API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scan` | Scan BLE devices |
| POST | `/api/connect` | Connect to robot |
| POST | `/api/disconnect` | Disconnect from robot |
| POST | `/api/move` | Movement control |
| POST | `/api/joystick` | Joystick control |
| POST | `/api/light` | Light control |
| POST | `/api/write` | Register write |
| POST | `/api/raw` | Raw hex command |
| GET | `/api/status` | Connection status |
| GET | `/api/registers` | Register list |

See `API_DOCUMENTATION.md` for full API documentation.

## Notes

- Existing advanced commands remain available in `minirobot_ble_control.py`.
- Current tested unit control works with XOR key `55` (already defaulted in `move` mode).