#!/usr/bin/python3

"""
mk_version.py
"""

import os
import re
import sys
import argparse

def eval_expr(expr, directives):
    """
    evaluate expression like "VER == 2" under directives
    like {"VER" : 3}
    """
    return eval(expr, directives)

def dict_replace(line, directives):
    """
    if {"VER" : 1} is in directives, replace %%VER%% with 1
    """
    x = line
    for k, v in directives.items():
        orig = "%%" + k + "%%"
        x = x.replace(orig, str(v))
    return x

class parser:
    """
    parse source file
    """
    def __init__(self, fp, mode):
        self.fp = fp
        self.line_no = 0
        self.next_line()
        self.mode = mode

    def classify_line(self):
        not_implemented

    def next_line(self):
        """
        get next line
        """
        self.line_no += 1
        self.line = self.fp.readline()
        self.tok, self.expr = self.classify_line()

    def parse_error(self, tok):
        """
        signal parse error
        """
        sys.stderr.write("parse error:%s:%d: expected %s, but got %s [%s]\n"
                         % (self.fp.name, self.line_no, tok, self.tok, self.line))
        assert(0)

    def chk_tok(self, tok):
        if self.tok != tok:
            self.parse_error(tok)
        
    def eat_if(self, directives, context):
        """
        eat the current line of "if"
        """
        self.chk_tok("if")
        e = eval_expr(self.expr, directives)
        #context.insert(0, e)
        context.insert(0, [e])
        self.next_line()

    def eat_elif(self, directives, context):
        """
        eat the current line of "elif"
        """
        self.chk_tok("elif")
        e = eval_expr(self.expr, directives)
        # this clause becomes on only if
        # (1) there were no previous clauses that were on and
        # (2) the expression of this clause is true
        context[0].insert(0, (not any(context[0])) and e)
        self.next_line()

    def eat_else(self, directives, context):
        """
        eat the current line of "else"
        """
        self.chk_tok("else")
        context[0].insert(0, (not any(context[0])))
        self.next_line()

    def eat_endif(self, directives, context):
        """
        eat the current line of "endif"
        """
        self.chk_tok("endif")
        context.pop(0)
        self.next_line()

    def eat_eof(self):
        """
        eat the current line of "endif"
        """
        self.chk_tok("eof")

    def parse_clause(self, directives, context):
        """
        parse a number of lines between two #ifpy, 
        #elifpy, #elsepy, #endifpy etc.
        """
        while 1:
            if self.tok == "if":
                self.parse_if_directive(directives, context)
            elif self.tok == "regular" or self.tok == "comment":
                # this line is printed if context is like
                # [[1,...],[1,...],...,[1,...]]
                if all(clause[0] for clause in context):
                    if self.tok == "regular":
                        if self.mode == "regular":
                            line_ex = dict_replace(self.line, directives)
                            print(line_ex, end="")
                    elif self.tok == "comment":
                        if self.mode == "comment":
                            print(self.expr)
                    else:
                        assert(self.tok in ["regular", "comment"]), self.tok
                self.next_line()
            else:
                break

    def parse_if_directive(self, directives, context):
        """
        parse the entire if directive from #ifpy to #endifpy
        """
        # ifpy l* (elifpy l*)* (elsepy l*)? endifpy
        self.eat_if(directives, context)
        self.parse_clause(directives, context)
        while self.tok == "elif":
            self.eat_elif(directives, context)
            self.parse_clause(directives, context)
        if self.tok == "else":
            self.eat_else(directives, context)
            self.parse_clause(directives, context)
        self.eat_endif(directives, context)

    def parse_file(self, directives):
        """
        parse the entire file
        """
        context = []
        self.parse_clause(directives, context)
        self.eat_eof()

    def close(self):
        self.fp.close()

class parser_gen(parser):
    def classify_line(self):
        """
        attach token label to the current line
        """
        if self.line == "":
            return "eof", None
        line = self.line.rstrip()
        m = re.match(r"#com\s+(?P<comment>.*)", line)
        if m:
            return "comment", m.group("comment")
        m = re.match(r"#ifpy\s+(?P<expr>.*)", line)
        if m:
            return "if", m.group("expr")
        m = re.match(r"#elifpy\s+(?P<expr>.*)", line)
        if m:
            return "elif", m.group("expr")
        m = re.match(r"#elsepy\s*", line)
        if m:
            return "else", None
        m = re.match(r"#endifpy\s*", line)
        if m:
            return "endif", None
        return "regular", None

class parser_ml(parser):
    def classify_line(self):
        """
        attach token label to the current line
        """
        if self.line == "":
            return "eof", None
        line = self.line.rstrip()
        m = re.match(r"\(\*\* com\s+(?P<comment>.*)\*\)", line)
        if m:
            return "comment", m.group("comment")
        m = re.match(r"\(\*\* if\s+(?P<expr>.*)\*\)", line)
        if m:
            return "if", m.group("expr")
        m = re.match(r"\(\*\* elif\s+(?P<expr>.*)\*\)", line)
        if m:
            return "elif", m.group("expr")
        m = re.match(r"\(\*\* else\s*\*\)", line)
        if m:
            return "else", None
        m = re.match(r"\(\*\* endif\s*\*\)", line)
        if m:
            return "endif", None
        return "regular", None
    
class parser_c(parser):
    def classify_line(self):
        """
        attach token label to the current line
        """
        if self.line == "":
            return "eof", None
        line = self.line.rstrip()
        m = re.match(r"/\*\*\* com\s+(?P<comment>.*)\*/", line)
        if m:
            return "comment", m.group("comment")
        m = re.match(r"/\*\*\* if\s+(?P<expr>.*)\*/", line)
        if m:
            return "if", m.group("expr")
        m = re.match(r"/\*\*\* elif\s+(?P<expr>.*)\*/", line)
        if m:
            return "elif", m.group("expr")
        m = re.match(r"/\*\*\* else\s*\*/", line)
        if m:
            return "else", None
        m = re.match(r"/\*\*\* endif\s*\*/", line)
        if m:
            return "endif", None
        return "regular", None
    
class parser_py(parser):
    def classify_line(self):
        """
        attach token label to the current line
        """
        if self.line == "":
            return "eof", None
        line = self.line.rstrip()
        m = re.match(r"### com\s+(?P<comment>.*)", line)
        if m:
            return "comment", m.group("comment")
        m = re.match(r"### if\s+(?P<expr>.*)", line)
        if m:
            return "if", m.group("expr")
        m = re.match(r"### elif\s+(?P<expr>.*)", line)
        if m:
            return "elif", m.group("expr")
        m = re.match(r"### else\s*", line)
        if m:
            return "else", None
        m = re.match(r"### endif\s*", line)
        if m:
            return "endif", None
        return "regular", None
    
def parse_int_or_string(x):
    try:
        return int(x)
    except ValueError:
        return x
    
def parse_var_defs(var_defs):
    """
    parse VAR=DEF
    """
    D = {}
    for vd in var_defs:
        m = re.match("(?P<var>.*?)=(?P<def>.*)", vd)
        assert(m), vd
        D[m.group("var")] = parse_int_or_string(m.group("def"))
    return D

def parse_args(argv):
    """
    parse command line args
    """
    psr = argparse.ArgumentParser(prog=argv[0])
    psr.add_argument("-D", dest="var_defs", default=[], action="append")
    psr.add_argument("--mode", dest="mode", metavar="MODE(regular/comment)",
                     default="regular")
    psr.add_argument("--lang", dest="lang", metavar="LANG(c/py/ml/jl/go/rs)")
    psr.add_argument("files", metavar="FILE", nargs="+")
    opt = psr.parse_args(argv[1:])
    opt.directives = parse_var_defs(opt.var_defs)
    full = opt.files[0]
    filename = os.path.basename(full)
    base = os.path.splitext(filename)[0]
    opt.directives["FULLNAME"] = full
    opt.directives["FILENAME"] = filename
    opt.directives["BASENAME"] = base
    return opt

def mk_parser(src, mode, lang):
    fp = open(src)
    if lang is None:
        base,ext = os.path.splitext(src)
        langs = ["c", "py", "ml", "jl", "go", "rs"]
        assert(ext[1:] in langs), ext
        lang = ext[1:]
    if lang == "gen":
        return parser_gen(fp, mode)
    elif lang == "py":
        return parser_py(fp, mode)
    elif lang == "ml":
        return parser_ml(fp, mode)
    elif lang == "jl":
        return parser_py(fp, mode)
    elif lang == "c":
        return parser_gen(fp, mode)
    elif lang == "go":
        return parser_c(fp, mode)
    elif lang == "rs":
        return parser_c(fp, mode)
    else:
        assert(0), lang
    return psr

def main():
    """
    main
    """
    opt = parse_args(sys.argv)
    for src in opt.files:
        psr = mk_parser(src, opt.mode, opt.lang)
        psr.parse_file(opt.directives)
        # handle_directives(fp, opt.directives)
        psr.close()

if __name__ == "__main__":
    main()
