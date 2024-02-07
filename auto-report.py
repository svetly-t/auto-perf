import argparse
import os.path
import subprocess
import sys
from typing import List

debug_flag=False

def debug_msg(msg: str):
    if not debug_flag:
        return
    print(f"[{sys.argv[0]}] {msg}")

def convert_file(file: str, directory: str) -> str:
    base = os.path.basename(file)
    subprocess.run(
            f"sudo perf report -i {file} | \
              head -n 100 | \
              sed '/^#.*/d' > {directory}/{base}_formatted",
              shell=True
            )
    return f"{directory}/{base}_formatted"

def convert_files(files: list[str], directory: str) -> List[str]:
    out = []
    for file in files:
        out.append(convert_file(file, directory))
    return out

def analyze(files: list[str]):
    filestr = ' '.join(str(f) for f in files)
    debug_msg(f"running ./analyze.sh {filestr}")
    analysis = subprocess.run(
        f"./analyze.sh {filestr}",
        shell=True,
        capture_output=True,
        text=True
        ).stdout
    print(analysis)

# strip the last '/' from a directory path
def format_directory(directory: str) -> str:
    if (len(directory) == 0):
        return ""
    if directory[-1] == '/':
        return directory[:-1]
    return directory

def delete_files(files: List[str]):
    for f in files:
        os.remove(f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog = 'auto-report',
        description = 'takes a series of perf.data files as input, converts them to text, and then outputs the most common symbols, with the average and standard deviations of their overheads'
    )
    parser.add_argument('files', nargs='+')
    parser.add_argument('--directory', '-d', nargs='?', default='/tmp')
    parser.add_argument('--save', '-s', action='store_true')
    parser.add_argument('--debug', '-b', action='store_true')

    args = parser.parse_args()

    debug_flag = args.debug

    directory = format_directory(args.directory)
    debug_msg(f"using directory {directory}")

    formatted_files = convert_files(args.files, directory)
    analyze(formatted_files)
    if not args.save:
        delete_files(formatted_files)