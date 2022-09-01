#!/usr/bin/python3

"""
work.py
"""

import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys

#     submitted_assignment.id == submitted_notebook.assignment_id
# and submitted_notebook.id == grade.notebook_id
# and submitted_notebook.id == base_cell.notebook_id
# submitted_assignment,submitted_notebook,grade,base_cell

def get_submission_dirs(inbound):
    """
    read all ipynb cells in a dir
    and make a dictionary student -> assignment -> directories.
    directories are sorted by their names, which effectively
    sort by timestamps (oldest to newest)
    """
    submissions = {}
    pat = re.compile(r"(?P<student>.*?)\+(?P<assignment>.*?)\+(?P<timestamp>.*?)\+")
    for sub_dir in os.listdir(inbound):
        matched = pat.match(sub_dir)
        if matched is None:
            continue
        student = matched.group("student")
        assignment = matched.group("assignment")
        if student not in submissions:
            submissions[student] = {}
        if assignment not in submissions[student]:
            submissions[student][assignment] = []
        submissions[student][assignment].append("%s/%s" % (inbound, sub_dir))
    for submissions_of_student in submissions.values():
        for submissions_of_student_assignment in submissions_of_student.values():
            submissions_of_student_assignment.sort()
    return submissions

def get_newest_submission_dirs(inbound):
    """
    make a dictionary student -> assignment ->
    the newest submission directory
    """
    submission_dirs = get_submission_dirs(inbound)
    newest_dirs = {}
    for student, dirs_of_student in submission_dirs.items():
        newest_dirs[student] = {}
        for assignment, dirs_of_assignment in dirs_of_student.items():
            newest_dir = dirs_of_assignment[-1]
            newest_dirs[student][assignment] = newest_dir
    return newest_dirs

def answer_cells_of_nb(a_ipynb):
    """
    get the contents of all answer cells (having grade_id)
    in an a_ipynb file
    """
    cells = {}
    with open(a_ipynb) as ipynb_fp:
        content = json.load(ipynb_fp)
        for cell in content["cells"]:
            meta = cell["metadata"]
            nbg = meta.get("nbgrader")
            if nbg is None or not nbg["solution"]:
                continue
            assert("grade_id" in nbg), (a_ipynb, cell)
            prob_name = nbg["grade_id"] # like a1-1-1
            source = cell["source"]
            outputs = cell.get("outputs", [])
            if prob_name in cells:
                if 0:
                    print("WARNING: duplicated problem label {} in {}"
                          .format(prob_name, a_ipynb), file=sys.stderr)
                # assert(prob_name not in cells), prob_name
            cells[prob_name] = source, outputs
    return cells

def answer_cells_of_dir(submission_dir):
    """
    get the contents of all solution cells
    of all ipynb files in a directory
    """
    cells = {}
    files = os.listdir(submission_dir)
    for filename in files:
        if not filename.endswith(".ipynb"):
            continue
        noext = filename[:-6]
        ipynb = "%s/%s" % (submission_dir, filename)
        cells[noext] = answer_cells_of_nb(ipynb)
    return cells

def get_answer_cells(inbound):
    """
    read all ipynb cells in a dir
    and make a dictionary 
    student -> assignment -> notebook_name -> prob_name -> content
    """
    submission_dirs = get_submission_dirs(inbound)
    cells = {}
    for student, dirs_of_student in submission_dirs.items():
        cells[student] = {}
        for assignment, dirs_of_assignment in dirs_of_student.items():
            newest_dir = dirs_of_assignment[-1] # get the newest
            cells_of_student_assignment = answer_cells_of_dir(newest_dir)
            cells[student][assignment] = cells_of_student_assignment
    return cells

def export_program(inbound, dst):
    """
    submission_dirs : student -> assignment -> dir
    """
    submission_dirs = get_newest_submission_dirs(inbound)
    for student, dirs_of_student in submission_dirs.items():
        for assignment, dir_of_assignment in dirs_of_student.items():
            dst_dir = "{}/{}/{}".format(dst, student, assignment)
            shutil.copytree(dir_of_assignment, dst_dir)

def do_sql(conn, sql, *vals):
    """
    issue an sql query on conn
    """
    # print(sql, vals)
    return conn.execute(sql, vals)

SQL_CREATE_COMMENT = """
create temp table commentx as
select submitted_assignment.student_id as student_id,
       assignment.name as assignment_name,
       notebook.name as notebook_name,
       base_cell.name as prob_name,
       comment.id as comment_id,
       comment.auto_comment as auto_comment,
       comment.manual_comment as manual_comment
from
assignment,submitted_assignment,submitted_notebook,notebook,base_cell,comment
on true
and submitted_assignment.assignment_id = assignment.id 
and submitted_notebook.assignment_id = submitted_assignment.id
and notebook.id = submitted_notebook.notebook_id
and base_cell.notebook_id = notebook.id
and comment.notebook_id = submitted_notebook.id
and comment.cell_id = base_cell.id
"""

SQL_CREATE_GRADE = """
create temp table gradex as
select submitted_assignment.student_id as student_id,
       assignment.name as assignment_name,
       notebook.name as notebook_name,
       base_cell.name as prob_name,
       grade.id as grade_id,
       grade.auto_score as auto_score,
       grade.manual_score as manual_score,
       grade.extra_credit as extra_credit,
       grade.needs_manual_grade as needs_manual_grade
from
assignment,submitted_assignment,submitted_notebook,notebook,base_cell,grade
on true
and submitted_assignment.assignment_id = assignment.id
and submitted_notebook.assignment_id = submitted_assignment.id
and notebook.id = submitted_notebook.notebook_id
and base_cell.notebook_id = notebook.id
and grade.notebook_id = submitted_notebook.id
and grade.cell_id = base_cell.id
"""

SQL_JOIN_GRADE_COMMENT = """
create temp table grade_comment as
select 
gradex.student_id as student_id,
gradex.assignment_name as assignment_name,
gradex.notebook_name as notebook_name,
gradex.prob_name as prob_name,
grade_id,
comment_id,
auto_score,
manual_score,
extra_credit,
needs_manual_grade,
auto_comment,
manual_comment
from gradex left join commentx 
on  gradex.student_id = commentx.student_id
and gradex.assignment_name = commentx.assignment_name
and gradex.notebook_name = commentx.notebook_name
and gradex.prob_name = commentx.prob_name
"""

SQL_ANSWER_CELL = """
create temp table answer_cell
  (student_id, 
   assignment_name, 
   notebook_name, 
   prob_name, 
   source, 
   outputs, 
   errors, 
   eval_ok,
   eval_out,
   eval_err,
   eval_diff)
"""

SQL_JOIN_GRADE_COMMENT_CELL = """
create temp table grade_comment_cell as
select 
grade_comment.student_id as student_id,
grade_comment.assignment_name as assignment_name,
grade_comment.notebook_name as notebook_name,
grade_comment.prob_name as prob_name,
source,
outputs,
errors,
eval_ok,
eval_out,
eval_err,
eval_diff,
auto_score,
manual_score,
extra_credit,
auto_comment,
manual_comment,
needs_manual_grade,
grade_id,
comment_id
from grade_comment left join answer_cell
on  grade_comment.student_id = answer_cell.student_id
and grade_comment.assignment_name = answer_cell.assignment_name
and grade_comment.notebook_name = answer_cell.notebook_name
and grade_comment.prob_name = answer_cell.prob_name
"""

SQL_TOTAL_SCORE = """
select 
assignment_name,
student_id,
sum(case when manual_score is NULL then auto_score else manual_score end) as score 
from 
grade_comment_cell
group by student_id,assignment_name 
order by assignment_name, student_id
"""

SQL_SELECT_ALL_GRADE_COMMENT_CELL = """
select * from grade_comment_cell

"""

def get_eval_result(exec_dir, assignment, notebook, prob, student):
    base = "{}/{}/{}/{}/{}".format(exec_dir, assignment, notebook, prob, student)
    eval_result = {}
    for ext in ["ok", "out", "err", "diff"]:
        eval_result[ext] = ""
        f = "{}.{}".format(base, ext)
        if os.path.exists(f):
            fp = open(f, errors="replace")
            output = fp.read()
            fp.close()
            max_cell_sz = 30 * 1024
            output = output[:max_cell_sz]
            eval_result[ext] = "== {} ==\n{}".format(ext, output)
    return eval_result

def join_outputs(outputs):
    # [
    #     {'data':
    #      {'text/plain':
    #       ["val bs_tree_insert : 'a -> 'a bs_tree -> 'a bs_tree = <fun>\n"]
    #       },
    #      'execution_count': 97,
    #      'metadata': {},
    #      'output_type': 'execute_result'
    #      }
    # ]
    out_s = []
    for dic in outputs:
        for val in dic.get("data", {}).values():
            out_s.extend(val)
    return "".join(out_s)
    
def join_errors(outputs):
    # [
    #     {
    #      "ename": "error",
    #      "evalue": "compile_error",
    #      "output_type": "error",
    #      "traceback": [
    #       "File \"[97]\", line 40, characters 0-3:\n40 | end\n     ^^^\nError: Syntax error: 'end' expected\nFile \"[97]\", line 2, characters 0-6:\n2 | object(s:'a)\n    ^^^^^^\n  This 'object' might be unmatched\n"
    #      ]
    #     }
    # ],
    out_s = []
    for dic in outputs:
        out_s.extend(dic.get("traceback", []))
    return "".join(out_s)
    
def make_table_of_cells(conn, cells, exec_dir):
    """
    make a table of cells
    """
    do_sql(conn, SQL_ANSWER_CELL)
    for student, cells_of_student in cells.items():
        for assignment, cells_of_student_notebook in cells_of_student.items():
            for notebook, cells_of_student_notebook_assignment in cells_of_student_notebook.items():
                for prob, (source, outputs) in cells_of_student_notebook_assignment.items():
                    source_s = "".join(source)
                    output_s = join_outputs(outputs)
                    error_s = join_errors(outputs)
                    eval_result = get_eval_result(exec_dir, assignment, notebook, prob, student)
                    do_sql(conn,
                           """insert into answer_cell(student_id, assignment_name, notebook_name, prob_name, source, 
                           outputs, errors, eval_ok, eval_out, eval_err, eval_diff)
                           values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                           student, assignment, notebook, prob,
                           source_s, output_s, error_s,
                           eval_result["ok"], eval_result["out"], eval_result["err"], eval_result["diff"])

def connect_to_db(gradebook_db, inbound, exec_dir):
    """
    connect db and make temporary tables
    """
    cells = get_answer_cells(inbound)
    conn = sqlite3.connect(gradebook_db)
    conn.row_factory = sqlite3.Row
    do_sql(conn, SQL_CREATE_COMMENT)
    do_sql(conn, SQL_CREATE_GRADE)
    do_sql(conn, SQL_JOIN_GRADE_COMMENT)
    make_table_of_cells(conn, cells, exec_dir)
    do_sql(conn, SQL_JOIN_GRADE_COMMENT_CELL)
    return conn

def query(gradebook_db, inbound, exec_dir, sql):
    """
    open database and inbound folder and run sql
    """
    conn = connect_to_db(gradebook_db, inbound, exec_dir)
    for row in do_sql(conn, sql):
        yield row
    conn.close()

def export_csv(gradebook_db, inbound, exec_dir, sql, header, out_csv):
    """
    export notebook info into csv
    """
    conn = connect_to_db(gradebook_db, inbound, exec_dir)
    if out_csv == "-":
        out_wp = sys.stdout
    else:
        out_wp = open(out_csv, "w")
    csv_wp = None
    for row in do_sql(conn, sql):
        if csv_wp is None:
            fields = row.keys()
            csv_wp = csv.DictWriter(out_wp, fields)
            if header:
                csv_wp.writeheader()
        csv_wp.writerow(dict(row))
    if out_wp is not sys.stdout:
        out_wp.close()

def export_txt(gradebook_db, inbound, exec_dir, sql, sep, out_txt):
    """
    export notebook info into txt
    """
    conn = connect_to_db(gradebook_db, inbound, exec_dir)
    if out_txt == "-":
        out_wp = sys.stdout
    else:
        out_wp = open(out_txt, "w")
    for row in do_sql(conn, sql):
        for val in dict(row).values():
            out_wp.write(val)
            out_wp.write("\n" + sep + "\n")
    if out_wp is not sys.stdout:
        out_wp.close()

def export_source(gradebook_db, inbound, exec_dir, student_id, assignment_name, notebook_name, prob_name, sep, out_txt):
    student_id_list = ",".join(['"{}"'.format(s) for s in student_id])
    assignment_name_list = ",".join(['"{}"'.format(s) for s in assignment_name])
    notebook_name_list = ",".join(['"{}"'.format(s) for s in notebook_name])
    prob_name_list = ",".join(['"{}"'.format(s) for s in prob_name])
    sql = ("""select source from grade_comment_cell 
    where student_id in ({student_id_list}) 
    and assignment_name in ({assignment_name_list}) 
    and notebook_name in ({notebook_name_list}) 
    and prob_name in ({prob_name_list}) 
    order by student_id, assignment_name, notebook_name, prob_name"""
           .format(student_id_list=student_id_list,
                   assignment_name_list=assignment_name_list,
                   notebook_name_list=notebook_name_list,
                   prob_name_list=prob_name_list))
    export_txt(gradebook_db, inbound, exec_dir, sql, sep, out_txt)

def export_score(gradebook_db, inbound, score_csv):
    """
    export score in gradebook_db into score_csv
    """
    conn = connect_and_make_temp_tables(gradebook_db, inbound)
    with open(score_csv, "w") as score_wp:
        csv_wp = None
        for row in do_sql(conn, SQL_TOTAL_SCORE):
            if csv_wp is None:
                fields = row.keys()
                csv_wp = csv.DictWriter(score_wp, fields)
                csv_wp.writeheader()
            dic = dict(row)
            csv_wp.writerow(dic)
    conn.close()

def make_sql_val(val):
    """
    make a value suitable for sqlite
    """
    if val == "":
        return None
    return float(val)

def import_grade_csv(grade_csv, gradebook_db):
    """
    import scores in grade_csv into gradebook_db
    """
    conn = sqlite3.connect(gradebook_db)
    conn.row_factory = sqlite3.Row
    with open(grade_csv) as grade_fp:
        csv_fp = csv.DictReader(grade_fp)
        for i, row in enumerate(csv_fp):
            manual_score = make_sql_val(row["manual_score"])
            extra_credit = make_sql_val(row["extra_credit"])
            needs_manual_grade = make_sql_val(row["needs_manual_grade"])
            grade_id = row["grade_id"]
            manual_comment = row["manual_comment"]
            comment_id = row["comment_id"]
            if manual_score is not None:
                needs_manual_grade = 0
            do_sql(conn,
                   """
                   update grade set
                   manual_score = ?,
                   extra_credit = ?,
                   needs_manual_grade = ?
                   where id = ?
                   """,
                   manual_score, extra_credit, needs_manual_grade, grade_id)
            if comment_id is not None:
                do_sql(conn,
                       """update comment set
                       manual_comment = ?
                       where id = ?""",
                       manual_comment, comment_id)
    conn.commit()
    conn.close()

def run(cmd, user):
    subprocess.run(cmd.format(user=user), check=True, shell=True)

def download_notebooks_and_submissions(user):
    os.makedirs("dl", exist_ok=True)
    run("rsync -avz {user}@taulec:notebooks dl/", user)
    run("rsync -avz {user}@taulec:/home/share/nbgrader/exchange/{user}/inbound dl/", user)
    
def upload_gradebook_db(user):
    """
    upload dl/notebooks/gradebook.db
    """
    run("ssh {user}@taulec cp notebooks/gradebook.db notebooks/gradebook.bak.db", user)
    run("scp dl/notebooks/gradebook.db {user}@taulec:notebooks/", user)
    
def parse_args(argv):
    """
    parse command line args
    """
    psr = argparse.ArgumentParser()
    psr.add_argument("--gradebook", metavar="GRADEBOOK_DB",
                     default="dl/notebooks/gradebook.db",
                     help="sqlite3 database of gradebook")
    psr.add_argument("--sql", metavar="SQL_STATEMENT",
                     default=SQL_SELECT_ALL_GRADE_COMMENT_CELL,
                     help="output csv file")
    psr.add_argument("--header", metavar="0/1",
                     default=1, type=int,
                     help="output header")
    psr.add_argument("--csv", metavar="GRADE_CSV",
                     default="grade.csv",
                     help="csv file for export")
    psr.add_argument("--txt", metavar="OUT_TXT",
                     default="out.txt",
                     help="txt file for export-txt")
    psr.add_argument("--inbound", metavar="DIRECTORY",
                     default="dl/inbound",
                     help="inbound directory")
    psr.add_argument("--exec-dir", metavar="DIRECTORY",
                     default="exec",
                     help="exec directory")
    psr.add_argument("--student-id", metavar="STUDENT_ID,STUDENT_ID,...",
                     default="", 
                     help="comma-separated student ids")
    psr.add_argument("--assignment-name", metavar="ASSIGNMENT_NAME,ASSIGNMENT_NAME,...",
                     default="", 
                     help="comma-separated assignment names")
    psr.add_argument("--notebook-name", metavar="NOTEBOOK_NAME,NOTEBOOK_NAME,...",
                     default="", 
                     help="comma-separated notebook names")
    psr.add_argument("--prob-name", metavar="PROB_NAME",
                     default="", 
                     help="comma-separated problem names")
    psr.add_argument("--separater", metavar="SEPARATER",
                     default="\n",
                     help="separater for export-source")
    psr.add_argument("--user", metavar="USER", 
                     help="user name on taulec to download/upload stuff from/to")
    # to be removed
    psr.add_argument("--prog", metavar="DIRECTORY",
                     default="programs",
                     help="program output directory")
    psr.add_argument("command", metavar="COMMAND", nargs=1)
    args = psr.parse_args(argv[1:])
    args.student_id = args.student_id.split(",")
    args.assignment_name = args.assignment_name.split(",")
    args.notebook_name = args.notebook_name.split(",")
    args.prob_name = args.prob_name.split(",")
    return args

def main():
    """
    main
    """
    args = parse_args(sys.argv)
    command = args.command[0]
    if command == "export":
        export_csv(args.gradebook, args.inbound, args.exec_dir, args.sql, args.header, args.csv)
    elif command == "export-txt":
        export_txt(args.gradebook, args.inbound, args.exec_dir, args.sql, args.separater, args.txt)
    elif command == "export-source": # to be removed
        export_source(args.gradebook, args.inbound, args.exec_dir,
                      args.student_id, args.assignment_name,
                      args.notebook_name, args.prob_name,
                      args.separater, args.txt)
    elif command == "import":
        import_grade_csv(args.csv, args.gradebook)
    elif command == "download":
        if args.user is None:
            print("specify user with --user", file=sys.stderr)
            return
        download_notebooks_and_submissions(args.user)
    elif command == "upload":
        if args.user is None:
            print("specify user with --user", file=sys.stderr)
            return
        upload_gradebook_db(args.user)
    elif command == "export_score":
        # not sure what this is for
        query(args.gradebook, args.inbound, args.exec_dir, SQL_TOTAL_SCORE, args.out_csv)
    elif command == "export-program": # to be removed
        export_program(args.inbound, args.prog)
    else:
        assert(0), command


main()
