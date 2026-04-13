#!/usr/bin/env python
import sys
import markdown
import sqlite3
import time

header = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LINE風チャット</title>
  <style>
    body {
      margin: 0;
      padding: 16px;
      background: #f0f0f0;
      font-family: sans-serif;
    }
    .chat {
      max-width: 1500px;
      margin: 0 auto;
    }
    .message {
      max-width: 70%;
      padding: 8px 12px;
      border-radius: 12px;
      margin-bottom: 8px;
      word-wrap: break-word;
    }
    .mine {
      background: #dcf8c6;
      margin-left: auto;
      border-bottom-right-radius: 0;
    }
    .yours {
      background: #fff;
      border: 1px solid #ddd;
      margin-right: auto;
      border-bottom-left-radius: 0;
    }
    .name {
      font-size: 0.8em;
      color: #666;
      margin-bottom: 2px;
    }
  </style>
</head>
<body>
<div class="chat">
"""

trailer = """
</div>
</body>
</html>
"""

def fmt_time(ts):
    # ローカル時刻の struct_time に変換
    local_time = time.localtime(ts)
    # 好きなフォーマットで文字列化
    formatted = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    return formatted

def table_exists(co, table_name):
    result = co.execute("select name from sqlite_master where type='table' and name=?", (table_name,)).fetchone()
    if result:
        return 1
    else:
        return 0

def main():
    a_sqlite = sys.argv[1]
    co = sqlite3.connect(a_sqlite)
    print(header)
    system_prompt = ""
    if table_exists(co, "misc"):
        for key, val in co.execute("select * from misc"):
            if key == "system_prompt":
                system_prompt = val
    if system_prompt:
        system_prompt_html = markdown.markdown(system_prompt)
        print(f"""<div class="message mine">
<div class="name">system prompt</div>
{system_prompt_html}
</div>""")
    if not system_prompt:
        print(f"could not find system prompt from {a_sqlite}", file=sys.stderr)
    for t0, magic, line, cell, inpt, t1, output, retval in co.execute("select * from hist"):
        if inpt:
            inpt_html = f"<pre>\n{inpt}\n</pre>"
        else:
            inpt_html = ""
        if output:
            if magic == "hey":
                output_html = markdown.markdown(output)
            else:
                output_html = f"<pre>\n{output}\n</pre>"
        else:
            output_html = ""
        t0_ = fmt_time(t0)
        t1_ = fmt_time(t1)
        print(f"""<div class="message mine">
<div class="name">自分</div>
{t0_} {magic} {line}<br/>
{inpt_html}
</div>""")
        print(f"""<div class="message yours">
<div class="name">相手</div>
{t1_}<br/>
{output_html}
</div>""")
    print(trailer)

main()
