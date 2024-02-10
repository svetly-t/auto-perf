import argparse
import os.path
from sortedcontainers import SortedDict
import subprocess
from typing import List

class Region:
    def __init__(self):
        self.start = 0
        self.hits = 0
        self.hits_per_symbol = {}
        self.dram_usage = 0
        self.cxl_usage = 0
    
    def __str__(self):
        usage_kb = (self.dram_usage + self.cxl_usage) / 1024
        string = f"{hex(self.start)}:\n"
        string += f"\tusage {usage_kb} KB\n"
        string += f"\tDRAM ratio {self.dram_ratio()}\n"
        string += f"\thits {self.hits}"
        for sym in self.hits_per_symbol:
            hitsym = self.hits_per_symbol[sym] 
            percent = float(self.hits_per_symbol[sym]) / float(self.hits) 
            percent = percent * 100.0
            string += f"\n\t\t'{sym}': {hitsym} ({int(percent)}%)"
        return string

    def dram_ratio(self) -> float:
        usage = self.dram_usage + self.cxl_usage
        if usage == 0.0:
            return 0.0
        return float(self.dram_usage) / float(usage)

# Node is DRAM if there are cpus on it
def is_dram_node(node: int) -> bool:
    cpulist = f"/sys/devices/system/node/node{node}/cpulist"
    with open(cpulist) as cpufile:
        for line in cpufile:
            if line[0] != '\n':
                return True
    return False

# Convert perf data to a text file via script
def perf_script(perf_data: str, output_dir: str) -> str:
    name = os.path.basename(perf_data)
    output = f"{output_dir}/{name}.txt"
    subprocess.run(
            f"perf script -F addr,ip,sym -i {perf_data} > {output}",
            shell=True
            )
    return output

# Parse over numa_maps and get us a list of memory regions
def get_regions(numa_maps: str):
    region_list = []
    with open(numa_maps) as nm:
        for line in nm:
            tokens = line.split()
            region = Region()
            for token in tokens[1:]:
                # Look for N[#]=[pages]
                if token[0] == 'N':
                    idx = token.find('=')
                    if idx == -1:
                        continue
                    node = int(token[1:idx])
                    pages = int(token[idx + 1:])
                    usage = pages * 4096
                    if is_dram_node(node):
                        region.dram_usage += usage
                    else:
                        region.cxl_usage += usage
            # Convert first token to address
            region.start = int(tokens[0],16)
            region_list.append(region)
    return region_list

# Insert regions into a sorted dictionary, key is starting address
def region_dict(region_list):
    d = SortedDict()
    for region in region_list:
        d[region.start] = region
    return d

# Parse over perf.data and update per-region info as appropriate
def update_regions(perf_data: str, regions):
    with open(perf_data) as perf:
        for line in perf:
            tokens = line.split()
            vaddr = int(tokens[0],16)
            symbol = tokens[2]
            # This gets the index of the first address in 'regions'
            # that is less than or equal to 'vaddr'
            idx = regions.bisect_right(vaddr) - 1
            key = regions.peekitem(idx)[0]
            regions[key].hits += 1
            if symbol not in regions[key].hits_per_symbol:
                regions[key].hits_per_symbol[symbol] = 1
            else:
                regions[key].hits_per_symbol[symbol] += 1

# Output region information
def print_regions(regions):
    no_hits = 0
    mem_missed = 0
    for key in regions:
        if regions[key].hits == 0:
            no_hits += 1
            mem_missed = regions[key].dram_usage + regions[key].cxl_usage
            continue
        print(regions[key])
        print("----")
    print(f"{no_hits} regions had zero samples")
    mem_missed /= 1024
    print(f"total of {mem_missed} KB had no (sampled!) LLC misses")

def csv_regions(regions):
    # Get all the symbols
    symdict = {}
    for key in regions:
        for sym in regions[key].hits_per_symbol:
            if sym not in symdict:
                symdict[sym] = True
    # Put the symbols in a list
    symlist = []
    for sym in symdict:
        symlist.append(sym)
    # print header
    header = "start_addr,usage_kb,dram_ratio,total_hits"
    for sym in symdict:
        header += f',{sym}'
    print(header)
    # print per region csl
    for key in regions:
        usage_kb = (regions[key].dram_usage + regions[key].cxl_usage) / 1024
        line = f"{hex(regions[key].start)},"
        line += f"{usage_kb},"
        line += f"{regions[key].dram_ratio()},"
        line += f"{regions[key].hits}"
        for sym in symlist:
            if sym not in regions[key].hits_per_symbol:
                line += ",0"
            else:
                line += f",{regions[key].hits_per_symbol[sym]}"
        print(line)

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
                prog = 'auto-script',
                description = 'Using samples from perf script, print information about VMAs'
            )
    parser.add_argument('--directory', '-d', nargs='?', default='/tmp')
    parser.add_argument('--csv', '-c', action='store_true')
    parser.add_argument('perf_data')
    parser.add_argument('numa_maps')
    args = parser.parse_args()

    directory = format_directory(args.directory)

    script = perf_script(args.perf_data, directory)

    list_of_regions = get_regions(args.numa_maps)

    regions = region_dict(list_of_regions)

    update_regions(script, regions)

    delete_files([script])

    if not args.csv:
        print_regions(regions)
    else:
        csv_regions(regions)
