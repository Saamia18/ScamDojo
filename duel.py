"""Real-time 1v1 red-flag duels over WebSockets.

The server is authoritative: it picks the messages, owns the clock, decides who claimed a red flag first and keeps the score.
This module never touches a socket library directly. A connection is any object with  send(str),  receive(timeout=...) -> str | None
and close(), which is what flask-sock and the built-in test transport (ws_transport.py) both provide.

Protocol (JSON text frames)
  client -> server   {"t":"claim","start":int,"end":int}   {"t":"done"}   {"t":"clean"}   {"t":"ping"}
  server -> client   joined, waiting, player_joined, countdown, round, claimed, wrong, late, round_end, match_end, opponent_left, error, ping
If nobody joins within BOT_WAIT seconds (default 120) an AI opponent joins automatically; it also takes over if a human leaves mid-match.
"""
import json
import random
import re
import secrets
import threading
import time

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L so codes are easy to read aloud
MAX_ROOMS = 100
MAX_MSG = 2000
MSGS_PER_SECOND = 40

CFG = {"rounds": 6, "seconds": 20.0, "bot_wait": 120.0, "between": 5.0, "countdown": 3.0, "bot_start": 3.0, "bot_gap": 2.6}
_CARDS = []


class RoomError(Exception):
    pass


def configure(cards, **overrides):
    """cards: the server's card list (each with .ai.highlights). Only English base cards are used so both players see the same text."""
    global _CARDS
    _CARDS = []
    for c in cards:
        if c.get("generated"):
            continue
        spans = []
        if c["scam"]:
            spans = [{"start": h["start"], "end": h["end"], "label": h.get("label", "")} for h in c["ai"]["highlights"] if h["kind"] in ("rule", "link")]
        if c["scam"] and not spans:
            continue
        _CARDS.append({"id": c["id"], "sender": c["sender"], "channel": c["channel"], "text": c["text"], "scam": c["scam"], "lesson": c["lesson"], "spans": spans})
    CFG.update({k: v for k, v in overrides.items() if k in CFG})


def clean_name(name):
    name = re.sub(r"[\x00-\x1f\x7f<>]", "", str(name or "")).strip()[:20]
    return name or "Player"


class Player:
    def __init__(self, name, ws=None, bot=False):
        self.name, self.ws, self.bot, self.connected = name, ws, bot, not bot


class Room:
    def __init__(self, code):
        self.code = code
        self.lock = threading.RLock()
        self.players = {}
        self.state = "waiting"          # waiting -> countdown -> playing -> between -> finished -> closed
        self.created = time.time()
        self.deck, self.round, self.scores = [], -1, {"A": 0, "B": 0}
        self.spans, self.locked, self.deadline, self.next_at, self.start_at = [], set(), 0.0, 0.0, 0.0
        self.bot_plan, self.finished_at = [], None
        threading.Thread(target=self._ticker, daemon=True).start()

    # ---------- sending ----------
    def _send(self, slot, msg):
        p = self.players.get(slot)
        if p and p.ws and p.connected:
            try:
                p.ws.send(json.dumps(msg, ensure_ascii=False))
            except Exception:
                p.connected = False

    def broadcast(self, msg):
        for slot in list(self.players):
            self._send(slot, msg)

    def names(self):
        return {s: p.name for s, p in self.players.items()}

    # ---------- joining and leaving ----------
    def add_human(self, name, ws):
        with self.lock:
            if "A" not in self.players:
                slot = "A"
            elif "B" not in self.players and self.state == "waiting":
                slot = "B"
            else:
                raise RoomError("That room is full or has already started.")
            self.players[slot] = Player(name, ws)
            self._send(slot, {"t": "joined", "you": slot, "code": self.code, "names": self.names(), "rounds": CFG["rounds"], "bot_wait": CFG["bot_wait"]})
            if slot == "B":
                self.broadcast({"t": "player_joined", "name": name, "names": self.names()})
                self._begin()
            else:
                self._send(slot, {"t": "waiting", "seconds_left": CFG["bot_wait"]})
            return slot

    def _add_bot(self, slot):
        self.players[slot] = Player("🤖 AI", bot=True)

    def leave(self, slot):
        with self.lock:
            p = self.players.get(slot)
            if not p or p.bot:
                return
            p.connected = False
            other = "B" if slot == "A" else "A"
            humans = [s for s, q in self.players.items() if not q.bot and q.connected]
            if not humans:
                self.state = "closed"
                return
            if self.state in ("countdown", "playing", "between") and not self.players.get(other, Player("", bot=False)).bot:
                self.broadcast({"t": "opponent_left", "name": p.name})
                self._add_bot(slot)  # the AI takes over the empty seat so the match can finish
                self.players[slot].name = "🤖 AI"

    # ---------- game flow ----------
    def _begin(self):
        pool_s = [c for c in _CARDS if c["scam"]]
        pool_l = [c for c in _CARDS if not c["scam"]]
        n_legit = max(1, CFG["rounds"] // 3)
        deck = random.sample(pool_s, min(len(pool_s), CFG["rounds"] - n_legit)) + random.sample(pool_l, min(len(pool_l), n_legit))
        random.shuffle(deck)
        self.deck = deck
        self.state, self.start_at = "countdown", time.time() + CFG["countdown"]
        self.broadcast({"t": "countdown", "seconds": CFG["countdown"], "names": self.names(), "rounds": len(deck)})

    def _start_round(self):
        self.round += 1
        card = self.deck[self.round]
        self.spans = [dict(s, by=None) for s in card["spans"]]
        self.locked, self.state = set(), "playing"
        now = time.time()
        self.deadline = now + CFG["seconds"]
        self.bot_plan = []
        if any(p.bot for p in self.players.values()):
            order = random.sample(range(len(self.spans)), len(self.spans))
            self.bot_plan = [(now + CFG["bot_start"] + k * CFG["bot_gap"] + random.random() * 1.2, i) for k, i in enumerate(order)]
        self.broadcast({"t": "round", "index": self.round, "total": len(self.deck), "sender": card["sender"], "channel": card["channel"],
                        "text": card["text"], "seconds": CFG["seconds"], "scores": self.scores, "names": self.names()})

    def _bot_slots(self):
        return [s for s, p in self.players.items() if p.bot]

    def claim(self, slot, start, end):
        with self.lock:
            if self.state != "playing" or slot in self.locked:
                return
            hit = next((s for s in self.spans if start < s["end"] and s["start"] < end), None)
            if hit is None:
                self.scores[slot] = max(0, self.scores[slot] - 1)
                self.broadcast({"t": "wrong", "by": slot, "start": start, "end": end, "scores": self.scores})
            elif hit["by"] is None:
                hit["by"] = slot
                self.scores[slot] += 2
                self.broadcast({"t": "claimed", "by": slot, "start": hit["start"], "end": hit["end"], "label": hit["label"], "scores": self.scores,
                                "remaining": sum(1 for s in self.spans if s["by"] is None)})
                if all(s["by"] for s in self.spans):
                    self._end_round("all flags found")
            else:
                self._send(slot, {"t": "late", "start": hit["start"], "end": hit["end"], "by": hit["by"]})

    def finalize(self, slot, kind):
        with self.lock:
            if self.state != "playing" or slot in self.locked:
                return
            card = self.deck[self.round]
            self.locked.add(slot)
            if kind == "clean":
                self.scores[slot] = self.scores[slot] + 2 if not card["scam"] else max(0, self.scores[slot] - 1)
            self.broadcast({"t": "locked", "by": slot, "kind": kind, "scores": self.scores})
            if all(s in self.locked for s, p in self.players.items() if not p.bot):
                self._end_round("everyone finished")

    def _end_round(self, reason):
        card = self.deck[self.round]
        self.state = "between"
        self.next_at = time.time() + CFG["between"]
        self.broadcast({"t": "round_end", "reason": reason, "truth": "scam" if card["scam"] else "genuine", "lesson": card["lesson"], "scores": self.scores,
                        "spans": [{"start": s["start"], "end": s["end"], "label": s["label"], "by": s["by"]} for s in self.spans],
                        "last": self.round + 1 >= len(self.deck)})

    def _finish(self):
        a, b = self.scores["A"], self.scores["B"]
        self.state, self.finished_at = "finished", time.time()
        self.broadcast({"t": "match_end", "winner": "A" if a > b else "B" if b > a else "tie", "scores": self.scores, "names": self.names()})

    def _ticker(self):
        while True:
            time.sleep(0.1)
            now = time.time()
            with self.lock:
                if self.state == "closed":
                    return
                if self.state == "waiting" and "B" not in self.players and now - self.created >= CFG["bot_wait"]:
                    self._add_bot("B")
                    self.broadcast({"t": "player_joined", "name": "🤖 AI", "names": self.names(), "bot": True})
                    self._begin()
                elif self.state == "countdown" and now >= self.start_at:
                    self._start_round()
                elif self.state == "playing":
                    due = [x for x in self.bot_plan if x[0] <= now]
                    self.bot_plan = [x for x in self.bot_plan if x[0] > now]
                    for _, i in due:
                        slot = self._bot_slots()[0] if self._bot_slots() else None
                        if slot and self.state == "playing" and self.spans[i]["by"] is None:
                            s = self.spans[i]
                            self.claim(slot, s["start"], s["end"])
                    if self.state == "playing" and now >= self.deadline:
                        self._end_round("time is up")
                elif self.state == "between" and now >= self.next_at:
                    self._finish() if self.round + 1 >= len(self.deck) else self._start_round()
                elif self.state == "finished" and now - self.finished_at > 30:
                    self.state = "closed"
                    return
                if self.state in ("waiting", "countdown", "playing", "between") and not any(not p.bot and p.connected for p in self.players.values()) and now - self.created > 2:
                    self.state = "closed"
                    return


class Manager:
    def __init__(self):
        self.rooms, self.lock = {}, threading.Lock()

    def _sweep(self):
        for code in [c for c, r in self.rooms.items() if r.state == "closed"]:
            del self.rooms[code]

    def create(self):
        with self.lock:
            self._sweep()
            if len(self.rooms) >= MAX_ROOMS:
                raise RoomError("The server is busy right now. Try again in a minute.")
            while True:
                code = "".join(secrets.choice(ALPHABET) for _ in range(4))
                if code not in self.rooms:
                    break
            self.rooms[code] = Room(code)
            return self.rooms[code]

    def get(self, code):
        with self.lock:
            r = self.rooms.get((code or "").upper())
        if not r or r.state == "closed":
            raise RoomError("No room with that code. Check it and try again.")
        return r

    def count(self):
        with self.lock:
            self._sweep()
            return len(self.rooms)


MANAGER = Manager()


def serve(ws, code, name):
    """Runs one player's connection until it closes. Call this from the WebSocket route (it blocks)."""
    if not _CARDS:
        ws.send(json.dumps({"t": "error", "message": "Live duels are not available."}))
        return
    name = clean_name(name)
    try:
        room = MANAGER.create() if (code or "").upper() == "NEW" else MANAGER.get(code)
        slot = room.add_human(name, ws)
    except RoomError as e:
        ws.send(json.dumps({"t": "error", "message": str(e)}))
        return
    window, count = time.time(), 0
    try:
        while room.state != "closed":
            raw = ws.receive(timeout=20)
            if raw is None:
                ws.send(json.dumps({"t": "ping"}))
                continue
            now = time.time()
            if now - window > 1:
                window, count = now, 0
            count += 1
            if count > MSGS_PER_SECOND or len(raw) > MAX_MSG:
                break
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            kind = msg.get("t") if isinstance(msg, dict) else None
            if kind == "claim" and isinstance(msg.get("start"), int) and isinstance(msg.get("end"), int) and 0 <= msg["start"] < msg["end"] <= 5000:
                room.claim(slot, msg["start"], msg["end"])
            elif kind in ("done", "clean"):
                room.finalize(slot, kind)
    except Exception:
        pass  # a closed or broken connection simply ends the player's turn
    finally:
        room.leave(slot)
        try:
            ws.close()
        except Exception:
            pass
