#!/usr/bin/env python

import json
import glob
import re
import sqlite3
import pandas as pd

import problem_index
PROBLEM_INDEX = problem_index.PROBLEM_INDEX
USERS = [f"u{x}" for x in range(26000, 26099)]

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

def make_dict(user_data):
    """
    make a dictionary of (topic, problem) -> html
    """
    sqlites = glob.glob("hist/home/*/notebooks/pl/*/problems/*/*/hist.sqlite")
    # sqlites = glob.glob("hist/home/u26002/notebooks/pl/*/problems/*/*/hist.sqlite")
    p = re.compile("hist/home/(?P<user>.*)/notebooks/pl/(?P<note>.*)/problems/(?P<topic>.*)/(?P<prob>.*)/hist.sqlite")
    D = []
    for sqlite in sqlites:
        m = p.match(sqlite)
        assert(m), sqlite
        user, note, topic, prob = m.group("user", "note", "topic", "prob")
        utac = user_data[user]["utac"]
        name = user_data[user]["real_name"]
        student_id = user_data[user]["id"]
        html = f"html/home/{user}/notebooks/pl/{note}/problems/{topic}/{prob}/hist.html"
        for c in analyze_sqlite(sqlite):
            C = {"user": user, "name": name, "student_id" : student_id, "utac": utac, "topic": topic, "prob": prob, "html": html}
            C.update(c)
            D.append(C)
    return D

def gen_js(D, a_js):
    data = json.dumps(D, indent=2, ensure_ascii=False)
    prob = json.dumps(PROBLEM_INDEX, indent=2, ensure_ascii=False)
    with open(a_js, "w") as f:
        f.write(f"const PROBLEM_INDEX = {prob};\n")
        f.write(f"const DATA = {data};\n")

def get_user_info(a_ods):
    df = pd.read_excel(a_ods)
    pl = df[df["class"] == "pl"][["user", "utac", "real_name", "id"]]
    D = pl.set_index("user").to_dict(orient="index")
    return D

def main():
    U = get_user_info("ldap_users_taulec.ods")
    D = make_dict(U)
    gen_js(D, "activity/data.js")

main()

    
