dl_note_sqlites:=$(wildcard dl/assignments/submitted/*/*/hist.sqlite)
dl_prob_sqlites:=$(wildcard dl/assignments/submitted/*/*/problems/*/*/hist.sqlite)

dl_note_dirs:=$(patsubst dl/assignments/submitted/%/hist.sqlite,dl_viewer/html/%/dir,$(dl_note_sqlites))
dl_prob_dirs:=$(patsubst dl/assignments/submitted/%/hist.sqlite,dl_viewer/html/%/dir,$(dl_prob_sqlites))

dl_note_htmls:=$(patsubst dl_viewer/html/%/dir,dl_viewer/html/%/hist.html,$(dl_note_dirs))
dl_prob_htmls:=$(patsubst dl_viewer/html/%/dir,dl_viewer/html/%/hist.html,$(dl_prob_dirs))

hist_note_sqlites:=$(wildcard hist/home/*/notebooks/pl/*/hist.sqlite)
hist_prob_sqlites:=$(wildcard hist/home/*/notebooks/pl/*/problems/*/*/hist.sqlite)

hist_note_dirs:=$(patsubst hist/home/%/hist.sqlite,hist_viewer/html/%/dir,$(hist_note_sqlites))
hist_prob_dirs:=$(patsubst hist/home/%/hist.sqlite,hist_viewer/html/%/dir,$(hist_prob_sqlites))

hist_note_htmls:=$(patsubst hist_viewer/html/%/dir,hist_viewer/html/%/hist.html,$(hist_note_dirs))
hist_prob_htmls:=$(patsubst hist_viewer/html/%/dir,hist_viewer/html/%/hist.html,$(hist_prob_dirs))

# $(warning note_sqlites=$(note_sqlites))
# $(warning prob_sqlite3=$(prob_sqlites))
# $(warning note_dirs=$(note_dirs))
# $(warning prob_dirs=$(prob_dirs))
# $(warning note_htmls=$(note_htmls))
# $(warning prob_htmls=$(prob_htmls))

all : dl_viewer/data.js hist_viewer/data.js

# find hist.sqlite files in dl/assignments/submitted
# extract user, note, topic, prob from the path using regex
# the patched path (USER/NOTE/problems/TOPIC/PROB/hist.sqlite) is used to generate the URL for the hist.html file
# USER/NOTE/problems/TOPIC/PROB/hist.sqlite -> URL_PREFIX/USER/NOTE/problems/TOPIC/PROB/hist.html

dl_viewer/data.js : $(dl_note_htmls) $(dl_prob_htmls) make_json.py
	./make_json.py --users-xlsx ldap_users_taulec.ods --top dl/assignments/submitted --pat '(?P<user>.*)/(?P<note>.*)/problems/(?P<topic>.*)/(?P<prob>.*)/hist.sqlite' --url-prefix html > $@

hist_viewer/data.js : $(hist_note_htmls) $(hist_prob_htmls) make_json.py
	./make_json.py --users-xlsx ldap_users_taulec.ods --top hist/home --pat '(?P<user>.*)/notebooks/pl/(?P<note>.*)/problems/(?P<topic>.*)/(?P<prob>.*)/hist.sqlite' --url-prefix html > $@

$(dl_note_dirs) $(dl_prob_dirs) : dl_viewer/html/%/dir :
	mkdir -p $@

$(hist_note_dirs) $(hist_prob_dirs) : hist_viewer/html/%/dir :
	mkdir -p $@

$(dl_note_htmls) $(dl_prob_htmls) : dl_viewer/html/%/hist.html : dl/assignments/submitted/%/hist.sqlite dl_viewer/html/%/dir hist2html.py
	./hist2html.py $< > $@

$(hist_note_htmls) $(hist_prob_htmls) : hist_viewer/html/%/hist.html : hist/home/%/hist.sqlite hist_viewer/html/%/dir hist2html.py
	./hist2html.py $< > $@

.DELETE_ON_ERROR:
