#!/usr/bin/python3
import json
import shutil
import sys

def fix_cell(cell, grade_ids_seen):
    metadata = cell.get("metadata")
    if metadata is None: return
    nbgrader = metadata.get("nbgrader")
    if nbgrader is None: return
    grade_id = nbgrader.get("grade_id")
    if grade_id is None: return
    if grade_id in grade_ids_seen:
        print(f"removing duplicated grade_id '{grade_id}'", file=sys.stderr)
        del metadata["nbgrader"]
    else:
        grade_ids_seen.add(grade_id)

def fix_json(js):
    grade_ids_seen = set()
    for cell in js["cells"]:
        fix_cell(cell, grade_ids_seen)
    return js
        
def fix_ipynb(i_ipynb, bak_ipynb):
    with open(i_ipynb) as fp:
        js = json.load(fp)
    js = fix_json(js)
    shutil.copy(i_ipynb, bak_ipynb)
    with open(i_ipynb, "w") as wp:
        json.dump(js, wp)
    return js

def main():
    i_ipynb = sys.argv[1]
    bak_ipynb = sys.argv[2] if len(sys.argv) > 2 else f"{i_ipynb}.bak"
    fix_ipynb(i_ipynb, bak_ipynb)

main()
