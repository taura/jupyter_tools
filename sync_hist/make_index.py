#!/usr/bin/env python

import csv
import glob
import os
import re
import sys
import sqlite3

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
    return f"""<table>
    <tr><td><br/></td><td>C</td><td>R</td><td><br/></td></tr>
    <tr><td>go</td><td>{R(C["bash","go","compile",0])}</td><td>{R(C["bash","go","run",0])}</td><td>{go_ok}</td></tr>
    <tr><td>jl</td><td>{R(C["bash","jl","compile",0])}</td><td>{R(C["bash","jl","run",0])}</td><td>{jl_ok}</td></tr>
    <tr><td>ml</td><td>{R(C["bash","ml","compile",0])}</td><td>{R(C["bash","ml","run",0])}</td><td>{ml_ok}</td></tr>
    <tr><td>rs</td><td>{R(C["bash","rs","compile",0])}</td><td>{R(C["bash","rs","run",0])}</td><td>{rs_ok}</td></tr>
    <tr><td>??</td><td>{B(C["bash","?","?",1])}</td><td>{R(C["bash","?","?",0])}</td></tr>
    <tr><td>hey</td><td>{R(C["hey"])}</td></tr>
    <tr><td>{html_s}</td></tr>
    </table>
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

def gen_csv(row_labels, col_labels, cells, a_csv):
    with open(a_csv, "w") as f:
        wp = csv.DictWriter(f, fieldnames=[""] + col_labels)
        wp.writeheader()
        for row_label in row_labels:
            row = {"": row_label}
            for col_label in col_labels:
                row[col_label] = cells.get((row_label, col_label), "")
            wp.writerow(row)

def gen_cells(users, problem_index, D):
    """
    D : (user, topic, problem) -> (html, C)
    """
    cells = {}
    rows = [f"sum"] + users
    cols = [f"sum"] + [f"{t}/{p}" for t,ps in problem_index for p in ps]
    # make a sum cell for each problem in the "sum" row
    for t,ps in problem_index:
        for p in ps:
            prob_info = aggr_users_of_problem(D, users, t, p)
            if prob_info:
                prob_info_s = info2cell(None, prob_info, 0)
                cells["sum", f"{t}/{p}"] = prob_info_s
    # make a sum cell for each user in the "sum" column
    for u in users:
        user_info = aggr_problems_of_user(D, problem_index, u)
        if user_info:
            user_info_s = info2cell(None, user_info, 0)
            cells[u, "sum"] = user_info_s
    # make all cells user x problem
    for u in users:
        for t,ps in problem_index:
            for p in ps:
                html_info = D.get((u, t, p))
                if html_info:
                    html, info = html_info
                    info_s = info2cell(html, info, 1)
                    cells[u, f"{t}/{p}"] = info_s
    return rows, cols, cells
    
def gen_table(users, problem_index, D, wp):
    w = wp.write
    # table
    # col group
    w(f"""<table border=1>\n""")
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
                    w(f"""<td><br/>{info_s}</td>\n""")
                else:
                    w(f"""<td><br/></td>\n""")
        w(f"</tr>\n")
    w(f"</tbody>\n")
    w(f"</table>\n")

header = """<!DOCTYPE html>
<html lang="us">
<head>
<style>
    body {
      font-family: Arial, sans-serif;
    }
    td {
      padding: 1px;
      vertical-align: top;
    }
    table {
      border-spacing: 0px;
    }
</style>
</head>
<body>

<ul>
<li> each number (or '-') in a cell shows how many times a user has experienced compile errors ('C' column) or a runtime errors ('R' column) for a certain language (e.g. go, jl, ml, rs) on a certain problem. '-' means 0 (never)</li>
<li> check mark (✅️) in the rightmost column of a problem means that the user has successfully run a solution for that problem at least once. </li>
<li> the row with '??' in a cell shows the number of times a user has experienced runtime errors with unknown language (could not guess the language from command line) </li>
<li> the row with 'hey' in a cell the number of times a user called the AI tutor</li>
<li> the first row of the table (with empty user) shows the aggregate of all users for each problem. </li>
<li> the first column of the table (with empty problem) shows the aggregate of all problems for each user. </li>
<li> the log link in a cell shows the detailed history of the user for that problem. </li>
</ul>


"""

trailer = """
</body>
</html>
"""

def main():
    D = make_dict()
    if 1:
        rows, cols, cells = gen_cells(USERS, PROBLEM_INDEX, D)
        gen_csv(rows, cols, cells, "index.csv")
    else:
        wp = sys.stdout
        wp.write(header)
        gen_table(USERS, PROBLEM_INDEX, D, wp)
        wp.write(trailer)
        wp.close()

main()

    
