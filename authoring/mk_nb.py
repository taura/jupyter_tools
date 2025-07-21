#!/usr/bin/python3
"""
mk_nb.py
"""
import argparse
import json
import os
import re
import subprocess
import sys

DBG = 2
# Bash, Ocaml default, Python 3, C

def canonicalize_kernel_dict():
    """
    canonicalize kernel name (c -> C etc.)
    """
    comp = {
        "python" : "Python 3 (ipykernel)",
        "py" : "Python 3 (ipykernel)",
        "bash" : "Bash",
        "c" : "C",
        "cc" : "C",
        "c++" : "C",
        "cpp" : "C",
        "go" : "Go",
        "golang" : "Go",
        "jl" : "Julia 1.11.4",
        "julia" : "Julia 1.11.4",
        "ocaml" : "OCaml 4.14.2",
        "caml" : "OCaml 4.14.2",
        "ml" : "OCaml 4.14.2",
        "rs" : "Rust",
        "rust" : "Rust",
        "sos" : "SoS"
    }
    update_comp = {v.lower() : v for v in comp.values()}
    comp.update(update_comp)
    return comp

def make_metadata_python():
    """
    aux data for python kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "Python 3 (ipykernel)",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.10"
        }
    }

def make_metadata_bash():
    """
    aux data for bash kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "Bash",
            "language": "bash",
            "name": "bash"
        },
        "language_info": {
            "codemirror_mode": "shell",
            "file_extension": ".sh",
            "mimetype": "text/x-sh",
            "name": "bash"
        }
    }

def make_metadata_c():
    """
    aux data for c kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "C",
            "language": "c",
            "name": "c_kernel"
        },
        "language_info": {
            "file_extension": ".c",
            "mimetype": "text/plain",
            "name": "c"
        }
    }

def make_metadata_go():
    """
    aux data for go kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "Go",
            "language": "go",
            "name": "gophernotes"
        },
        "language_info": {
            "codemirror_mode": "",
            "file_extension": ".go",
            "mimetype": "",
            "name": "go",
            "nbconvert_exporter": "",
            "pygments_lexer": "",
            "version": "go1.13.8"
        }
    }

def make_metadata_julia():
    """
    aux data for julia kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "Julia 1.11.4",
            "language": "julia",
            "name": "julia-1.11"
        },
        "language_info": {
            "file_extension": ".jl",
            "mimetype": "application/julia",
            "name": "julia",
            "version": "1.11.4"
        }
    }

def make_metadata_ocaml():
    """
    aux data for ocaml kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "OCaml 4.14.2",
            "language": "OCaml",
            "name": "ocaml-jupyter"
        },
        "language_info": {
            "codemirror_mode": "text/x-ocaml",
            "file_extension": ".ml",
            "mimetype": "text/x-ocaml",
            "name": "OCaml",
            "nbconverter_exporter": null,
            "pygments_lexer": "OCaml",
            "version": "4.14.2"
        }
    }

def make_metadata_rust():
    """
    aux data for rust kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "Rust",
            "language": "rust",
            "name": "rust"
        },
        "language_info": {
            "codemirror_mode": "rust",
            "file_extension": ".rs",
            "mimetype": "text/rust",
            "name": "Rust",
            "pygment_lexer": "rust",
            "version": ""
        }
    }

def make_metadata_sos():
    """
    aux data for sos kernel
    """
    return {
        "celltoolbar": "Create Assignment",
        "kernelspec": {
            "display_name": "SoS",
            "language": "sos",
            "name": "sos"
        },
        "language_info": {
            "codemirror_mode": "sos",
            "file_extension": ".sos",
            "mimetype": "text/x-sos",
            "name": "sos",
            "nbconvert_exporter": "sos_notebook.converter.SoS_Exporter",
            "pygments_lexer": "sos"
        },
        "sos": {
            "kernels": [
                ["Bash", "bash", "bash", "", "shell"],
                ["C", "c_kernel", "c", "", ""],
                ["Go", "gophernotes", "go", "", ""],
                ["Julia 1.11.4", "julia-1.11", "julia", "", ""],
                ["OCaml 4.14.2", "ocaml-jupyter", "OCaml", "", "text/x-ocaml"],
                ["Python 3 (ipykernel)", "python3", "python3", "", {"name": "ipython", "version": 3}],
                ["Rust", "rust", "rust", "", ""]
            ],
            "panel": {
                "displayed": True,
                "height": 0
            },
            "version": "0.23.3"
        }
    }

def make_metadata(syntax):
    """
    aux data
    """
    aux_data_dict = {
        "Python 3 (ipykernel)" : make_metadata_python,
        "Bash" : make_metadata_bash,
        "C" : make_metadata_c,
        "Go" : make_metadata_go,
        "Julia 1.11.4" : make_metadata_julia,
        "OCaml 4.14.2" : make_metadata_ocaml,
        "Rust" : make_metadata_rust,
        "SoS" : make_metadata_sos,
    }
    return aux_data_dict[syntax]()

def run_cmd(cmd):
    """
       run cmd and get its standard output
    """
    try:
        proc = subprocess.run(cmd, shell=True, check=True, capture_output=True)
        return proc.stdout.decode("utf-8")
    except OSError:
        return None

def read_file(filename):
    """
        read filename and return its content
    """
    in_fp = open(filename)
    content = in_fp.read()
    in_fp.close()
    return content

class Counter:
    """
    heading counter
    """
    def __init__(self):
        self.heading_format = [
            "{0}.",
            "{0}-{1}.",
            "{0}-{1}-{2}.",
            "{0}-{1}-{2}-{3}.",
        ]
        self.count = []
    def next(self, level):
        """
        next heading
        """
        self.count = self.count[:level]
        n_count = len(self.count)
        if n_count == level:
            self.count[level - 1] += 1
        else:
            self.count += [1] * (level - n_count)
        return self.heading_format[level - 1].format(*self.count)

class ParserBase:
    """
    base class of the parser
    """
    # syntax
    # file := cell*
    # cell := begin_cell | source* | end_cell
    # begin_cell := <!--- cell_attr* --->
    #             | """ --- cell_attr*
    #             | (** --- cell_attr*
    #             | /** --- cell_attr*
    # end_cell := <!--- end --->
    #           | --- """
    #           | --- *)
    #           | --- */
    # cell_attr := md | code=alpha_digit* | grade=digit+ | locked | exec | write | test | answer
    # source := include | other
    # include := <!--- dir* --->
    # dir := include filename | exec-include cmd
    def __init__(self, input_file, output_file, syntax, labels):
        self.input_file = input_file
        self.output_file = output_file
        self.kernel_dict = canonicalize_kernel_dict()
        self.syntax = self.canonicalize_kernel(syntax)
        self.labels = labels
        self.in_fp = None
        self.line = None
        self.token = None
        self.line_no = 0
        self.grade_id = 0
        self.cell_id = 0
        self.matched = None
        self.heading_counter = Counter()
        self.counters = {"P" : ("Problem", '<font color="green">', '</font>', 1)}
        self.make_patterns()
    tok_begin_md = "tok_begin_md"
    tok_begin_code = "tok_begin_code"
    tok_end_md = "tok_end_md"
    tok_end_code = "tok_end_code"
    tok_include = "tok_include"
    tok_other = "tok_other"
    tok_eof = "tok_eof"
    def canonicalize_kernel(self, syntax):
        return self.kernel_dict[syntax.lower()]
    
    def make_patterns(self):
        """
        make regexes for parsing a line
        """
        if self.syntax == "SoS":
            self.patterns = [
                (self.tok_begin_md,
                 re.compile(r'<\!\-\-\- (?P<cell_attrs>md.*) \-\-\->')),
                (self.tok_end_md,
                 re.compile(r'<!--- end md --->')),
                (self.tok_begin_code,
                 re.compile(r'<\!\-\-\- (?P<cell_attrs>code.*) \-\-\->')),
                (self.tok_end_code,
                 re.compile(r'<!--- end code --->')),
                (self.tok_include,
                 re.compile(r'<!--- (?P<cmd>(include|exec-include).*) --->')),
                (self.tok_eof,
                 re.compile(r'<!--- eof --->')),
            ]
        elif self.syntax == "Python 3 (ipykernel)":
            self.patterns = [
                (self.tok_begin_md,
                 re.compile(r'""" *(?P<cell_attrs>md.*)')),
                (self.tok_end_md,
                 re.compile(r' *"""$')),
                (self.tok_begin_code,
                 re.compile(r'""" *(?P<cell_attrs>code.*)"""')),
                (self.tok_end_code,
                 re.compile(r'""" """')),
                (self.tok_include,
                 re.compile(r'""" *(?P<cmd>(include|exec-include).*)"""')),
                (self.tok_eof,
                 re.compile(r'""" *eof *"""')),
            ]
        elif self.syntax == "OCaml 4.14.2":
            self.patterns = [
                (self.tok_begin_md,
                 re.compile(r'\(\*\* *(?P<cell_attrs>md.*)')),
                (self.tok_end_md,
                 re.compile(r' *\*\)')),
                (self.tok_begin_code,
                 re.compile(r'\(\*\* *(?P<cell_attrs>code.*)\*\)')),
                (self.tok_end_code,
                 re.compile(r'\(\*\* *\*\)')),
                (self.tok_include,
                 re.compile(r'\(\*\* *(?P<cmd>(include|exec-include).*)\*\)')),
                (self.tok_eof,
                 re.compile(r'\(\*\* *eof *\*\)')),
            ]
        elif self.syntax == "C":
            self.patterns = [
                (self.tok_begin_md,
                 re.compile(r'/\*\* (?P<cell_attrs>md.*)')),
                (self.tok_end_md,
                 re.compile(r' *\*/')),
                (self.tok_begin_code,
                 re.compile(r'/\*\* (?P<cell_attrs>code.*)\*/')),
                (self.tok_end_code,
                 re.compile(r'/\*\* *\*/')),
                (self.tok_include,
                 re.compile(r'/\*\* (?P<cmd>(include|exec-include).*)\*/')),
                (self.tok_eof,
                 re.compile(r'/\*\* *eof *\*/')),
            ]
        else:
            assert(0), self.syntax
    def classify_line(self, line):
        """
        determine the token kind of the line
        """
        self.matched = None
        if line == "":
            return self.tok_eof
        for tok, pattern in self.patterns:
            matched = pattern.match(line)
            if matched:
                self.matched = matched
                return tok
        return self.tok_other
    def next(self):
        """
        read next line and determine the token kind
        """
        if self.line == "":
            return
        self.line = self.in_fp.readline()
        self.token = self.classify_line(self.line)
        if DBG >= 2:
            print("{}:{}:[{}]: {}"
                  .format(self.input_file, self.line_no,
                          self.token, self.line), end="")
        if self.token != "eof":
            self.line_no += 1
    def parse_error(self, msg):
        """
        raise a parse error
        """
        sys.stderr.write("error:{}:{}: {}\n"
                         .format(self.input_file, self.line_no, msg))
        sys.exit(1)
    def eat(self, tok):
        """
        eat the current token if it matches the specified kind.
        otherwise it raises a parse error
        """
        if self.token != tok:
            self.parse_error("expected %s but got %s" % (tok, self.token))
        self.next()
    def parse(self):
        """
        parse
        """
        if self.input_file is None:
            self.in_fp = sys.stdin
        else:
            self.in_fp = open(self.input_file)
        self.next()
        cells = self.parse_file()
        if self.input_file is not None:
            self.in_fp.close()
        result = {
            "cells" : cells,
            "metadata" : make_metadata(self.syntax),
            "nbformat" : 4,
            "nbformat_minor" : 4,
        }
        dump = json.dumps(result, ensure_ascii=False, indent=2)
        if self.output_file is not None:
            out_wp = open(self.output_file, "w")
        else:
            out_wp = sys.stdout
        out_wp.write(dump)
        if self.output_file is not None:
            out_wp.close()
    def parse_file_xxx(self):
        """
        parse an entire file

           file := cell*
        """
        cells = []
        while self.line == "\n":
            self.eat(self.tok_other)
        while self.token in [self.tok_begin_md, self.tok_begin_code]:
            cell = self.parse_cell()
            if cell is not None:
                cells.append(cell)
            while self.line != "" and self.line.strip() == "":
                self.eat(self.tok_other)
        self.eat(self.tok_eof)
        return cells
    def empty_line(self):
        return self.token != self.tok_eof and self.line.strip() == ""
    def parse_file(self):
        """
        parse an entire file

           file := cell*
        """
        cells = []
        while self.empty_line():
            self.eat(self.tok_other)
        while self.token in [self.tok_begin_md, self.tok_begin_code, self.tok_other]:
            if self.token in [self.tok_begin_md, self.tok_begin_code]:
                cell = self.parse_cell()
            else:
                assert(self.token == self.tok_other), self.token
                cell = self.parse_md_non_cell()
            if cell is not None:
                cells.append(cell)
            while self.empty_line():
                self.eat(self.tok_other)
        self.eat(self.tok_eof)
        return cells
    def make_cell(self, cell_attrs, sources):
        """
        make a cell from attributes and sources
        """
        attrs_dict = {}
        for attr in cell_attrs.split():
            if "=" in attr:
                [key, val] = attr.split("=", 1)
            else:
                key, val = attr, True
            attrs_dict[key] = val
        # process label=ans; if not given, defaults to label=prob
        # if the specified label is not in labels in command line
        # (--labels, which again defaults to prob), it is skipped
        labels = attrs_dict.get("label")
        if labels is None:
            ok = 1
        else:
            ok = 0
            for label in labels.split(","):
                if label in self.labels:
                    ok = 1
        if ok == 0:
            return None
        cell_type = "markdown" if "md" in attrs_dict else "code"
        kernel = attrs_dict.get("kernel", self.syntax)
        kernel = self.canonicalize_kernel(kernel)
        grade = "points" in attrs_dict
        solution = grade
        #locked = (not grade) and ("w" not in attrs_dict)
        locked = ("w" not in attrs_dict)
        if grade:
            self.grade_id += 1
            grade_id = "p-%03d" % self.grade_id
            sources = ["BEGIN SOLUTION\n", "END SOLUTION\n"] + sources
        else:
            self.cell_id += 1
            grade_id = "c-%03d" % self.cell_id
        if sources and sources[-1].endswith("\n"):
            sources[-1] = sources[-1][:-1]
        cell = {
            "cell_type" : cell_type,
            "metadata" : {
                "kernel" : kernel,
                "nbgrader" : {
                    "grade" : grade,
                    "grade_id" : grade_id,
                    "locked" : locked,
                    "schema_version" : 3,
                    "solution" : solution,
                    "task" : False,
                }
            },
            "source" : sources
        }
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        if grade:
            points = int(attrs_dict["points"])
            cell["metadata"]["nbgrader"]["points"] = points
        return cell
    def parse_cell(self):
        """
        parse a cell

          cell := begin | source* | end
        """
        self.is_md = (self.token == self.tok_begin_md)
        if self.is_md:
            cell_attrs = self.parse_begin_md()
        else:
            cell_attrs = self.parse_begin_code()
        sources = []
        while self.token in [self.tok_include, self.tok_other]:
            sources.extend(self.parse_source())
        if self.is_md:
            self.parse_end_md()
        else:
            self.parse_end_code()
        return self.make_cell(cell_attrs, sources)
    def parse_md_non_cell(self):
        """
        parse a md cell outside <--- md --->

          cell := source*
        """
        cell_attrs = "md"
        sources = []
        self.is_md = 1
        while self.token in [self.tok_include, self.tok_other]:
            sources.extend(self.parse_source())
        return self.make_cell(cell_attrs, sources)
    def parse_begin_md(self):
        """
        parse a begin cell

          begin_cell := <!--- cell_attr* --->
                      | ''' --- cell_attr*
                      | (** --- cell_attr*
                      | /** --- cell_attr*
        """
        matched = self.matched
        self.eat(self.tok_begin_md)
        return matched.group("cell_attrs")
    def parse_end_md(self):
        """
        parse an end cell

          end_cell := <!--- end --->
                    | --- '''
                    | --- *)
                    | --- */
        """
        self.eat(self.tok_end_md)
    def parse_begin_code(self):
        """
        parse a begin cell

          begin_cell := <!--- cell_attr* --->
                      | ''' --- cell_attr*
                      | (** --- cell_attr*
                      | /** --- cell_attr*
        """
        matched = self.matched
        self.eat(self.tok_begin_code)
        return matched.group("cell_attrs")
    def parse_end_code(self):
        """
        parse an end cell

          end_cell := <!--- end --->
                    | --- '''
                    | --- *)
                    | --- */
        """
        self.eat(self.tok_end_code)
    def parse_source(self):
        """
        parse a source line (include directive or regular line)

          source := include | other
        """
        if self.token == self.tok_include:
            return self.parse_include()
        if self.token == self.tok_other:
            return [self.parse_other()]
        self.parse_error("source")
        return []
    def parse_other(self):
        """
        parse a regular line
        """
        line = self.line
        self.eat(self.tok_other)
        if not self.is_md:
            return line
        matched = re.match(r"(?P<hashes>#*)(?P<ast>\*?)(?P<sym>[^ ]*)(?P<rest>.*)", line)
        hashes = matched["hashes"]
        level = len(hashes)
        ast = matched["ast"]
        sym = matched["sym"]
        rest = matched["rest"]
        #
        # (1) # blah bla -> # 3. blah bla
        # (2) #* blah bla -> # blah bla
        # (3) #P blah bla -> # <font color="green">3. Problem 2 : blah bla</font>
        # (3) #*P blah bla -> # <font color="green">Problem 2 : blah bla</font>
        if level > 0:
            if sym != "":      #
                if sym in self.counters:
                    if ast == "":       # no asterisk -> get the section number
                        heading = self.heading_counter.next(level)
                    else:
                        heading = ""
                    name, tag_begin, tag_end, number = self.counters[sym]
                    self.counters[sym] = name, tag_begin, tag_end, number + 1
                    line = ('{} {}{} {} {} : {}{}'
                            .format(hashes, tag_begin,
                                    heading, name, number, rest,
                                    tag_end))
                else:
                    # like #include ... -> keep it intact
                    pass
            else:
                if ast == "":       # no asterisk -> get the section number
                    heading = self.heading_counter.next(level)
                else:
                    heading = ""
                line = "{} {}{}".format(hashes, heading, rest)
        return line
    def parse_include(self):
        """
        parse an include directive

          include := <!--- dir* --->
        """
        matched = self.matched
        cmd = matched.group("cmd").strip()
        cmd_args = cmd.split(None, 1)
        if len(cmd_args) != 2:
            self.parse_error("include")
        [cmd, args] = cmd_args
        if cmd == "include":
            content = read_file(args)
        elif cmd == "exec-include":
            content = run_cmd(args)
        else:
            self.parse_error("include")
        self.eat(self.tok_include)
        lines = content.split("\n")
        lines_with_newlines = [x + "\n" for x in lines[:-1]]
        lines_with_newlines += [x for x in lines[-1:] if x != ""]
        return lines_with_newlines

def parse_args(argv):
    """
    parse cmd line args
    """
    global DBG
    psr = argparse.ArgumentParser(prog=argv[0])
    psr.add_argument("input", help="input file")
    psr.add_argument("-o", "--output", help="output file")
    psr.add_argument("--syntax", help="specify syntax (sos|python|ocaml|c)")
    psr.add_argument("--labels", help="labels to generate (e.g., ans,en)",
                     default="prob")
    psr.add_argument("--dbg", help="dbg level", default=0)
    opt = psr.parse_args(argv[1:])
    DBG = int(opt.dbg)
    opt.labels = [x for x in opt.labels.split(",") if x != ""]
    if opt.syntax is None:
        if opt.input is None:
            opt.syntax = "sos"
        else:
            _, ext = os.path.splitext(opt.input)
            opt.syntax = ext[1:]
    return opt

def main(argv):
    """
    main
    """
    opt = parse_args(argv)
    psr = ParserBase(opt.input, opt.output, opt.syntax, opt.labels)
    psr.parse()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
