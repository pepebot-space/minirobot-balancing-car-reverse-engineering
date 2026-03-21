#!/usr/bin/env python3
import argparse
import asyncio
from typing import Any, Optional

from bleak import BleakClient, BleakScanner

SVC_NUS = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
CHR_WRITE_NUS = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
CHR_NOTIFY_NUS = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


def build_frame(cmd: int, typ: int, addr: int, payload: bytes) -> bytes:
    frame = bytearray(
        (0x55, 0xAA, (len(payload) + 2) & 0xFF, cmd & 0xFF, typ & 0xFF, addr & 0xFF)
    )
    frame.extend(payload)
    chk = (~sum(frame[2:])) & 0xFFFF
    frame.extend((chk & 0xFF, (chk >> 8) & 0xFF))
    return bytes(frame)


def read_cmd2(addr: int, sub: int) -> bytes:
    return build_frame(0x0A, 0x01, addr, bytes([sub & 0xFF]))


def xor_bytes(data: bytes, key: int) -> bytes:
    return bytes((b ^ key) for b in data)


def parse_one_frame(data: bytes) -> Optional[tuple[int, int, int, bytes]]:
    if len(data) < 8 or data[0] != 0x55 or data[1] != 0xAA:
        return None
    total = data[2] + 6
    if total > len(data):
        return None
    frm = data[:total]
    chk = ((frm[-1] << 8) | frm[-2]) & 0xFFFF
    calc = (~sum(frm[2:-2])) & 0xFFFF
    if chk != calc:
        return None
    payload_len = frm[2] - 2
    payload = frm[6 : 6 + payload_len]
    return frm[3], frm[4], frm[5], payload


def decode_frame_any(data: bytes) -> Optional[tuple[int, int, int, bytes, str]]:
    for mode, key in (("none", None), ("55", 0x55), ("d8", 0xD8)):
        probe = data if key is None else xor_bytes(data, key)
        parsed = parse_one_frame(probe)
        if parsed is not None:
            cmd, typ, addr, payload = parsed
            return cmd, typ, addr, payload, mode
    return None


def estimate_percent(raw: int, min_dv: int, max_dv: int) -> int:
    if max_dv <= min_dv:
        return 0
    p = int(round((raw - min_dv) * 100.0 / (max_dv - min_dv)))
    return max(0, min(100, p))


async def find_device(address: Optional[str], name: Optional[str], timeout: float):
    if address:
        return await BleakScanner.find_device_by_address(address, timeout=timeout)
    devices = await BleakScanner.discover(timeout=timeout)
    if name:
        q = name.lower()
        for d in devices:
            if d.name and q in d.name.lower():
                return d
    for d in devices:
        if d.name and d.name.startswith(("M6", "Mini", "A6")):
            return d
    return None


async def main_async(args) -> None:
    target = None
    if args.address:
        target = args.address
        print(f"[BLE] target address: {args.address}")
    else:
        dev = await find_device(args.address, args.name, args.scan_timeout)
        if not dev:
            raise RuntimeError("Device not found")
        target = dev
        print(f"[BLE] {dev.name} ({dev.address})")
    got = asyncio.Event()
    result: dict[str, Any] = {"raw": None}

    async with BleakClient(target, timeout=20.0) as client:

        def on_notify(_, data: bytearray):
            parsed = decode_frame_any(bytes(data))
            if not parsed:
                return
            cmd, typ, addr, payload, mode = parsed
            if cmd == 0x0D and typ == 0x01 and addr == 0xBB and len(payload) >= 2:
                raw = int.from_bytes(payload[:2], "little", signed=False)
                result["raw"] = raw
                result["mode"] = mode
                got.set()

        await client.start_notify(CHR_NOTIFY_NUS, on_notify)

        frame = read_cmd2(0xBB, 0x02)
        for _ in range(max(1, args.tries)):
            wire = (
                frame
                if args.xor_key == "none"
                else xor_bytes(frame, 0x55 if args.xor_key == "55" else 0xD8)
            )
            await client.write_gatt_char(CHR_WRITE_NUS, wire, response=False)
            await asyncio.sleep(args.interval)

        try:
            await asyncio.wait_for(got.wait(), timeout=args.timeout)
        finally:
            await client.stop_notify(CHR_NOTIFY_NUS)

    raw = result["raw"]
    if raw is None:
        print("No battery response received")
        return

    volts = raw / 10.0
    pct = estimate_percent(raw, args.min_dv, args.max_dv)
    print(f"raw(0xBB): {raw} deci-volt")
    print(f"voltage: {volts:.1f} V")
    print(
        f"battery: {pct}% (est., range {args.min_dv / 10:.1f}-{args.max_dv / 10:.1f} V)"
    )
    print(f"rx decode mode: {result.get('mode', 'unknown')}")


def main() -> None:
    p = argparse.ArgumentParser(description="Read MiniRobot battery from register 0xBB")
    p.add_argument("--address", help="BLE MAC address")
    p.add_argument("--name", help="BLE name contains")
    p.add_argument("--scan-timeout", type=float, default=8.0)
    p.add_argument("--xor-key", choices=("none", "55", "d8"), default="55")
    p.add_argument("--tries", type=int, default=4)
    p.add_argument("--interval", type=float, default=0.15)
    p.add_argument("--timeout", type=float, default=4.0)
    p.add_argument(
        "--min-dv", type=int, default=195, help="0%% battery voltage in deci-volt"
    )
    p.add_argument(
        "--max-dv", type=int, default=252, help="100%% battery voltage in deci-volt"
    )
    args = p.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
