#!/usr/bin/env python
"""join the tables we have about students into a single Excel

  data/utas.xlsx    the official student list (学生証番号, 氏名, ...)
  data/utol.xlsx    the same students plus their submission status on UTOL
  data/jupyter.xlsx the bridge between 学生証番号 and the jupyter user name
  and the result of the students' work, in either of two formats
    --status status.xlsx  the table out2xlsx.py makes out of out/
    --grade  grade.xlsx   the long table work.py export makes out of nbgrader

utas and utol are joined on 学生証番号, jupyter on its id column, and
status/grade on the jupyter user name (u26xxx).

the rows follow the order of utas; students who are not in utas come
after them, in the order of utol, then jupyter, then status/grade.
"""

import argparse
import os
import shutil
import sys

import openpyxl
import pandas as pd
from openpyxl.utils import get_column_letter

# ------------------------------------------------------------------ loading

def cell_val(cell):
    if cell is None or cell.value is None:
        return ""
    return cell.value


def load_sheet(xlsx, sheet=0, header_rows=(0,), start_row=None):
    """read an xlsx and return (header, rows), both of plain values

    header_rows may name several rows (utol has the assignment name on one
    row and the field name on the next); they are forward-filled and joined
    with a slash, so that every column gets a distinct, telling name
    """
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
    rows = [[cell_val(cell) for cell in row] for row in ws.rows]

    parts = []
    for i in header_rows:
        line, last = [], ""
        for value in rows[i]:
            last = value if value != "" else last
            line.append(str(last))
        parts.append(line)
    header = ["/".join(dict.fromkeys(p for p in col if p != ""))
              for col in zip(*parts)]

    if start_row is None:
        start_row = max(header_rows) + 1
    return header, rows[start_row:]


def load_status(xlsx):
    """status.xlsx : 3 header rows (topic, problem, lang), then a row per user

    returns (header, {user : [(value, link), ...]})

    the columns added by hand hold formulas whose references are relative to
    status.xlsx; they would mean something else entirely once moved into the
    joined sheet, so we take the value Excel cached for them rather than the
    formula itself
    """
    ws = openpyxl.load_workbook(xlsx, data_only=True).worksheets[0]
    formulas = openpyxl.load_workbook(xlsx).worksheets[0]
    rows = list(ws.rows)

    header = []
    for j in range(1, ws.max_column):
        name = "/".join(dict.fromkeys(
            str(cell_val(rows[i][j])) for i in range(3) if cell_val(rows[i][j]) != ""))
        # a column of one's own with no heading at all: name it after itself
        header.append(name if name != "" else f"({get_column_letter(j + 1)})")

    by_user = {}
    n_formula = [0] * len(header)
    n_value = [0] * len(header)
    for i, row in enumerate(rows[3:], start=4):
        user = cell_val(row[0])
        if user == "":
            continue
        cells = []
        for j in range(1, ws.max_column):
            value = cell_val(row[j])
            if value != "":
                n_value[j - 1] += 1
            elif str(formulas.cell(row=i, column=j + 1).value or "").startswith("="):
                n_formula[j - 1] += 1
            cells.append((value, row[j].hyperlink.target
                          if row[j].hyperlink else None))
        by_user[user] = cells

    # a formula that has never been evaluated has no value cached in the file;
    # an empty one is normal (a formula may well yield ""), a whole column of
    # them means the file has not been through Excel/LibreOffice yet
    stale = {header[j] for j in range(len(header))
             if n_formula[j] > 0 and n_value[j] == 0}

    if stale:
        print(f"WARN: {xlsx} has formulas with no value cached in the file:"
              f" {', '.join(sorted(stale))}", file=sys.stderr)
        print(f"WARN: open {xlsx} with Excel/LibreOffice and save it,"
              " so that their values can be copied", file=sys.stderr)
    return header, by_user


def read_csv_xlsx_ods(a_file):
    """read xlsx, ods, or csv and return a pandas data frame"""
    if a_file.endswith(".csv"):
        return pd.read_csv(a_file, keep_default_na=False)
    if a_file.endswith(".ods"):
        return pd.read_excel(a_file, keep_default_na=False, engine="odf")
    if a_file.endswith(".xlsx"):
        return pd.read_excel(a_file, keep_default_na=False)
    sys.exit(f"{a_file}: not a .csv, .ods or .xlsx")


def load_grade(a_file,
               row_field="student_id",
               col_fields=("assignment_name", "notebook_name", "prob_name"),
               val_field="manual_score"):
    """grade.xlsx (or .csv/.ods) of work.py export : one row per problem

    pivot it into the same shape as load_status returns, that is
    (header, {user : [(value, link), ...]}), a column per
    assignment/notebook/problem
    """
    df = read_csv_xlsx_ods(a_file)
    data, all_col_keys = {}, set()
    for _, row in df.iterrows():
        user = row[row_field]
        col_keys = tuple(row[field] for field in col_fields)
        all_col_keys.add(col_keys)
        if (user, col_keys) in data:
            print(f"WARN: duplicated {user} {col_keys} in {a_file}", file=sys.stderr)
        data[(user, col_keys)] = row[val_field]
    cols = sorted(all_col_keys)
    header = ["/".join(str(k) for k in col_keys) for col_keys in cols]
    by_user = {}
    for user in dict.fromkeys(df[row_field]):
        by_user[user] = [(data.get((user, col_keys), ""), None) for col_keys in cols]
    return header, by_user


# --------------------------------------------------- the texts UTOL keeps aside

def find_assignment_dir(top, assignment):
    """the directory of ASSIGNMENT under TOP, whose name is a prefix of it"""
    for d in sorted(os.listdir(top)):
        if assignment.replace("/", "_").startswith(d):
            return d
    return None


def read_submission_texts(header, rows, directory, id_col):
    """replace 'submissionText.txt' with what the student actually wrote

    UTOL only names the file in the 成果物ファイル名 cell; the text itself is
    in <directory>/<student_id>/<assignment>/<student_id>_submissionText.txt
    """
    if not os.path.isdir(directory):
        print(f"{directory}: no such directory, submitted texts not read",
              file=sys.stderr)
        return rows
    mark = "/成果物ファイル名"
    text_cols = {j: name[:-len(mark)]
                 for j, name in enumerate(header) if name.endswith(mark)}
    for row in rows:
        student_id = row[id_col]
        for j, assignment in text_cols.items():
            if "submissionText.txt" not in str(row[j]):
                continue
            top = f"{directory}/{student_id}"
            d = find_assignment_dir(top, assignment) if os.path.isdir(top) else None
            if d is None:
                print(f"WARN: no directory for {student_id} {assignment}",
                      file=sys.stderr)
                continue
            with open(f"{top}/{d}/{student_id}_submissionText.txt") as fp:
                row[j] = fp.read()
    return rows


# ------------------------------------------------------------------- keys

def student_id_key(value):
    """学生証番号 as it is written in utas, utol (03-240396) and jupyter"""
    key = str(value).replace("-", "").strip()
    if key.isdigit() and len(key) < 8:
        key = key.zfill(8)
    return key


def index_by(rows, col, key=student_id_key):
    """{key : row}, warning about duplicates"""
    table = {}
    for row in rows:
        k = key(row[col])
        if k == "":
            continue
        if k in table:
            print(f"WARN: duplicated key {k}", file=sys.stderr)
        table[k] = row
    return table


# ------------------------------------------------------------------- join

def join(utas, utol, jupyter, work):
    """(header, rows, links) of the joined table

    utas/utol are (header, rows, id_column), jupyter is (header, rows,
    id_column, user_column) and work is what load_status/load_grade returned;
    links[i][j] is the hyperlink of cell (i, j), if any
    """
    utas_header, utas_rows, utas_id = utas
    utol_header, utol_rows, utol_id = utol
    jupyter_header, jupyter_rows, jupyter_id, jupyter_user = jupyter
    work_header, work_by_user = work

    utas_by_id = index_by(utas_rows, utas_id)
    utol_by_id = index_by(utol_rows, utol_id)
    jupyter_by_id = index_by(jupyter_rows, jupyter_id)
    user_of_id = {student_id_key(row[jupyter_id]): row[jupyter_user]
                  for row in jupyter_rows}

    no_utas = [""] * len(utas_header)
    no_utol = [""] * len(utol_header)
    no_jupyter = [""] * len(jupyter_header)
    no_work = [("", None)] * len(work_header)
    n_left = len(utas_header) + len(utol_header) + len(jupyter_header)

    # the students of utas first, then those only in utol, then those only in
    # jupyter -- each in its own file's order
    order, seen = [], set()
    for rows, id_col in ((utas_rows, utas_id), (utol_rows, utol_id),
                         (jupyter_rows, jupyter_id)):
        for row in rows:
            sid = student_id_key(row[id_col])
            if sid != "" and sid not in seen:
                seen.add(sid)
                order.append(sid)

    rows, links = [], []

    def add(utas_row, utol_row, jupyter_row, cells):
        rows.append(list(utas_row) + list(utol_row) + list(jupyter_row)
                    + [value for value, _ in cells])
        links.append([None] * n_left + [link for _, link in cells])

    for sid in order:
        user = user_of_id.get(sid, "")
        add(utas_by_id.get(sid, no_utas),
            utol_by_id.get(sid, no_utol),
            jupyter_by_id.get(sid, no_jupyter),
            work_by_user.pop(user, no_work) if user else no_work)

    # anyone left has no student id anywhere; show them by user name alone
    for user in sorted(work_by_user):
        print(f"WARN: {user} is in none of utas/utol/jupyter", file=sys.stderr)
        jupyter_row = list(no_jupyter)
        jupyter_row[jupyter_user] = user
        add(no_utas, no_utol, jupyter_row, work_by_user[user])

    header = utas_header + utol_header + jupyter_header + work_header
    return header, rows, links


# ------------------------------------------------------------------ output

# a hidden sheet remembering which columns we wrote last time, so that we can
# tell our own obsolete columns (to be removed) from the ones added by hand
# (to be kept)
RECORD_SHEET = "_join_columns"

BOLD_FONT = openpyxl.styles.Font(bold=True)
LINK_FONT = openpyxl.styles.Font(color="0563C1", underline="single")


def make_backup_file_name(a_xlsx):
    b = f"{a_xlsx}~"
    if not os.path.exists(b):
        return b
    for i in range(10):
        b = f"{a_xlsx}~{i}~"
        if not os.path.exists(b):
            return b
    print(f"too many backup files for {a_xlsx}. perhaps you want to (re)move them",
          file=sys.stderr)
    return None


def create_xlsx(header, rows, links, a_xlsx):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for cell in ws[1]:
        cell.font = BOLD_FONT
    for i, row in enumerate(rows):
        ws.append(row)
        for j, link in enumerate(links[i]):
            if link is not None:
                cell = ws.cell(row=i + 2, column=j + 1)
                cell.hyperlink = link
                cell.font = LINK_FONT
    ws.freeze_panes = "A2"
    write_record(wb, header)
    wb.save(a_xlsx)
    print(f"{ws.max_row} x {ws.max_column} cells written to {a_xlsx}")
    return 1


KEY_COLUMNS = ("学生証番号", "user", "uid")


def keys_of(values, key_cols):
    """what identifies a student in a row: the student id, the jupyter user
    name, whichever of them the row happens to carry"""
    return {(key_cols[j], str(values[j])) for j in key_cols
            if values[j] not in (None, "")}


def row_layout(ws, header, rows, col_map):
    """decide which row of the sheet holds each row of the data

    the sheet may well have been sorted, or have rows of one's own (a note,
    a total) below the data, so we go by who the row is about rather than by
    where it is.  a student the sheet does not have yet is appended at the
    end.

    returns row_map, where row_map[i] is the 1-origin row of the sheet
    holding the i-th row of the data, or None if the sheet says two different
    rows are the same student
    """
    key_cols = {j: name for j, name in enumerate(header) if name in KEY_COLUMNS}

    where = {}
    for r in range(2, ws.max_row + 1):
        values = {j: ws.cell(row=r, column=col_map[j]).value for j in key_cols}
        for key in keys_of(values, key_cols):
            where.setdefault(key, set()).add(r)

    row_map, n_added = [], 0
    for row in rows:
        found = set()
        for key in keys_of({j: row[j] for j in key_cols}, key_cols):
            found |= where.get(key, set())
        if len(found) > 1:
            print(f"WARN: rows {sorted(found)} of the sheet all look like"
                  f" {[row[j] for j in key_cols]}", file=sys.stderr)
            row_map.append(None)
        elif found:
            row_map.append(found.pop())
        else:                           # a student the sheet does not have
            n_added += 1
            row_map.append(ws.max_row + n_added)
    if n_added:
        print(f"note: {n_added} student(s) not in the sheet, appended at the end")
    return row_map


def column_layout(ws, header):
    """decide which column of the sheet holds each column of the data

    a column the sheet does not have is APPENDED AT THE END, never inserted:
    inserting one would move everything to its right, and the formulas of the
    sheet, which we cannot rewrite the way Excel does, would then all point
    at the wrong columns.  the sheet keeps its own columns where they are.

    returns (col_map, appended)
    """
    names = [ws.cell(row=1, column=j).value for j in range(1, ws.max_column + 1)]
    col_map, missing = [], []
    at = 0
    for j, h in enumerate(header):
        k = at
        while k < len(names) and names[k] != h:
            k += 1                      # skip the columns only the sheet has
        if k < len(names):
            col_map.append(k + 1)
            at = k + 1
        else:
            col_map.append(None)        # not there; it goes to the end
            missing.append(j)

    appended = []
    for j in missing:
        col = len(names) + 1
        ws.cell(row=1, column=col, value=header[j]).font = BOLD_FONT
        names.append(header[j])
        col_map[j] = col
        appended.append(header[j])
    return col_map, appended


def read_record(wb):
    """the header we wrote the last time, or None if we never did"""
    if RECORD_SHEET not in wb.sheetnames:
        return None
    return [cell_val(row[0]) for row in wb[RECORD_SHEET].rows]


def write_record(wb, header):
    if RECORD_SHEET in wb.sheetnames:
        del wb[RECORD_SHEET]
    ws = wb.create_sheet(RECORD_SHEET)
    for name in header:
        ws.append([name])
    ws.sheet_state = "hidden"


def update_xlsx(header, rows, links, a_xlsx):
    """write the data into an existing sheet, changing as little as possible

    only cell values are touched; no column or row is ever inserted in the
    middle or removed, so every formula and every reference of the sheet
    keeps meaning what it meant
    """
    wb = openpyxl.load_workbook(a_xlsx)
    ws = wb.worksheets[0]

    col_map, appended = column_layout(ws, header)
    row_map = row_layout(ws, header, rows, col_map)

    n_updated = 0
    for i, row in enumerate(rows):
        if row_map[i] is None:          # we do not know which row is theirs
            continue
        for j, value in enumerate(row):
            cell = ws.cell(row=row_map[i], column=col_map[j])
            if cell.value == value or (cell.value is None and value == ""):
                continue
            cell.value = value
            link = links[i][j]
            if link is not None:
                cell.hyperlink = link
                cell.font = LINK_FONT
            n_updated += 1

    # columns we wrote before and no longer have; removing them ourselves
    # would move the columns after them, so leave that to Excel
    ours = read_record(wb) or []
    names = {ws.cell(row=1, column=j).value for j in range(1, ws.max_column + 1)}
    obsolete = sorted(set(ours) & names - set(header))
    if obsolete:
        print(f"note: {len(obsolete)} column(s) we no longer have are still in"
              f" the sheet; delete them with Excel if you want them gone"
              f" (it will mend the references, we cannot): "
              + ", ".join(obsolete))

    write_record(wb, header)
    wb.save(a_xlsx)
    print(f"{n_updated} cells of {a_xlsx} updated"
          + (f", {len(appended)} columns appended: " + ", ".join(appended)
             if appended else ""))
    return 1


def create_or_update_xlsx(header, rows, links, a_xlsx, update, backup):
    if not (update and os.path.exists(a_xlsx)):
        return create_xlsx(header, rows, links, a_xlsx)
    if backup:
        b_xlsx = make_backup_file_name(a_xlsx)
        if b_xlsx is None:
            return 0
        shutil.copyfile(a_xlsx, b_xlsx)
    return update_xlsx(header, rows, links, a_xlsx)


def parse_args(argv):
    psr = argparse.ArgumentParser(description=__doc__)
    psr.add_argument("--utas", metavar="UTAS_XLSX", default="data/utas.xlsx",
                     help="UTAS Excel (UTAS -> 成績登録 -> select your lecture"
                     " -> Excel出力 -> Excel (和文)); remove password by opening"
                     " it with Windows Excel and File -> 情報 -> ブックの保護"
                     " -> パスワードによる暗号化")
    psr.add_argument("--lms", metavar="LMS_XLSX", default="data/utol.xlsx",
                     help="LMS assignment Excel (UTOL -> 課題 -> 全履修者の提出物"
                     "確認 -> zipダウンロード -> zip解凍 -> ExcelをWindowsのExcel"
                     "で開く -> 情報 -> ブックの保護 -> パスワードによる暗号化"
                     " -> パスワードを空にして保存)")
    psr.add_argument("--lms-submission-files-dir", metavar="DIR",
                     default="data/utol",
                     help="Directory of submitted files (上記zipの解凍してできた"
                     "フォルダ)")
    psr.add_argument("--jupyter", metavar="JUPYTER_XLSX", default="data/jupyter.xlsx",
                     help="Jupyter Excel (Jupyter Googlesheet)")
    work = psr.add_mutually_exclusive_group()
    work.add_argument("--status", metavar="STATUS_XLSX",
                      help="the table out2xlsx.py makes out of out/"
                      " (default: status.xlsx, unless --grade is given)")
    work.add_argument("--grade", metavar="GRADE_CSV/ODS/XLSX",
                      help="grade.xlsx generated by work.py export")
    psr.add_argument("--out", metavar="OUT_XLSX",
                     default="utas_lms_jupyter_nbgrader.xlsx",
                     help="Output Excel")
    psr.add_argument("--update", metavar="0/1", type=int, default=1,
                     help="if the output Excel file exists, update it rather"
                     " than create it")
    psr.add_argument("--backup", metavar="0/1", type=int, default=1,
                     help="if the existing Excel file is updated, make a backup")
    args = psr.parse_args(argv[1:])
    if args.grade is None and args.status is None:
        args.status = "status.xlsx"
    return args


def main():
    args = parse_args(sys.argv)

    utas_header, utas_rows = load_sheet(args.utas, header_rows=(3,))
    utol_header, utol_rows = load_sheet(args.lms, header_rows=(0, 1))
    jupyter_header, jupyter_rows = load_sheet(args.jupyter, header_rows=(0,))
    utol_id = utol_header.index("学生証番号")
    utol_rows = read_submission_texts(utol_header, utol_rows,
                                      args.lms_submission_files_dir, utol_id)

    if args.status is not None:
        work = load_status(args.status)
    else:
        work = load_grade(args.grade)

    header, rows, links = join(
        (utas_header, utas_rows, utas_header.index("学生証番号")),
        (utol_header, utol_rows, utol_id),
        (jupyter_header, jupyter_rows,
         jupyter_header.index("id"), jupyter_header.index("user")),
        work)

    ok = create_or_update_xlsx(header, rows, links, args.out,
                               args.update, args.backup)
    return 0 if ok else 1


sys.exit(main())
