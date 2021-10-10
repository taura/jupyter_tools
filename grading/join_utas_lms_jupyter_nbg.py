#!/usr/bin/python3

import argparse
import sys

import openpyxl

def load_worksheet(xlsx, sheet=0, header_row=None, start_row=None):
    wb = openpyxl.load_workbook(xlsx, data_only=True) # , read_only=True
    if isinstance(sheet, type(0)):
        ws = wb.worksheets[sheet]
    else:
        ws = wb[sheet]
    rows = list(ws.rows)
    if header_row is None:
        header = None
    else:
        header = [cell.value for cell in rows[header_row]]
    if start_row is None:
        if header_row is None:
            start_row = 0
        else:
            start_row = header_row + 1
    return header, rows[start_row:]

def merge_rows(rows0, make_key0, rows1, make_key1):
    rows0 = sorted(rows0, key=make_key0)
    rows1 = sorted(rows1, key=make_key1)
    n0 = len(rows0)
    n1 = len(rows1)
    ei = (None,) * len(rows0[0]) if n0 > 0 else ()
    ej = (None,) * len(rows1[0]) if n1 > 0 else ()
    merged_rows = []
    i = 0
    j = 0
    while i < n0 or j < n1:
        if j >= n1:
            ri = rows0[i]
            merged_rows.append(ri + ej)
            i += 1
        elif i >= n0:
            rj = rows1[j]
            merged_rows.append(ei + rj)
            j += 1
        else:
            ri = rows0[i]
            rj = rows1[j]
            ki = make_key0(ri)
            kj = make_key1(rj)
            if ki < kj:
                merged_rows.append(ri + ej)
                i += 1
            elif ki > kj:
                merged_rows.append(ei + rj)
                j += 1
            else:
                assert(ki == kj)
                merged_rows.append(ri + rj)
                i += 1
                j += 1
    return merged_rows

def cell_val(cell):
    if cell is None:
        return ""
    elif cell.value is None:
        return ""
    else:
        return cell.value

def make_joined_wb(utas_header, utas_rows, lms_header, lms_rows,
                   jupyter_header, jupyter_rows, nbg_header, nbg_rows):
    utas_id_col = utas_header.index("学生証番号")
    def utas_key(row):
        return cell_val(row[utas_id_col])
    lms_id_col = lms_header.index("学生証番号")
    def lms_key(row):
        return cell_val(row[lms_id_col]).replace("-", "")
    jupyter_id_col = jupyter_header.index("id")
    jupyter_user_col = jupyter_header.index("user")
    def jupyter_id_key(row):
        return cell_val(row[jupyter_id_col]).replace("-", "")
    utas_lms_rows = merge_rows(utas_rows, utas_key, lms_rows, lms_key)
    utas_lms_n_cols = len(utas_lms_rows[0])
    utas_lms_jupyter_rows = merge_rows(utas_lms_rows, utas_key,
                                      jupyter_rows, jupyter_id_key)
    def jupyter_user_key(row):
        return cell_val(row[utas_lms_n_cols + jupyter_user_col])
    nbg_student_id_col = nbg_header.index("student_id")
    def nbg_user_key(row):
        return cell_val(row[nbg_student_id_col])
    all_rows = merge_rows(utas_lms_jupyter_rows, jupyter_user_key,
                          nbg_rows, nbg_user_key)
    all_header = utas_header + lms_header + jupyter_header + nbg_header
    return all_header, all_rows

def save_xlsx(header, rows, a_xlsx):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append([cell.value if cell is not None else None for cell in row])
    wb.save(a_xlsx)

def parse_args(argv):
    psr = argparse.ArgumentParser()
    psr.add_argument("--utas", metavar="UTAS_XLSX",
                     default="data/utas.xlsx",
                     help="UTAS Excel")
    psr.add_argument("--lms", metavar="LMS_XLSX",
                     default="data/lms.xlsx",
                     help="LMS assignment Excel")
    psr.add_argument("--jupyter", metavar="JUPYTER_XLSX",
                     default="data/jupyter.xlsx",
                     help="Jupyter Excel")
    psr.add_argument("--nbg", metavar="NBG_XLSX",
                     default="data/nbg.xlsx",
                     help="nbgrader Excel")
    psr.add_argument("--out", metavar="UTAS_LMS_JUPYTER_NBGRADER_XLSX",
                     default="utas_lms_jupyter_nbgrader.xlsx",
                     help="Output Excel")
    args = psr.parse_args(argv[1:])
    return args

def main():
    args = parse_args(sys.argv)
    utas_header, utas_rows = load_worksheet(args.utas, header_row=3)
    lms_header, lms_rows = load_worksheet(args.lms, sheet='課題全体提出状況',
                                          header_row=1)
    jupyter_header, jupyter_rows = load_worksheet(args.jupyter, header_row=0)
    nbg_header, nbg_rows = load_worksheet(args.nbg, header_row=4)
    header, rows = make_joined_wb(utas_header, utas_rows, lms_header, lms_rows,
                                  jupyter_header, jupyter_rows, nbg_header, nbg_rows)
    save_xlsx(header, rows, args.out)
    return rows
    
main()


