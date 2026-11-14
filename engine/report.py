"""Deeper evaluation: confidence intervals, threshold trade-off, calibration, confidence reliability, per-category recall,
per-rule precision, evasion robustness, link benchmark and speed. Every number is computed here from the data."""
import csv
import os
import random
import statistics
import time

from . import fusion
from .evasion import TRANSFORMS
from .urlcheck import analyze_url

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _prf(pairs):
    tp = sum(1 for y, p in pairs if y and p); fp = sum(1 for y, p in pairs if not y and p); fn = sum(1 for y, p in pairs if y and not p)
    pr = tp / (tp + fp) if tp + fp else 0.0; rc = tp / (tp + fn) if tp + fn else 0.0
    return pr, rc, (2 * pr * rc / (pr + rc) if pr + rc else 0.0)


def bootstrap_ci(pairs, n=1000, seed=11):
    """95% interval for precision, recall and F1 by resampling the test messages."""
    rng = random.Random(seed)
    stats = [[], [], []]
    for _ in range(n):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        for k, v in enumerate(_prf(sample)):
            stats[k].append(v)
    out = {}
    for name, vals in zip(("precision", "recall", "f1"), stats):
        vals.sort()
        out[name] = [round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n) - 1], 3)]
    return out


def threshold_curve(scored):
    """scored = [(truth, risk)]. Precision/recall at each decision threshold."""
    rows = []
    for k in range(10, 95, 5):
        th = k / 100
        pairs = [(y, r >= th) for y, r in scored]
        pr, rc, f1 = _prf(pairs)
        rows.append({"threshold": th, "precision": round(pr, 3), "recall": round(rc, 3), "f1": round(f1, 3),
                     "false_alarms": sum(1 for y, p in pairs if not y and p), "missed": sum(1 for y, p in pairs if y and not p)})
    return rows


def calibration(scored, bins=5):
    """Does '80% risk' mean about 80% of such messages are scams?"""
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        inb = [(y, r) for y, r in scored if lo <= r < hi or (b == bins - 1 and r == 1.0)]
        out.append({"range": [lo, hi], "n": len(inb), "scam_rate": round(sum(y for y, _ in inb) / len(inb), 3) if inb else None,
                    "mean_risk": round(statistics.mean(r for _, r in inb), 3) if inb else None})
    return out


def confidence_reliability(results):
    out = []
    for level in ("high", "medium", "low"):
        sub = [(y, res) for y, res in results if res["confidence"] == level]
        correct = sum(1 for y, res in sub if (res["risk"] >= 0.5) == bool(y))
        out.append({"level": level, "n": len(sub), "accuracy": round(correct / len(sub), 3) if sub else None})
    return out


def by_category(rows, results):
    cats = {}
    for r, (y, res) in zip(rows, results):
        k = r.get("kind") or "other"
        c = cats.setdefault(k, {"label": int(y), "n": 0, "right": 0})
        c["n"] += 1
        c["right"] += 1 if (res["risk"] >= 0.5) == bool(y) else 0
    return sorted(({"kind": k, "truth": "scam" if v["label"] else "genuine", "n": v["n"], "right": v["right"], "rate": round(v["right"] / v["n"], 3)} for k, v in cats.items()),
                  key=lambda x: (x["rate"], -x["n"], x["kind"]))


def extras(rows, results):
    """results = [(truth, analysis)] aligned with rows."""
    scored = [(y, res["risk"]) for y, res in results]
    pairs = [(bool(y), res["risk"] >= 0.5) for y, res in results]
    return {"ci": bootstrap_ci(pairs), "thresholds": threshold_curve(scored), "calibration": calibration(scored),
            "confidence": confidence_reliability(results)}


def rule_stats(all_results):
    """For every rule: how often it fired on scams vs genuine messages (pooled over the hand-written sets)."""
    stats = {}
    for y, res in all_results:
        for rs in res["reasons"]:
            if rs["source"] != "rule":
                continue
            s = stats.setdefault(rs["id"], {"id": rs["id"], "title": rs["title"], "fires_scam": 0, "fires_genuine": 0})
            s["fires_scam" if y else "fires_genuine"] += 1
    for s in stats.values():
        tot = s["fires_scam"] + s["fires_genuine"]
        s["precision"] = round(s["fires_scam"] / tot, 3)
    return sorted(stats.values(), key=lambda s: (s["precision"], -(s["fires_scam"] + s["fires_genuine"])))


def evasion(model, scam_texts):
    """Recall on scams after each disguise, with the normaliser OFF vs ON."""
    def recall(texts, normalizer):
        return sum(1 for t in texts if fusion.analyze(t, model=model, normalizer=normalizer)["risk"] >= 0.5) / len(texts)
    base_on, base_off = recall(scam_texts, True), recall(scam_texts, False)
    rows = []
    for key, label, fn in TRANSFORMS:
        changed = [fn(t) for t in scam_texts]
        n_changed = sum(1 for a, b in zip(scam_texts, changed) if a != b)
        rows.append({"id": key, "label": label, "changed": n_changed, "recall_off": round(recall(changed, False), 3), "recall_on": round(recall(changed, True), 3)})
    return {"n": len(scam_texts), "baseline_off": round(base_off, 3), "baseline_on": round(base_on, 3), "rows": rows}


def link_benchmark():
    path = os.path.join(DATA, "url_testset.csv")
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    res = [(int(r["label"]), analyze_url(r["url"]), r) for r in rows]
    def conf(th):
        pairs = [(bool(y), a["risk"] >= th) for y, a, _ in res]
        pr, rc, f1 = _prf(pairs)
        return {"threshold": th, "precision": round(pr, 3), "recall": round(rc, 3), "f1": round(f1, 3),
                "tp": sum(1 for y, p in pairs if y and p), "fp": sum(1 for y, p in pairs if not y and p),
                "tn": sum(1 for y, p in pairs if not y and not p), "fn": sum(1 for y, p in pairs if y and not p)}
    kinds = {}
    for y, a, r in res:
        k = kinds.setdefault(r["kind"], {"kind": r["kind"], "truth": "phishing" if y else "genuine", "n": 0, "right": 0})
        k["n"] += 1; k["right"] += 1 if (a["risk"] >= 0.5) == bool(y) else 0
    misses = [{"url": r["url"], "truth": "phishing" if y else "genuine", "risk": a["risk"], "kind": r["kind"], "signals": [s["label"] for s in a["signals"]]}
              for y, a, r in res if (a["risk"] >= 0.5) != bool(y)]
    return {"n": len(res), "n_phish": sum(1 for y, _, _ in res if y), "n_genuine": sum(1 for y, _, _ in res if not y),
            "at_050": conf(0.5), "at_030": conf(0.3), "by_kind": sorted(kinds.values(), key=lambda k: (k["truth"], k["kind"])), "misses": misses}


def speed(model, texts, reps=6):
    lat = []
    t0 = time.perf_counter()
    for _ in range(reps):
        for t in texts:
            s = time.perf_counter()
            fusion.analyze(t, model=model)
            lat.append((time.perf_counter() - s) * 1000)
    total = time.perf_counter() - t0
    lat.sort()
    q = lambda p: round(lat[min(len(lat) - 1, int(p * len(lat)))], 2)
    return {"messages": len(lat), "p50_ms": q(0.5), "p95_ms": q(0.95), "p99_ms": q(0.99), "mean_ms": round(statistics.mean(lat), 2),
            "throughput_per_s": round(len(lat) / total), "note": "one Python thread on the machine that ran training"}
