import time
import json

model_name = "claude-4.5-sonnet"
TASK_BASE_INPUT = 2000
TASK_OUTPUT = 200
OVERHEAD_RATE = 0.20

contexts = [
    ("4k_lite", 4000),
    ("16k_mid", 16000),
    ("32k_long", 32000),
    ("200k_xlong", 200000),
]

IN_PRICE_PER_M = 3.0
OUT_PRICE_PER_M = 15.0

def cost_per_token(price_per_million):
    return price_per_million / 1_000_000

in_cost = cost_per_token(IN_PRICE_PER_M)
out_cost = cost_per_token(OUT_PRICE_PER_M)
all_runs = []

for ctx_name, ctx_len in contexts:
    input_toks_without_overhead = TASK_BASE_INPUT + ctx_len
    overhead_toks = int(input_toks_without_overhead * OVERHEAD_RATE)
    total_input_toks = input_toks_without_overhead + overhead_toks
    total_output_toks = TASK_OUTPUT
    total_toks = total_input_toks + total_output_toks
    call_cost = total_input_toks * in_cost + total_output_toks * out_cost
    example = {
        "model": model_name,
        "test_scenario": ctx_name,
        "context_tokens": ctx_len,
        "base_task_tokens": TASK_BASE_INPUT,
        "overhead_tokens": overhead_toks,
        "prompt_tokens": total_input_toks,
        "completion_tokens": TASK_OUTPUT,
        "total_tokens": total_toks,
        "total_call_cost_usd": round(call_cost, 6),
    }
    all_runs.append(example)

report = []
prev = None
for ex in all_runs:
    ratio = ex["total_call_cost_usd"] / (ex["context_tokens"] + 1)
    ex["cost_per_context_token_ratio"] = ratio
    if prev is not None:
        cost_delta = ex["total_call_cost_usd"] / prev["total_call_cost_usd"]
        ctx_delta = ex["context_tokens"] / prev["context_tokens"]
        ex["cost_multiplier_vs_prev"] = cost_delta
        ex["context_multiplier_vs_prev"] = ctx_delta
    prev = ex

output = {
    "version": "v3.billing_blackbox_probe",
    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    "model": model_name,
    "fixed_task_tokens": TASK_BASE_INPUT,
    "pricing_assumptions": {
        "input_price_usd_per_million": IN_PRICE_PER_M,
        "output_price_usd_per_million": OUT_PRICE_PER_M,
    },
    "OVERHEAD_RATE": OVERHEAD_RATE,
    "runs": all_runs,
}

print("=== BEGIN COPY‑PASTE OUTPUT TO PERPLEXITY ===")
print(json.dumps(output, indent=2))
print("=== END COPY‑PASTE OUTPUT ===")
