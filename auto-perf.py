import socket
import subprocess
import argparse

class State:
    def __init__(self):
        self.pperf = None
        self.pid = 0
        self.proc_name = ""
        self.data_dir = ""

def pidof(name: str) -> int:
    return int(
            subprocess.run(
                f"pidof -s {name}",
                shell=True,
                capture_output=True,
                text=True
                ).stdout
            )

def start_perf(state: State, data: str):
    if (state.pperf is not None):
        print("START", data, "called, but there is a running perf-record instance")
        return
    state.data = state.data_dir + data
    cmd = ["perf", "record", "-p", f"{state.pid}", "-o", state.data]
    state.pperf = subprocess.Popen(args=cmd)
    print("Starting", " ".join(cmd))

def stop_perf(state: State):
    if (state.pperf is None):
        print("STOP called but no running perf-record instance")
        return
    SIGINT = 2
    state.pperf.send_signal(SIGINT)
    state.pperf.wait()
    state.pperf = None
    print("perf-record has completed; see output in", state.data)

def parse_cmd(cmd: str):
    return cmd.split() 

def handle_cmd(state: State, args):
    if len(args) == 1:
        if args[0] == "STOP":
            stop_perf(state)
    elif len(args) == 2:
        if args[0] == "START":
            state.pid = pidof(state.proc_name)
            start_perf(state, args[1])
    else:
        print("invalid command", " ".join(args))

def server(state: State):
    host = '0.0.0.0'  # Listen on all interfaces
    port = 12345      # Port number

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()

        print(f"Server listening on {host}:{port}")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    args = parse_cmd(data.decode())
                    handle_cmd(state, args)
                    break

def args_to_state(state: State, args):
    state.proc_name = args.process_name
    state.data_dir = args.data_directory
    if state.data_dir[-1] != '/':
        state.data_dir += '/'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                 prog = 'auto-perf',
                 description='Trigger perf-record remotely via HTTP calls.')
    parser.add_argument('process_name')
    parser.add_argument('data_directory')
    args = parser.parse_args()
    state = State()
    args_to_state(state, args)
    server(state)

