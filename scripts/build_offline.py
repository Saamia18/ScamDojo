"""Exports what the browser needs for the OFFLINE quick check from the same Python definitions the server uses:
web/data/offline_pack.json = ASCII-only rule patterns + brand / domain knowledge. Run: python scripts/build_offline.py"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import brands, rules  # noqa: E402


def js_safe(p):
    return all(ord(c) < 128 for c in p)


def main():
    pack = {
        "rules": [{"id": r["id"], "category": r["category"], "weight": r["weight"], "neg": bool(r.get("neg")), "ctx_skip": bool(r.get("ctx_skip")),
                   "title": r["title"], "why": r["why"], "tip": r["tip"], "patterns": [p for p in r["patterns"] if js_safe(p)]} for r in rules.RULES],
        "safe_rules": [{"id": r["id"], "weight": r["weight"], "title": r["title"], "why": r["why"], "patterns": [p for p in r["patterns"] if js_safe(p)]} for r in rules.SAFE_RULES],
        "brands": {b: {"keywords": kws, "official": doms} for b, (kws, doms) in brands.BRANDS.items()},
        "multi_suffix": sorted(brands.MULTI_SUFFIX), "trusted_suffixes": list(brands.TRUSTED_SUFFIXES), "shorteners": sorted(brands.SHORTENERS),
        "risky_tlds": sorted(brands.SUSPICIOUS_TLDS), "free_hosting": sorted(brands.FREE_HOSTING), "path_words": list(brands.PATH_WORDS), "tld_list": brands.TLD_LIST,
        "benign_ctx": rules._BENIGN_CTX.pattern, "neg_ctx": rules._NEG_RE.pattern,
    }
    out = os.path.join(ROOT, "web", "data", "offline_pack.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, separators=(",", ":"))
    skipped = sum(len(r["patterns"]) for r in rules.RULES) - sum(len(r["patterns"]) for r in pack["rules"])
    print("offline pack: %d rules (%d non-ASCII patterns skipped), %d brands, %d bytes" % (len(pack["rules"]), skipped, len(pack["brands"]), os.path.getsize(out)))


if __name__ == "__main__":
    main()
