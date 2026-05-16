"""
Probe: Observe API response shape, latency, and contract behavior
under authentication, malformed, and ambiguous stimuli.

This is an observational probe, not a validator or benchmark.
"""

import requests
import time
import json
from collections import Counter

# ----------------------------
# Configuration
# ----------------------------

TIMEOUT = 10

HEADERS = {
    "User-Agent": "contract-probe/0.1"
}

APIS = [
    {
        "name": "GitHub",
        "stimuli": {
            "auth": "https://api.github.com/user",
            "malformed": "https://api.github.com/this/does/not/exist"
        }
    },
    {
        "name": "OpenAI",
        "stimuli": {
            "auth": "https://api.openai.com/v1/models",
            "malformed": "https://api.openai.com/v1/this_does_not_exist"
        }
    },
    {
        "name": "Stripe",
        "stimuli": {
            "auth": "https://api.stripe.com/v1/charges",
            "malformed": "https://api.stripe.com/v1/not_a_real_endpoint"
        }
    },
    {
        "name": "Twitter/X",
        "stimuli": {
            "auth": "https://api.twitter.com/2/users/me",
            "malformed": "https://api.twitter.com/2/this_endpoint_does_not_exist"
        }
    },
    {
        "name": "Reddit",
        "stimuli": {
            "auth": "https://www.reddit.com/api/v1/me",
            "malformed": "https://www.reddit.com/this/does/not/exist"
        }
    },
    {
        "name": "Socrata",
        "stimuli": {
            "auth": "https://data.cityofnewyork.us/resource/xxxx-xxxx.json",
            "malformed": "https://data.cityofnewyork.us/resource/zzzz-zzzz.json"
        }
    },
    {
        "name": "Wikipedia",
        "stimuli": {
            "ambiguous": "https://en.wikipedia.org/wiki/Special:Random",
            "nonsense": "https://en.wikipedia.org/wiki/ThisPageDoesNotExist123456"
        }
    }
]

# ----------------------------
# Helpers
# ----------------------------

def classify_mode(content_type, body_len):
    if body_len == 0:
        return "OTHER"
    if content_type is None:
        return "OTHER"
    if "json" in content_type:
        return "JSON"
    if "html" in content_type:
        return "HTML"
    return "OTHER"

def classify_size(body_len):
    if body_len == 0:
        return "EMPTY"
    if body_len < 2000:
        return "SMALL"
    return "HUGE"

def try_parse_json(text):
    try:
        json.loads(text)
        return True
    except Exception:
        return False

def is_actionable(status, json_ok):
    return status in (400, 401, 403, 404) and json_ok

def is_contract_violation(mode, size, json_ok, status):
    if status >= 500:
        return True
    if mode == "HTML" and status != 200:
        return True
    if size == "EMPTY" and status >= 400:
        return True
    if not json_ok and status >= 400:
        return True
    return False

# ----------------------------
# Probe Execution
# ----------------------------

rows = []
latency_by_api = {}

for api in APIS:
    api_name = api["name"]
    latency_by_api[api_name] = []

    for stimulus, url in api["stimuli"].items():
        start = time.time()
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            elapsed_ms = int((time.time() - start) * 1000)
        except Exception as e:
            rows.append({
                "API": api_name,
                "Stimulus": stimulus,
                "Status": "ERR",
                "Mode": "OTHER",
                "Size": "EMPTY",
                "JSON": False,
                "Act": False,
                "Ctrct": True,
                "ms": None,
                "Retry": False,
                "Rate": False,
                "Page": False,
                "Preview": str(e)[:120]
            })
            continue

        latency_by_api[api_name].append(elapsed_ms)

        status = resp.status_code
        content_type = resp.headers.get("Content-Type", "")
        body = resp.text or ""
        body_len = len(body)

        mode = classify_mode(content_type, body_len)
        size = classify_size(body_len)
        json_ok = try_parse_json(body)
        actionable = is_actionable(status, json_ok)
        contract_violation = is_contract_violation(mode, size, json_ok, status)

        retry = "Retry-After" in resp.headers
        rate = status == 429
        page = status == 200 and mode == "HTML"

        preview = body[:120].replace("\n", " ").replace("\r", " ")

        rows.append({
            "API": api_name,
            "Stimulus": stimulus,
            "Status": status,
            "Mode": mode,
            "Size": size,
            "JSON": json_ok,
            "Act": actionable,
            "Ctrct": contract_violation,
            "ms": elapsed_ms,
            "Retry": retry,
            "Rate": rate,
            "Page": page,
            "Preview": preview
        })

# ----------------------------
# Reporting
# ----------------------------

headers = [
    "API", "Stimulus", "Status", "Mode", "Size",
    "JSON", "Act", "Ctrct", "ms", "Retry", "Rate", "Page", "Preview"
]

print("API          Stimulus   Status  Mode   Size    JSON  Act  Ctrct  ms     Retry  Rate  Page  Preview")
print("-" * 150)

for r in rows:
    print(
        f"{r['API']:<12} {r['Stimulus']:<10} {str(r['Status']):<7} "
        f"{r['Mode']:<6} {r['Size']:<7} "
        f"{str(r['JSON']):<5} {str(r['Act']):<4} {str(r['Ctrct']):<5} "
        f"{str(r['ms']):<6} {str(r['Retry']):<6} {str(r['Rate']):<5} {str(r['Page']):<5} "
        f"{r['Preview']}"
    )

print("\n=== GLOBAL SIGNALS ===")
print("mode       →", Counter(r["Mode"] for r in rows))
print("size       →", Counter(r["Size"] for r in rows))
print("json       →", Counter(r["JSON"] for r in rows))
print("action     →", Counter(r["Act"] for r in rows))
print("contract   →", Counter(r["Ctrct"] for r in rows))

print("\n=== LATENCY (ms) BY API ===")
for api, vals in latency_by_api.items():
    if not vals:
        continue
    print(f"{api:<12} → min={min(vals)}  max={max(vals)}  avg={sum(vals)//len(vals)}")

print("\n=== CONTRACT VIOLATIONS BY API ===")
by_api = {}
for r in rows:
    by_api.setdefault(r["API"], []).append(r["Ctrct"])

for api, vals in by_api.items():
    print(f"{api:<12} → {sum(vals)}/{len(vals)} violations")
