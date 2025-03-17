# note: /usr/local/bin/opam must exist
# and be installed by
# bash -c "sh <(curl -fsSL https://raw.githubusercontent.com/ocaml/opam/master/shell/install.sh)"

install:
	opam init --yes
	eval $$(opam env) && opam install --yes jupyter menhir
# jupyter-archimedes 
	~/.opam/default/bin/ocaml-jupyter-opam-genspec
	. ~share/venv/jupyter/bin/activate && jupyter kernelspec install --user --name ocaml-jupyter ~/.opam/default/share/jupyter

uninstall:
	rm -rf ~/.opam
	chmod 'u+w' ~/.local/share/jupyter/kernels ; rm -rf ~/.local/share/jupyter/kernels/ocaml-jupyter
