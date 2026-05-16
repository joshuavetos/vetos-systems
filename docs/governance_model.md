# Governance Model

## Trust boundaries

The governance stack treats every caller-provided action, prompt, file path, row payload, uploaded asset, and UI buffer as untrusted input. Policy validation happens before tool lookup or execution. External runtimes such as Earth Engine, PDF rendering, and model checkpoint parsing are outside the trust boundary and must return deterministic fail-closed outcomes on failure.

## Fail-closed principles

Governed paths deny by default. Schema failures, policy failures, payload limit failures, malformed input, runtime exceptions, and external dependency failures all terminate as explicit halt, policy violation, tool error, or critical-failure results. The stack does not permit permissive fallbacks after validation errors.

## Deterministic guarantees

Policy decisions are based on typed schemas, canonical paths, stable JSON serialization, explicit lexical safety features, and fixed thresholds. The governance code does not use random sampling, network-dependent policy decisions, or probabilistic acceptance. Identical validated inputs produce identical policy outcomes.

## Receipt lineage model

Guardrail receipts form a chained lineage. Each receipt hash is computed from the prior receipt hash, the canonical input hash, and the receipt timestamp. The genesis hash is sixty zero characters. Updating the in-memory last hash after each receipt creates an append-only tamper-evident sequence for a single engine instance.

## Schema contracts

Action requests use a top-level `ActionRequest` schema with a `tool` and `target`. Tool-specific targets are validated with separate schemas: `QueryTarget` for bounded row queries, `ReadFileTarget` for CSV paths, and `RunTestTarget` for registered test suites. Unknown fields and unsupported tool names are rejected before execution.

## Adversarial assumptions

Attackers may supply traversal paths, deeply nested structures, recursive objects, NaN and Infinity values, oversized row lists, malformed Unicode, binary buffers, unsafe lexical prompts mixed with safe language, punctuation spam, extremely long tokens, suspicious model checkpoints, and unsupported files. These inputs must be rejected or halted deterministically without partial execution.

## Payload limits

Governed action payloads enforce maximum supplied rows, maximum serialized JSON bytes, and maximum nesting depth. Text insertion enforces maximum source, insertion, and resulting file sizes. PDF generation enforces maximum serialized report size and generated PDF size. Torch checkpoints enforce file-size, tensor-count, tensor-element, and dtype ceilings.

## Governance invariants

* Default behavior is fail-closed.
* Tool execution occurs only after schema and policy success.
* Unsafe prompt signals dominate mixed safe/unsafe prompts.
* Caller-owned payloads are not mutated during policy evaluation.
* Receipt chains are deterministic for identical engine state and canonical input.
* Runtime exceptions are isolated into structured error outcomes.
* Canonical path checks prevent filesystem traversal outside allowed roots.
