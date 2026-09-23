#!/usr/bin/env python
import sys

def main():
    filenames = []
    D = {}
    for o in sys.argv[1:]:
        if "=" in o:
            [var, val] = o.split("=", 1)
            D[var.strip()] = val.strip()
        else:
            filenames.append(o)
    S = []
    for f in filenames:
        fp = open(f)
        S.append(fp.read())
    s = "".join(S)
    t = s.format(**D)
    print(t, end="")

main()
