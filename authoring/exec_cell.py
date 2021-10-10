#!/usr/bin/python3

"""
exec_cell.py
"""

from queue import Queue
from threading import Thread
import os
import re
import subprocess
import sys
import tempfile

dbg = 0

class RealTimeSubprocess(subprocess.Popen):
    """
    A subprocess that allows to read its stdout and stderr in real time
    """

    def __init__(self, cmd):
        """
        :param cmd: the command to execute
        """
        super().__init__(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self._stdio_queue = Queue()
        # stdout -> _stdio_queue
        self._stdout_thread = Thread(target=self._enqueue_output,
                                     args=(self.stdout, 'stdout'))
        self._stdout_thread.daemon = True
        self._stdout_thread.start()
        # stderr -> _stdio_queue
        self._stderr_thread = Thread(target=self._enqueue_output,
                                     args=(self.stderr, 'stderr'))
        self._stderr_thread.daemon = True
        self._stderr_thread.start()

    def _enqueue_output(self, stream, stream_name):
        """
        Add chunks of data from a stream to a queue until the stream is empty.
        """
        for line in iter(lambda: stream.read(4096), b''):
            self._stdio_queue.put((stream_name, line))
        self._stdio_queue.put((stream_name, None))
        stream.close()

    def get_next(self):
        """
        get_next
        """
        (stream_name, line) = self._stdio_queue.get()
        return (stream_name, line)

def send_response(sock, kind, payload):
    """
    send_response
    """
    assert(sock is None), sock
    assert(kind == "stream"), kind
    stream = payload["name"]
    if stream == "stdout":
        fp = sys.stdout
    elif stream == "stderr":
        fp = sys.stderr
    else:
        assert(0), stream
    fp.write(payload["text"])
    fp.flush()

def create_jupyter_subprocess(cmd):
    """
    create_jupyter_subprocess
    """
    return RealTimeSubprocess(cmd)

def filter_magics(code):
    """
    filter_magics
    """
    magics = []
    for line in code.splitlines():
        if line.startswith('//%') or line.startswith('##%'):
            key, value = line[3:].split(":", 2)
            key = key.strip().lower()
            if key == 'file':
                magics.append(('file', value.strip()))
            elif key == 'cmd':
                this_cmd = []
                for argument in re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', value):
                    this_cmd.append(argument)
                magics.append(('cmd', ["bash", "-c", value]))
    return magics

def create_file(filename, code, src_filename):
    if filename is None:
        wp = self.new_temp_file(suffix='.c')
    else:
        if os.path.exists(filename) and filename == src_filename:
            sys.stderr.write("error: file [%s] exists\n" % filename)
            wp = None
        else:
            wp = open(filename, "w")
    if wp:
        wp.write(code)
        wp.close()
        return 1
    else:
        return 0

    
class CKernel:                  # (Kernel)
    """
    CKernel
    """
    def __init__(self):
        self.files = []
        self.iopub_socket = None
    def cleanup_files(self):
        """Remove all the temporary files created by the kernel"""
        for file in self.files:
            os.remove(file)

    def new_temp_file(self, **kwargs):
        """Create a new temp file to be deleted when the kernel shuts down"""
        # We don't want the file to be deleted when closed, but only when the kernel stops
        kwargs['delete'] = False
        kwargs['mode'] = 'w'
        file = tempfile.NamedTemporaryFile(**kwargs)
        self.files.append(file.name)
        return file

    def _write_to_stdout(self, contents):
        send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': contents})

    def _write_to_stderr(self, contents):
        send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': contents})

    def exec_process(self, cmd):
        if dbg:
            self._write_to_stderr("cmd = %s\n" % cmd)
        proc = create_jupyter_subprocess(cmd)
        closed = {}
        while len(closed) < 2:
            if dbg:
                self._write_to_stderr("get_next\n")
            stream_name, contents = proc.get_next()
            if contents is None:
                if dbg:
                    self._write_to_stderr("CLOSE %s\n" % stream_name)
                closed[stream_name] = 1
            else:
                contents = contents.decode("utf-8")
                if dbg:
                    self._write_to_stderr("[%s] --> %s\n"
                                          % (contents, stream_name))
                send_response(None, 'stream',
                              {'name': stream_name, 'text': contents})
                if dbg:
                    self._write_to_stderr("[%s] -> %s DONE\n"
                                          % (contents, stream_name))
        if dbg:
            self._write_to_stderr("WAIT ...\n")
        proc.wait()
        if dbg:
            self._write_to_stderr("WAIT %s\n" % proc.returncode)
        if proc.returncode != 0:  # Compilation failed
            self._write_to_stderr("[C kernel] command exited with code {},"
                                  " subsequent commands will not be"
                                  " executed\n".format(proc.returncode))
        return proc.returncode

    def do_execute(self, code, src):
        """
        do_execute
        """
        magics = filter_magics(code)
        ok = 1
        for kw, magic in magics:
            if dbg:
                self._write_to_stderr("%s: %s\n" % (kw, magic))
            if kw == "file":
                if create_file(magic, code, src) == 0:
                    ok = 0
                    break
            elif kw == "cmd":
                if self.exec_process(magic) != 0:
                    ok = 0
                    break
            else:
                assert(0), magics
        return {'status': ('ok' if ok else 'error'),
                'execution_count': 0, # self.execution_count
                'payload': [],
                'user_expressions': {}}

    def do_shutdown(self):
        """Cleanup the created source code files and executables when shutting down the kernel"""
        self.cleanup_files()

def main():
    """
    main
    """
    arg = sys.argv[1]
    fp = open(arg)
    code = fp.read()
    fp.close()
    k = CKernel()
    res = k.do_execute(code, arg)
    k.do_shutdown()
    return 0 if res["status"] == "ok" else 1

sys.exit(main())

