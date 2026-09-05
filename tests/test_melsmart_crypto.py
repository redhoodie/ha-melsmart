"""Encrypt/decrypt tests for the /smart transport. No Home Assistant required."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "melsmart"))

from crypto import CryptoError, decrypt_payload, encrypt_payload, pad_key  # noqa: E402


def test_encrypt_decrypt_roundtrip():
    iv = bytes(range(16))
    cipher = encrypt_payload("<CSV></CSV>", b"unregistered", iv)
    assert decrypt_payload(cipher, b"unregistered") == "<CSV></CSV>"


def test_encrypt_uses_padded_unregistered_key():
    assert pad_key(b"unregistered") == b"unregistered\x00\x00\x00\x00"
    iv = b"\x11" * 16
    a = encrypt_payload("<CSV></CSV>", b"unregistered", iv)
    b = encrypt_payload("<CSV></CSV>", b"unregistered\x00\x00\x00\x00", iv)
    assert a == b
    assert decrypt_payload(a, b"unregistered") == "<CSV></CSV>"


def test_decrypt_rejects_short_ciphertext():
    with pytest.raises(CryptoError, match="too short"):
        decrypt_payload("", b"unregistered")
