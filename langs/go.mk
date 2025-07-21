targz:=go1.24.1.linux-amd64.tar.gz
#targz:=go1.24.1.linux-arm64.tar.gz

install:
	wget -O ~/$(targz) https://go.dev/dl/$(targz)
	tar xf ~/$(targz) -C ~/
	cd ~/ && ~/go/bin/go install github.com/gopherdata/gophernotes@latest
	mkdir -p ~/.local/share/jupyter/kernels
	chmod 'u+w' ~/.local/share/jupyter/kernels
	chmod 'u+w' ~/.local/share/jupyter/kernels/gophernotes ; rm -rf ~/.local/share/jupyter/kernels/gophernotes
	cp -r ~/go/pkg/mod/github.com/gopherdata/gophernotes@v0.7.5/kernel ~/.local/share/jupyter/kernels/gophernotes
	chmod 644 ~/.local/share/jupyter/kernels/gophernotes/kernel.json
	sed 's:"gophernotes":"~/go/bin/gophernotes":g' ~/.local/share/jupyter/kernels/gophernotes/kernel.json.in > ~/.local/share/jupyter/kernels/gophernotes/kernel.json

uninstall:
	chmod -R 'u+w' ~/go ; rm -rf ~/go
	chmod -R 'u+w' ~/.local/share/jupyter/kernels/gophernotes ; rm -rf ~/.local/share/jupyter/kernels/gophernotes
	rm -f ~/$(targz)
