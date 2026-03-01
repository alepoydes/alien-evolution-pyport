from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BlockPtr:
    """Pointer into a concrete block buffer."""

    array: bytes | bytearray
    index: int

    def add(self, delta: int) -> BlockPtr:
        return BlockPtr(
            array=self.array,
            index=self.index + int(delta),
        )

    def sub(self, delta: int) -> BlockPtr:
        return self.add(-int(delta))

    def with_index(self, index: int) -> BlockPtr:
        return BlockPtr(
            array=self.array,
            index=int(index),
        )

    def check_span(self, size: int, op: str) -> None:
        if size < 0:
            raise ValueError(f"Negative span for {op}: size={size}")
        end = self.index + int(size)
        if self.index < 0 or end > len(self.array):
            raise ValueError(
                f"{op} crosses block boundary: "
                f"index={self.index}, size={size}, len={len(self.array)}",
            )

    def read_u8(self) -> int:
        self.check_span(1, "read")
        return self.array[self.index]

    def read_bytes(self, size: int) -> bytes:
        self.check_span(size, "read")
        return bytes(self.array[self.index : self.index + int(size)])

    def write_u8(self, value: int) -> None:
        if not isinstance(self.array, bytearray):
            raise TypeError("Pointer targets immutable block")
        self.check_span(1, "write")
        self.array[self.index] = value & 0xFF

    def write_bytes(self, data: bytes | bytearray) -> None:
        if not isinstance(self.array, bytearray):
            raise TypeError("Pointer targets immutable block")
        payload = bytes(data)
        self.check_span(len(payload), "write")
        self.array[self.index : self.index + len(payload)] = payload

    def fill(self, size: int, value: int) -> None:
        if not isinstance(self.array, bytearray):
            raise TypeError("Pointer targets immutable block")
        self.check_span(size, "fill")
        self.array[self.index : self.index + int(size)] = bytes([value & 0xFF]) * int(size)


@dataclass(frozen=True)
class StructFieldPtr:
    """Pointer into typed structured data (lists/dataclasses), not byte memory."""

    root: object
    path: tuple[int | str, ...] = ()

    def index(self, idx: int) -> StructFieldPtr:
        return StructFieldPtr(
            root=self.root,
            path=self.path + (int(idx),),
        )

    def field(self, name: str) -> StructFieldPtr:
        if not name:
            raise ValueError("Field name must be non-empty")
        return StructFieldPtr(
            root=self.root,
            path=self.path + (name,),
        )

    def add(self, delta: int) -> StructFieldPtr:
        shift = int(delta)
        new_path = list(self.path)
        for i in range(len(new_path) - 1, -1, -1):
            step = new_path[i]
            if isinstance(step, int):
                new_path[i] = step + shift
                return StructFieldPtr(root=self.root, path=tuple(new_path))
        raise ValueError("StructFieldPtr.add requires an index step in path")

    def _resolve_value(self) -> Any:
        cur: Any = self.root
        for step in self.path:
            if isinstance(step, int):
                cur = cur[step]
            else:
                cur = getattr(cur, step)
        return cur

    def _write_value(self, value: Any) -> None:
        if not self.path:
            raise ValueError("Cannot write to StructFieldPtr root directly")

        cur: Any = self.root
        for step in self.path[:-1]:
            if isinstance(step, int):
                cur = cur[step]
            else:
                cur = getattr(cur, step)

        tail = self.path[-1]
        if isinstance(tail, int):
            cur[tail] = value
        else:
            setattr(cur, tail, value)

    def read_u8(self) -> int:
        return int(self._resolve_value()) & 0xFF

    def read_u16(self) -> int:
        return int(self._resolve_value()) & 0xFFFF

    def write_u8(self, value: int) -> None:
        self._write_value(int(value) & 0xFF)

    def write_u16(self, value: int) -> None:
        self._write_value(int(value) & 0xFFFF)
