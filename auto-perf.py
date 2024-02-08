import socket
import subprocess
import argparse
import os
import time

class State:
    def __init__(self):
        self.pperf = None
        self.pid = 0
        self.proc_name = ""
        self.data_dir = ""
        self.start_time = time.time()
        self.end_time = self.start_time
        self.event = ""
        self.frequency = 0
        self.stop_script = ""

def pidof(name: str) -> int:
    return int(
            subprocess.run(
                f"pidof -s {name}",
                shell=True,
                capture_output=True,
                text=True
                ).stdout
            )

def event_is_precise(event: str) -> bool:
    if len(event) == 0:
        return False
    if event[-1] == "p":
        return True
    return False

def start_perf(state: State, data: str):
    if (state.pperf is not None):
        print("START", data, "called, but there is a running perf-record instance")
        return
    state.data = data
    path = state.data_dir + state.data
    cmd = ["sudo", "perf", "record", "-e", f"{state.event}", "-p", f"{state.pid}", "-o", path, "-F", f"{state.frequency}"]
    # -d flag collects ADDR in the sample output
    if event_is_precise(state.event):
        cmd.extend(["-d"])
    state.pperf = subprocess.Popen(args=cmd)
    state.start_time = time.time()
    print("Starting", " ".join(cmd))

def format_stop_script(state: State, argument: str) -> str:
    formatted = state.stop_script
    formatted = formatted.replace("$START_ARGS", state.data)
    formatted = formatted.replace("$STOP_ARGS", argument)
    formatted = formatted.replace("$OUTPUT_DIR", state.data_dir)
    return formatted

def stop_script(command: str):
    print(f"running stop-script {command}:")
    subprocess.run(f"{command}", shell=True, capture_output=True)

def stop_perf(state: State, data: str):
    if (state.pperf is None):
        print("STOP", data, "called but no running perf-record instance")
        return
    SIGINT = 2
    SIGKILL = 9
    print("sending SIGINT to perf")
    # state.pperf.send_signal(SIGINT)
    pidof_perf = pidof("perf")
    subprocess.run(f"sudo kill -2 {pidof_perf}", shell=True)
    print("sent SIGINT to perf")
    state.pperf.wait()
    state.pperf = None
    state.end_time = time.time()
    # run stop script
    if state.stop_script != "":
        stop_script_formatted = format_stop_script(state, data)
        stop_script(stop_script_formatted)
    # get runtime in seconds
    seconds = state.end_time - state.start_time
    # convert to integer
    seconds = int(seconds)
    # store the runtime in the file name
    newpath = state.data_dir + state.data + "_" + str(seconds)
    os.rename(state.data_dir + state.data, newpath)
    print(f"perf-record completed in {seconds}s; see output in", newpath)

def parse_cmd(cmd: str):
    return cmd.split() 

def handle_cmd(state: State, args):
    if len(args) < 1:
        print("invalid empty command")
    # get command and arguments from the array
    command = args[0]
    data = ""
    if len(args) > 1:
        data = " ".join(args[1:])
    # only valid commands are STOP and START
    if command == "STOP":
        stop_perf(state, data)
    elif command == "START":
        if data == "":
            print("invalid START command:", " ".join(args))
            return
        state.pid = pidof(state.proc_name)
        start_perf(state, data)
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
    state.event = args.event
    state.frequency = args.frequency
    state.stop_script = args.stop_script

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                 prog = 'auto-perf',
                 description='Trigger perf-record remotely via HTTP calls.')
    parser.add_argument('process_name')
    parser.add_argument('data_directory')
    parser.add_argument('--event', '-e', nargs='?', default='cycles')
    parser.add_argument('--frequency', '-F', nargs='?', type=int, default=100)
    parser.add_argument('--stop_script', '-s', nargs='?', default="")
    args = parser.parse_args()
    state = State()
    args_to_state(state, args)
    server(state)

