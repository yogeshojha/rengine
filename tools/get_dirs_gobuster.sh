#!/bin/sh

gobuster -u $1 -w $2 -o $3 -x $4 -t $5 -s $6 -l
# Example for gobuster v3: gobuster dir --url $1 --wordlist $2 --output $3 --extensions $4 --threads $5 --status-codes $6 --include-length
