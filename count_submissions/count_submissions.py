#!/usr/bin/python3
import csv
import re
import sys

def read_lms_list(filename):
    with open(filename) as fp:
        return [line.strip() for line in fp]

def read_users_nopw(filename):
    U = {}
    with open(filename) as fp:
        rp = csv.DictReader(fp)
        for row in rp:
            id = row["id"]
            U[id] = row
    return U

def choose_last_before(submissions, deadline):
    year, month, day, hour, min, sec, hash, line = (None, ) * 8
    for year, month, day, hour, min, sec, hash, line in submissions:
        if (year, month, day, hour, min, sec) > deadline:
            break
    return year, month, day, hour, min, sec, hash, line

def output_submitted_students(D, lms_list_txt, users_nopw_csv, deadline):
    students = read_lms_list(lms_list_txt)
    users = read_users_nopw(users_nopw_csv)
    # scan LMS table in order
    n_submissions = 0
    for s in students:
        # find his/her user name (uXXXXX)
        row = users.get(s)
        if row is None:
            # this student has never used Jupyter
            print(f"")
        else:
            # find user name in the "user" column
            u = row["user"]
            submissions = D.get(u)
            if submissions is None:
                print(f"")
            else:
                (year, month, day, hour, min, sec, hash, line) = choose_last_before(submissions, deadline)
                print(f"{s} {year}-{month}-{day} {hour}:{min}:{sec}")
                n_submissions += 1
    print(f"{n_submissions} / {len(students)}", file=sys.stderr)

def read_dir():
    fp = sys.stdin
    # fp = open("list_submissions")
    p = re.compile("/home/share/nbgrader/exchange/(?P<course>.*?)/inbound/(?P<user>.+)\+(?P<assignment>.*?)\+(?P<year>\d+)\-(?P<month>\d+)\-(?P<day>\d+) (?P<hour>\d+):(?P<min>\d+):(?P<sec>\d+\.\d+) (?P<hash>.*)$")
    D = {}
    for i, line in enumerate(fp):
        m = p.match(line)
        assert(m), line
        course, user, assignment, year, month, day, hour, min, sec, hash = m["course"], m["user"], m["assignment"], int(m["year"]), int(m["month"]), int(m["day"]), int(m["hour"]), int(m["min"]), float(m["sec"]), m["hash"]
        if (course, assignment) not in D:
            D[course, assignment] = {}
        if user not in D[course, assignment]:
            D[course, assignment][user] = []
        D[course, assignment][user].append((year, month, day, hour, min, sec, hash, line))
    return D

def main():
    deadline = (2024, 1, 24, 10, 15, 0)
    D = read_dir()
    lms_list_csv = "lms_list.csv"
    users_nopw_csv = "users_nopw.csv"
    course = sys.argv[1]
    assignment = sys.argv[2]
    D_ua = D.get((course,assignment), {})
    output_submitted_students(D_ua, lms_list_csv, users_nopw_csv, deadline)
    if 0:
        for (course, assignment), submissions_by_all_users in sorted(D.items()):
            n = len(submissions_by_all_users)
            print(f"{course} {assignment} {n} submissions")
            for user, submissions in sorted(submissions_by_all_users.items()):
                m = len(submissions)
                print(f" {user} {m}")
                year, month, day, hour, min, sec, hash, line = max(submissions)
                print(f"  {line}", end="")

main()
