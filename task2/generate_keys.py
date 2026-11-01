"""Generate three API keys (one per consumer).

- Only SHA-256 hashes go into api_keys.json (what the server keeps).
- Raw keys are printed once and saved in issued_keys.txt (git-ignored).
  Share each key privately with its tester, never in the public repo.
"""
import hashlib
import json
import secrets

CONSUMERS = ["tester_one", "tester_two", "tester_three"]

hashes, issued = {}, {}
for name in CONSUMERS:
    key = "rs_" + secrets.token_urlsafe(32)
    issued[name] = key
    hashes[name] = hashlib.sha256(key.encode()).hexdigest()

with open("api_keys.json", "w") as f:
    json.dump(hashes, f, indent=2)

with open("issued_keys.txt", "w") as f:
    for name, key in issued.items():
        f.write(f"{name}={key}\n")

print("Keys generated. Give each one to its tester privately:\n")
for name, key in issued.items():
    print(f"  {name}: {key}")
