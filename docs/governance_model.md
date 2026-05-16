# Governance Model

## Trust boundaries

The governance stack treats every caller-provided action, prompt, file path, row payload, uploaded asset, and UI buffer as untrusted input. Policy validation happens before tool lookup or execution. External runtimes such as Earth Engine, PDF rendering, and model checkpoint parsing are outside the trust boundary and must return deterministic fail-closed outcomes on failure.

## Fail-closed principles

Governed paths deny by default. Schema failures, policy failures, payload limit failures, malformed input, runtime exceptions, ledger replay failures, lineage discontinuities, and external dependency failures all terminate as explicit halt, policy violation, tool error, or critical-failure results. The stack does not permit permissive fallbacks after validation errors.

## Structured governance errors

Governance failures are represented with one stable machine-readable halt envelope:

```json
{
  "status": "HALT",
  "error": {
    "category": "...",
    "code": "...",
    "detail": "..."
  }
}
```

The runtime taxonomy separates generic governance runtime failures, external dependency failures, serialization failures, canonicalization failures, resource limit failures, and lexical policy failures. This makes failure outcomes observable without replacing explicit policy states with exception-only control flow.

## Deterministic guarantees

Policy decisions are based on typed schemas, canonical paths, stable JSON serialization, explicit lexical safety features, fixed thresholds, and replay-validated local receipt ledgers. The governance code does not use random sampling, network-dependent policy decisions, wall-clock timestamps for receipt tests, or probabilistic acceptance. Identical validated inputs and identical lineage state produce identical policy outcomes and receipt hashes.

## Deterministic serialization rules

Canonical governance serialization uses JSON with sorted keys, no NaN or Infinity values, compact separators, and Decimal-based pre-serialization float quantization for receipt timestamps and confidence scores. Payloads that cannot be serialized canonically fail closed. Ledger rows, audit rows, and advisory lock metadata must be stored in exactly canonical form; replay rejects rows that parse successfully but are not byte-equivalent to canonical serialization.

## Receipt replay model

Guardrail receipts form a chained lineage. Each receipt contains a monotonic sequence number, canonical input hash, previous receipt hash, confidence score, explicit decision, deterministic timestamp field supplied by the validated payload, and lexical reasoning metadata. The genesis hash is sixty zero characters.

A durable ledger stores one canonical JSON object per line. Each row contains the receipt and a deterministic row hash over the receipt payload. Startup validation streams the ledger from genesis, verifies sequence continuity, verifies previous-hash continuity, recomputes every receipt hash, recomputes every row hash, and returns the next append sequence and tail state. Receipt accumulation is opt-in so default replay validation remains constant-memory with respect to receipt objects. A non-existent ledger is treated as deterministic genesis.

## Durable lineage guarantees

Receipt persistence is append-only JSONL on the local filesystem with a fail-closed advisory lock file to reject concurrent append attempts. Lock files are hidden siblings derived deterministically from the governed path, contain the owner PID and monotonic creation timestamp, reject malformed or future-dated metadata, and may be recovered only after the deterministic stale-lock timeout when the owner PID can be verified as absent. Ambiguous lock ownership, unsupported PID verification, or ambiguous cleanup state fails closed. Appends use the validated cached tail state when the ledger size is unchanged and revalidate if the file changed out of band, avoiding full post-append replay on every receipt. Replay fails closed on malformed JSON, non-canonical serialization, duplicate sequence identifiers, reordered rows, row-hash mismatch, receipt-hash mismatch, previous-hash mismatch, truncated rows, oversized ledgers, and invalid filesystem targets. This detects lineage inconsistencies within the current ledger state; it is not a substitute for external anchoring, signed checkpoints, immutable storage, or historical notarization.

## Filesystem trust boundaries

Filesystem governance canonicalizes local paths before use. CSV tool targets must resolve under the configured data root and retain a `.csv` suffix. Ledger and audit paths must have existing directory parents and may not be symlinks, including broken or circular symlink leaf paths. Ambiguous paths, directory escapes, broken filesystem assumptions, and symlink traversal are rejected deterministically rather than normalized into permissive access. These checks reduce path confusion but do not claim fd-based race-free secure-open semantics. The advisory lock is a local coordination mechanism for cooperative writers; it does not provide distributed locking, kernel-enforced mandatory locking, fd-level append proofs across all filesystems, or protection from privileged local mutation. Deployments that require historical immutability should place ledgers on immutable storage or externally anchored append-only media.

## Runtime resource governance

Governed action and guardrail payloads enforce byte ceilings, recursion-depth ceilings, object-count ceilings, per-string byte ceilings, container-fanout ceilings, recursion rejection, and JSON compatibility in one deterministic traversal before schema validation or policy execution. Row-query governance enforces supplied-row and query-limit ceilings. Ledger and audit files enforce byte ceilings, and audit events enforce a per-event size ceiling. Non-finite numeric values fail canonical serialization and halt deterministically.

## Lexical policy model

The lexical guardrail is deterministic and explainable. It extracts bounded token features, weighted safe and unsafe token classes, phrase-level unsafe patterns, capped repetition amplification, long-token anomalies, punctuation floods, suspicious encoding patterns, digit ratio, and low-token-entropy anomalies. Unsafe signals dominate mixed safe/unsafe inputs without permitting unbounded score inflation. Receipts include structured reasoning metadata with unsafe terms, anomaly flags, and a score breakdown.

No NLP frameworks, machine-learning models, embeddings, network services, or probabilistic acceptance paths are part of lexical policy evaluation.

## Audit logging model

Audit logging is local, deterministic, append-only JSONL with the same fail-closed advisory lock semantics as receipt appends. Audit rows use canonical serialization, monotonic sequence numbers, explicit event-type field schemas, and redaction-safe event fields. The audit log records policy denials and runtime failures without raw prompt, context, or payload content. Validation rejects truncated rows, malformed JSON, non-canonical rows, sequence discontinuities, oversized logs, unknown fields, missing required fields, wrong field types, and rows that contain forbidden raw payload keys at any nesting level, including list, tuple, and set nesting encountered before canonical serialization.

## Replay verification semantics

Replay validation is an enforcement mechanism, not a diagnostic-only utility. A replay violation prevents ledger startup or append from continuing. Ledger replay iterates line-by-line and does not accumulate receipt objects unless receipt inclusion is explicitly requested. This preserves deterministic fail-closed semantics for receipt lineage and prevents the engine from silently building on corrupted state.

## Schema contracts

Action requests use a top-level `ActionRequest` schema with a `tool` and `target`. Tool-specific targets are validated with separate schemas: `QueryTarget` for bounded row queries, `ReadFileTarget` for CSV paths, and `RunTestTarget` for registered test suites. Unknown fields and unsupported tool names are rejected before execution.

## Adversarial assumptions

Attackers may supply traversal paths, deeply nested structures, recursive objects, NaN and Infinity values, oversized row lists, malformed Unicode, binary buffers, unsafe lexical prompts mixed with safe language, punctuation spam, extremely long tokens, suspicious encodings, reordered receipt rows, duplicated sequence identifiers, invalid canonical hashes, truncated ledger files, and unsupported files. These inputs must be rejected or halted deterministically without partial execution.

## Cryptographic signing model

The current receipt ledger is hash-chained and replay-verifiable but unsigned. No placeholder cryptography is used. If signing is introduced later, it must be optional, feature-gated, backed by a real Ed25519 implementation, and validation must fail closed whenever signatures are enabled and invalid. Unsigned operation must remain deterministic.

## Governance invariants

* Default behavior is fail-closed.
* Tool execution occurs only after schema and policy success.
* Unsafe prompt signals dominate mixed safe/unsafe prompts.
* Caller-owned payloads are not mutated during policy evaluation.
* Recursive payload structures fail closed safely.
* Receipt chains are durable, replayable, and deterministic for identical current ledger state and canonical input, but historical immutability requires external anchoring or immutable storage.
* Runtime exceptions and policy denials use a single `{"status":"HALT","error":...}` envelope.
* Canonical path checks prevent filesystem traversal outside allowed roots.
* Audit events never require network telemetry or asynchronous logging.
