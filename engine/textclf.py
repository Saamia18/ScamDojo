"""Text classifier: TF-IDF features + logistic regression, written in plain Python (no ML libraries needed).

Why this model: it is small, fast, and fully explainable. Every word has a learned weight, so we can show which
words pushed a message towards "scam" or towards "safe". The weights live in engine/model/model.json.
"""
import json
import math
import random
import re

from .urlcheck import find_urls

_TOKEN_RE = re.compile(
    r"""(?P<phone>(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)|1800[\s-]?\d{3}[\s-]?\d{3,4})
        |(?P<money>(?:₹|rs\.?|inr)\s?\d[\d,]*(?:\.\d+)?)
        |(?P<num>\d[\d,]*(?:\.\d+)?)
        |(?P<word>[^\W\d_]+(?:'[^\W\d_]+)?)""",
    re.X | re.I,
)


def tokenize(norm):
    """Return [(feature, a, b)] where a,b are positions in norm.text. URLs, phones and numbers become placeholders."""
    text = norm.text
    out = []
    cursor = 0
    segments = []
    for a, b, _ in find_urls(text):
        if a >= cursor:
            segments.append((cursor, a, False))
            segments.append((a, b, True))
            cursor = b
    segments.append((cursor, len(text), False))
    for a, b, is_url in segments:
        if b <= a:
            continue
        if is_url:
            out.append(("<url>", a, b))
            continue
        for m in _TOKEN_RE.finditer(text[a:b]):
            s, e = a + m.start(), a + m.end()
            kind = m.lastgroup
            if kind == "word":
                out.append((m.group(0).lower(), s, e))
            elif kind == "phone":
                out.append(("<phone>", s, e))
            elif kind == "money":
                out.append(("<money>", s, e))
            else:
                digits = re.sub(r"\D", "", m.group(0))
                out.append(("<num4_8>" if 4 <= len(digits) <= 8 else "<num>", s, e))
    return out


def features(tokens):
    """Unigram + bigram counts. Returns (counts, bigram positions)."""
    counts = {}
    for f, _, _ in tokens:
        counts[f] = counts.get(f, 0) + 1
    for (f1, _, _), (f2, _, _) in zip(tokens, tokens[1:]):
        k = f1 + " " + f2
        counts[k] = counts.get(k, 0) + 1
    return counts


def _sigmoid(z):
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


class TextClassifier:
    def __init__(self):
        self.feat = {}  # name -> (idf, weight)
        self.bias = 0.0
        self.meta = {}

    # ---------- training ----------
    def fit(self, norms, labels, epochs=60, lr=2.0, l2=3e-5, min_df=2, seed=7):
        docs = [features(tokenize(n)) for n in norms]
        df = {}
        for d in docs:
            for k in d:
                df[k] = df.get(k, 0) + 1
        n = len(docs)
        vocab = {k: i for i, k in enumerate(sorted(k for k, c in df.items() if c >= min_df))}
        idf = {k: math.log((1 + n) / (1 + df[k])) + 1.0 for k in vocab}

        X = []
        for d in docs:
            vec = {vocab[k]: (1 + math.log(c)) * idf[k] for k, c in d.items() if k in vocab}
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            X.append({j: v / norm for j, v in vec.items()})

        w = [0.0] * len(vocab)
        b = 0.0
        pos = sum(labels)
        cw = {1: n / (2.0 * max(pos, 1)), 0: n / (2.0 * max(n - pos, 1))}
        rng = random.Random(seed)
        order = list(range(n))
        for ep in range(epochs):
            rng.shuffle(order)
            eta = lr / (1.0 + 0.08 * ep)
            for i in order:
                x = X[i]
                z = b + sum(w[j] * v for j, v in x.items())
                grad = (_sigmoid(z) - labels[i]) * cw[labels[i]]
                for j, v in x.items():
                    w[j] -= eta * (grad * v + l2 * w[j])
                b -= eta * grad
        inv = {i: k for k, i in vocab.items()}
        self.feat = {inv[i]: (round(idf[inv[i]], 4), round(w[i], 4)) for i in range(len(vocab))}
        self.bias = round(b, 4)
        self.meta = {"n_train": n, "n_features": len(vocab), "epochs": epochs, "min_df": min_df}
        return self

    # ---------- inference ----------
    def _vector(self, counts):
        vec = {}
        for k, c in counts.items():
            if k in self.feat:
                vec[k] = (1 + math.log(c)) * self.feat[k][0]
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {k: v / norm for k, v in vec.items()}

    def predict_proba(self, norm):
        toks = tokenize(norm)
        vec = self._vector(features(toks))
        z = self.bias + sum(self.feat[k][1] * v for k, v in vec.items())
        return _sigmoid(z)

    def explain(self, norm, top=8, min_contrib=0.25):
        """Per-word contribution (in log-odds). Positive pushes towards scam, negative towards safe."""
        toks = tokenize(norm)
        vec = self._vector(features(toks))
        contrib = [0.0] * len(toks)
        for i, (f, _, _) in enumerate(toks):
            if f in vec:
                contrib[i] += self.feat[f][1] * vec[f]
            if i + 1 < len(toks):
                k = f + " " + toks[i + 1][0]
                if k in vec:
                    share = self.feat[k][1] * vec[k] / 2.0
                    contrib[i] += share
                    contrib[i + 1] += share
        items = [(contrib[i], toks[i]) for i in range(len(toks)) if not toks[i][0].startswith("<")]
        up = sorted((x for x in items if x[0] >= min_contrib), key=lambda x: -x[0])[:top]
        down = sorted((x for x in items if x[0] <= -min_contrib), key=lambda x: x[0])[:5]
        fmt = lambda lst: [{"word": t[0], "a": t[1], "b": t[2], "contribution": round(c, 3)} for c, t in lst]
        return fmt(up), fmt(down)

    def top_features(self, k=15):
        uni = [(n, w) for n, (_, w) in self.feat.items() if " " not in n and not n.startswith("<")]
        return ([{"feature": n, "weight": w} for n, w in sorted(uni, key=lambda x: -x[1])[:k]],
                [{"feature": n, "weight": w} for n, w in sorted(uni, key=lambda x: x[1])[:k]])

    # ---------- persistence ----------
    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"bias": self.bias, "meta": self.meta, "features": {k: list(v) for k, v in self.feat.items()}}, f, ensure_ascii=False)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        m = cls()
        m.bias = d["bias"]
        m.meta = d.get("meta", {})
        m.feat = {k: tuple(v) for k, v in d["features"].items()}
        return m
