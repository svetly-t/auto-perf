#!/bin/bash

# Check if exactly three arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <Process Name> <Directory> <Filename>"
    exit 1
fi

# Assign arguments to variables for better readability
PID=$(pidof -s $1)
DIR=$2
FILENAME=$3

# Check if we have a PID with the given name
if [ ! -n "$PID" ]; then
    echo "No process exists with name $1. Exiting."
    exit 1
fi

# Check if the directory exists, if not, create it
if [ ! -d "$DIR" ]; then
    echo "Directory $DIR does not exist. Exiting."
    exit 1
fi

# Construct the full file path
FULL_PATH="$DIR/$FILENAME.smaps"

# Use cat to read /proc/$PID/smaps and redirect the output to the specified file
cat "/proc/$PID/smaps" > "$FULL_PATH"

echo "Memory mapping for PID $PID saved to $FULL_PATH"

