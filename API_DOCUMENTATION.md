# MiniRobot BLE Web API Documentation

Base URL: `http://localhost:8000`

## Overview

REST API untuk mengontrol MiniRobot Balancing Car via Bluetooth Low Energy (BLE).

Frontend tersedia di root URL (`http://localhost:8000/`).

## Authentication

Tidak ada authentication. API ini dirancang untuk penggunaan lokal atau jaringan terpercaya.

## Endpoints

---

### GET /

Frontend web interface untuk kontrol robot.

---

### 1. GET /api/status

Mendapatkan status koneksi robot.

**Response:**
```json
{
  "address": "CB:F4:C1:BF:F4:79",
  "name": "Mini",
  "connected": "true",
  "last_command": "move:forward",
  "last_response": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| address | string\|null | MAC address robot |
| name | string\|null | Nama perangkat |
| connected | string | "true" atau "false" |
| last_command | string\|null | Command terakhir |
| last_response | string\|null | Response/error terakhir |

---

### 2. GET /api/scan

Scan perangkat BLE yang tersedia.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| timeout | float | 8.0 | Timeout scan dalam detik |

**Response:**
```json
{
  "devices": [
    {
      "name": "Mini",
      "address": "CB:F4:C1:BF:F4:79"
    }
  ]
}
```

---

### 3. POST /api/connect

Koneksi ke robot.

**Request Body:**
```json
{
  "address": "CB:F4:C1:BF:F4:79",
  "name": null,
  "scan_timeout": 8.0,
  "xor_key": "55"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| address | string | no* | MAC address target |
| name | string | no* | Nama perangkat (partial match) |
| scan_timeout | float | no | Timeout scan (default: 8.0) |
| xor_key | string | no | XOR key: "none", "55", "d8" (default: "55") |

*cukup salah satu: `address` atau `name`

**Response:**
```json
{
  "status": "connected",
  "address": "CB:F4:C1:BF:F4:79",
  "name": "Mini"
}
```

**Error Codes:**
- `404` - Device not found
- `503` - Robot not connected

---

### 4. POST /api/disconnect

Putuskan koneksi dari robot.

**Response:**
```json
{
  "status": "disconnected"
}
```

---

### 5. POST /api/move

Gerakan robot (simple movement).

**Request Body:**
```json
{
  "action": "forward",
  "power": 9000,
  "duration": 1.5,
  "drive_interval": 0.04,
  "poll_interval": 0.20,
  "xor_key": "55"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| action | string | yes | "forward", "backward", "left", "right", "stop" |
| power | int | no | Kekuatan 0-32767 (default: 9000) |
| duration | float | no | Durasi dalam detik (default: 1.5) |
| drive_interval | float | no | Interval kirim frame (default: 0.04) |
| poll_interval | float | no | Interval polling (default: 0.20) |
| xor_key | string | no | XOR key (default: "55") |

**Response:**
```json
{
  "status": "started",
  "action": "forward",
  "power": 9000,
  "duration": 1.5
}
```

**Error Codes:**
- `400` - Invalid action atau power value
- `503` - Robot not connected

---

### 6. POST /api/joystick

Kontrol joystick manual dengan nilai X dan Y.

**Request Body:**
```json
{
  "x": 5000,
  "y": 0,
  "duration": 2.0,
  "drive_interval": 0.04,
  "poll_interval": 0.20,
  "xor_key": "55",
  "unlock": true,
  "remote_enable": true,
  "remote_disable": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| x | int | yes | Nilai X (-32768 to 32767) |
| y | int | yes | Nilai Y (-32768 to 32767) |
| duration | float | no | Durasi dalam detik (default: 2.0) |
| drive_interval | float | no | Interval kirim frame (default: 0.04) |
| poll_interval | float | no | Interval polling (default: 0.20) |
| xor_key | string | no | XOR key (default: "55") |
| unlock | bool | no | Unlock robot (default: true) |
| remote_enable | bool | no | Enable remote mode (default: true) |
| remote_disable | bool | no | Disable remote mode di akhir (default: false) |

**Response:**
```json
{
  "status": "started",
  "x": 5000,
  "y": 0,
  "duration": 2.0
}
```

---

### 7. POST /api/write

Tulis nilai ke register.

**Request Body:**
```json
{
  "reg": "limit",
  "value": 1,
  "protocol": "cmd2",
  "xor_key": "55"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| reg | string | yes | Nama register (lihat daftar) |
| value | int | yes | Nilai untuk ditulis |
| protocol | string | no | "cmd" atau "cmd2" (default: "cmd2") |
| xor_key | string | no | XOR key (default: "55") |

**Available Registers:**

| Register | Address | Description |
|----------|---------|-------------|
| limit | 0x72 | Limit mode |
| lock | 0x70 | Lock (unlock: 0) |
| lock2 | 0x71 | Lock 2 (unlock: 0) |
| normal_speed | 0x73 | Normal speed |
| train_speed | 0x74 | Training speed |
| max_speed | 0x7D | Max speed |
| turn_scale | 0xA1 | Turn scale |
| riding_scale | 0xA2 | Riding scale |
| power_balance | 0xA3 | Power balance |
| riding_balance | 0xFC | Riding balance |
| light_flags | 0xD3 | Light flags |

**Response:**
```json
{
  "status": "sent",
  "register": "limit",
  "address": "0x72",
  "value": 1,
  "frame": "55 AA 04 0A 03 72 01 00 7B FF"
}
```

---

### 8. POST /api/light

Kontrol lampu dan flags.

**Request Body:**
```json
{
  "headlight": true,
  "brakelight": false,
  "lock_shutdown": false,
  "lock_warn": false,
  "back_alarm": false,
  "carlight": true,
  "xor_key": "55"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| headlight | bool | false | Headlight |
| brakelight | bool | false | Brake light |
| lock_shutdown | bool | false | Lock shutdown |
| lock_warn | bool | false | Lock warning |
| back_alarm | bool | false | Back alarm |
| carlight | bool | false | Car light |
| xor_key | string | "55" | XOR key |

**Response:**
```json
{
  "status": "sent",
  "value": 129,
  "bits": {
    "headlight": true,
    "brakelight": false,
    "lock_shutdown": false,
    "lock_warn": false,
    "back_alarm": false,
    "carlight": true
  },
  "frame": "55 AA 04 0A 03 D3 81 00 28 FE"
}
```

---

### 9. POST /api/raw

Kirim frame hex raw.

**Request Body:**
```json
{
  "hex": "55AA040A037201007BFF",
  "xor_key": "55"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| hex | string | yes | Hex string (dengan/tanpa separator) |
| xor_key | string | no | XOR key (default: "55") |

**Response:**
```json
{
  "status": "sent",
  "frame": "55 AA 04 0A 03 72 01 00 7B FF"
}
```

---

### 10. POST /api/drive

Drive channel mode (legacy/experimental).

**Request Body:**
```json
{
  "channel": 1,
  "axis": null,
  "percent": 20,
  "repeat": 8,
  "stop_after": true,
  "xor_key": "55"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| channel | int | no | Channel 1-7 (default: 1) |
| axis | int | no* | Raw axis value (-128 to 127) |
| percent | int | no* | Axis percent (-100 to 100) |
| repeat | int | no | Repeat count (default: 1) |
| stop_after | bool | no | Send neutral after (default: false) |
| xor_key | string | no | XOR key (default: "55") |

*Salah satu: `axis` atau `percent`

**Response:**
```json
{
  "status": "sent",
  "channel": 1,
  "axis": 25,
  "frames": ["55 AA ...", "55 AA ..."]
}
```

---

### 11. GET /api/registers

Daftar semua register.

**Response:**
```json
{
  "registers": {
    "limit": "0x72",
    "lock": "0x70",
    "lock2": "0x71",
    "normal_speed": "0x73",
    "train_speed": "0x74",
    "max_speed": "0x7d",
    "turn_scale": "0xa1",
    "riding_scale": "0xa2",
    "power_balance": "0xa3",
    "riding_balance": "0xfc",
    "light_flags": "0xd3"
  }
}
```

---

### 12. GET /api/battery

Baca status baterai dari register `0xBB` pada robot yang sudah terkoneksi.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| xor_key | string | "55" | XOR key: "none", "55", "d8" |
| tries | int | 4 | Jumlah kirim request read |
| interval | float | 0.15 | Jeda antar request (detik) |
| timeout | float | 4.0 | Timeout tunggu notifikasi (detik) |
| min_dv | int | 195 | Tegangan 0% baterai (deci-volt) |
| max_dv | int | 252 | Tegangan 100% baterai (deci-volt) |

**Response:**
```json
{
  "status": "ok",
  "raw_deci_volt": 233,
  "voltage": 23.3,
  "battery_percent": 67,
  "battery_percent_source": "battery1Level(0x1F)",
  "battery_percent_estimate": 65,
  "battery1_level": 67,
  "range_deci_volt": {
    "min": 195,
    "max": 252
  },
  "range_volt": {
    "min": 19.5,
    "max": 25.2
  },
  "rx_decode_mode": "55",
  "telemetry_decode_mode": "55",
  "request_xor_key": "55"
}
```

`battery_percent` akan memakai `battery1Level` dari telemetry `0x1F` jika bisa dideteksi; jika tidak, fallback ke estimasi linear dari `0xBB`.

**Error Codes:**
- `400` - Query parameter tidak valid
- `500` - Unknown BLE profile
- `503` - Robot not connected
- `504` - Tidak ada respons battery dari robot

---

## Error Responses

**Standard Error Format:**
```json
{
  "detail": "Error message"
}
```

**Common Error Codes:**

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Device not found |
| 500 | Internal Server Error - Unknown BLE profile |
| 503 | Service Unavailable - Robot not connected |

---

## Frame Format

Semua frame BLE menggunakan format:

```
55 AA LEN CMD TYPE ADDR PAYLOAD... CHK_L CHK_H
```

- `LEN` = payload length + 2
- `CMD` = Command byte
- `TYPE` = Type byte
- `ADDR` = Register address
- `PAYLOAD` = Data bytes
- `CHK_L/CHK_H` = Checksum (~sum bytes from index 2)

---

## XOR Keys

| Key | Value | Description |
|-----|-------|-------------|
| none | 0x00 | No XOR (raw frame) |
| 55 | 0x55 | Standard XOR |
| d8 | 0xD8 | Alternative XOR |

---

## Examples (curl)

```bash
# Scan devices
curl http://localhost:8000/api/scan

# Connect by address
curl -X POST http://localhost:8000/api/connect \
  -H "Content-Type: application/json" \
  -d '{"address": "CB:F4:C1:BF:F4:79"}'

# Connect by name
curl -X POST http://localhost:8000/api/connect \
  -H "Content-Type: application/json" \
  -d '{"name": "Mini"}'

# Move forward
curl -X POST http://localhost:8000/api/move \
  -H "Content-Type: application/json" \
  -d '{"action": "forward", "power": 9000, "duration": 2}'

# Joystick control
curl -X POST http://localhost:8000/api/joystick \
  -H "Content-Type: application/json" \
  -d '{"x": 5000, "y": 3000, "duration": 3}'

# Set headlights
curl -X POST http://localhost:8000/api/light \
  -H "Content-Type: application/json" \
  -d '{"headlight": true, "carlight": true}'

# Write register
curl -X POST http://localhost:8000/api/write \
  -H "Content-Type: application/json" \
  -d '{"reg": "limit", "value": 1}'

# Send raw frame
curl -X POST http://localhost:8000/api/raw \
  -H "Content-Type: application/json" \
  -d '{"hex": "55AA040A037201007BFF"}'

# Read battery (0xBB)
curl "http://localhost:8000/api/battery?xor_key=55&min_dv=195&max_dv=252"

# Disconnect
curl -X POST http://localhost:8000/api/disconnect

# Open frontend
open http://localhost:8000/
```
