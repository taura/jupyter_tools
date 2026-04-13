#!/usr/bin/env python

import glob
import os
import re
import sys
import sqlite3

import problem_index
PROBLEM_INDEX = problem_index.PROBLEM_INDEX
USERS = [f"u{x}" for x in range(26000, 26099)]

def analyze_sqlite(hist_sqlite):
    co = sqlite3.connect(hist_sqlite)
    langs = ["go", "jl", "ml", "rs"]
    C = {"hey" : 0}
    for lang in langs:
        C["writefile",lang] = 0
        for cmd in ["compile", "run"]:
            for ok in [0,1]:
                C["bash",lang,cmd,ok] = 0
    for ok in [0,1]:
        C["bash","?","?",ok] = 0
    for t0, magic, line, cell, inpt, t1, output, retval in co.execute("select * from hist"):
        if magic == "writefile":
            for lang in langs:
                if line.startswith(f"{lang}/") and line.endswith(f".{lang}"):
                    C[magic,lang] += 1
        elif magic == "bash":
            found = 0
            for kws, lang, cmd in [([".go", "build"], "go", "compile"),
                                   ([".ml", "ocaml"], "ml", "compile"),
                                   ([".rs", "rustc"], "rs", "compile"),
                                   (["go/"], "go", "run"),
                                   (["jl/"], "jl", "run"),
                                   (["ml/"], "ml", "run"),
                                   (["rs/"], "rs", "run"),
                                   ]:
                if all([kw in cell for kw in kws]):
                    found = 1
                    ok = int(retval == 0)
                    C[magic,lang,cmd,ok] += 1
                    break
            else:
                ok = int(retval == 0)
                C[magic,"?","?",ok] += 1
        elif magic == "hey":
            C[magic] += 1
        else:
            assert(0), magic
    return C

def info2cell(html, C, individual):
    def R(x):
        if x == 0:
            return "-"
        elif x > 5:
            return f"<font color=red>{x}</font>"
        else:
            return f"{x}"
    def B(x):
        if x == 0:
            return f"-"
        else:
            return f"<font color=green>{x}</font>"
    if html is None:
        html_s = ""
    else:
        html_s = f'<a href="{html}">log</a>'
    go_ok = "✅️" if individual and C["bash","go","run",1] > 0 else ""
    jl_ok = "✅️" if individual and C["bash","jl","run",1] > 0 else ""
    ml_ok = "✅️" if individual and C["bash","ml","run",1] > 0 else ""
    rs_ok = "✅️" if individual and C["bash","rs","run",1] > 0 else ""
    if 1:
        return f"""<table>
        <tr><td>{R(C["bash","go","compile",0])}</td><td>{R(C["bash","go","run",0])}</td><td>{go_ok}</td></tr>
        <tr><td>{R(C["bash","jl","compile",0])}</td><td>{R(C["bash","jl","run",0])}</td><td>{jl_ok}</td></tr>
        <tr><td>{R(C["bash","ml","compile",0])}</td><td>{R(C["bash","ml","run",0])}</td><td>{ml_ok}</td></tr>
        <tr><td>{R(C["bash","rs","compile",0])}</td><td>{R(C["bash","rs","run",0])}</td><td>{rs_ok}</td></tr>
        <tr><td>{B(C["bash","?","?",1])}</td><td>{R(C["bash","?","?",0])}</td></tr>
        <tr><td>{R(C["hey"])}</td></tr>
        <tr><td>{html_s}</td></tr>
        </table>
        """
    else:
        return f"""
        {B(C["writefile","go"])}/{B(C["bash","go","compile",1])}/{R(C["bash","go","compile",0])}/{B(C["bash","go","run",1])}/{R(C["bash","go","run",0])}{go_ok}<br/>
        {B(C["writefile","jl"])}/{B(C["bash","jl","compile",1])}/{R(C["bash","jl","compile",0])}/{B(C["bash","jl","run",1])}/{R(C["bash","jl","run",0])}{jl_ok}<br/>
        {B(C["writefile","ml"])}/{B(C["bash","ml","compile",1])}/{R(C["bash","ml","compile",0])}/{B(C["bash","ml","run",1])}/{R(C["bash","ml","run",0])}{ml_ok}<br/>
        {B(C["writefile","rs"])}/{B(C["bash","rs","compile",1])}/{R(C["bash","rs","compile",0])}/{B(C["bash","rs","run",1])}/{R(C["bash","rs","run",0])}{rs_ok}<br/>
        {B(C["bash","?","?",1])}/{R(C["bash","?","?",0])}<br/>
        {R(C["hey"])}
        {html_s}
    """

def make_dict():
    """
    make a dictionary of (topic, problem) -> html
    """
    sqlites = glob.glob("hist/home/*/notebooks/pl/*/problems/*/*/hist.sqlite")
    p = re.compile("hist/home/(?P<user>.*)/notebooks/pl/(?P<note>.*)/problems/(?P<topic>.*)/(?P<prob>.*)/hist.sqlite")
    D = {}
    for sqlite in sqlites:
        m = p.match(sqlite)
        assert(m), sqlite
        user, note, topic, prob = m.group("user", "note", "topic", "prob")
        html = f"html/home/{user}/notebooks/pl/{note}/problems/{topic}/{prob}/hist.html"
        C = analyze_sqlite(sqlite)
        D[user, topic, prob] = (html, C)
    return D

def aggr_users_of_problem(D, users, topic, prob):
    C = {}
    for u in users:
        _, dC = D.get((u, topic, prob), (None, None))
        if dC is not None:
            for k, v in dC.items():
                C[k] = C.get(k, 0) + v
    return C

def aggr_problems_of_user(D, problem_index, user):
    C = {}
    for t, ps in problem_index:
        for p in ps:
            _, dC = D.get((user, t, p), (None, None))
            if dC is not None:
                for k, v in dC.items():
                    C[k] = C.get(k, 0) + v
    return C

def gen_table(users, problem_index, D, wp):
    w = wp.write
    # table
    # col group
    if 1:
        w(f"""<table border=1>\n""")
    else:
        w(f"""<table style="table-layout: fixed; width: 100%;" border=1>\n""")
        w(f"<colgroup>\n")
        w(f"""<col style="width: 60px;">\n""")
        for t,ps in problem_index:
            for p in ps:
                w(f"""<col style="width: 50px;">\n""")
    w(f"</colgroup>\n")
    # header
    w(f"<thead>\n")
    w(f"<tr>\n")
    w(f"<td><br/></td>\n")
    for t,ps in problem_index:
        for p in ps:
            w(f"<td>{t}/{p}</td>\n")
    w(f"</tr>\n")
    w(f"</thead>\n")
    # body
    w(f"<tbody>\n")
    # the first line showing aggregate of all users for each problem
    w(f"<tr>\n")
    w(f"<td><br/></td>\n")
    for t,ps in problem_index:
        for p in ps:
            prob_info = aggr_users_of_problem(D, users, t, p)
            if prob_info:
                prob_info_s = info2cell(None, prob_info, 0)
                w(f"""<td>{prob_info_s}</td>\n""")
            else:
                w(f"""<td><br/></td>\n""")
    w(f"</tr>\n")
    # a row per user
    for u in users:
        w(f"<tr>\n")
        # aggregate all problems by this user
        user_info = aggr_problems_of_user(D, problem_index, u)
        if user_info:
            user_info_s = info2cell(None, user_info, 0)
            w(f"""<td>{u}<br/>{user_info_s}</td>\n""")
        else:
            w(f"""<td>{u}</td>\n""")
        for t,ps in problem_index:
            for p in ps:
                html_info = D.get((u, t, p))
                if html_info:
                    html, info = html_info
                    info_s = info2cell(html, info, 1)
                    w(f"""<td>{info_s}</td>\n""")
                else:
                    w(f"""<td><br/></td>\n""")
        w(f"</tr>\n")
    w(f"</tbody>\n")
    w(f"</table>\n")

header = """<!DOCTYPE html>
<html lang="us">
<head>
<style>
    td {
      padding: 1px;
    }
    table {
      border-spacing: 0px;
    }
</style>
</head>
<body>
"""

trailer = """
</body>
</html>
"""

def main():
    D = make_dict()
    wp = sys.stdout
    wp.write(header)
    gen_table(USERS, PROBLEM_INDEX, D, wp)
    wp.write(trailer)
    wp.close()

main()

    
