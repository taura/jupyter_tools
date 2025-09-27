#!/usr/bin/env python
"""
progress viewer
"""
import csv
import re
import sqlite3
import time
import dash
# the right way to import dcc and html depend
# on python version
if hasattr(dash, "dcc"):
    #deprecated
    from dash import dcc
    from dash import html
else:
    import dash_core_components as dcc
    import dash_html_components as html
import dash_auth
#import plotly.express as px
import plotly.graph_objects as go
#from dash.dependencies import Input, Output, State
from dash.dependencies import Input, Output

################################################
# read config
################################################

import progress_viewer_config

SYNC_SQLITE = progress_viewer_config.SYNC_SQLITE
USERS_CSV = progress_viewer_config.USERS_CSV
USER_ATTRS = progress_viewer_config.USER_ATTRS
PASSWD = progress_viewer_config.PASSWD
URL_TEMPLATE = progress_viewer_config.URL_TEMPLATE
VALID_USERNAME_PASSWORD_PAIRS = progress_viewer_config.BASIC_AUTH_USER_PASSWORD_PAIRS

################################################
# the app object
################################################

if __name__ == "__main__":
    # when launched as a standalone process
    app = dash.Dash(__name__)
else:
    # when launched from apache as wsgi application
    app = dash.Dash(__name__, requests_pathname_prefix='/progress_viewer/')

app = dash.Dash(__name__)
auth = dash_auth.BasicAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

application = app.server

if 0:
    progress_viewer_config = None
    try:
        import progress_viewer_config
    except:
        pass

    if progress_viewer_config:
        SYNC_SQLITE = progress_viewer_config.SYNC_SQLITE
        USERS_CSV = progress_viewer_config.USERS_CSV
        USER_ATTRS = progress_viewer_config.USER_ATTRS
        PASSWD = progress_viewer_config.PASSWD
        URL_TEMPLATE = progress_viewer_config.URL_TEMPLATE
    else:
        # default values likely to need to be overwritten
        SYNC_SQLITE = "sync.sqlite"
        USERS_CSV = "users.csv"
        USER_ATTRS = ["real_name", "class", "team"]
        PASSWD = "es1seePh"
        URL_TEMPLATE = "https://taulec.zapto.org:8000/user/tau/notebooks/sync_dest/{filename}"

################################################
# nuts and bolts
################################################
def sqlite_connect(a_sqlite):
    """
    connect to sqlite3 database
    """
    conn = sqlite3.connect(a_sqlite)
    conn.row_factory = sqlite3.Row
    return conn

def do_sql(conn, cmd):
    """
    issue an sql query
    """
    # print(cmd)
    return conn.execute(cmd)

################################################
# styles
################################################

def h1_style():
    """
    h1 style
    """
    return {
        "textAlign" : "center",
        "border-color" : "#99A1AA",
        "background-color" : "#BBDDBB"
    }

def h2_style():
    """
    h2 style
    """
    return {
        "border-color" : "#99A1AA",
        "background-color" : "#CCEECC"
    }

################################################
# activity graph
################################################

def activity_graph_div():
    """
    div to show the progress graph
    """
    div = html.Div([
        html.Ul([
            # textbox to enter password
            html.Li(["passwd: ",
                     dcc.Textarea(id="activity_graph_passwd",
                                  value="", style={"height": 15, "width": 100}),
            ]),
            # textbox to choose or enter regular expression to select files
            html.Li(["path regexp (e.g., /notebooks/u21.* ): ",
                     dcc.Textarea(id="activity_graph_path_re",
                                  value="", style={"height": 15, "width": 300}),
                     dcc.Checklist(id="activity_graph_path_re_options",
                                    options=[],
                                    value=[],
                                    labelStyle={'display': 'block'}),
                     dcc.RadioItems(id="activity_graph_path_re_options_xxx",
                                    options=[],
                                    value="",
                                    labelStyle={'display': 'block'})
            ]),
            # threshold
            html.Li(["show path groups larger than: ",
                     dcc.Textarea(id="activity_graph_threshold",
                                  value="10", style={"height": 15, "width": 100}),
            ]),
            # two textboxes choosing time period
            html.Li(['time (e.g., 2021-03-15, 2021-03-15T09:23:00, -1 days, -2 hours, -30 mins): ',
                     html.Br(),
                     dcc.Textarea(id="activity_graph_time_after", value="", style={"height": 15}),
                     ' -- ',
                     dcc.Textarea(id="activity_graph_time_before", value="", style={"height": 15})
            ]),
            # sorting criteria
            html.Li(['sort :',
                     dcc.RadioItems(id="activity_graph_sort_criteria",
                                    options=[
                                        {'label': 'latest',      'value': 'latest'},
                                        {'label': 'most OKs',    'value': 'most_ok'},
                                        {'label': 'most errors', 'value': 'most_error'},
                                        {'label': 'user', 'value': 'user'},
                                        {'label': 'team', 'value': 'team'},
                                    ],
                                    value='latest',
                                    labelStyle={'display': 'inline-block'})
            ]),
            # checkbox to say show only the latest
            html.Li(['show only latest :',
                     dcc.Checklist(id="activity_graph_show_only_latest",
                                   options=[
                                       {'label': 'Show only latest', 'value': 'show_only_latest'},
                                   ],
                                   value=[])
            ]),
            # max number of entries
            html.Li(["max entries (e.g., 100): ",
                     dcc.Textarea(id="activity_graph_max_lines", value="100", style={"height": 15})
            ]),
        ]),
        html.P(id="n_rows"),
        dcc.Graph(id="activity_graph"),
    ])
    return div

def remove_backup_part(filename):
    """
    foo.bak_2021-04-23T12:34:56.ipynb -> foo.ipynb
    """
    pat = re.compile(r"(?P<base>.*?)(\.bak_(?P<t>.{19}))?(?P<ext>(\.[^\.]*)?)$")
    matched = pat.match(filename)
    if matched is None:
        return filename
    return "{}{}".format(matched["base"], matched["ext"])

def hover_of_row(i, drow):
    """
    hover of a row
    """
    url = URL_TEMPLATE.format(**drow)
    hover = ("""<a href="{url}" style="color:yellow">
{code_ok}/{code_display}/{code_stream}/{code_error}/{code_empty}
</a>""".format(url=url, **drow))
    return hover

def y_of_row(i, drow):
    """
    y of a row
    """
    fmt = " ".join(["{" + key + "}" for key in ["src_filename"] + USER_ATTRS + ["owner"]])
    return fmt.format(i=i, **drow)

def color_of_row(i, drow):
    """
    determine the color of the circle for a record.
    * have an error -> red
    * have some OK/display/stream and no empty -> green
    """
    error = drow["code_error"]
    n_ok = drow["code_ok"]
    display = drow["code_display"]
    stream = drow["code_stream"]
    empty = drow["code_empty"]
    if error > 0:
        return "red"
    if n_ok + display + stream > 0 and empty == 0:
        return "green"
    return "blue"

def size_of_row(i, drow):
    """
    determine the color of the circle for a record
    (5 -- 15)
    """
    error = drow["code_error"]
    ok = drow["code_ok"]
    display = drow["code_display"]
    stream = drow["code_stream"]
    empty = drow["code_empty"]
    n_all = ok + display + stream + error + empty
    n_ok = ok + display + stream
    if n_all == 0:
        return 5
    return 5 + 10 * n_ok / n_all

def mk_sql_time_expr(time_spec, default):
    """
    conver time expression the user entered in the cell
    into an expression understood by sqlite
    """
    if time_spec == "":
        return default
    if time_spec[:1] == "-":           # -12345 = now - 12345 sec
        return 'datetime("now", "localtime", "{}")'.format(time_spec)
    return 'datetime("{}")'.format(time_spec)

def make_flattened_values(dic, key_order, fun):
    """
    dic is a dictionary mapping keys in key_order to a list.
    each element of a list is another dictionary.
    i.e., dic looks like
    dic = { k0 : [ {l0 : v00}, {l1 : v01} ... ],
            k1 : [ {l0 : v10}, {l1 : v11} ... ], ... }
    key_order is a list of keys of (k0, k1, k2, ...) that specifies
    the order in which items are taken from dic. e.g.,
    key_order = [k1, k3, k2, k0]
    f is a fuction applied to each item of the list
    """
    vals = []
    for k in key_order:
        vals.extend([fun(i, d) for i, d in enumerate(dic[k])])
    return vals

def guess_owner(filename):
    """
    guess the owner of a file from the path name
    """
    matched = re.match("home/(?P<owner>[^/]+)/", filename)
    if matched:
        return matched["owner"]
    return "unknown"

def read_csv(users_csv):
    """
    read a csv and returns a list of rows
    """
    with open(users_csv) as csv_fp:
        return list(csv.DictReader(csv_fp))

def make_user_info(users_csv):
    """
    make a dictionary mapping user -> row in a csv file
    """
    return {row["uid"] : row for row in read_csv(users_csv)}

class record_sorter:
    """
    class having many sort_CRITERIA methods that return key for sorting
    of a filename
    rs = record_sorted()
    rs.sort_key_most_ok(filename) return the key for the filename
    when sorting by most_ok
    """
    def __init__(self, finfo):
        self.finfo = finfo
    def sort_key_most_ok(self, filename):
        """
        key to get records with most code_ok's first
        """
        return -self.finfo[filename][0]["code_ok"]
    def sort_key_most_error(self, filename):
        """
        key to get records with most code_error's first
        """
        return -self.finfo[filename][0]["code_error"]
    def sort_key_latest(self, filename):
        """
        key to get latest records first
        """
        return -time.mktime(time.strptime(self.finfo[filename][0]["t"], "%Y-%m-%dT%H:%M:%S"))
    def sort_key_user(self, filename):
        """
        key to sort by owner's dictionary order
        """
        return self.finfo[filename][0]["owner"]
    def sort_key_team(self, filename):
        """
        key to sort by owner's team
        """
        return self.finfo[filename][0]["team"]

def make_sort_key(records, criteria):
    """
    make a sort key (function) according to the criteria ("most_ok", etc.)
    """
    rec_sorter = record_sorter(records)
    sort_key = getattr(rec_sorter, "sort_key_{}".format(criteria))
    return sort_key

def make_regexps_for_path(path):
    """
    given a path like a/b/c/d/e.ipynb, return
    many regexps mathing this path. specifically,
    [^/]+/b/c/d/e.ipy
    a/[^/]+/c/d/e.ipy
    a/b/[^/]+/d/e.ipy
    a/b/c/[^/]+/e.ipy
    a/b/c/d/[^/]+
    """
    components = path.split("/")
    patterns = []
    for i in range(len(components)):
        pat = components[:i] + [ "[^/]+" ] + components[i+1:]
        patterns.append("/".join(pat))
    return patterns

def group_paths(paths, threshold):
    """
    given a set of filenames in paths, return
    regexps matching at least threshold numbers
    of them.
    """
    path_groups = {}
    for path in paths:
        for pat in make_regexps_for_path(path):
            if ".ipynb_checkpoints" in pat:
                continue
            if pat not in path_groups:
                path_groups[pat] = []
            path_groups[pat].append(path)
    large_groups = []
    for pat, paths_in_group in path_groups.items():
        if len(paths_in_group) >= threshold:
            large_groups.append((pat, len(paths_in_group)))
    large_groups.sort()
    return large_groups

def select_records(a_sqlite, users_csv, cols_to_mask,
                   time_after_expr, time_before_expr):
    """
    select records from the database in the specified time range.
    it also joins user information to each record.
    """
    conn = sqlite_connect(SYNC_SQLITE)
    user_info = make_user_info(users_csv)
    for user_val in user_info.values():
        for key in cols_to_mask:
            user_val[key] = "*"
    records = {}               # src_filename -> sql row + user info
    sql = ("""select * from summary
    where datetime(t) >= {time_after_expr} and datetime(t) <= {time_before_expr} 
    order by t desc"""
           .format(time_after_expr=time_after_expr, time_before_expr=time_before_expr))
    for row in do_sql(conn, sql):
        drow = dict(row)
        filename = drow["filename"]
        src_filename = remove_backup_part(filename)
        if src_filename is None:
            continue
        drow["src_filename"] = src_filename
        if src_filename not in records:
            records[src_filename] = []
        # join owner info
        owner_record = {key : "?" for key in USER_ATTRS}
        owner = drow["owner"]
        owner_record.update(user_info.get(owner, {}))
        for key in owner_record.keys():
            assert(key not in drow), key
        drow.update(owner_record)
        records[src_filename].append(drow)
    conn.close()
    return records

def make_scatter_data(records, path_regexps, sort_criteria, show_only_latest, limit):
    """
    make data to do a scatter plot
    """
    #print(path_regexps)
    pats = [re.compile(path_regexp) for path_regexp in path_regexps]
    # filter out all non .ipynb files
    ipynb_pat = re.compile(r".*\.ipynb$")
    ipynb_filenames = [filename for filename in records.keys() if ipynb_pat.match(filename) ]
    # filenames that match the specified regexp
    filenames = [filename for filename in ipynb_filenames if any(pat.search(filename) for pat in pats)]
    # sort them according to the criteria
    filenames.sort(key=make_sort_key(records, sort_criteria))
    # limit the number of entries
    if limit != "":
        limit = int(limit)
        filenames = filenames[:limit]
    records = {f : records[f] for f in filenames}
    if "show_only_latest" in show_only_latest:
        records = {k : v[:1] for k, v in records.items()}
    filenames.reverse()
    scatter = go.Scatter(x=make_flattened_values(records, filenames, (lambda i, d: d["t"])),
                         y=make_flattened_values(records, filenames, y_of_row),
                         hovertext=make_flattened_values(records, filenames, hover_of_row),
                         hoverinfo="text",
                         marker=dict(color=make_flattened_values(records, filenames, color_of_row),
                                     size=make_flattened_values(records, filenames, size_of_row)),
                         mode='markers')
    fig = go.FigureWidget([scatter], layout={"hovermode" : "closest"})
    n_rows = len(filenames)
    height = 100 if n_rows == 0 else 500 // n_rows if n_rows < 20 else 1000 / n_rows if n_rows < 45 else 25
    # height = 70 if n_rows < 6 else 40 if n_rows < 13 else 30 if n_rows < 44 else 25
    fig.update_layout(height=max(100, height * n_rows))
    return fig, n_rows

def make_regexp_suggestions(records, threshold):
    """
    make a list of suggested regular expressions
    """
    patterns = group_paths(records, threshold)
    options = [{"label" : "{} {}".format(c, x), "value" : x} for x, c in patterns + [("", "")]]
    radio_items = dcc.RadioItems(options=options, value="",
                                 labelStyle={'display': 'block'})
    return options

def safe_int(x):
    try:
        return int(x)
    except:
        return 10

@app.callback(
    Output("n_rows",                         "children"),
    Output("activity_graph",                 "figure"),
    Output("activity_graph_path_re_options", "options"),
    Input("activity_graph_passwd",           "value"),
    Input("activity_graph_path_re",          "value"),
    Input("activity_graph_path_re_options",  "value"),
    Input("activity_graph_sort_criteria",    "value"),
    Input("activity_graph_show_only_latest", "value"),
    Input("activity_graph_max_lines",        "value"),
    Input("activity_graph_time_after",       "value"),
    Input("activity_graph_time_before",      "value"),
    Input("activity_graph_threshold",        "value"),
)
def update_activity_graph(passwd, path_re, path_re_options,
                          sort_criteria, show_only_latest, limit,
                          time_after, time_before, threshold):
    """
    update the activity graph
    """
    cols_to_mask = [] if passwd == PASSWD else ["uid"] + USER_ATTRS
    path_regexps = [path_re] if path_re else path_re_options if path_re_options else [".*"]
    time_after_expr = mk_sql_time_expr(time_after, 'datetime(0, "unixepoch")')
    time_before_expr = mk_sql_time_expr(time_before, 'datetime("now", "localtime")')
    records = select_records(SYNC_SQLITE, USERS_CSV, cols_to_mask, time_after_expr, time_before_expr)
    fig, n_rows = make_scatter_data(records, path_regexps, sort_criteria, show_only_latest, limit)
    radio_items = make_regexp_suggestions(records, safe_int(threshold))
    return ("{} rows".format(n_rows), fig, radio_items)


################################################
# the whole page
################################################

app.layout = html.Div(
    [
        html.H1("Activity", style=h1_style()),
        activity_graph_div(),
    ],
    style={"padding": "2%", "margin": "auto"},
)

if __name__ == "__main__":
    #app.run_server(debug=True, host="0.0.0.0")
    app.run(debug=True, host="0.0.0.0")
