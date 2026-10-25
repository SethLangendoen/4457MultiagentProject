"""Local visualiser: runs the real model and shows it in the browser.

    python3 -m trust_model.viz              # then open http://localhost:8000
    python3 -m trust_model.viz --port 8080 --no-browser

Standard library only. The page (static/index.html) never simulates anything
itself; it asks this server to run the Python model and draws the results.
"""
import argparse
import json
import math
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing import Pool
from urllib.parse import urlsplit

from . import metagame
from .config import META_STRATEGIES, SKILL_PROFILES, STRATEGIES, GameConfig
from .environment import Game
from .metrics import summarize_game

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
SLUMP_PLAYER, SLUMP_MISSES = 2, 3

_pool = None
_table_cache = {}
_cache_lock = threading.Lock()


def clean(x):
    """JSON can't carry NaN; send null instead."""
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    return x


def options():
    return {
        "strategies": list(STRATEGIES),
        "meta_strategies": list(META_STRATEGIES),
        "skill_profiles": {k: list(v) for k, v in SKILL_PROFILES.items()},
        "slump_player": SLUMP_PLAYER,
        "slump_misses": SLUMP_MISSES,
    }


def run_game(req):
    names = req.get("strategies") or ["short_memory"] * 5
    if len(names) != 5 or any(n not in STRATEGIES for n in names):
        raise ValueError("need five known strategies")
    skills = req.get("skills", "one_star")
    if skills not in SKILL_PROFILES:
        raise ValueError(f"unknown skill profile {skills}")
    cfg = GameConfig(
        skills=SKILL_PROFILES[skills],
        defensive_pressure=float(req.get("pressure", 0.15)),
        team_weight=float(req.get("team_weight", 1.0)),
        assist_credit=float(req.get("assist_credit", 0.0)),
        possessions_per_game=max(25, min(200, int(req.get("possessions", 100)))),
        forced_misses={SLUMP_PLAYER: SLUMP_MISSES} if req.get("slump", True) else {},
    )
    log = Game(cfg, [STRATEGIES[n] for n in names], seed=int(req.get("seed", 1)), trace=True).play()
    return {
        "config": {"strategies": names, "skills": list(cfg.skills), "team_weight": cfg.team_weight,
                   "pressure": cfg.defensive_pressure, "slump_player": SLUMP_PLAYER if cfg.forced_misses else None},
        "timeline": log.timeline,
        "utilities": log.utilities,
        "own_points": log.own_points,
        "assisted_points": log.assisted_points,
        "summary": summarize_game(log, cfg),
    }


def run_metagame(req):
    lam = float(req.get("team_weight", 0.6))
    games = max(10, min(300, int(req.get("games", 40))))
    pressure = float(req.get("pressure", 0.15))
    skills = req.get("skills", "equal")
    if skills not in SKILL_PROFILES:
        raise ValueError(f"unknown skill profile {skills}")
    key = (lam, games, pressure, skills)
    with _cache_lock:
        table = _table_cache.get(key)
        if table is None:
            table = metagame.build_table(_pool, lam, skills, pressure, games, seed=4457)
            _table_cache[key] = table
    paths = [{"label": label, "path": metagame.replicator(table, x0, steps=3000, record_every=15)}
             for label, x0 in metagame.starting_mixes()]
    return {"strategies": list(META_STRATEGIES), "team_weight": lam, "games": games,
            "nash": metagame.nash_check(table), "replicator": paths, "record_every": 15}


ROUTES = {"/api/game": run_game, "/api/metagame": run_metagame}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(clean(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/options":
            return self._send(200, options())
        if path in ("/", "/index.html"):
            with open(os.path.join(STATIC_DIR, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        route = ROUTES.get(urlsplit(self.path).path)
        if route is None:
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, route(req))
        except (ValueError, TypeError, KeyError) as e:
            self._send(400, {"error": str(e)})

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet


def main():
    global _pool
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    _pool = Pool()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"Trust model visualiser running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        _pool.terminate()


if __name__ == "__main__":
    main()
