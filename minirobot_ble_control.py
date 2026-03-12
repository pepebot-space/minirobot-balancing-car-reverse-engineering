#!/usr/bin/env python3
import argparse
import asyncio
import time
from typing import Dict, Iterable, Optional

from bleak import BleakClient, BleakScanner

SVC_NUS = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
CHR_WRITE_NUS = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
CHR_NOTIFY_NUS = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

SVC_FFE = "0000FFE0-0000-1000-8000-00805F9B34FB"
CHR_FFE = "0000FFE1-0000-1000-8000-00805F9B34FB"

NAME_PREFIXES = ("M6", "Mini", "A6")


def hexdump(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def maybe_xor(data: bytes, key: str) -> bytes:
    if key == "none":
        return data
    b = 0x55 if key == "55" else 0xD8
    return bytes((x ^ b) for x in data)


def build_frame(cmd: int, typ: int, addr: int, payload: bytes) -> bytes:
    if not (0 <= cmd <= 0xFF and 0 <= typ <= 0xFF and 0 <= addr <= 0xFF):
        raise ValueError("cmd/type/addr must be 0..255")
    if len(payload) > 255:
        raise ValueError("payload too long")

    frame = bytearray()
    frame.extend((0x55, 0xAA))
    frame.append((len(payload) + 2) & 0xFF)
    frame.append(cmd & 0xFF)
    frame.append(typ & 0xFF)
    frame.append(addr & 0xFF)
    frame.extend(payload)

    checksum = (~sum(frame[2:])) & 0xFFFF
    frame.append(checksum & 0xFF)
    frame.append((checksum >> 8) & 0xFF)
    return bytes(frame)


def write_cmd2(addr: int, value: int) -> bytes:
    payload = int(value & 0xFFFF).to_bytes(2, "little", signed=False)
    return build_frame(cmd=0x0A, typ=0x03, addr=addr, payload=payload)


def write_cmd(addr: int, value: int) -> bytes:
    payload = int(value & 0xFFFF).to_bytes(2, "little", signed=False)
    return build_frame(cmd=0x06, typ=0x03, addr=addr, payload=payload)


def write_array_cmd2(addr: int, payload: bytes) -> bytes:
    return build_frame(cmd=0x0A, typ=0x03, addr=addr, payload=payload)


def read_cmd2(addr: int, sub: int) -> bytes:
    payload = bytes([sub & 0xFF])
    return build_frame(cmd=0x0A, typ=0x01, addr=addr, payload=payload)


REG: Dict[str, int] = {
    "limit": 0x72,
    "lock": 0x70,
    "lock2": 0x71,
    "normal_speed": 0x73,
    "train_speed": 0x74,
    "max_speed": 0x7D,
    "turn_scale": 0xA1,
    "riding_scale": 0xA2,
    "power_balance": 0xA3,
    "riding_balance": 0xFC,
    "light_flags": 0xD3,
}


def remote_channel_addr(channel: int) -> int:
    if not (1 <= channel <= 7):
        raise ValueError("channel must be 1..7")
    return 0xC8 + (channel * 2)


def encode_drive_value(axis: int) -> int:
    # Reverse result from native touch handler:
    # value = sign16((axis << 8) + 0x00F0)
    if axis < -128 or axis > 127:
        raise ValueError("axis must be -128..127")
    raw = ((axis << 8) + 0x00F0) & 0xFFFF
    if raw >= 0x8000:
        raw -= 0x10000
    return raw


async def find_target(name: Optional[str], address: Optional[str], timeout: float):
    if address:
        d = await BleakScanner.find_device_by_address(address, timeout=timeout)
        return d

    devices = await BleakScanner.discover(timeout=timeout)
    if name:
        name_l = name.lower()
        for d in devices:
            if d.name and name_l in d.name.lower():
                return d
        return None

    for d in devices:
        if d.name and d.name.startswith(NAME_PREFIXES):
            return d
    return None


def choose_profile(services) -> str:
    uuids = {s.uuid.upper() for s in services}
    if SVC_NUS in uuids:
        return "nus"
    if SVC_FFE in uuids:
        return "ffe"
    return "unknown"


async def send_frames(args, frames: Iterable[bytes]) -> None:
    device = await find_target(args.name, args.address, args.scan_timeout)
    if not device:
        raise RuntimeError("Device not found. Use --name or --address.")

    print(f"[BLE] device: {device.name} ({device.address})")

    async with BleakClient(device, timeout=20.0) as client:
        services = client.services
        profile = choose_profile(services)
        if profile == "nus":
            write_uuid = CHR_WRITE_NUS
            notify_uuid = CHR_NOTIFY_NUS
        elif profile == "ffe":
            write_uuid = CHR_FFE
            notify_uuid = CHR_FFE
        else:
            raise RuntimeError("Known BLE profile not found (NUS/FFE).")

        print(f"[BLE] profile: {profile}, write={write_uuid}")

        if args.listen:

            def on_notify(_, data: bytearray):
                print(f"RX: {hexdump(bytes(data))}")

            await client.start_notify(notify_uuid, on_notify)

        for f in frames:
            wire = maybe_xor(f, args.xor_key)
            print(f"TX: {hexdump(wire)}")
            await client.write_gatt_char(write_uuid, wire, response=False)
            await asyncio.sleep(args.delay)

        if args.listen:
            await asyncio.sleep(args.listen)
            await client.stop_notify(notify_uuid)


async def run_session(args) -> None:
    device = await find_target(args.name, args.address, args.scan_timeout)
    if not device:
        raise RuntimeError("Device not found. Use --name or --address.")

    print(f"[BLE] device: {device.name} ({device.address})")

    async with BleakClient(device, timeout=20.0) as client:
        services = client.services
        profile = choose_profile(services)
        if profile == "nus":
            write_uuid = CHR_WRITE_NUS
            notify_uuid = CHR_NOTIFY_NUS
        elif profile == "ffe":
            write_uuid = CHR_FFE
            notify_uuid = CHR_FFE
        else:
            raise RuntimeError("Known BLE profile not found (NUS/FFE).")

        print(f"[BLE] profile: {profile}, write={write_uuid}")

        def on_notify(_, data: bytearray):
            print(f"RX: {hexdump(bytes(data))}")

        if args.notify:
            await client.start_notify(notify_uuid, on_notify)

        async def tx(frame: bytes, tag: str) -> None:
            wire = maybe_xor(frame, args.xor_key)
            print(f"TX[{tag}]: {hexdump(wire)}")
            await client.write_gatt_char(write_uuid, wire, response=False)
            await asyncio.sleep(args.delay)

        if args.unlock:
            await tx(write_cmd(0x70, 0), "unlock70")
            await tx(write_cmd2(0x71, 0), "unlock71")

        if args.remote_enable:
            await tx(write_cmd2(0x7A, 1), "remote_on")

        if args.init_reads:
            await tx(read_cmd2(0x1F, 0x02), "read1f02")
            await tx(read_cmd2(0xBB, 0x02), "readbb02")
            await tx(read_cmd2(0x7D, 0x02), "read7d02")

        x = int(args.x)
        y = int(args.y)
        if x < -32768 or x > 32767 or y < -32768 or y > 32767:
            raise ValueError("x/y must be int16")

        payload = x.to_bytes(2, "little", signed=True) + y.to_bytes(
            2, "little", signed=True
        )

        t_end = time.monotonic() + max(0.2, float(args.duration))
        next_drive = time.monotonic()
        next_poll = time.monotonic()
        while time.monotonic() < t_end:
            now = time.monotonic()
            if now >= next_drive:
                await tx(write_array_cmd2(0x7B, payload), "joy")
                next_drive += max(0.01, float(args.drive_interval))
            if now >= next_poll:
                await tx(read_cmd2(0x1F, 0x10), "poll1f10")
                next_poll += max(0.05, float(args.poll_interval))
            await asyncio.sleep(0.005)

        zero = (0).to_bytes(2, "little", signed=True)
        await tx(write_array_cmd2(0x7B, zero + zero), "joy_zero")

        if args.remote_disable:
            await tx(write_cmd2(0x7A, 0), "remote_off")

        if args.notify:
            await asyncio.sleep(max(0.0, float(args.post_listen)))
            await client.stop_notify(notify_uuid)


async def run_autotest(args) -> None:
    device = await find_target(args.name, args.address, args.scan_timeout)
    if not device:
        raise RuntimeError("Device not found. Use --name or --address.")

    print(f"[BLE] device: {device.name} ({device.address})")

    async with BleakClient(device, timeout=20.0) as client:
        services = client.services
        profile = choose_profile(services)
        if profile == "nus":
            write_uuid = CHR_WRITE_NUS
            notify_uuid = CHR_NOTIFY_NUS
        elif profile == "ffe":
            write_uuid = CHR_FFE
            notify_uuid = CHR_FFE
        else:
            raise RuntimeError("Known BLE profile not found (NUS/FFE).")

        print(f"[BLE] profile: {profile}, write={write_uuid}")

        def on_notify(_, data: bytearray):
            print(f"RX: {hexdump(bytes(data))}")

        if args.notify:
            await client.start_notify(notify_uuid, on_notify)

        async def tx(frame: bytes, tag: str, xor_key: str) -> None:
            wire = maybe_xor(frame, xor_key)
            print(f"TX[{tag}|{xor_key}]: {hexdump(wire)}")
            await client.write_gatt_char(write_uuid, wire, response=False)
            await asyncio.sleep(args.delay)

        for key in ("none", "55", "d8"):
            await tx(write_cmd(0x70, 0), "unlock70", key)
            await tx(write_cmd2(0x71, 0), "unlock71", key)
            await tx(write_cmd2(0x7A, 1), "remote_on", key)
            await tx(read_cmd2(0x1F, 0x02), "read1f02", key)
            await tx(read_cmd2(0xBB, 0x02), "readbb02", key)
            await tx(read_cmd2(0x7D, 0x02), "read7d02", key)

        amp = int(args.amplitude)
        tests = []
        for key in ("none", "55", "d8"):
            tests.extend(
                [
                    (key, 0, amp, "forward?"),
                    (key, 0, -amp, "backward?"),
                    (key, amp, 0, "right?"),
                    (key, -amp, 0, "left?"),
                ]
            )

        for idx, (key, x, y, label) in enumerate(tests, start=1):
            print(f"STEP {idx}: key={key} x={x} y={y} ({label})")
            payload = x.to_bytes(2, "little", signed=True) + y.to_bytes(
                2, "little", signed=True
            )
            t_end = time.monotonic() + max(0.2, float(args.step_duration))
            next_drive = time.monotonic()
            next_poll = time.monotonic()
            while time.monotonic() < t_end:
                now = time.monotonic()
                if now >= next_drive:
                    await tx(write_array_cmd2(0x7B, payload), "joy", key)
                    next_drive += max(0.01, float(args.drive_interval))
                if now >= next_poll:
                    await tx(read_cmd2(0x1F, 0x10), "poll1f10", key)
                    next_poll += max(0.05, float(args.poll_interval))
                await asyncio.sleep(0.005)

            zero = (0).to_bytes(2, "little", signed=True)
            await tx(write_array_cmd2(0x7B, zero + zero), "joy_zero", key)
            await asyncio.sleep(max(0.1, float(args.step_gap)))

        if args.notify:
            await asyncio.sleep(max(0.0, float(args.post_listen)))
            await client.stop_notify(notify_uuid)


async def run_move(args) -> None:
    amp = abs(int(args.power))
    if amp > 32767:
        raise ValueError("power must be 0..32767")

    mapping = {
        "left": (0, amp),
        "right": (0, -amp),
        "forward": (amp, 0),
        "backward": (-amp, 0),
        "stop": (0, 0),
    }
    x, y = mapping[args.action]

    if args.xor_key == "none":
        args.xor_key = "55"

    args.x = x
    args.y = y
    args.duration = max(0.2, float(args.duration))
    args.drive_interval = float(args.drive_interval)
    args.poll_interval = float(args.poll_interval)
    args.unlock = True
    args.remote_enable = True
    args.remote_disable = bool(args.remote_disable)
    args.init_reads = True
    args.notify = bool(args.notify)
    args.post_listen = float(args.post_listen)

    await run_session(args)


def parse_hex_bytes(s: str) -> bytes:
    clean = "".join(ch for ch in s if ch in "0123456789abcdefABCDEF")
    if len(clean) % 2:
        clean = "0" + clean
    if not clean:
        raise ValueError("empty hex")
    return bytes.fromhex(clean)


def build_command_frames(args) -> Iterable[bytes]:
    if args.mode == "raw":
        return [parse_hex_bytes(args.hex)]

    if args.mode == "write":
        reg = REG[args.reg]
        if args.protocol == "cmd":
            return [write_cmd(reg, args.value)]
        return [write_cmd2(reg, args.value)]

    if args.mode == "light":
        val = 0
        if args.headlight:
            val |= 0x01
        if args.brakelight:
            val |= 0x02
        if args.lock_shutdown:
            val |= 0x04
        if args.lock_warn:
            val |= 0x08
        if args.back_alarm:
            val |= 0x10
        if args.carlight:
            val |= 0x80
        return [write_cmd2(REG["light_flags"], val)]

    if args.mode == "drive":
        if args.axis is not None:
            axis = int(args.axis)
        else:
            pct = max(-100, min(100, int(args.percent)))
            axis = int(round((pct * 127) / 100))

        value = encode_drive_value(axis)
        addr = remote_channel_addr(args.channel)

        frames = []
        repeat = max(1, int(args.repeat))
        for _ in range(repeat):
            frames.append(write_cmd2(addr, value))
        if args.stop_after:
            frames.append(write_cmd2(addr, encode_drive_value(0)))
        return frames

    if args.mode == "remote":
        x = int(args.x)
        y = int(args.y)
        if x < -32768 or x > 32767 or y < -32768 or y > 32767:
            raise ValueError("x/y must be int16")
        payload = x.to_bytes(2, "little", signed=True) + y.to_bytes(
            2, "little", signed=True
        )
        frames = [
            write_array_cmd2(0x7B, payload) for _ in range(max(1, int(args.repeat)))
        ]
        if args.stop_after:
            zero = (0).to_bytes(2, "little", signed=True)
            frames.append(write_array_cmd2(0x7B, zero + zero))
        return frames

    if args.mode == "session":
        return []

    if args.mode == "autotest":
        return []

    if args.mode == "move":
        return []

    raise ValueError("unknown mode")


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MiniRobot BLE controller (reverse engineered)"
    )
    p.add_argument("--address", help="Target BLE MAC address")
    p.add_argument("--name", help="Target BLE name contains")
    p.add_argument("--scan-timeout", type=float, default=8.0)
    p.add_argument("--delay", type=float, default=0.08, help="Delay between TX frames")
    p.add_argument(
        "--xor-key",
        choices=("none", "55", "d8"),
        default="none",
        help="Apply XOR to whole frame (from app native mode)",
    )
    p.add_argument(
        "--listen", type=float, default=0.0, help="Listen notification for N seconds"
    )

    sub = p.add_subparsers(dest="mode", required=True)

    s_raw = sub.add_parser("raw", help="Send raw hex frame")
    s_raw.add_argument("hex", help="Example: 55AA040A037201007BFF")

    s_write = sub.add_parser("write", help="Write register value")
    s_write.add_argument("reg", choices=sorted(REG.keys()))
    s_write.add_argument("value", type=int)
    s_write.add_argument("--protocol", choices=("cmd2", "cmd"), default="cmd2")

    s_light = sub.add_parser("light", help="Set D3 bit flags")
    s_light.add_argument("--headlight", action="store_true")
    s_light.add_argument("--brakelight", action="store_true")
    s_light.add_argument("--lock-shutdown", action="store_true")
    s_light.add_argument("--lock-warn", action="store_true")
    s_light.add_argument("--back-alarm", action="store_true")
    s_light.add_argument("--carlight", action="store_true")

    s_drive = sub.add_parser(
        "drive", help="Send remote-drive style value (legacy, likely not movement)"
    )
    s_drive.add_argument(
        "--channel",
        type=int,
        default=1,
        help="Remote channel 1..7 (maps to addr 0xCA..0xD6)",
    )
    s_drive.add_argument("--axis", type=int, help="Raw axis value -128..127")
    s_drive.add_argument(
        "--percent",
        type=int,
        default=0,
        help="Axis percent -100..100 (used if --axis missing)",
    )
    s_drive.add_argument(
        "--repeat", type=int, default=1, help="Send same frame N times"
    )
    s_drive.add_argument(
        "--stop-after", action="store_true", help="Send neutral frame after command"
    )

    s_remote = sub.add_parser(
        "remote", help="Send joystick pair to addr 0x7B (x,y int16)"
    )
    s_remote.add_argument("--x", type=int, required=True, help="X axis int16")
    s_remote.add_argument("--y", type=int, required=True, help="Y axis int16")
    s_remote.add_argument(
        "--repeat", type=int, default=8, help="Send same frame N times"
    )
    s_remote.add_argument(
        "--stop-after", action="store_true", help="Send (0,0) after command"
    )

    s_session = sub.add_parser(
        "session", help="Run full remote session (unlock + reads + joystick loop)"
    )
    s_session.add_argument("--x", type=int, default=0, help="Joystick X int16")
    s_session.add_argument("--y", type=int, default=9000, help="Joystick Y int16")
    s_session.add_argument("--duration", type=float, default=8.0)
    s_session.add_argument("--drive-interval", type=float, default=0.04)
    s_session.add_argument("--poll-interval", type=float, default=0.20)
    s_session.add_argument(
        "--unlock", action=argparse.BooleanOptionalAction, default=True
    )
    s_session.add_argument(
        "--remote-enable", action=argparse.BooleanOptionalAction, default=True
    )
    s_session.add_argument(
        "--remote-disable", action=argparse.BooleanOptionalAction, default=False
    )
    s_session.add_argument(
        "--init-reads", action=argparse.BooleanOptionalAction, default=True
    )
    s_session.add_argument(
        "--notify", action=argparse.BooleanOptionalAction, default=True
    )
    s_session.add_argument("--post-listen", type=float, default=0.5)

    s_autotest = sub.add_parser(
        "autotest", help="Cycle XOR and joystick variants to find moving combination"
    )
    s_autotest.add_argument("--amplitude", type=int, default=9000)
    s_autotest.add_argument("--step-duration", type=float, default=2.0)
    s_autotest.add_argument("--step-gap", type=float, default=1.2)
    s_autotest.add_argument("--drive-interval", type=float, default=0.04)
    s_autotest.add_argument("--poll-interval", type=float, default=0.20)
    s_autotest.add_argument(
        "--notify", action=argparse.BooleanOptionalAction, default=True
    )
    s_autotest.add_argument("--post-listen", type=float, default=0.5)

    s_move = sub.add_parser(
        "move", help="Simple movement command: forward/backward/left/right/stop"
    )
    s_move.add_argument(
        "action", choices=("forward", "backward", "left", "right", "stop")
    )
    s_move.add_argument("--power", type=int, default=9000, help="Joystick amplitude")
    s_move.add_argument("--duration", type=float, default=1.5)
    s_move.add_argument("--drive-interval", type=float, default=0.04)
    s_move.add_argument("--poll-interval", type=float, default=0.20)
    s_move.add_argument(
        "--notify", action=argparse.BooleanOptionalAction, default=False
    )
    s_move.add_argument(
        "--remote-disable", action=argparse.BooleanOptionalAction, default=False
    )
    s_move.add_argument("--post-listen", type=float, default=0.2)

    return p


async def main_async() -> None:
    args = make_parser().parse_args()
    if args.mode == "session":
        await run_session(args)
        return
    if args.mode == "autotest":
        await run_autotest(args)
        return
    if args.mode == "move":
        await run_move(args)
        return
    frames = build_command_frames(args)
    await send_frames(args, frames)


if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass
