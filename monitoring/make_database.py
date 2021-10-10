#!/usr/bin/python3

import argparse
import json
import os
import re
import sqlite3
import sys
import time

def do_sql(conn, stmt, dry_run, *vals):
    """
    run stmt on sqlite connection conn
    """
    print(stmt, vals)
    if dry_run == 0:
        return conn.execute(stmt, vals)
    else:
        return []

def open_database(a_sqlite, dry_run):
    """
    connect to a_sqlite
    """
    conn = sqlite3.connect(a_sqlite)
    do_sql(conn,
           """create table if not exists
           summary(filename unique, t, code_ok, code_display, code_stream, code_error, code_empty)""",
           dry_run)
    do_sql(conn,
           """create table if not exists
           problems(filename, grade_id, result)""",
           dry_run)
    return conn

def get_timestamp(filename):
    st = os.stat(filename)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime))
    return stamp

def insert_ipynb_info(conn, path, filename, timestamp, info, dry_run):
    """
    insert record (filename, info) 
    """
    vals = [filename, timestamp] + list(info)
    print("path = {}".format(path))
    do_sql(conn,
           """insert or replace into
           summary(filename, t, 
           code_ok, code_display, code_stream, code_error, code_empty)
           values (?,?,?,?,?,?,?)""",
           dry_run,
           *vals)
    conn.commit()

class ipynb_parser:
    """
    parser for ipynb file
    """
    def __init__(self):
        pass
    def print_cell_stats(self, a_ipynb, counts):
        print("{} :".format(a_ipynb))
        for cell_type, counts_of_type in counts.items():
            print(" {} :".format(cell_type))
            for grade, counts_of_grade in counts_of_type.items():
                print("  {} :".format(grade))
                for output_type, count in counts_of_grade.items():
                    print("   {} : {}".format(output_type, count))
        
    def parse(self, a_ipynb):
        fp = open(a_ipynb)
        nb = json.load(fp)
        # cell_type -> grade -> list of (grade_id, source, results)
        cells = {cell_type : {True : [], False :[]} 
                 for cell_type in ["raw", "markdown", "code"]}
        for cell in nb["cells"]:
            cell_type = cell["cell_type"]
            nbgrader = cell["metadata"].get("nbgrader")
            if nbgrader is None:
                continue
            if "grade_id" not in nbgrader:
                continue
            grade_id = nbgrader["grade_id"]
            grade = nbgrader["grade"]
            source = "".join(cell["source"])
            if cell_type == "code":
                # code -> 実行結果がOKかerrorか
                output_types = [out["output_type"] for out in cell["outputs"]]
            else:
                output_types = []
            cells[cell_type][grade].append((grade_id, source, output_types))
        fp.close()
        counts = self.count_cell_stats(cells)
        if 0:
            self.print_cell_stats(a_ipynb, counts)
        status = {s : counts["code"][True][s] + (0 * counts["code"][False][s])
                  for s in ["execute_result", "display_data", "stream",
                            "error", "non-empty", "empty"]}
        return (status["execute_result"], status["display_data"],
                status["stream"], status["error"], status["empty"])

    def calc_output_type(self, source, output_types):
        for output_type in ["error", "display_data", "stream", "execute_result"]:
            if output_type in output_types:
                return output_type
        if len(source) == 0:
            return "empty"
        else:
            return "non-empty"
        
    def count_cell_stats(self, cells):
        """
        counts["markdown" or "code"][true or false]["empty"/"non-empty"/"execute_result"/"display_data"/"stream"/"error"]
        """
        counts = {cell_type :
                  {grade :
                   {"empty" : 0,
                    "non-empty" : 0,
                    "execute_result" : 0,
                    "display_data" : 0,
                    "stream" : 0,
                    "error" : 0}
                   for grade in [True, False]}
                  for cell_type in ["raw", "markdown", "code"]}
        for cell_type, cells_of_type in cells.items():
            for grade, cells_of_grade in cells_of_type.items():
                for grade_id, source, output_types in cells_of_grade:
                    if 1:
                        output_type = self.calc_output_type(source, output_types)
                        counts[cell_type][grade][output_type] += 1
                    else:
                        if len(source) > 0:
                            counts[cell_type][grade]["non-empty"] += 1
                        else:
                            counts[cell_type][grade]["empty"] += 1
                        for output_type in output_types:
                            counts[cell_type][grade][output_type] += 1
        return counts

def read_copied_files(rsync_out, dest_dir, a_sqlite, dry_run):
    pat = re.compile("(?P<info>.{11})\|(?P<path>.*)\|$")
    conn = open_database(a_sqlite, dry_run)
    psr = ipynb_parser()
    with open(rsync_out) as fp:
        suffix_line = next(fp)
        match = re.match("suffix=(?P<suffix>.*)", suffix_line)
        bak_suffix = match.group("suffix")
        for line in fp:
            matched = pat.match(line)
            assert(matched), line
            info = matched.group("info")
            if info[1] != "f":
                continue
            org_path = matched.group("path")
            # if we see a path name in rsync output,
            # like abc.ext, what happened is either
            # (1) abc.ext, did not exist and was just created, or
            # (2) abc.ext did exist and was renamed to abc.ext.suffix
            #     and abc.ext was created again
            # so we need to check abc.ext and abc.ext.suffix
            # the latter is renamed to abc.suffix.ext
            for path, suffix in [(org_path, ""), (org_path, bak_suffix)]:
                base, ext = os.path.splitext(path)
                if base[:1] == "/": # absolute path
                    base = base[1:]
                path0 = "{}/{}{}{}".format(dest_dir, base, ext, suffix)
                path1 = "{}/{}{}{}".format(dest_dir, base, suffix, ext)
                if ext == ".ipynb":
                    rel_path = "{}{}{}".format(base, suffix, ext)
                    if os.path.exists(path0):
                        xinfo = psr.parse(path0)
                        timestamp = get_timestamp(path0)
                        insert_ipynb_info(conn, path0, rel_path, timestamp, xinfo, dry_run)
                        if suffix != "":
                            os.rename(path0, path1)
                    elif os.path.exists(path1):
                        xinfo = psr.parse(path1)
                        timestamp = get_timestamp(path1)
                        insert_ipynb_info(conn, path1, rel_path, timestamp, xinfo, dry_run)
                if 0:
                    if os.path.exists(path0):
                        if ext == ".ipynb":
                            info = psr.parse(path0)
                            timestamp = get_timestamp(path0)
                            rel_path1 = "{}{}{}".format(base, suffix, ext)
                            insert_ipynb_info(conn, rel_path1, timestamp, info, dry_run)
                        if suffix != "":
                            os.rename(path0, path1)
    conn.close()
    return 1                    # OK

def parse_argv(argv):
    psr = argparse.ArgumentParser(prog=argv[0])
    psr.add_argument("--log", default="rsync.log")
    psr.add_argument("--dest", default="dst")
    psr.add_argument("--db", default="a.sqlite")
    psr.add_argument("--dry-run", default=0, type=int)
    psr.add_argument("--parse-only")
    opt = psr.parse_args(argv[1:])
    return opt

def main():
    opt = parse_argv(sys.argv)
    if opt.parse_only:
        psr = ipynb_parser()
        info = psr.parse(opt.parse_only)
        return 0
    elif read_copied_files(opt.log, opt.dest, opt.db, opt.dry_run):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
