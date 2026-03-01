from __future__ import annotations

from dataclasses import fields, is_dataclass
import hashlib
import json
from typing import Mapping, Protocol

from .pointers import BlockPtr, StructFieldPtr

STATE_ENVELOPE_FORMAT_V1 = "zx-runtime-state-v1"


class StateEnvelopeError(ValueError):
    """Raised when serialized runtime state envelope is malformed."""


class StatefulRuntime(Protocol):
    """Optional runtime protocol for persisted state support."""

    def save_state(self) -> dict[str, object]:
        ...

    def load_state(self, state: Mapping[str, object]) -> None:
        ...


class StatefulManifestRuntime(StatefulRuntime):
    """Common manifest-driven save/load implementation for game runtimes.

    Subclasses declare dynamic-field manifests and provide codec/apply hooks
    for game-specific value representations.
    """

    STATE_SCHEMA_VERSION: int
    _STATE_SCHEMA_HASH: str
    _STATE_DYNAMIC_VALUE_FIELDS: tuple[str, ...] = ()
    _STATE_DYNAMIC_BLOCK_PTR_FIELDS: tuple[str, ...] = ()
    _STATE_DYNAMIC_STRUCT_PTR_FIELDS: tuple[str, ...] = ()
    _STATE_DYNAMIC_OBJECT_REF_FIELDS: dict[str, tuple[str, ...]] = {}
    _STATE_HISTORY_FIELD_NAME: str = "_state_step_input_history"
    _STATE_DATACLASS_TYPES: Mapping[str, type] = {}
    _STATE_REBIND_BLOCK_PTR_FIELDS: tuple[str, ...] = ()
    _STATE_REBIND_STRUCT_PTR_FIELDS: tuple[str, ...] = ()

    STATE_META_LOAD_MODE_KEY = "load_mode"
    STATE_LOAD_MODE_RESET_REPLAY = "reset_replay"
    _STATE_TAG = "__kind__"
    _STATE_TAG_BYTES = "bytes"
    _STATE_TAG_BYTEARRAY = "bytearray"
    _STATE_TAG_TUPLE = "tuple"
    _STATE_TAG_DATACLASS = "dataclass"
    _STATE_TAG_BLOCK_PTR = "block_ptr"
    _STATE_TAG_STRUCT_PTR = "struct_ptr"
    _STATE_TAG_OBJECT_REF = "object_ref"

    def save_state(self) -> dict[str, object]:
        return self._state_build_envelope(load_mode=self.STATE_LOAD_MODE_RESET_REPLAY)

    def save_autosave_state(self) -> dict[str, object]:
        return self.save_state()

    def _state_build_envelope(self, *, load_mode: str) -> dict[str, object]:
        payload_values: dict[str, object] = {}
        for field_name in self._STATE_DYNAMIC_VALUE_FIELDS:
            self._state_require_manifest_attr(field_name, section="dynamic_values")
            payload_values[field_name] = self._state_encode_json_value(getattr(self, field_name))

        payload_block_ptrs: dict[str, object] = {}
        for field_name in self._STATE_DYNAMIC_BLOCK_PTR_FIELDS:
            self._state_require_manifest_attr(field_name, section="dynamic_block_ptrs")
            payload_block_ptrs[field_name] = self._state_encode_block_ptr(getattr(self, field_name))

        payload_struct_ptrs: dict[str, object] = {}
        for field_name in self._STATE_DYNAMIC_STRUCT_PTR_FIELDS:
            self._state_require_manifest_attr(field_name, section="dynamic_struct_ptrs")
            payload_struct_ptrs[field_name] = self._state_encode_struct_ptr(getattr(self, field_name))

        payload_object_refs: dict[str, object] = {}
        for field_name, allowed_targets in self._STATE_DYNAMIC_OBJECT_REF_FIELDS.items():
            self._state_require_manifest_attr(field_name, section="dynamic_object_refs")
            payload_object_refs[field_name] = self._state_encode_object_ref(
                getattr(self, field_name),
                allowed_targets=allowed_targets,
            )

        payload = {
            "values": payload_values,
            "block_ptrs": payload_block_ptrs,
            "struct_ptrs": payload_struct_ptrs,
            "object_refs": payload_object_refs,
        }
        frame_counter = int(getattr(self, "frame_counter", 0)) & 0xFFFFFFFF
        meta = {
            "frame_counter": frame_counter,
            "host_frame_index": frame_counter,
            self.STATE_META_LOAD_MODE_KEY: load_mode,
        }
        return build_state_envelope(
            runtime_id=runtime_id_for(self),
            schema_version=self.STATE_SCHEMA_VERSION,
            schema_hash=self._STATE_SCHEMA_HASH,
            payload=payload,
            meta=meta,
        )

    def _state_require_manifest_attr(self, field_name: str, *, section: str) -> None:
        if hasattr(self, field_name):
            return
        raise ValueError(
            f"State manifest mismatch in {section}: missing runtime field {field_name!r}",
        )

    def load_state(self, state: Mapping[str, object]) -> None:
        envelope = validate_state_envelope(dict(state))
        runtime_id = runtime_id_for(self)
        state_runtime_id = envelope["runtime_id"]
        accepted_runtime_ids = {runtime_id}
        aliases = getattr(self, "STATE_RUNTIME_ID_ALIASES", ())
        if isinstance(aliases, tuple):
            accepted_runtime_ids.update(
                alias for alias in aliases if isinstance(alias, str) and alias
            )
        if state_runtime_id not in accepted_runtime_ids:
            raise ValueError(
                "State runtime_id mismatch: "
                f"got {state_runtime_id!r}, expected one of {sorted(accepted_runtime_ids)!r}",
            )
        state_schema_version = envelope["schema_version"]
        if int(state_schema_version) != self.STATE_SCHEMA_VERSION:
            raise ValueError(
                "State schema_version mismatch: "
                f"got {state_schema_version}, expected {self.STATE_SCHEMA_VERSION}",
            )
        state_schema_hash = envelope["schema_hash"]
        if state_schema_hash != self._STATE_SCHEMA_HASH:
            raise ValueError(
                f"State schema_hash mismatch: got {state_schema_hash!r}, expected {self._STATE_SCHEMA_HASH!r}",
            )

        meta = envelope["meta"]
        if not isinstance(meta, dict):
            raise ValueError("State meta must be an object")
        load_mode = meta.get(self.STATE_META_LOAD_MODE_KEY, self.STATE_LOAD_MODE_RESET_REPLAY)
        if not isinstance(load_mode, str):
            raise ValueError("State meta.load_mode must be a string")
        if load_mode != self.STATE_LOAD_MODE_RESET_REPLAY:
            raise ValueError(f"Unsupported state load_mode: {load_mode!r}")

        payload = envelope["payload"]
        if not isinstance(payload, dict):
            raise ValueError("State payload must be an object")

        values = payload.get("values", {})
        block_ptrs = payload.get("block_ptrs", {})
        struct_ptrs = payload.get("struct_ptrs", {})
        object_refs = payload.get("object_refs", {})
        if not isinstance(values, dict):
            raise ValueError("State payload.values must be an object")
        if not isinstance(block_ptrs, dict):
            raise ValueError("State payload.block_ptrs must be an object")
        if not isinstance(struct_ptrs, dict):
            raise ValueError("State payload.struct_ptrs must be an object")
        if not isinstance(object_refs, dict):
            raise ValueError("State payload.object_refs must be an object")

        self.reset()
        self._state_apply_payload_values(
            values=values,
            block_ptrs=block_ptrs,
            struct_ptrs=struct_ptrs,
            object_refs=object_refs,
        )
        self._state_clear_history_buffer()
        self._state_validate_rebind_pointer_fields()
        self._state_reset_transient_runtime_state()

    def _state_clear_history_buffer(self) -> None:
        if hasattr(self, self._STATE_HISTORY_FIELD_NAME):
            setattr(self, self._STATE_HISTORY_FIELD_NAME, [])

    @staticmethod
    def _state_attr_priority(attr_name: str) -> tuple[int, str]:
        if attr_name.startswith("var_"):
            return (0, attr_name)
        if attr_name.startswith("str_"):
            return (1, attr_name)
        if attr_name.startswith("const_"):
            return (2, attr_name)
        if attr_name.startswith("patch_"):
            return (3, attr_name)
        if attr_name.startswith("_"):
            return (4, attr_name)
        return (5, attr_name)

    def _state_find_attr_name_for_object(
        self,
        obj: object,
        *,
        allowed_attrs: tuple[str, ...] | None = None,
    ) -> str:
        candidates = []
        names = allowed_attrs if allowed_attrs is not None else tuple(vars(self).keys())
        for name in names:
            if name not in vars(self):
                continue
            if vars(self)[name] is obj:
                candidates.append(name)
        if not candidates:
            raise ValueError(f"Unable to resolve state object reference for {type(obj)!r}")
        candidates.sort(key=self._state_attr_priority)
        return candidates[0]

    def _state_is_block_ptr(self, value: object) -> bool:
        return isinstance(value, BlockPtr)

    def _state_is_struct_ptr(self, value: object) -> bool:
        return isinstance(value, StructFieldPtr)

    def _state_encode_block_ptr(self, ptr: object) -> dict[str, object]:
        if not self._state_is_block_ptr(ptr):
            raise TypeError(f"State value is not BlockPtr: {type(ptr)!r}")
        ptr_any = ptr
        target_attr = self._state_find_attr_name_for_object(ptr_any.array)
        return {
            self._STATE_TAG: self._STATE_TAG_BLOCK_PTR,
            "target_attr": target_attr,
            "index": int(ptr_any.index),
        }

    def _state_decode_block_ptr(self, encoded: object) -> object:
        if not isinstance(encoded, dict) or encoded.get(self._STATE_TAG) != self._STATE_TAG_BLOCK_PTR:
            raise ValueError("Invalid block_ptr state payload")
        target_attr = encoded.get("target_attr")
        index = encoded.get("index")
        if not isinstance(target_attr, str):
            raise ValueError("block_ptr.target_attr must be a string")
        if not isinstance(index, int):
            raise ValueError("block_ptr.index must be an integer")
        if not hasattr(self, target_attr):
            raise ValueError(f"Unknown block_ptr target_attr: {target_attr}")
        array = getattr(self, target_attr)
        if not isinstance(array, (bytes, bytearray)):
            raise ValueError(
                f"block_ptr target_attr {target_attr} does not reference bytes/bytearray",
            )
        return BlockPtr(array=array, index=index)

    def _state_encode_struct_ptr(self, ptr: object) -> dict[str, object]:
        if not self._state_is_struct_ptr(ptr):
            raise TypeError(f"State value is not StructFieldPtr: {type(ptr)!r}")
        ptr_any = ptr
        root_attr = self._state_find_attr_name_for_object(ptr_any.root)
        return {
            self._STATE_TAG: self._STATE_TAG_STRUCT_PTR,
            "root_attr": root_attr,
            "path": [step for step in ptr_any.path],
        }

    def _state_decode_struct_ptr(self, encoded: object) -> object:
        if not isinstance(encoded, dict) or encoded.get(self._STATE_TAG) != self._STATE_TAG_STRUCT_PTR:
            raise ValueError("Invalid struct_ptr state payload")
        root_attr = encoded.get("root_attr")
        path = encoded.get("path")
        if not isinstance(root_attr, str):
            raise ValueError("struct_ptr.root_attr must be a string")
        if not isinstance(path, list):
            raise ValueError("struct_ptr.path must be a list")
        if not hasattr(self, root_attr):
            raise ValueError(f"Unknown struct_ptr root_attr: {root_attr}")
        path_tuple: list[int | str] = []
        for step in path:
            if not isinstance(step, (int, str)):
                raise ValueError("struct_ptr.path entries must be int or str")
            path_tuple.append(step)
        return StructFieldPtr(root=getattr(self, root_attr), path=tuple(path_tuple))

    def _state_encode_object_ref(
        self,
        obj: object,
        *,
        allowed_targets: tuple[str, ...],
    ) -> dict[str, object]:
        target_attr = self._state_find_attr_name_for_object(obj, allowed_attrs=allowed_targets)
        return {
            self._STATE_TAG: self._STATE_TAG_OBJECT_REF,
            "target_attr": target_attr,
        }

    def _state_decode_object_ref(
        self,
        encoded: object,
        *,
        allowed_targets: tuple[str, ...],
    ) -> object:
        if not isinstance(encoded, dict) or encoded.get(self._STATE_TAG) != self._STATE_TAG_OBJECT_REF:
            raise ValueError("Invalid object_ref state payload")
        target_attr = encoded.get("target_attr")
        if not isinstance(target_attr, str):
            raise ValueError("object_ref.target_attr must be a string")
        if target_attr not in allowed_targets:
            raise ValueError(
                f"object_ref target_attr {target_attr!r} is not allowed for this field",
            )
        if not hasattr(self, target_attr):
            raise ValueError(f"Unknown object_ref target_attr: {target_attr}")
        return getattr(self, target_attr)

    # Generic codec for scalar/bytes/containers/dataclasses.
    def _state_encode_json_value(self, value: object) -> object:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, bytes):
            return {self._STATE_TAG: self._STATE_TAG_BYTES, "hex": value.hex()}
        if isinstance(value, bytearray):
            return {self._STATE_TAG: self._STATE_TAG_BYTEARRAY, "hex": bytes(value).hex()}
        if self._state_is_block_ptr(value):
            return self._state_encode_block_ptr(value)
        if self._state_is_struct_ptr(value):
            return self._state_encode_struct_ptr(value)
        if isinstance(value, list):
            return [self._state_encode_json_value(item) for item in value]
        if isinstance(value, tuple):
            return {
                self._STATE_TAG: self._STATE_TAG_TUPLE,
                "items": [self._state_encode_json_value(item) for item in value],
            }
        if isinstance(value, dict):
            out: dict[str, object] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError(f"State dict keys must be strings, got {type(key)!r}")
                out[key] = self._state_encode_json_value(item)
            return out
        if is_dataclass(value):
            return {
                self._STATE_TAG: self._STATE_TAG_DATACLASS,
                "name": type(value).__name__,
                "fields": {
                    field.name: self._state_encode_json_value(getattr(value, field.name))
                    for field in fields(value)
                },
            }
        raise TypeError(f"Unsupported state value type: {type(value)!r}")

    def _state_decode_json_value(self, encoded: object, *, target: object | None) -> object:
        if isinstance(encoded, dict):
            kind = encoded.get(self._STATE_TAG)
            if kind == self._STATE_TAG_BYTES:
                payload_hex = encoded.get("hex")
                if not isinstance(payload_hex, str):
                    raise ValueError("bytes payload must contain hex string")
                return bytes.fromhex(payload_hex)
            if kind == self._STATE_TAG_BYTEARRAY:
                payload_hex = encoded.get("hex")
                if not isinstance(payload_hex, str):
                    raise ValueError("bytearray payload must contain hex string")
                payload = bytes.fromhex(payload_hex)
                if isinstance(target, bytearray):
                    target[:] = payload
                    return target
                return bytearray(payload)
            if kind == self._STATE_TAG_TUPLE:
                raw_items = encoded.get("items")
                if not isinstance(raw_items, list):
                    raise ValueError("tuple payload must contain items array")
                target_items = target if isinstance(target, tuple) else ()
                decoded_items = []
                for i, item in enumerate(raw_items):
                    item_target = target_items[i] if i < len(target_items) else None
                    decoded_items.append(self._state_decode_json_value(item, target=item_target))
                return tuple(decoded_items)
            if kind == self._STATE_TAG_DATACLASS:
                class_name = encoded.get("name")
                raw_fields = encoded.get("fields")
                if not isinstance(class_name, str):
                    raise ValueError("dataclass payload must contain class name")
                if not isinstance(raw_fields, dict):
                    raise ValueError("dataclass payload must contain fields object")
                if is_dataclass(target):
                    for field in fields(target):
                        if field.name not in raw_fields:
                            continue
                        setattr(
                            target,
                            field.name,
                            self._state_decode_json_value(
                                raw_fields[field.name],
                                target=getattr(target, field.name),
                            ),
                        )
                    return target
                cls = self._STATE_DATACLASS_TYPES.get(class_name)
                if cls is None:
                    raise ValueError(f"Unsupported dataclass in state payload: {class_name}")
                kwargs = {
                    key: self._state_decode_json_value(value, target=None)
                    for key, value in raw_fields.items()
                }
                return cls(**kwargs)
            if kind == self._STATE_TAG_BLOCK_PTR:
                return self._state_decode_block_ptr(encoded)
            if kind == self._STATE_TAG_STRUCT_PTR:
                return self._state_decode_struct_ptr(encoded)
            if kind == self._STATE_TAG_OBJECT_REF:
                # Object refs are decoded by field-specific handlers.
                return encoded
            if target is not None and isinstance(target, dict):
                target.clear()
                for key, value in encoded.items():
                    if not isinstance(key, str):
                        raise ValueError("State object keys must be strings")
                    target[key] = self._state_decode_json_value(value, target=None)
                return target
            return {
                str(key): self._state_decode_json_value(value, target=None)
                for key, value in encoded.items()
            }

        if isinstance(encoded, list):
            if isinstance(target, list):
                if len(target) == len(encoded):
                    for i, value in enumerate(encoded):
                        target[i] = self._state_decode_json_value(value, target=target[i])
                else:
                    target[:] = [
                        self._state_decode_json_value(value, target=None)
                        for value in encoded
                    ]
                return target
            return [self._state_decode_json_value(value, target=None) for value in encoded]

        if isinstance(target, bytearray):
            raise ValueError("Expected encoded bytearray payload for bytearray target")
        if isinstance(target, bytes):
            raise ValueError("Expected encoded bytes payload for bytes target")
        return encoded

    def _state_apply_payload_values(
        self,
        *,
        values: Mapping[str, object],
        block_ptrs: Mapping[str, object],
        struct_ptrs: Mapping[str, object],
        object_refs: Mapping[str, object],
    ) -> None:
        for field_name in self._STATE_DYNAMIC_VALUE_FIELDS:
            if field_name not in values:
                continue
            current = getattr(self, field_name, None)
            decoded = self._state_decode_json_value(values[field_name], target=current)
            setattr(self, field_name, decoded)

        for field_name in self._STATE_DYNAMIC_BLOCK_PTR_FIELDS:
            if field_name not in block_ptrs:
                continue
            setattr(self, field_name, self._state_decode_block_ptr(block_ptrs[field_name]))

        for field_name in self._STATE_DYNAMIC_STRUCT_PTR_FIELDS:
            if field_name not in struct_ptrs:
                continue
            setattr(self, field_name, self._state_decode_struct_ptr(struct_ptrs[field_name]))

        for field_name, allowed_targets in self._STATE_DYNAMIC_OBJECT_REF_FIELDS.items():
            if field_name not in object_refs:
                continue
            setattr(
                self,
                field_name,
                self._state_decode_object_ref(
                    object_refs[field_name],
                    allowed_targets=allowed_targets,
                ),
            )

    def _state_validate_rebind_pointer_fields(self) -> None:
        for field_name in self._STATE_REBIND_BLOCK_PTR_FIELDS:
            if not hasattr(self, field_name):
                raise ValueError(f"Missing rebind BlockPtr field after load: {field_name}")
            value = getattr(self, field_name)
            if not isinstance(value, BlockPtr):
                raise ValueError(f"Rebind field {field_name} is not BlockPtr: {type(value)!r}")

        for field_name in self._STATE_REBIND_STRUCT_PTR_FIELDS:
            if not hasattr(self, field_name):
                raise ValueError(f"Missing rebind StructFieldPtr field after load: {field_name}")
            value = getattr(self, field_name)
            if not isinstance(value, StructFieldPtr):
                raise ValueError(
                    f"Rebind field {field_name} is not StructFieldPtr: {type(value)!r}",
                )

    def _state_reset_transient_runtime_state(self) -> None:
        return


def runtime_id_for(instance: object) -> str:
    cls = type(instance)
    return f"{cls.__module__}.{cls.__qualname__}"


def compute_schema_hash(*, schema_version: int, manifest: object, codec_version: int = 1) -> str:
    payload = {
        "schema_version": int(schema_version),
        "codec_version": int(codec_version),
        "manifest": manifest,
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def build_state_envelope(
    *,
    runtime_id: str,
    schema_version: int,
    schema_hash: str,
    payload: object,
    meta: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "format": STATE_ENVELOPE_FORMAT_V1,
        "runtime_id": runtime_id,
        "schema_version": int(schema_version),
        "schema_hash": str(schema_hash),
        "payload": payload,
        "meta": dict(meta or {}),
    }


def validate_state_envelope(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise StateEnvelopeError("State envelope must be a JSON object")

    required = ("format", "runtime_id", "schema_version", "schema_hash", "payload", "meta")
    for key in required:
        if key not in raw:
            raise StateEnvelopeError(f"State envelope is missing required field: {key}")

    format_name = raw["format"]
    if format_name != STATE_ENVELOPE_FORMAT_V1:
        raise StateEnvelopeError(
            f"Unsupported state format: {format_name!r}; expected {STATE_ENVELOPE_FORMAT_V1!r}",
        )

    runtime_id = raw["runtime_id"]
    if not isinstance(runtime_id, str) or not runtime_id:
        raise StateEnvelopeError("State envelope field runtime_id must be a non-empty string")

    schema_version = raw["schema_version"]
    if not isinstance(schema_version, int):
        raise StateEnvelopeError("State envelope field schema_version must be an integer")

    schema_hash = raw["schema_hash"]
    if not isinstance(schema_hash, str) or not schema_hash:
        raise StateEnvelopeError("State envelope field schema_hash must be a non-empty string")

    meta = raw["meta"]
    if not isinstance(meta, dict):
        raise StateEnvelopeError("State envelope field meta must be a JSON object")

    return raw


def ensure_stateful_runtime(runtime: object) -> StatefulRuntime:
    save_state = getattr(runtime, "save_state", None)
    load_state = getattr(runtime, "load_state", None)
    if not callable(save_state) or not callable(load_state):
        raise TypeError(
            f"Runtime {type(runtime).__name__} does not implement save_state/load_state",
        )
    return runtime  # type: ignore[return-value]
