#!/usr/bin/env python

import argparse
import json
import glob
import re
import sqlite3
import sys
import pathlib

import pandas as pd

import problem_index
PROBLEM_INDEX = problem_index.PROBLEM_INDEX
# USERS = [f"u{x}" for x in range(26000, 26099)]

def analyze_sqlite(hist_sqlite):
    """
    read hist.sqlite and count how many times a user has
    experienced compile errors or runtime errors for each language on
    each problem, and how many times a user has called the AI tutor.
    returned as a dictionary
       C["hey"]
       C["writefile",lang]
       C[magic,lang,cmd,ok]
    where
    - magic is "bash" or "hey",
    - lang is "go", "jl", "ml", "rs" or "?",
    - cmd is "compile" or "run" or "?", and
    - ok is 0 or 1.
    """
    co = sqlite3.connect(hist_sqlite)
    # {"user":"u26001","name":"Kenjiro Taura","utac":"2615215597","topic":"recursion","prob":"gcd","cell_type":"writefile","lang":"py","cmd":"","status":""},
    C = []
    for t0, magic, line, cell, inpt, t1, output, retval in co.execute("select * from hist"):
        if magic == "writefile":
            for lang in ["go", "jl", "ml", "rs"]:
                if line.startswith(f"{lang}/") and line.endswith(f".{lang}"):
                    C.append({"cell_type": magic,
                              "lang": lang,
                              "cmd": "",
                              "status":""})
                    break
        elif magic == "bash":
            for kws, lang, cmd in [([".go", "build"], "go", "compile"),
                                   ([".ml", "ocaml"], "ml", "compile"),
                                   ([".rs", "rustc"], "rs", "compile"),
                                   (["go/"], "go", "run"),
                                   (["jl/"], "jl", "run"),
                                   (["ml/"], "ml", "run"),
                                   (["rs/"], "rs", "run"),
                                   ]:
                if all([kw in cell for kw in kws]):
                    C.append({"cell_type": magic,
                              "lang": lang,
                              "cmd": cmd,
                              "status": retval})
                    break
            else:
                C.append({"cell_type": magic,
                          "lang": "?",
                          "cmd": "?",
                          "status": retval})
        elif magic == "hey":
            C.append({"cell_type": magic,
                        "lang": "",
                        "cmd": "",
                        "status": ""})
        else:
            assert(0), magic
    return C

def find_matching(root: str, pattern: str) -> list[dict]:
    regex = re.compile(pattern)
    results = []
    for path in pathlib.Path(root).rglob("*"):
        if path.is_file():
            # Match against the relative path
            rel = path.relative_to(root).as_posix()
            m = regex.fullmatch(rel)
            if m:
                results.append({"path": rel, **m.groupdict()})
    return results

def make_dict(user_data, top, pat, url_prefix):
    """
    make a dictionary of (topic, problem) -> html
    """
    found = find_matching(top, pat)
    D = []
    for r in found:
        # m = p.match(sqlite)
        # assert(m), sqlite
        sqlite_path, user, note, topic, prob = str(r["path"]), r["user"], r["note"], r["topic"], r["prob"]
        utac = user_data[user]["utac"]
        name = user_data[user]["real_name"]
        student_id = user_data[user]["id"]
        # link to conversation (path is determined by the source of data)
        rel_href = sqlite_path.replace("hist.sqlite", "hist.html")
        href = f"{url_prefix}/{rel_href}"
        for c in analyze_sqlite(f"{top}/{sqlite_path}"):
            C = {"user": user, "name": name, "student_id" : student_id, "utac": utac,
                 "topic": topic, "prob": prob, "html": href}
            C.update(c)
            D.append(C)
    return D

def gen_js(D):
    data = json.dumps(D, indent=2, ensure_ascii=False)
    prob = json.dumps(PROBLEM_INDEX, indent=2, ensure_ascii=False)
    print(f"const PROBLEM_INDEX = {prob};")
    print(f"const DATA = {data};")

def get_user_info(a_ods):
    df = pd.read_excel(a_ods)
    pl = df[df["class"] == "pl"][["user", "utac", "real_name", "id"]]
    D = pl.set_index("user").to_dict(orient="index")
    return D

def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--top",        required=1, help="top directory to search for hist.sqlite")
    parser.add_argument("--pat",        required=1, help="regex pattern to find hist.sqlite, with named groups user, note, topic and prob")
    parser.add_argument("--url-prefix", required=1, help="prefix to prepend to href")
    parser.add_argument("--users-xlsx", required=1, help="path to ods/xlsx file containing user info")
    args = parser.parse_args(argv[1:])
    return args

def main():
    opts = parse_args(sys.argv)
    U = get_user_info(opts.users_xlsx)
    D = make_dict(U, opts.top, opts.pat, opts.url_prefix)
    gen_js(D)

main()

    
