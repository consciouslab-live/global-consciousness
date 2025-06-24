#!/usr/bin/env bash
set -euo pipefail

BITFILE=/dev/shm/qbits.txt
TMP=/dev/shm/qbits.tmp
ROWS=4 ; COLS=4

while true; do
  row=''
  >"$TMP"  # clear file
  for ((r=0; r<ROWS; r++)); do
    row=''
    # Generate a row of COLS 0/1 values, separated by spaces
    for ((c=0; c<COLS; c++)); do
      byte=$(od -An -N1 -tu1 /dev/urandom)
      [[ $byte -lt 128 ]] && bit=0 || bit=1
      row+="$bit "
    done
    echo "${row::-1}" >>"$TMP"   # Remove trailing space at end of line
  done
  mv -f "$TMP" "$BITFILE"        # Atomic replace
  sleep 1                        # Refresh at 1 Hz
done