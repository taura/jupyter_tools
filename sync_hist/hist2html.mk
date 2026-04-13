note_sqlites:=$(wildcard hist/home/*/notebooks/pl/*/hist.sqlite)
prob_sqlites:=$(wildcard hist/home/*/notebooks/pl/*/problems/*/*/hist.sqlite)

note_dirs:=$(patsubst hist/%/hist.sqlite,html/%/dir,$(note_sqlites))
prob_dirs:=$(patsubst hist/%/hist.sqlite,html/%/dir,$(prob_sqlites))

note_htmls:=$(patsubst html/%/dir,html/%/hist.html,$(note_dirs))
note_htmls:=$(patsubst html/%/dir,html/%/hist.html,$(prob_dirs))

# $(warning $(note_sqlites))
# $(warning $(prob_sqlites))
# $(warning $(note_dirs))
# $(warning $(prob_dirs))
# $(warning $(note_htmls))
# $(warning $(prob_htmls))

index.html : $(note_htmls) $(prob_htmls) make_index.py
	./make_index.py > $@

$(note_dirs) $(prob_dirs) : html/%/dir :
	mkdir -p $@

$(note_htmls) $(prob_htmls) : html/%/hist.html : hist/%/hist.sqlite html/%/dir hist2html.py
	./hist2html.py $< > $@

.DELETE_ON_ERROR:
