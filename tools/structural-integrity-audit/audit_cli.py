import argparse
import requests
import sys
import os
import json

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", required=True)
    p.add_argument("--server", default="http://127.0.0.1:8000")
    args = p.parse_args()

    if os.path.isdir(args.path):
        r = requests.post(f"{args.server}/batch-audit", data={"directory_path": args.path})
        data = r.json()
        fails = [k for k, v in data.items() if v["verdict"] == "FAILS"]
        print(json.dumps(data, indent=2))
        sys.exit(1 if fails else 0)
    else:
        with open(args.path, "rb") as f:
            r = requests.post(f"{args.server}/audit", files={"file": f})
            data = r.json()
            print(json.dumps(data, indent=2))
            sys.exit(1 if data["verdict"] == "FAILS" else 0)

if __name__ == "__main__":
    main()
