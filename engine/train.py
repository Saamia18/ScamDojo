"""Train the text model and measure the whole engine. Run:  python -m engine.train

Writes engine/model/model.json (weights) and engine/model/metrics.json (everything shown on the Under-the-hood page).

How the numbers are produced (all of it is measured by this script, nothing is typed in by hand):
  seed_holdout : templates the model never saw during training (split by template, not by message)
  devset       : hand-written India messages, used while tuning rules and thresholds (so it is optimistic)
  blindset     : hand-written India messages written AFTER the engine was frozen, evaluated without tuning
  cards        : the messages used in the game
"""
import csv
import datetime
import hashlib
import json
import os
import statistics
import sys

from . import fusion
from .normalize import normalize
from .textclf import TextClassifier
from . import report

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MODEL_DIR = os.path.join(HERE, "model")
THRESH = 0.5


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_test_template(tid):
    return int(hashlib.md5(tid.encode()).hexdigest(), 16) % 5 == 0


def confusion(pairs):
    tp = sum(1 for y, p in pairs if y and p)
    fp = sum(1 for y, p in pairs if not y and p)
    tn = sum(1 for y, p in pairs if not y and not p)
    fn = sum(1 for y, p in pairs if y and not p)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    n = len(pairs)
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "accuracy": round((tp + tn) / n, 3) if n else 0.0, "tp": tp, "fp": fp, "tn": tn, "fn": fn}


def evaluate_set(rows, model, name=""):
    """Run the full engine on labelled rows. Returns (summary, failures, latencies)."""
    results = []
    for r in rows:
        res = fusion.analyze(r["text"], model=model)
        results.append((int(r["label"]), res, r))
    ab = {
        "text_only": confusion([(y, res["components"]["text"] >= THRESH) for y, res, _ in results]),
        "rules_only": confusion([(y, res["components"]["rules"] >= THRESH) for y, res, _ in results]),
        "links_only": confusion([(y, res["components"]["links"] >= THRESH) for y, res, _ in results]),
        "fused": confusion([(y, res["risk"] >= THRESH) for y, res, _ in results]),
    }
    verdicts = {"scam": {"scam": 0, "suspicious": 0, "safe": 0}, "legit": {"scam": 0, "suspicious": 0, "safe": 0}}
    for y, res, _ in results:
        verdicts["scam" if y else "legit"][res["verdict"]] += 1
    fails = []
    for y, res, r in results:
        if (res["risk"] >= THRESH) != bool(y):
            fails.append({"text": r["text"], "truth": "scam" if y else "legit", "risk": res["risk"], "verdict": res["verdict"],
                          "components": res["components"], "kind": r.get("kind", ""),
                          "why": [x["title"] for x in res["reasons"][:3]]})
    summary = {"n": len(rows), "n_scam": sum(1 for y, _, _ in results if y), "n_legit": sum(1 for y, _, _ in results if not y),
               "ablation": ab, "verdicts": verdicts}
    aligned = [(y, res) for y, res, _ in results]
    summary.update(report.extras(rows, aligned))
    summary["categories"] = report.by_category(rows, aligned)
    evaluate_set.last = aligned
    return summary, fails, [res["timing_ms"] for _, res, _ in results]


def main():
    seed = read_csv(os.path.join(DATA, "seed_train.csv"))
    extra = read_csv(os.path.join(DATA, "extra_train.csv"))
    for i, r in enumerate(extra):
        r["template"] = "extra_%d" % i
    rows = seed + extra
    train = [r for r in rows if not is_test_template(r["template"])]
    hold = [r for r in rows if is_test_template(r["template"])]
    print("training rows: %d, held-out template rows: %d" % (len(train), len(hold)))

    # 1) model trained WITHOUT the held-out templates -> honest test on unseen message patterns
    m_split = TextClassifier().fit([normalize(r["text"]) for r in train], [int(r["label"]) for r in train])
    hold_summary, hold_fails, _ = evaluate_set(hold, m_split, "seed_holdout")

    # 2) the shipped model uses all seed rows
    final = TextClassifier().fit([normalize(r["text"]) for r in rows], [int(r["label"]) for r in rows])
    os.makedirs(MODEL_DIR, exist_ok=True)
    final.save(os.path.join(MODEL_DIR, "model.json"))
    fusion.set_model(final)

    sets, failures, lat = {"seed_holdout": hold_summary}, {"seed_holdout": hold_fails[:8]}, []
    pooled, scam_texts, all_msgs = [], [], []
    for name, fname in (("devset", "india_testset.csv"), ("blindset", "india_blindset.csv"), ("cards", "cards_eval.csv")):
        data = read_csv(os.path.join(DATA, fname))
        if not data:
            continue
        s, f, l = evaluate_set(data, final, name)
        sets[name], failures[name] = s, f[:10]
        lat += l
        pooled += evaluate_set.last
        scam_texts += [r["text"] for r in data if int(r["label"])]
        all_msgs += [r["text"] for r in data]
    up, down = final.top_features(12)
    scam_total = sum(int(r["label"]) for r in rows)
    metrics = {
        "generated": datetime.date.today().isoformat(), "model_version": fusion.MODEL_VERSION, "threshold": THRESH,
        "dataset": {"seed_rows": len(seed), "extra_rows": len(extra), "scam": scam_total, "legit": len(rows) - scam_total,
                    "templates": len({r["template"] for r in rows}), "train_rows": len(train), "heldout_rows": len(hold),
                    "split": "by message template (about 1 in 5 templates held out)", "features": final.meta.get("n_features")},
        "sets": sets, "failures": failures,
        "top_features": {"scam": up, "safe": down},
        "rule_stats": report.rule_stats(pooled), "evasion": report.evasion(final, scam_texts), "link_benchmark": report.link_benchmark(),
        "performance": report.speed(final, all_msgs[:80]),
        "latency_ms": {"mean": round(statistics.mean(lat), 2) if lat else None,
                       "p95": round(sorted(lat)[int(0.95 * (len(lat) - 1))], 2) if lat else None, "n": len(lat)},
        "notes": [
            "The seed training set is written from templates, so it is cleaner than real SMS traffic. Scores on seed_holdout are an upper bound.",
            "devset was used while tuning rules and thresholds, so its scores are optimistic. blindset was written after tuning stopped.",
            "All sets are small. Treat the numbers as a development check, not a claim about real-world accuracy.",
            "Message text from users is never stored by the server.",
        ],
    }
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=1, ensure_ascii=False)
    for name, s in sets.items():
        fu = s["ablation"]["fused"]
        tx = s["ablation"]["text_only"]
        print("%-13s n=%-4d fused P=%.3f R=%.3f F1=%.3f | text-only F1=%.3f | rules-only F1=%.3f | links-only F1=%.3f" % (
            name, s["n"], fu["precision"], fu["recall"], fu["f1"], tx["f1"], s["ablation"]["rules_only"]["f1"], s["ablation"]["links_only"]["f1"]))
    print("latency mean %.2f ms" % metrics["latency_ms"]["mean"] if lat else "")
    for n in ("devset",):
        for f in failures.get(n, []):
            print("FAIL[%s] truth=%s risk=%.2f comps=%s | %s" % (n, f["truth"], f["risk"], f["components"], f["text"][:90]))


if __name__ == "__main__":
    sys.exit(main())
