#!/usr/bin/env python

import sys
import sqlite3
import csv
import argparse

class user_map:
    """
    user_map is a database managing the mapping from regular user name (e.g. UTokyo Account)
    to local user name (e.g., unix account).
    it is essentially a list of tuples (A, B), where A is the regular user name
    and B the local user name.
    it allows the following operations.
    - add_local : given B, ensure a tuple (x, B) exists. if not already exists, add ("", B)
    - bind : given (A, B), establish mapping A -> B
       if there is a tuple (x, B), if x = "", update it to (A, B) otherwise error
       if there is no tuple (x, B), add (A, B)
    - add_user : given A, find any tuple ("", y) and update it to (A, y)
    """
    def __init__(self, a_sqlite):
        """
        m = user_map("user_map.sqlite")
        """
        self.a_sqlite = a_sqlite
        self.co = sqlite3.connect(a_sqlite)
    def sql(self, q, *values):
        """
        execute sql query
        """
        co = self.co
        return co.execute(q, values)
    def begin(self):
        """
        begin transaction
        """
        self.sql("begin immediate")
    def commit(self):
        """
        commit transaction
        """
        self.co.commit()
    def rollback(self):
        """
        abort transaction
        """
        self.co.rollback()
    def ensure_db(self):
        """
        ensure database exists
        """
        self.begin()
        self.sql("create table if not exists users (user text, local text)")
        self.sql("create table if not exists cfg (key, val)")
        found = list(self.sql("select val from cfg where key=?", "self_register"))
        if len(found) == 0:
            self.sql("insert into cfg values (?, ?)", "self_register", 0)
        self.commit()
    def show_db(self):
        """
        initialize database
        """
        print("cfg:")
        for k,v in self.sql("select key, val from cfg"):
            print(f"{k} = {v}")
        print("users:")
        print("user,local")
        for user, local in self.sql("select user,local from users"):
            print(f"{user},{local}")
    def add_local(self, local):
        """
        ensure (any, local) exists in the database, adding ("", local) if necessary.
        return the any (i.e., if an entry already exists, return it, otherwise "")
        """
        self.begin()
        found = list(self.sql("select user from users where local = ?", local))
        assert(len(found) < 2)
        if len(found) == 1:
            self.rollback()
            [(user,)] = found
            print(f"warning: an entry {user} -> {local} already exists (ignored)", file=sys.stderr)
            return user
        self.sql("insert into users values(?, ?)", "", local)
        self.commit()
        return ""
    def bind(self, user, local, force):
        """
        ensure tuple (user, local) exists, unless conflicting tuple (?, local) already exists.
        """
        self.begin()
        found = list(self.sql("select user from users where local = ?", local))
        assert(len(found) < 2)
        if len(found) == 1:
            [(u,)] = found
            if u == "":
                self.sql("update users set user = ? where local = ?", user, local)
            elif u != user:
                self.rollback()
                print(f"error: conflicting entry {u} -> {local} already exists",
                      file=sys.stderr)
                return u
            else:
                print(f"warning: same entry {user} -> {local} already exists",
                      file=sys.stderr)
        else:
            found = list(self.sql("select local from users where user = ?", user))
            assert(len(found) < 2)
            if len(found) == 1:
                [(l,)] = found
                if l != local:
                    if force:
                        self.sql("update users set local = ? where user = ?", local, user)
                    else:
                        self.rollback()
                        print(f"error: conflicting entry {user} -> {l} already exists",
                              file=sys.stderr)
                        return None
                else:
                    print(f"warning: same entry {user} -> {local} already exists",
                          file=sys.stderr)
            else:
                self.sql("insert into users values(?, ?)", user, local)
        self.commit()
        return user
    def binds(self, a_csv, force):
        err = 0
        with open(a_csv) as fp:
            for row in csv.DictReader(fp):
                user, local = row["user"], row["local"]
                u = self.bind(user, local, force)
                if u != user:
                    err += 1
        return int(err == 0)
    def query(self, user):
        """
        (user, ?) exists?
        """
        found = list(self.sql("select local from users where user = ?", user))
        if len(found) == 0:
            return None
        else:
            [(local,)] = found
            return local
    def queryl(self, local):
        """
        (?, local) exists?
        """
        found = list(self.sql("select user from users where local = ?", local))
        if len(found) == 0:
            return None
        else:
            [(user,)] = found
            return user
    def alloc(self, user):
        """
        find any tuple ("", y) and update it to (user, y)
        return y or None (when no entries are available)
        """
        local = self.query(user)
        if local is not None:
            return local
        if not self.get_self_register():
            print(f"error: {user} not found and self registration not allowed now",
                  file=sys.stderr)
            return None
        self.begin()
        local, = self.sql("select min(local) from users where user = ?", "").fetchone()
        if local is None:
            self.rollback()
            print(f"error: no available entry for {user}", file=sys.stderr)
            return None
        else:
            self.sql("update users set user = ? where local = ?", user, local)
            self.commit()
            return local
    def set_self_register(self, s):
        self.begin()
        self.sql("update cfg set val=? where key=?", s, "self_register")
        self.commit()
    def get_self_register(self):
        s, = self.sql("select val from cfg where key=?", "self_register").fetchone()
        return s

def parse_args(argv):
    pall = argparse.ArgumentParser(prog='udb', description='manage user mapping database')
    # 共通オプション
    pall.add_argument("--verbose", action="store_true")
    # subcommand 用
    subp = pall.add_subparsers(dest="command")
    # --- subcommand: init ---
    p_ensure = subp.add_parser("ensure", help="ensure database exists")
    # --- subcommand: show ---
    p_help = subp.add_parser("show", help="show database content")
    # --- subcommand: query ---
    p_query = subp.add_parser("query", help="query database for the user")
    p_query.add_argument("user", help="user to search for")
    # --- subcommand: queryl ---
    p_queryl = subp.add_parser("queryl", help="query database for local user LOCAL")
    p_queryl.add_argument("local", help="local user to search for", metavar="LOCAL")
    # --- subcommand: local ---
    p_local = subp.add_parser("local", help="add LOCAL as an unmapped local user")
    p_local.add_argument("local", help="local user to add", metavar="LOCAL")
    # --- subcommand: bind ---
    p_bind = subp.add_parser("bind", help="map USER to LOCAL")
    p_bind.add_argument("user", help="user to map to LOCAL", metavar="USER")
    p_bind.add_argument("local", help="local user to map from USER", metavar="LOCAL")
    p_bind.add_argument("--force", help="overwrite existing entry", action="store_true")
    # --- subcommand: binds ---
    p_binds = subp.add_parser("binds", help="map USER to LOCAL from csv")
    p_binds.add_argument("file", help="csv having 'user' and 'local' columns", metavar="FILE")
    p_binds.add_argument("--force", help="overwrite existing entry", action="store_true")
    # --- subcommand: alloc ---
    p_alloc = subp.add_parser("alloc", help="allocate a local user to USER")
    p_alloc.add_argument("user")
    # --- subcommand: register ---
    p_reg = subp.add_parser("register", help="enable or disable self registration")
    p_reg.add_argument("on_off")
    # --- subcommand: help ---
    p_help = subp.add_parser("help")
    # --- parse! ---
    opts = pall.parse_args(argv[1:])
    if opts.command == "help" or opts.command is None:
        pall.print_help()
        return (pall, None, 0)
    if opts.command == "register":
        b = opts.on_off.lower()
        on = b in ["on", "true", "1"]
        off = b in ["off", "false", "0"]
        if on:
            opts.b = 1
        elif off:
            opts.b = 0
        else:
            pall.print_help()
            return (pall, None, 1)
    return (pall, opts, 0)

def main():
    psr, opts, status = parse_args(sys.argv)
    if opts is None:
        return status
    cmd = opts.command
    a_sqlite = "user_map.sqlite"
    um = user_map(a_sqlite)
    if cmd == "ensure":
        um.ensure_db()
    elif cmd == "show":
        um.show_db()
    elif cmd == "query":
        local = um.query(opts.user)
        if local is not None:
            print(local)
    elif cmd == "queryl":
        user = um.queryl(opts.local)
        if user is not None:
            print(user)
    elif cmd == "local":
        user = um.add_local(opts.local)
        return 0                # OK
    elif cmd == "bind":
        user = um.bind(opts.user, opts.local, opts.force)
        if user == opts.user:
            return 0            # OK
        else:
            return 1
    elif cmd == "binds":
        ok = um.binds(opts.file, opts.force)
        if ok:
            return 0            # OK
        else:
            return 1
    elif cmd == "alloc":
        local = um.alloc(opts.user)
        if local is not None:
            return 0            # OK
        else:
            return 1            # NG
    elif cmd == "register":
        um.set_self_register(opts.b)
    else:
        assert(0), cmd
        return 1


if __name__ == "__main__":
    main()
