install:
	curl -fsSL https://install.julialang.org > ~/julia_install.sh
	sh ~/julia_install.sh --yes
	mkdir -p ~/.local/share/jupyter/kernels
	chmod -R 'u+w' ~/.local/share/jupyter/kernels
	~/.juliaup/bin/julia -e 'import Pkg; Pkg.add("IJulia"); using IJulia'

uninstall:
#	rm -rf ~/.julia
#	rm -rf ~/julia-1.8.5
#	rm -f ~/julia-1.8.5-linux-x86_64.tar.gz
	rm -rf ~/.juliaup
	rm -f ~/julia_install.sh

