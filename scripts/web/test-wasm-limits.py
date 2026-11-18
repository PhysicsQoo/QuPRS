#!/usr/bin/env python3
"""Negative and boundary fixtures for the actual WASM memory-limit validator."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CHECKER = Path(__file__).with_name("check-wasm-limits.py")
HEADER = b"\x00asm\x01\x00\x00\x00"


def leb(number: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = number & 0x7F
        number >>= 7
        encoded.append(byte | (0x80 if number else 0))
        if not number:
            return bytes(encoded)


def module_with_memory(maximum: int | None, minimum: int = 1, count: int = 1) -> bytes:
    types = b"".join(
        leb(1 if maximum is not None else 0) +
        leb(minimum) +
        (leb(maximum) if maximum is not None else b"")
        for _ in range(count)
    )
    section = leb(count) + types
    return HEADER + b"\x05" + leb(len(section)) + section


class MemoryLimitTests(unittest.TestCase):
    def check(self, image: bytes, accepted: bool) -> None:
        with tempfile.TemporaryDirectory(prefix="wasm-memory-contract-") as root:
            candidate = Path(root) / "fixture.wasm"
            candidate.write_bytes(image)
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(candidate)],
                capture_output=True, text=True, check=False, timeout=5,
            )
            if accepted:
                self.assertEqual(result.returncode, 0, result.stderr)
                parsed = json.loads(result.stdout)
                self.assertEqual(len(parsed), 1)
                self.assertEqual(parsed[0]["memory"][0]["maximum_pages"], 8192)
            else:
                self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_exact_512_mib_ceiling_is_admitted(self) -> None:
        self.check(module_with_memory(8192), True)

    def test_larger_ceiling_is_rejected(self) -> None:
        self.check(module_with_memory(8193), False)

    def test_unbounded_memory_is_rejected(self) -> None:
        self.check(module_with_memory(None), False)

    def test_absent_memory_is_rejected(self) -> None:
        self.check(HEADER, False)

    def test_multiple_memory_declarations_are_rejected(self) -> None:
        self.check(module_with_memory(8192, count=2), False)


if __name__ == "__main__":
    unittest.main()
