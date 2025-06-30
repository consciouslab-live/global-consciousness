#!/usr/bin/env bash
set -euo pipefail

BITFILE=/dev/shm/qbits.txt
TMP=/dev/shm/qbits.tmp
ROWS=4 ; COLS=4
API_URL="http://127.0.0.1:80/bits?count=16"

while true; do
  >"$TMP"  # clear file
  
  # Get quantum bits from API
  response=$(curl -s "$API_URL" 2>/dev/null || echo "")
  
  # Extract bits array from JSON response using grep and sed
  bits=$(echo "$response" | grep -o '"bits":\[[0-9,]*\]' | sed 's/"bits":\[\([0-9,]*\)\]/\1/' | tr -d ',')
  
  # Check if we got valid data
  if [[ -z "$bits" ]] || [[ ${#bits} -ne 16 ]]; then
    echo "Error: Failed to get valid quantum bits from API. Response: $response" >&2
    sleep 1
    continue
  fi
  
  # Format bits into 4x4 matrix
  for ((r=0; r<ROWS; r++)); do
    row=''
    for ((c=0; c<COLS; c++)); do
      idx=$((r * COLS + c))
      bit="${bits:$idx:1}"
      row+="$bit "
    done
    echo "${row::-1}" >>"$TMP"   # Remove trailing space at end of line
  done
  
  mv -f "$TMP" "$BITFILE"        # Atomic replace
  sleep 1                        # Refresh at 1 Hz
done