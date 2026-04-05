install:
	touch ~/.bash_profile
	mkdir -p ~/tmp/julia_install
	curl -fsSL https://install.julialang.org > ~/julia_install.sh
	TMPDIR=~/tmp/julia_install bash ~/julia_install.sh --yes
	mkdir -p ~/.local/share/jupyter/kernels
	chmod -R 'u+w' ~/.local/share/jupyter/kernels
	~/.juliaup/bin/julia -e 'import Pkg; Pkg.add("IJulia"); using IJulia'
	rm -f ~/julia_install.sh
	rm -rf ~/tmp/julia_install

uninstall:
	rm -rf ~/.julia
	rm -rf ~/.juliaup
	rm -f ~/julia_install.sh
	rm -rf ~/tmp/julia_install

#	rm -rf ~/julia-1.8.5
#	rm -f ~/julia-1.8.5-linux-x86_64.tar.gz
