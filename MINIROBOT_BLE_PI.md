# MiniRobot BLE Control (Python, Raspberry Pi)

Dokumen ini untuk script `minirobot_ble_control.py`.

## 1) Bisa langsung jalan di Raspberry Pi?

**Bisa**, dengan syarat:

- Raspberry Pi punya Bluetooth aktif (builtin atau USB dongle).
- OS Linux dengan BlueZ aktif (`bluetoothd`).
- Python 3.9+.
- Paket Python `bleak` terpasang.

## 2) Setup di Raspberry Pi

```bash
sudo apt update
sudo apt install -y bluetooth bluez python3-pip
python3 -m pip install --upgrade bleak
```

Pastikan service Bluetooth aktif:

```bash
sudo systemctl enable --now bluetooth
bluetoothctl show
```

## 3) Cara pakai cepat

Di folder project ini:

```bash
python3 minirobot_ble_control.py --name Mini write limit 1
```

Perintah di atas kirim command "limit on" memakai frame reverse engineering.

## 4) Contoh command

### A. Kirim frame raw

```bash
python3 minirobot_ble_control.py --name Mini raw 55AA040A037201007BFF
```

### B. Tulis register (mode cmd2 default)

```bash
# limit ON / OFF
python3 minirobot_ble_control.py --name Mini write limit 1
python3 minirobot_ble_control.py --name Mini write limit 0

# speed tuning
python3 minirobot_ble_control.py --name Mini write normal_speed 12000
python3 minirobot_ble_control.py --name Mini write train_speed 16000
python3 minirobot_ble_control.py --name Mini write max_speed 8000

# scale / balance
python3 minirobot_ble_control.py --name Mini write turn_scale 30
python3 minirobot_ble_control.py --name Mini write riding_scale 20
python3 minirobot_ble_control.py --name Mini write power_balance -10
python3 minirobot_ble_control.py --name Mini write riding_balance -500
```

### C. Atur bit lampu/safety (`ADDR 0xD3`)

```bash
# nyalakan headlight + carlight
python3 minirobot_ble_control.py --name Mini light --headlight --carlight

# matikan semua bit (kirim 0)
python3 minirobot_ble_control.py --name Mini light
```

### D. Dengar notifikasi balikan 5 detik

```bash
python3 minirobot_ble_control.py --name Mini --listen 5 write limit 1
```

### E. Drive (maju/mundur/kiri/kanan) - mode eksperimen non-root

Karena HP tidak root, payload joystick asli tidak bisa diambil langsung dari HCI snoop.
Saya sudah turunkan pola dari native dan tambahkan mode `drive` untuk uji langsung.

#### Format yang dipakai mode `drive`

- `ADDR = 0xC8 + 2 * channel` (`channel` 1..7 -> `0xCA..0xD6`)
- `value = sign16((axis << 8) + 0x00F0)`
- frame dikirim via `SendWriteCmd2` (`CMD=0x0A`, `TYPE=0x03`)

#### Langkah aman mapping arah

1. Angkat roda robot dulu (jangan menyentuh tanah).
2. Uji channel satu per satu dengan nilai kecil.
3. Catat channel mana yang bikin maju/mundur/kanan/kiri.

Contoh uji:

```bash
# channel 1, dorong pelan, lalu netral otomatis
python3 minirobot_ble_control.py --name Mini drive --channel 1 --percent 20 --repeat 8 --stop-after

# channel 1, arah kebalikannya
python3 minirobot_ble_control.py --name Mini drive --channel 1 --percent -20 --repeat 8 --stop-after

# coba channel lain
python3 minirobot_ble_control.py --name Mini drive --channel 2 --percent 20 --repeat 8 --stop-after
python3 minirobot_ble_control.py --name Mini drive --channel 3 --percent 20 --repeat 8 --stop-after
```

Setelah mapping ketemu, kamu bisa pakai channel tetap untuk arah yang diinginkan.

### F. Full session emulation (disarankan)

Mode ini meniru loop app lebih dekat:

- unlock (`0x70/0x71`)
- enable remote (`0x7A`)
- init read (`0x1F/0xBB/0x7D`)
- poll periodik (`0x1F, sub=0x10`)
- kirim joystick periodik ke `ADDR 0x7B` (payload `x,y` int16)

Contoh maju:

```bash
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 session --x 0 --y 9000 --duration 8
```

Contoh mundur:

```bash
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 session --x 0 --y -9000 --duration 8
```

Contoh belok kanan/kiri:

```bash
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 session --x 9000 --y 0 --duration 5
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 session --x -9000 --y 0 --duration 5
```

Jika perlu matikan remote mode di akhir:

```bash
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 session --x 0 --y 9000 --duration 8 --remote-disable
```

### G. Command sederhana (tanpa ubah mode lama)

Saya tambahkan mode baru `move` supaya lebih mudah dipakai.
Mode lama (`raw`, `write`, `light`, `drive`, `remote`, `session`, `autotest`) **tetap ada**.

Catatan mapping hasil test unit ini (XOR `55`):

- `left` -> `x=0, y=+power`
- `right` -> `x=0, y=-power`
- `forward` -> `x=+power, y=0`
- `backward` -> `x=-power, y=0`

Contoh dari Raspberry Pi:

```bash
# default auto pakai xor-key 55 di mode move
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --duration 1.5
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move backward --duration 1.5
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move left --duration 1.0
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move right --duration 1.0
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move stop --duration 0.4
```

Atur kekuatan gerak:

```bash
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --power 12000 --duration 2
```

Contoh via SSH langsung dari laptop:

```bash
ssh pi@192.168.100.124 "~/minirobot-venv/bin/python ~/minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move forward --duration 1.5"
ssh pi@192.168.100.124 "~/minirobot-venv/bin/python ~/minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move left --duration 1.0"
ssh pi@192.168.100.124 "~/minirobot-venv/bin/python ~/minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 move stop --duration 0.4"
```

## 5) Opsi koneksi

- Scan by name: `--name Mini`
- Direct by MAC: `--address XX:XX:XX:XX:XX:XX`

Contoh pakai MAC:

```bash
python3 minirobot_ble_control.py --address CB:F4:C1:BF:F4:79 write limit 1
```

## 6) Register map yang sudah dipakai script

- `limit` -> `0x72`
- `lock` -> `0x70`
- `lock2` -> `0x71`
- `normal_speed` -> `0x73`
- `train_speed` -> `0x74`
- `max_speed` -> `0x7D`
- `turn_scale` -> `0xA1`
- `riding_scale` -> `0xA2`
- `power_balance` -> `0xA3`
- `riding_balance` -> `0xFC`
- `light_flags` -> `0xD3`

## 7) Format frame (hasil reverse)

```
55 AA LEN CMD TYPE ADDR PAYLOAD... CHK_L CHK_H
```

- `LEN = payload_len + 2`
- `checksum = ~sum(bytes dari index 2 sampai akhir payload) & 0xFFFF`

## 8) Troubleshooting

- Jika tidak ketemu device:
  - Dekatkan Pi ke robot.
  - Coba `--address` langsung.
  - Pastikan robot sedang advertising.
- Jika permission BLE error:
  - Jalankan dengan user yang punya akses Bluetooth.
  - Opsi cepat: `sudo -E python3 ...`.
- Jika gerakan tidak sesuai arah:
  - Balik tanda nilai (`--percent` dari `20` jadi `-20`).
  - Coba channel lain (`--channel 1..7`).
