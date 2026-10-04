"""
Jupyter kernel launcher: run an IPython kernel on a Miyabi login node.

    kernel.json argv: ["python", "{resource_dir}/miyabi_kernel.py", "{connection_file}"]

It rides on the user's "ssh miyabig" login (ControlMaster) and never
authenticates by itself (BatchMode). Per kernel:

  1. check the ControlMaster exists (no Miyabi session used)
  2. one ssh session runs a small bootstrap with the Miyabi venv's python;
     the bootstrap picks free ports on Miyabi, writes a private connection
     file, starts ipykernel and reports the ports. The kernel key goes over
     stdin, never on a command line. When the session's stdin closes (this
     launcher is gone), the bootstrap stops the kernel
  3. forward Jupyter's local ports to those Miyabi ports through the master
     (ssh -O forward; no session). Forwards outlive the requesting ssh, so
     they are cancelled at exit and recorded to clean up after a kill

The kernel runs in the Miyabi directory matching the notebook's: a notebook
under ~/miyabi (mount-miyabi) runs in /work/gt81/share/home/<user>/...;
otherwise in the Miyabi home.

If the kernel can't be started, a local stand-in kernel takes over that
prints the reason (and what to do) on every cell, so students see it and
Jupyter doesn't restart-loop. Log: ~/.local/state/miyabi-kernel/log.
"""

import base64
import collections
import getpass
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time

HOST = "miyabig"
REMOTE_PYTHON = "/work/gt81/share/env/.venv/bin/python"
REMOTE_BASE = "/work/gt81/share/home"
MOUNT = os.path.expanduser("~/miyabi")
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=no"]
STATE = os.path.expanduser("~/.local/state/miyabi-kernel")
PORTS = ("shell_port", "iopub_port", "stdin_port", "control_port", "hb_port")
START_TIMEOUT = 60        # seconds to wait for the bootstrap to report ports
EARLY_EXIT = 20           # a kernel dying this soon is shown as a start failure

MSG_LOGIN = """Not logged in to Miyabi.
Open a terminal (File > New > Terminal) and run:
    mount-miyabi
then restart the kernel (Kernel > Restart Kernel)."""

MSG_SESSIONS = """Too many open sessions on your Miyabi login (at most 10).
Shut down kernels and close terminals you no longer use, then restart the kernel
(Kernel > Restart Kernel). If that does not help, run in a terminal:
    ssh -O exit miyabig
    mount-miyabi
and restart the kernel."""

MSG_ENV = """The Python environment on Miyabi is missing ({python}).
Please tell your instructor."""

MSG_OTHER = """Could not start the kernel on Miyabi:
{detail}
Restart the kernel to retry (Kernel > Restart Kernel).
If it keeps failing, tell your instructor."""

MSG_EARLY = """The kernel on Miyabi stopped right after starting (exit code {code}):
{detail}
Restart the kernel to retry (Kernel > Restart Kernel).
If it keeps failing, tell your instructor."""

# Runs on Miyabi with the venv's python (3.9: keep it plain).
BOOTSTRAP = r'''
import json, os, socket, subprocess, sys, tempfile, threading
cfg = json.loads(sys.stdin.readline())
socks, ports = [], {}
for name in cfg["names"]:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    socks.append(s)
    ports[name] = s.getsockname()[1]
for s in socks:
    s.close()
conn = dict(cfg["conn"], ip="127.0.0.1", transport="tcp", **ports)
d = os.path.expanduser("~/.local/share/miyabi-kernel")
os.makedirs(d, mode=0o700, exist_ok=True)
fd, path = tempfile.mkstemp(prefix="kernel-", suffix=".json", dir=d)
with os.fdopen(fd, "w") as f:
    json.dump(conn, f)
note = ""
cwd = cfg["cwd"]
if cwd and not os.path.isdir(cwd):
    note = "no such directory on Miyabi: " + cwd + "; using the home directory"
    cwd = ""
os.chdir(cwd or os.path.expanduser("~"))
# as if the venv were activated: !sub, !pip, !python in a cell use the venv's
venv_bin = os.path.dirname(sys.executable)
env = dict(os.environ, VIRTUAL_ENV=os.path.dirname(venv_bin),
           PATH=venv_bin + os.pathsep + os.environ.get("PATH", ""))
p = subprocess.Popen([sys.executable, "-m", "ipykernel_launcher", "-f", path],
                     stdin=subprocess.DEVNULL, stdout=sys.stderr, env=env)
print(json.dumps({"ports": ports, "pid": p.pid, "host": socket.gethostname(),
                  "cwd": os.getcwd(), "note": note}), flush=True)
def watch():
    sys.stdin.read()              # EOF: the launcher on taulec is gone
    p.terminate()
    try:
        p.wait(5)
    except subprocess.TimeoutExpired:
        p.kill()
threading.Thread(target=watch, daemon=True).start()
code = p.wait()
os.unlink(path)
print(json.dumps({"exit": code}), flush=True)
'''


class StartError(Exception):
    """The kernel can't be started; the message is shown to the student."""


def log(msg):
    line = f"[miyabi-kernel {getpass.getuser()} {time.strftime('%F %T')}] {msg}"
    print(line, file=sys.stderr, flush=True)
    try:
        os.makedirs(STATE, mode=0o700, exist_ok=True)
        with open(os.path.join(STATE, "log"), "a") as fp:
            fp.write(line + "\n")
    except OSError:
        pass


def ssh_ctl(*args):
    return subprocess.run(["ssh", *args, HOST], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True)


def remote_user():
    out = subprocess.run(["ssh", "-G", HOST], capture_output=True, text=True).stdout
    for line in out.splitlines():
        k, _, v = line.partition(" ")
        if k == "user":
            return v
    return None


def remote_cwd(here):
    """Miyabi directory for the notebook's directory here ("" = Miyabi home)."""
    mnt = os.path.realpath(MOUNT)
    user = remote_user()
    if user and (here == mnt or here.startswith(mnt + os.sep)):
        return REMOTE_BASE + "/" + user + here[len(mnt):]
    return ""


class Forwards:
    """Local -> Miyabi port forwards on the master, recorded under STATE/forwards
    so ones left by a killed launcher are cancelled before reusing the port."""

    def __init__(self):
        self.dir = os.path.join(STATE, "forwards")
        os.makedirs(self.dir, mode=0o700, exist_ok=True)
        self.specs = []

    def _file(self, spec):
        return os.path.join(self.dir, spec.split(":")[1])

    def clear_stale(self, local_ports):
        for lp in local_ports:
            f = os.path.join(self.dir, str(lp))
            if os.path.exists(f):
                with open(f) as fp:
                    ssh_ctl("-O", "cancel", "-L", fp.read().strip())
                os.unlink(f)

    def add(self, lp, rp):
        spec = f"127.0.0.1:{lp}:127.0.0.1:{rp}"
        r = ssh_ctl("-O", "forward", "-L", spec)
        if r.returncode != 0:
            raise StartError(MSG_OTHER.format(detail=f"port forwarding failed: {r.stderr.strip()}"))
        self.specs.append(spec)
        with open(self._file(spec), "w") as fp:
            fp.write(spec)

    def cancel_all(self):
        for spec in self.specs:
            ssh_ctl("-O", "cancel", "-L", spec)
            try:
                os.unlink(self._file(spec))
            except OSError:
                pass
        self.specs = []


def explain(tail):
    text = "\n".join(tail)
    if "Session open refused" in text:
        return MSG_SESSIONS
    if "Permission denied" in text or "Host key verification failed" in text:
        return MSG_LOGIN
    if REMOTE_PYTHON in text and "No such file" in text:
        return MSG_ENV.format(python=REMOTE_PYTHON)
    return MSG_OTHER.format(detail=text or "(no output)")


def run(conn, notebook_dir):
    """Run the remote kernel until it exits; return its exit code."""
    if ssh_ctl("-O", "check").returncode != 0:
        raise StartError(MSG_LOGIN)

    cwd = remote_cwd(notebook_dir)
    code = base64.b64encode(BOOTSTRAP.encode()).decode()
    pycmd = f"import base64;exec(compile(base64.b64decode('{code}'),'miyabi-boot','exec'))"
    cmd = f"exec {shlex.quote(REMOTE_PYTHON)} -c {shlex.quote(pycmd)}"
    proc = subprocess.Popen([*SSH, "-T", HOST, cmd], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    tail = collections.deque(maxlen=15)

    def pump_stderr():
        for line in proc.stderr:
            line = line.rstrip()
            if not line or line.startswith("**"):      # skip ssh's post-quantum notice
                continue
            tail.append(line)
            print(line, file=sys.stderr, flush=True)
    threading.Thread(target=pump_stderr, daemon=True).start()

    # The key goes over stdin; stdin then stays open as the liveness signal.
    keep = {k: conn[k] for k in ("key", "signature_scheme", "kernel_name") if k in conn}
    proc.stdin.write(json.dumps({"names": PORTS, "conn": keep, "cwd": cwd}) + "\n")
    proc.stdin.flush()

    started = {}
    def read_first():
        line = proc.stdout.readline()
        if line:
            started.update(json.loads(line))
    t = threading.Thread(target=read_first, daemon=True)
    t.start()
    t.join(START_TIMEOUT)
    if not started:
        proc.kill()
        proc.wait()
        time.sleep(0.2)                                 # let stderr drain
        if t.is_alive():
            raise StartError(MSG_OTHER.format(detail=f"no answer from Miyabi in {START_TIMEOUT} s"))
        raise StartError(explain(tail))

    t0 = time.monotonic()
    log(f"kernel on {started['host']} pid {started['pid']} cwd {started['cwd']}"
        + ("" if cwd else f" (notebook dir {notebook_dir} is not under {MOUNT})"))
    if started["note"]:
        log(started["note"])

    fw = Forwards()
    def stop(signum, frame):
        log(f"signal {signum}; stopping")
        fw.cancel_all()
        proc.kill()
        sys.exit(1)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGHUP, stop)
    try:
        fw.clear_stale([conn[p] for p in PORTS])
        for p in PORTS:
            fw.add(conn[p], started["ports"][p])
        status = None
        for line in proc.stdout:
            status = json.loads(line).get("exit", status)
        proc.wait()
    finally:
        fw.cancel_all()
        if proc.poll() is None:
            proc.kill()

    code = status if status is not None else proc.returncode
    log(f"kernel exited ({code})")
    if code != 0 and time.monotonic() - t0 < EARLY_EXIT:
        time.sleep(0.2)
        raise StartError(MSG_EARLY.format(code=code, detail="\n".join(tail) or "(no output)"))
    return code


def stand_in_kernel(connection_file, message):
    """Serve Jupyter's connection locally with a kernel that only shows message."""
    from ipykernel.kernelapp import IPKernelApp
    from ipykernel.kernelbase import Kernel

    class MiyabiErrorKernel(Kernel):
        implementation = "miyabi-error"
        implementation_version = "1"
        language_info = {"name": "python", "mimetype": "text/x-python", "file_extension": ".py"}
        banner = message

        async def do_execute(self, code, silent, store_history=True, user_expressions=None,
                             allow_stdin=False, **kwargs):
            if not silent:
                self.send_response(self.iopub_socket, "stream",
                                   {"name": "stderr", "text": "Miyabi kernel: " + message + "\n"})
            return {"status": "error", "execution_count": self.execution_count,
                    "ename": "MiyabiKernelError", "evalue": message.splitlines()[0], "traceback": []}

    IPKernelApp.launch_instance(argv=["-f", connection_file], kernel_class=MiyabiErrorKernel)


def main():
    connection_file = os.path.abspath(sys.argv[1])
    with open(connection_file) as fp:
        conn = json.load(fp)
    # Jupyter starts us in the notebook's directory, often inside the sshfs
    # mount (~/miyabi); staying there would keep it busy (mount-miyabi -u
    # fails, and a lazily unmounted sshfs lingers with its Miyabi session)
    notebook_dir = os.path.realpath(os.getcwd())
    os.chdir(os.path.expanduser("~"))
    # Interrupts come as messages (kernel.json interrupt_mode); a stray SIGINT must not kill us
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        return run(conn, notebook_dir)
    except StartError as e:
        log("start failed: " + str(e).replace("\n", " | "))
        stand_in_kernel(connection_file, str(e))
        return 0


if __name__ == "__main__":
    sys.exit(main())
