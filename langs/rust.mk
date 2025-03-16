install:
	curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > ~/rust_install.sh
	sh ~/rust_install.sh -y
	~/.cargo/bin/cargo install evcxr_jupyter
	~/.cargo/bin/evcxr_jupyter --install

uninstall:
	rm -rf ~/.cargo ~/.rustup
	chmod 'u+w' ~/.local/share/jupyter/kernels ; rm -rf ~/.local/share/jupyter/kernels/rust
	rm -f ~/rust_install.sh

