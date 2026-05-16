import copy
import hashlib
import json
import math
import os
import string
from collections import Counter
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, NamedTuple, cast

import numpy as np
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

# --- Configuration ---
CONFIDENCE_THRESHOLD = 0.92  # High bar for "Fail-Closed"
DOMAIN_WHITELIST = ["financial", "industrial", "audit"]
GENESIS_HASH = "0" * 64
MAX_GOVERNANCE_PAYLOAD_BYTES = 1_000_000
MAX_GOVERNANCE_DEPTH = 20
MAX_LEDGER_BYTES = 10_000_000
MAX_AUDIT_BYTES = 2_000_000
MAX_GOVERNANCE_OBJECTS = 10_000
MAX_GOVERNANCE_STRING_BYTES = 16_384
MAX_GOVERNANCE_CONTAINER_ITEMS = 2_000
MAX_UNSAFE_TOTAL = 12.0
MAX_QUERY_BYTES = 16_384
AUDIT_EVENT_BYTES = 4_096
FORBIDDEN_AUDIT_KEYS = {"payload", "query", "context", "raw_query", "prompt", "input"}
AUDIT_FIELD_ALLOWLIST = {
    "policy_denial": {"category", "code", "decision", "input_hash", "receipt_id"},
    "runtime_failure": {"category", "code", "detail"},
}


class GovernanceErrorPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    code: str
    detail: str


class GovernanceRuntimeError(Exception):
    category: ClassVar[str] = "runtime"
    code: ClassVar[str] = "GOVERNANCE_RUNTIME_ERROR"

    def __init__(self, detail: str, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.error_code = code or self.code

    def payload(self) -> dict[str, str]:
        return GovernanceErrorPayload(
            category=self.category, code=self.error_code, detail=self.detail
        ).model_dump()


class ExternalDependencyError(GovernanceRuntimeError):
    category: ClassVar[str] = "external_dependency"
    code: ClassVar[str] = "EXTERNAL_DEPENDENCY_ERROR"


class SerializationError(GovernanceRuntimeError):
    category: ClassVar[str] = "serialization"
    code: ClassVar[str] = "SERIALIZATION_ERROR"


class CanonicalizationError(GovernanceRuntimeError):
    category: ClassVar[str] = "canonicalization"
    code: ClassVar[str] = "CANONICALIZATION_ERROR"


class ResourceLimitError(GovernanceRuntimeError):
    category: ClassVar[str] = "resource_limit"
    code: ClassVar[str] = "RESOURCE_LIMIT_ERROR"


class LexicalPolicyError(GovernanceRuntimeError):
    category: ClassVar[str] = "lexical_policy"
    code: ClassVar[str] = "LEXICAL_POLICY_ERROR"


class GovernanceDecision(str, Enum):
    EXECUTE = "EXECUTE"
    HALT = "HALT"


class LexicalReasoning(BaseModel):
    model_config = ConfigDict(frozen=True)

    unsafe_terms: list[str]
    anomaly_flags: list[str]
    score_breakdown: dict[str, float]


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    context: str
    domain: str
    timestamp: float = 0.0

    @field_validator("domain")
    @classmethod
    def domain_must_be_whitelisted(cls, v: str) -> str:
        if v not in DOMAIN_WHITELIST:
            raise ValueError(f"Domain '{v}' not in whitelist: {DOMAIN_WHITELIST}")
        return v

    @field_validator("query", "context")
    @classmethod
    def text_fields_are_bounded(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_QUERY_BYTES:
            raise ValueError("text field byte ceiling exceeded")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("timestamp must be finite")
        return _normalize_float(v, 6)


class DecisionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int
    receipt_id: str
    input_hash: str
    previous_hash: str
    confidence_score: float
    decision: GovernanceDecision
    timestamp: float
    reasoning: LexicalReasoning

    @field_validator("confidence_score")
    @classmethod
    def confidence_must_be_quantized(cls, v: float) -> float:
        return _normalize_float(v, 8)

    @field_validator("timestamp")
    @classmethod
    def receipt_timestamp_must_be_quantized(cls, v: float) -> float:
        return _normalize_float(v, 6)


class ReplayValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    valid: bool
    last_hash: str
    next_sequence: int
    receipts: list[DecisionReceipt]
    ledger_size: int = 0


class LexicalFeatures(NamedTuple):
    logits: np.ndarray
    reasoning: LexicalReasoning


def softmax(logits: np.ndarray) -> np.ndarray:
    """Compute a numerically stable softmax without external dependencies."""
    shifted = logits - np.max(logits)
    exp_values = np.exp(shifted)
    return cast(np.ndarray, exp_values / np.sum(exp_values))


def _canonical_json(data: Any) -> str:
    try:
        return json.dumps(data, sort_keys=True, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError, RecursionError) as exc:
        raise SerializationError(str(exc), code="NON_CANONICAL_JSON") from exc


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_hash(data: Any) -> str:
    return _sha256_text(_canonical_json(data))


def _normalize_float(value: float, places: int) -> float:
    if not math.isfinite(value):
        raise SerializationError("non-finite float rejected", code="NON_FINITE_FLOAT")
    return round(float(value), places)


def _max_depth(value: Any, depth: int = 0, seen: set[int] | None = None) -> int:
    if seen is None:
        seen = set()
    if depth > MAX_GOVERNANCE_DEPTH:
        return depth
    if isinstance(value, dict):
        object_id = id(value)
        if object_id in seen:
            return MAX_GOVERNANCE_DEPTH + 1
        seen.add(object_id)
        child_depth = max(
            (_max_depth(child, depth + 1, seen) for child in value.values()), default=depth
        )
        seen.remove(object_id)
        return child_depth
    if isinstance(value, (list, tuple, set)):
        object_id = id(value)
        if object_id in seen:
            return MAX_GOVERNANCE_DEPTH + 1
        seen.add(object_id)
        child_depth = max((_max_depth(child, depth + 1, seen) for child in value), default=depth)
        seen.remove(object_id)
        return child_depth
    return depth


def _bounded_payload_walk(
    value: Any, depth: int = 0, seen: set[int] | None = None, count: list[int] | None = None
) -> None:
    if seen is None:
        seen = set()
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > MAX_GOVERNANCE_OBJECTS:
        raise ResourceLimitError("payload object ceiling exceeded", code="PAYLOAD_OBJECT_LIMIT")
    if depth > MAX_GOVERNANCE_DEPTH:
        raise ResourceLimitError("payload nesting depth exceeded", code="PAYLOAD_NESTING_DEPTH")
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_GOVERNANCE_STRING_BYTES:
            raise ResourceLimitError(
                "payload string byte ceiling exceeded", code="PAYLOAD_STRING_TOO_LARGE"
            )
        return
    if isinstance(value, (int, bool)) or value is None:
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SerializationError("non-finite float rejected", code="NON_FINITE_FLOAT")
        return
    if isinstance(value, dict):
        object_id = id(value)
        if object_id in seen:
            raise ResourceLimitError("payload cycle rejected", code="PAYLOAD_CYCLE")
        if len(value) > MAX_GOVERNANCE_CONTAINER_ITEMS:
            raise ResourceLimitError(
                "payload container fanout exceeded", code="PAYLOAD_FANOUT_LIMIT"
            )
        seen.add(object_id)
        for key, child in value.items():
            if not isinstance(key, str):
                raise SerializationError(
                    "payload object keys must be strings", code="PAYLOAD_KEY_TYPE"
                )
            _bounded_payload_walk(key, depth + 1, seen, count)
            _bounded_payload_walk(child, depth + 1, seen, count)
        seen.remove(object_id)
        return
    if isinstance(value, (list, tuple, set)):
        object_id = id(value)
        if object_id in seen:
            raise ResourceLimitError("payload cycle rejected", code="PAYLOAD_CYCLE")
        if len(value) > MAX_GOVERNANCE_CONTAINER_ITEMS:
            raise ResourceLimitError(
                "payload container fanout exceeded", code="PAYLOAD_FANOUT_LIMIT"
            )
        seen.add(object_id)
        for child in value:
            _bounded_payload_walk(child, depth + 1, seen, count)
        seen.remove(object_id)
        return
    raise SerializationError("payload contains non-JSON value", code="PAYLOAD_NON_JSON_VALUE")


def _immutable_payload_copy(payload: dict[str, Any]) -> dict[str, Any]:
    _bounded_payload_walk(payload)
    if _max_depth(payload) > MAX_GOVERNANCE_DEPTH:
        raise ResourceLimitError("payload nesting depth exceeded", code="PAYLOAD_NESTING_DEPTH")
    canonical = _canonical_json(payload)
    size = len(canonical.encode("utf-8"))
    if size > MAX_GOVERNANCE_PAYLOAD_BYTES:
        raise ResourceLimitError("payload byte ceiling exceeded", code="PAYLOAD_TOO_LARGE")
    try:
        copied = json.loads(canonical)
    except json.JSONDecodeError as exc:
        raise SerializationError(str(exc), code="CANONICAL_ROUNDTRIP_FAILED") from exc
    if not isinstance(copied, dict):
        raise SerializationError("payload root must be object", code="PAYLOAD_ROOT_NOT_OBJECT")
    return cast(dict[str, Any], copied)


@contextmanager
def _exclusive_lock(path: Path):
    lock_path = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise GovernanceRuntimeError("append lock already exists", code="APPEND_LOCK_HELD") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _contains_forbidden_audit_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key in FORBIDDEN_AUDIT_KEYS:
                return True
            if _contains_forbidden_audit_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_audit_key(child) for child in value)
    return False


def _validate_audit_event(row: dict[str, Any], expected_sequence: int) -> None:
    event_type = row.get("event_type")
    if not isinstance(event_type, str) or event_type not in AUDIT_FIELD_ALLOWLIST:
        raise GovernanceRuntimeError(
            "audit event type is not allowlisted", code="AUDIT_EVENT_TYPE_INVALID"
        )
    allowed_keys = {"event_type", "sequence"} | AUDIT_FIELD_ALLOWLIST[event_type]
    if set(row) - allowed_keys:
        raise GovernanceRuntimeError(
            "audit row contains non-allowlisted fields", code="AUDIT_FIELD_NOT_ALLOWED"
        )
    if row.get("sequence") != expected_sequence:
        raise GovernanceRuntimeError(
            "audit sequence discontinuity", code="AUDIT_SEQUENCE_DISCONTINUITY"
        )
    if _contains_forbidden_audit_key(row):
        raise GovernanceRuntimeError(
            "audit row contains raw payload", code="AUDIT_RAW_PAYLOAD_REJECTED"
        )
    string_fields = AUDIT_FIELD_ALLOWLIST[event_type]
    if any(not isinstance(row.get(field), str) for field in string_fields):
        raise GovernanceRuntimeError(
            "audit row field type invalid", code="AUDIT_FIELD_TYPE_INVALID"
        )


def _canonical_ledger_path(path: Path) -> Path:
    parent = path.parent
    if not parent.exists() or not parent.is_dir():
        raise CanonicalizationError(
            "ledger parent directory does not exist", code="LEDGER_PARENT_MISSING"
        )
    try:
        raw_parts = [path, parent, *parent.parents]
        if any(part.is_symlink() for part in raw_parts):
            raise CanonicalizationError(
                "ledger path must not traverse symlinks", code="LEDGER_SYMLINK_REJECTED"
            )
        return parent.resolve(strict=True) / path.name
    except CanonicalizationError:
        raise
    except (OSError, RuntimeError) as exc:
        raise CanonicalizationError(str(exc), code="LEDGER_CANONICALIZATION_FAILED") from exc


class ReceiptLedger:
    """Append-only JSONL receipt ledger with deterministic replay validation."""

    def __init__(self, path: Path | str) -> None:
        self.path = _canonical_ledger_path(Path(path))
        self._state = self.validate(self.path)

    @property
    def last_hash(self) -> str:
        return self._state.last_hash

    @property
    def next_sequence(self) -> int:
        return self._state.next_sequence

    @staticmethod
    def receipt_payload(receipt: DecisionReceipt) -> dict[str, Any]:
        return receipt.model_dump(mode="json")

    @staticmethod
    def receipt_hash_payload(payload: dict[str, Any]) -> str:
        hash_payload = dict(payload)
        hash_payload["receipt_id"] = ""
        return _canonical_hash(hash_payload)

    @staticmethod
    def receipt_hash(receipt: DecisionReceipt) -> str:
        return ReceiptLedger.receipt_hash_payload(ReceiptLedger.receipt_payload(receipt))

    @staticmethod
    def row_hash(receipt_payload: dict[str, Any]) -> str:
        return _canonical_hash({"receipt": receipt_payload})

    @classmethod
    def encode_row(cls, receipt: DecisionReceipt) -> str:
        payload = cls.receipt_payload(receipt)
        row = {"receipt": payload, "row_hash": cls.row_hash(payload)}
        return _canonical_json(row)

    @classmethod
    def decode_row(
        cls, line: str, expected_sequence: int, expected_previous: str
    ) -> DecisionReceipt:
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SerializationError(str(exc), code="LEDGER_ROW_MALFORMED_JSON") from exc
        if not isinstance(row, dict) or set(row.keys()) != {"receipt", "row_hash"}:
            raise SerializationError("ledger row schema invalid", code="LEDGER_ROW_SCHEMA_INVALID")
        receipt_payload = row["receipt"]
        if not isinstance(receipt_payload, dict):
            raise SerializationError(
                "ledger receipt payload invalid", code="LEDGER_RECEIPT_SCHEMA_INVALID"
            )
        if _canonical_json(row) != line:
            raise SerializationError("ledger row is not canonical", code="LEDGER_ROW_NON_CANONICAL")
        if row["row_hash"] != cls.row_hash(receipt_payload):
            raise SerializationError("ledger row hash mismatch", code="LEDGER_ROW_HASH_MISMATCH")
        try:
            receipt = DecisionReceipt.model_validate(receipt_payload)
        except ValidationError as exc:
            raise SerializationError(str(exc), code="LEDGER_RECEIPT_SCHEMA_INVALID") from exc
        if receipt.sequence != expected_sequence:
            raise GovernanceRuntimeError(
                "receipt sequence discontinuity", code="LEDGER_SEQUENCE_DISCONTINUITY"
            )
        if receipt.previous_hash != expected_previous:
            raise GovernanceRuntimeError(
                "receipt lineage discontinuity", code="LEDGER_LINEAGE_DISCONTINUITY"
            )
        if receipt.receipt_id != cls.receipt_hash(receipt):
            raise GovernanceRuntimeError(
                "receipt hash mismatch", code="LEDGER_RECEIPT_HASH_MISMATCH"
            )
        return receipt

    @classmethod
    def validate(
        cls, path: Path | str, *, include_receipts: bool = False
    ) -> ReplayValidationResult:
        ledger_path = _canonical_ledger_path(Path(path))
        if not ledger_path.exists():
            return ReplayValidationResult(
                valid=True, last_hash=GENESIS_HASH, next_sequence=0, receipts=[], ledger_size=0
            )
        if not ledger_path.is_file():
            raise CanonicalizationError("ledger path is not a file", code="LEDGER_NOT_FILE")
        ledger_size = ledger_path.stat().st_size
        if ledger_size > MAX_LEDGER_BYTES:
            raise ResourceLimitError("ledger byte ceiling exceeded", code="LEDGER_TOO_LARGE")
        data = ledger_path.read_bytes()
        if data and not data.endswith(b"\n"):
            raise SerializationError("ledger row is truncated", code="LEDGER_TRUNCATED_ROW")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SerializationError(str(exc), code="LEDGER_UTF8_INVALID") from exc
        previous = GENESIS_HASH
        receipts: list[DecisionReceipt] = []
        next_sequence = 0
        for expected_sequence, line in enumerate(text.splitlines()):
            if line == "":
                raise SerializationError("empty ledger row", code="LEDGER_EMPTY_ROW")
            receipt = cls.decode_row(line, expected_sequence, previous)
            if include_receipts:
                receipts.append(receipt)
            previous = receipt.receipt_id
            next_sequence = expected_sequence + 1
        return ReplayValidationResult(
            valid=True,
            last_hash=previous,
            next_sequence=next_sequence,
            receipts=receipts,
            ledger_size=ledger_size,
        )

    def append(self, receipt: DecisionReceipt) -> None:
        encoded = self.encode_row(receipt)
        if receipt.receipt_id != self.receipt_hash(receipt):
            raise GovernanceRuntimeError(
                "receipt hash mismatch", code="LEDGER_APPEND_HASH_MISMATCH"
            )
        with _exclusive_lock(self.path):
            current_size = self.path.stat().st_size if self.path.exists() else 0
            if current_size != self._state.ledger_size:
                self._state = self.validate(self.path)
            if (
                receipt.sequence != self._state.next_sequence
                or receipt.previous_hash != self._state.last_hash
            ):
                raise GovernanceRuntimeError(
                    "receipt does not extend current ledger", code="LEDGER_APPEND_LINEAGE_MISMATCH"
                )
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
            self._state = ReplayValidationResult(
                valid=True,
                last_hash=receipt.receipt_id,
                next_sequence=receipt.sequence + 1,
                receipts=[],
                ledger_size=current_size + len((encoded + "\n").encode("utf-8")),
            )


class DeterministicAuditLog:
    """Append-only redaction-safe governance telemetry log."""

    def __init__(self, path: Path | str) -> None:
        self.path = _canonical_ledger_path(Path(path))
        self._next_sequence = self.validate(self.path)

    @classmethod
    def validate(cls, path: Path | str) -> int:
        audit_path = _canonical_ledger_path(Path(path))
        if not audit_path.exists():
            return 0
        if not audit_path.is_file():
            raise CanonicalizationError("audit path is not a file", code="AUDIT_NOT_FILE")
        if audit_path.stat().st_size > MAX_AUDIT_BYTES:
            raise ResourceLimitError("audit log byte ceiling exceeded", code="AUDIT_TOO_LARGE")
        data = audit_path.read_bytes()
        if data and not data.endswith(b"\n"):
            raise SerializationError("audit row is truncated", code="AUDIT_TRUNCATED_ROW")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SerializationError(str(exc), code="AUDIT_UTF8_INVALID") from exc
        for expected_sequence, line in enumerate(text.splitlines()):
            if not line:
                raise SerializationError("empty audit row", code="AUDIT_EMPTY_ROW")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SerializationError(str(exc), code="AUDIT_ROW_MALFORMED_JSON") from exc
            if _canonical_json(row) != line:
                raise SerializationError(
                    "audit row is not canonical", code="AUDIT_ROW_NON_CANONICAL"
                )
            if not isinstance(row, dict):
                raise SerializationError(
                    "audit row schema invalid", code="AUDIT_ROW_SCHEMA_INVALID"
                )
            _validate_audit_event(row, expected_sequence)
        return len(text.splitlines())

    def append(self, event_type: str, fields: dict[str, Any]) -> None:
        event = {"event_type": event_type, "sequence": self._next_sequence, **fields}
        _validate_audit_event(event, self._next_sequence)
        encoded = _canonical_json(event)
        if len(encoded.encode("utf-8")) > AUDIT_EVENT_BYTES:
            raise ResourceLimitError(
                "audit event byte ceiling exceeded", code="AUDIT_EVENT_TOO_LARGE"
            )
        with _exclusive_lock(self.path):
            self._next_sequence = self.validate(self.path)
            event["sequence"] = self._next_sequence
            _validate_audit_event(event, self._next_sequence)
            encoded = _canonical_json(event)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
            self._next_sequence += 1


class GuardrailEngine:
    def __init__(
        self, ledger_path: Path | str | None = None, audit_log_path: Path | str | None = None
    ) -> None:
        self._ledger = ReceiptLedger(ledger_path) if ledger_path is not None else None
        self._audit_log = (
            DeterministicAuditLog(audit_log_path) if audit_log_path is not None else None
        )
        self._last_hash = self._ledger.last_hash if self._ledger is not None else GENESIS_HASH
        self._next_sequence = self._ledger.next_sequence if self._ledger is not None else 0
        self._last_reasoning = LexicalReasoning(
            unsafe_terms=[], anomaly_flags=[], score_breakdown={}
        )

    def _compute_hash(self, data: dict[str, Any]) -> str:
        """Structural hashing of dictionary content."""
        return _canonical_hash(data)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens: list[str] = []
        current: list[str] = []
        for char in text.lower().replace("_", " "):
            if char.isalnum() or char in {"-", "/", "=", "+"}:
                current.append(char)
            elif current:
                tokens.append("".join(current))
                current = []
        if current:
            tokens.append("".join(current))
        return tokens

    def _extract_lexical_features(self, text: str) -> LexicalFeatures:
        tokens = self._tokenize(text)
        token_count = max(len(tokens), 1)
        unique_ratio = len(set(tokens)) / token_count
        digit_ratio = sum(ch.isdigit() for ch in text) / max(len(text), 1)
        punctuation_count = sum(char in string.punctuation for char in text)
        punctuation_ratio = punctuation_count / max(len(text), 1)
        token_counts = Counter(tokens)

        safe_terms = {
            "audit": 1.2,
            "calculate": 1.1,
            "liquidity": 1.0,
            "validate": 1.3,
            "reconcile": 1.3,
            "report": 0.8,
        }
        unsafe_terms = {
            "bypass": 3.0,
            "exploit": 4.0,
            "exfiltrate": 4.5,
            "disable": 2.5,
            "weaponize": 4.0,
            "malware": 4.5,
            "credentials": 3.0,
            "credential": 2.0,
        }
        ambiguous_terms = {"maybe", "guess", "unknown", "private", "secret", "credential"}
        unsafe_phrases = [
            ("disable", "audit"),
            ("bypass", "policy"),
            ("exfiltrate", "credentials"),
            ("exploit", "credentials"),
        ]

        safe_score = sum(safe_terms.get(token, 0.0) for token in tokens)
        unsafe_score = sum(unsafe_terms.get(token, 0.0) for token in tokens)
        ambiguous_score = sum(1.0 for token in tokens if token in ambiguous_terms)
        phrase_hits = 0
        token_pairs = set(zip(tokens, tokens[1:], strict=False))
        for phrase in unsafe_phrases:
            if phrase in token_pairs:
                phrase_hits += 1
        repetition_score = sum(max(count - 2, 0) for count in token_counts.values())
        long_token_score = sum(1 for token in tokens if len(token) > 48)
        encoding_score = sum(
            text.lower().count(marker) for marker in ("%2f", "%5c", "base64", "==", "0x")
        )
        punctuation_flood = 1 if punctuation_count >= 10 or punctuation_ratio > 0.45 else 0
        entropy_anomaly = 1 if unique_ratio < 0.35 and token_count >= 6 else 0

        anomaly_flags: list[str] = []
        if repetition_score:
            anomaly_flags.append("repetition_amplification")
        if long_token_score:
            anomaly_flags.append("long_token")
        if punctuation_flood:
            anomaly_flags.append("punctuation_flood")
        if encoding_score:
            anomaly_flags.append("suspicious_encoding")
        if entropy_anomaly:
            anomaly_flags.append("low_token_entropy")
        if phrase_hits:
            anomaly_flags.append("unsafe_phrase")
        if unsafe_score and safe_score:
            anomaly_flags.append("mixed_safe_unsafe_dominance")

        unsafe_total = min(
            unsafe_score + (2.0 * phrase_hits) + (0.7 * repetition_score) + encoding_score,
            MAX_UNSAFE_TOTAL,
        )
        anomaly_total = (
            ambiguous_score
            + (4.0 * punctuation_ratio)
            + (0.6 * long_token_score)
            + (1.2 * punctuation_flood)
            + (0.6 * entropy_anomaly)
        )
        unsafe_terms_found = sorted({token for token in tokens if token in unsafe_terms})
        score_breakdown = {
            "safe_terms": round(safe_score, 6),
            "unsafe_terms": round(unsafe_score, 6),
            "ambiguous_terms": round(ambiguous_score, 6),
            "unsafe_phrases": float(phrase_hits),
            "repetition": round(float(repetition_score), 6),
            "digit_ratio": round(digit_ratio, 6),
            "punctuation_ratio": round(punctuation_ratio, 6),
            "encoding_patterns": float(encoding_score),
            "long_tokens": float(long_token_score),
        }
        reasoning = LexicalReasoning(
            unsafe_terms=unsafe_terms_found,
            anomaly_flags=sorted(anomaly_flags),
            score_breakdown=score_breakdown,
        )
        safe_logit = 0.25 + safe_score + (0.4 * unique_ratio)
        ambiguous_logit = 0.1 + anomaly_total + abs(token_count - 8) / 20
        unsafe_logit = -0.3 + unsafe_total + (0.8 * ambiguous_score) + (2.0 * digit_ratio)
        if unsafe_total > 0:
            safe_logit -= 3.0 + unsafe_total
            ambiguous_logit += 1.0
        return LexicalFeatures(
            np.array([safe_logit, ambiguous_logit, unsafe_logit], dtype=float), reasoning
        )

    def _deterministic_inference_logits(self, text: str) -> np.ndarray:
        """Return deterministic safety logits derived from auditable text features."""
        features = self._extract_lexical_features(text)
        self._last_reasoning = features.reasoning
        return features.logits

    def _build_receipt(
        self,
        clean_input: InputSchema,
        confidence: float,
        decision: GovernanceDecision,
        reasoning: LexicalReasoning,
    ) -> DecisionReceipt:
        input_hash = self._compute_hash(clean_input.model_dump())
        payload = {
            "sequence": self._next_sequence,
            "receipt_id": "",
            "input_hash": input_hash,
            "previous_hash": self._last_hash,
            "confidence_score": _normalize_float(confidence, 8),
            "decision": decision,
            "timestamp": _normalize_float(clean_input.timestamp, 6),
            "reasoning": reasoning,
        }
        receipt_id = ReceiptLedger.receipt_hash_payload(
            DecisionReceipt.model_validate(payload).model_dump(mode="json")
        )
        payload["receipt_id"] = receipt_id
        return DecisionReceipt.model_validate(payload)

    def _emit_receipt(self, receipt: DecisionReceipt) -> None:
        if self._ledger is not None:
            self._ledger.append(receipt)
            self._last_hash = self._ledger.last_hash
            self._next_sequence = self._ledger.next_sequence
            return
        self._last_hash = receipt.receipt_id
        self._next_sequence += 1

    def _audit(self, event_type: str, fields: dict[str, Any]) -> None:
        if self._audit_log is None:
            return
        self._audit_log.append(event_type, fields)

    def _halt_for_error(self, error: GovernanceRuntimeError) -> dict[str, Any]:
        self._audit("runtime_failure", error.payload())
        return {"status": GovernanceDecision.HALT.value, "error": error.payload()}

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Main execution gate with explicit fail-closed policy outcomes."""
        try:
            stable_payload = _immutable_payload_copy(payload)
            clean_input = InputSchema.model_validate(copy.deepcopy(stable_payload))
        except ValidationError as exc:
            error = GovernanceRuntimeError(
                f"Schema Validation Failed: {str(exc)}", code="SCHEMA_VALIDATION_FAILED"
            )
            self._audit("runtime_failure", error.payload())
            return {"status": GovernanceDecision.HALT.value, "error": error.payload()}
        except GovernanceRuntimeError as exc:
            return self._halt_for_error(exc)

        features = self._extract_lexical_features(clean_input.query)
        logits = features.logits
        probs = softmax(logits)
        confidence = _normalize_float(float(np.max(probs)), 8)

        decision = GovernanceDecision.HALT
        if int(np.argmax(probs)) == 0 and confidence >= CONFIDENCE_THRESHOLD:
            decision = GovernanceDecision.EXECUTE

        receipt = self._build_receipt(clean_input, confidence, decision, features.reasoning)
        try:
            self._emit_receipt(receipt)
        except GovernanceRuntimeError as exc:
            return self._halt_for_error(exc)

        if decision is GovernanceDecision.HALT:
            self._audit(
                "policy_denial",
                {
                    "category": "lexical_policy",
                    "code": "INSUFFICIENT_CONFIDENCE",
                    "decision": decision.value,
                    "input_hash": receipt.input_hash,
                    "receipt_id": receipt.receipt_id,
                },
            )
            return {
                "status": GovernanceDecision.HALT.value,
                "error": {
                    "category": "lexical_policy",
                    "code": "INSUFFICIENT_CONFIDENCE",
                    "detail": (
                        f"Insufficient Confidence ({confidence:.4f} < {CONFIDENCE_THRESHOLD})"
                    ),
                },
                "receipt": receipt.model_dump(mode="json"),
            }

        return {
            "status": GovernanceDecision.EXECUTE.value,
            "payload": f"Processed: {clean_input.query}",
            "receipt": receipt.model_dump(mode="json"),
        }


# --- Quick Test ---
if __name__ == "__main__":
    engine = GuardrailEngine()

    print(
        engine.process(
            {
                "query": "Calculate net liquidity for Q3",
                "context": "Banking audit",
                "domain": "financial",
            }
        )
    )

    print(
        engine.process({"query": "Generate meme", "context": "social", "domain": "entertainment"})
    )
