"""
Shared helpers for ./enroll and ../agents/agent_setup:
env/roster parsing, the LiteLLM admin API, rerunning under sudo, and
dropping to a user's uid for work in that user's home.
Standard library only.
"""

import csv
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def parse_env(text):
    """Parse KEY=value lines (an optional leading "export" is allowed)."""
    env = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, sep, val = line.partition("=")
        if sep:
            env[key.strip()] = val.strip().strip("'\"")
    return env


def split_set(arg):
    """'a, b,c' -> {'a', 'b', 'c'}; None/'' -> None (no filter)."""
    return {x.strip() for x in arg.split(",") if x.strip()} if arg else None


def read_roster(text, users=None, classes=None):
    """Returns (rows, problems). Only rows whose user is in users and whose
    class is in classes (None = no filter) are kept; a row repeating an
    earlier user is dropped. Per-service columns (each empty = don't set up
    that service for the row):
        jupyter_user  Google account that logs in to JupyterHub as user
        webui_user    Google account for Open WebUI
        litellm_user  LiteLLM user_id owning the key (issue one if litellm_key is empty)
        miyabi        Miyabi account (~/.ssh/config Host miyabig/miyabic)
    Google accounts are lowercased; "raw" is the original row. Uniqueness of
    jupyter_user is up to the caller (only JupyterHub needs it)."""
    rows, problems, seen_user = [], [], {}
    for lineno, r in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        def col(name):
            return (r.get(name) or "").strip()
        user = col("user")
        if not user:
            continue
        if users is not None and user not in users:
            continue
        if classes is not None and col("class") not in classes:
            continue
        if user in seen_user:
            problems.append((user, f"line {lineno}: duplicate user (first at line {seen_user[user]})"))
            continue
        seen_user[user] = lineno
        rows.append({"line": lineno, "user": user,
                     "jupyter_user": col("jupyter_user").lower(),
                     "webui_user": col("webui_user").lower(),
                     "litellm_user": col("litellm_user"),
                     "miyabi": col("miyabi"),
                     "key": col("litellm_key"), "team": col("litellm_team"),
                     "name": col("real_name") or user, "raw": r})
    return rows, problems


def rerun_as_root(script, files, args, capture=False):
    """Read files (name -> path) as the invoking user, then rerun script under
    sudo with "--stdin" and their contents as JSON on stdin. This lets the
    inputs live on a FUSE mount (e.g. gocryptfs) that root cannot read.
    Returns the exit status, or (status, stdout) with capture=True (the child
    should then log to stderr)."""
    payload = {}
    for name, path in files.items():
        with open(path, encoding="utf-8") as fp:
            payload[name] = fp.read()
    argv = ["sudo", sys.executable, os.path.abspath(script), "--stdin"] + args
    r = subprocess.run(argv, input=json.dumps(payload), text=True,
                       stdout=subprocess.PIPE if capture else None)
    return (r.returncode, r.stdout) if capture else r.returncode


def as_user(pw, fn, errors=()):
    """Run fn() in a forked child with pw's uid and groups; return its result
    (must be JSON-serializable). Used when root reads or writes a user's home,
    so links the user planted can't make root touch other files. An exception
    that is an instance of a class in errors is re-raised as that class (by
    message); anything else becomes OSError. Results come back as JSON, never
    pickle: the child runs as the user."""
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r)
        try:
            os.setgroups(os.getgrouplist(pw.pw_name, pw.pw_gid))
            os.setgid(pw.pw_gid)
            os.setuid(pw.pw_uid)
            out = {"ok": fn()}
        except BaseException as e:
            cls = next((c for c in errors if isinstance(e, c)), OSError)
            out = {"err": cls.__name__, "msg": str(e)}
        try:
            os.write(w, json.dumps(out).encode())
        finally:
            os._exit(0)
    os.close(w)
    data = b""
    while chunk := os.read(r, 65536):
        data += chunk
    os.close(r)
    os.waitpid(pid, 0)
    try:
        out = json.loads(data)
    except ValueError:
        raise OSError(f"child for {pw.pw_name} failed")
    if "ok" in out:
        return out["ok"]
    cls = {c.__name__: c for c in errors}.get(out["err"], OSError)
    raise cls(out["msg"])


class ApiError(Exception):
    pass


def http(method, url, token, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read() or b"null")
    except urllib.error.HTTPError as e:
        raise ApiError(f"{method} {url}: {e.code} {e.read().decode(errors='replace')[:300]}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"{method} {url}: {e.reason}") from None


class LiteLLM:
    """LiteLLM admin API. token must be allowed to create teams and keys."""

    def __init__(self, url, token, dry_run=False, key_duration=None, key_max_budget=None, issuer="enroll"):
        self.url, self.token, self.dry_run = url.rstrip("/"), token, dry_run
        self.key_duration, self.key_max_budget, self.issuer = key_duration, key_max_budget, issuer
        self.teams = {t.get("team_alias"): t["team_id"]
                      for t in self.get("/team/list") if t.get("team_alias")}
        self._models = None

    def get(self, path):
        return http("GET", self.url + path, self.token)

    def post(self, path, body):
        return http("POST", self.url + path, self.token, body)

    def team_id(self, alias):
        """Team id for alias, creating the team (with all current models) if missing.
        Returns (team_id, created)."""
        if alias in self.teams:
            return self.teams[alias], False
        if self.dry_run:
            return f"<new team {alias}>", True
        # An empty models list means "no-default-models", not "all" (litellm/README.md)
        if self._models is None:
            self._models = [m["id"] for m in self.get("/v1/models")["data"]]
        team = self.post("/team/new", {"team_alias": alias, "models": self._models})
        self.teams[alias] = team["team_id"]
        return team["team_id"], True

    def generate_key(self, alias, email, team_id):
        """key_alias must be unique across LiteLLM; one email may own several keys."""
        body = {"key_alias": alias, "user_id": email, "metadata": {"enrolled_by": self.issuer}}
        if team_id:
            body["team_id"] = team_id
        if self.key_duration:
            body["duration"] = self.key_duration
        if self.key_max_budget is not None:
            body["max_budget"] = self.key_max_budget
        return self.post("/key/generate", body)["key"]

    def delete_key(self, key):
        self.post("/key/delete", {"keys": [key]})

    def issue_key(self, alias, email, team_alias):
        """Issue a key, creating the team if needed. Returns (key, note);
        key is None on a dry run. LiteLLM shows a key only once, so the
        caller must save it."""
        team_id, note = None, ""
        if team_alias:
            team_id, created = self.team_id(team_alias)
            note = f" team={team_alias}" + (" (new)" if created else "")
        if self.dry_run:
            return None, note
        return self.generate_key(alias, email, team_id), note
