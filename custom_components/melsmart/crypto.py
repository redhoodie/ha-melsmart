"""AES-128-CBC helpers for the Mitsubishi /smart transport."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY_SIZE = 16


class CryptoError(Exception):
    """Raised when a /smart payload cannot be decrypted."""


def pad_key(key: bytes) -> bytes:
    if len(key) < KEY_SIZE:
        return key + b"\x00" * (KEY_SIZE - len(key))
    return key[:KEY_SIZE]


def _pad_iso7816(data: bytes) -> bytes:
    data = data + b"\x80"
    if len(data) % KEY_SIZE:
        data += b"\x00" * (KEY_SIZE - len(data) % KEY_SIZE)
    return data


def _unpad_iso7816(data: bytes) -> bytes:
    end = len(data)
    while end > 0 and data[end - 1] == 0:
        end -= 1
    if end > 0 and data[end - 1] == 0x80:
        end -= 1
    return data[:end]


def encrypt_payload(plain: str, key: bytes, iv: bytes | None = None) -> str:
    key = pad_key(key)
    if iv is None:
        iv = os.urandom(KEY_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = cipher.update(_pad_iso7816(plain.encode("utf-8"))) + cipher.finalize()
    return base64.b64encode(iv + ct).decode("ascii")


def decrypt_payload(payload_b64: str, key: bytes) -> str:
    key = pad_key(key)
    raw = base64.b64decode(payload_b64)
    if len(raw) < KEY_SIZE:
        raise CryptoError("ciphertext too short")
    iv, ct = raw[:KEY_SIZE], raw[KEY_SIZE:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = _unpad_iso7816(cipher.update(ct) + cipher.finalize())
    return plain.decode("utf-8", errors="replace")
