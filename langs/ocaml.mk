# note: /usr/local/bin/opam must exist
# and be installed by
# bash -c "sh <(curl -fsSL https://raw.githubusercontent.com/ocaml/opam/master/shell/install.sh)"

switch=4.14.2
install:
	cd && opam init --yes
	opam switch create $(switch)
	eval $$(opam env --set-switch --switch=$(switch)) && opam install --yes jupyter menhir
	~/.opam/$(switch)/bin/ocaml-jupyter-opam-genspec
	. ~share/venv/jupyter/bin/activate && jupyter kernelspec install --user --name ocaml-jupyter ~/.opam/jupyter/share/jupyter

uninstall:
	rm -rf ~/.opam
	chmod 'u+w' ~/.local/share/jupyter/kernels ; rm -rf ~/.local/share/jupyter/kernels/ocaml-jupyter
