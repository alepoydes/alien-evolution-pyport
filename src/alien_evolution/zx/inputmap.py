from __future__ import annotations

# Mapping from semantic key character to ZX keyboard row-port and bit index.
# Port values are full 16-bit row probes used by classic IN (C) keyboard scan.
KEY_CHAR_TO_ZX_KEYBOARD_SCAN: dict[str, tuple[int, int]] = {
    "z": (0xFEFE, 1),
    "x": (0xFEFE, 2),
    "c": (0xFEFE, 3),
    "v": (0xFEFE, 4),
    "a": (0xFDFE, 0),
    "s": (0xFDFE, 1),
    "d": (0xFDFE, 2),
    "f": (0xFDFE, 3),
    "g": (0xFDFE, 4),
    "q": (0xFBFE, 0),
    "w": (0xFBFE, 1),
    "e": (0xFBFE, 2),
    "r": (0xFBFE, 3),
    "t": (0xFBFE, 4),
    "1": (0xF7FE, 0),
    "2": (0xF7FE, 1),
    "3": (0xF7FE, 2),
    "4": (0xF7FE, 3),
    "5": (0xF7FE, 4),
    "0": (0xEFFE, 0),
    "9": (0xEFFE, 1),
    "8": (0xEFFE, 2),
    "7": (0xEFFE, 3),
    "6": (0xEFFE, 4),
    "p": (0xDFFE, 0),
    "o": (0xDFFE, 1),
    "i": (0xDFFE, 2),
    "u": (0xDFFE, 3),
    "y": (0xDFFE, 4),
    "\n": (0xBFFE, 0),
    "\r": (0xBFFE, 0),
    "l": (0xBFFE, 1),
    "k": (0xBFFE, 2),
    "j": (0xBFFE, 3),
    "h": (0xBFFE, 4),
    " ": (0x7FFE, 0),
    "m": (0x7FFE, 2),
    "n": (0x7FFE, 3),
    "b": (0x7FFE, 4),
}

# ZX keyboard row probe ports in hardware row order.
ZX_KEYBOARD_ROW_PORTS: tuple[int, ...] = (
    0xFEFE,  # CAPS SHIFT, Z, X, C, V
    0xFDFE,  # A, S, D, F, G
    0xFBFE,  # Q, W, E, R, T
    0xF7FE,  # 1, 2, 3, 4, 5
    0xEFFE,  # 0, 9, 8, 7, 6
    0xDFFE,  # P, O, I, U, Y
    0xBFFE,  # ENTER, L, K, J, H
    0x7FFE,  # SPACE, SYMBOL SHIFT, M, N, B
)

ZX_KEYBOARD_ROW_INDEX_BY_PORT: dict[int, int] = {
    port: idx for idx, port in enumerate(ZX_KEYBOARD_ROW_PORTS)
}
