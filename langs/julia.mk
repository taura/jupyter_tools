install:
	touch ~/.bash_profile
	mkdir -p ~/tmp
	curl -fsSL https://install.julialang.org > ~/julia_install.sh
	TMPDIR=~/tmp bash ~/julia_install.sh --yes
	mkdir -p ~/.local/share/jupyter/kernels
	chmod -R 'u+w' ~/.local/share/jupyter/kernels
	~/.juliaup/bin/julia -e 'import Pkg; Pkg.add("IJulia"); using IJulia'
	rm -f ~/julia_install.sh
	rm -rf ~/tmp

uninstall:
	rm -rf ~/.julia
	rm -rf ~/.juliaup
	rm -f ~/julia_install.sh
	rm -rf ~/tmp

#	rm -rf ~/julia-1.8.5
#	rm -f ~/julia-1.8.5-linux-x86_64.tar.gz
