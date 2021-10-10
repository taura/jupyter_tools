
./make_src.py --- make src/ directory
./rsync_notebooks --- copy src into dst/ and update sqlite3 database

repeat:
  ./make_src.py
  ./rsync_notebooks
