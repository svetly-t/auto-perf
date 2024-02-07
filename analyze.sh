#!/bin/bash

# Check if at least one file is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 file1 [file2 ...]"
    exit 1
fi

# Process each file
# for file in "$@"; do
awk '
{
    # Extract the percentage (remove the % sign) and the symbol
    percentage = substr($1, 1, length($1)-1)
    symbol = $5

    # Accumulate the sum and sum of squares for each symbol
    sum[symbol] += percentage
    sumsq[symbol] += percentage^2
    count[symbol]++
}
END {
    # Calculate and print the average and standard deviation for each symbol
    print "Symbol\tAverage\tStandard Deviation"

    for (symbol in sum) {
        avg = sum[symbol] / count[symbol]
        avghun = avg * 100.0
        avgstr = sprintf("%04.0f", avghun)
        stddev = sqrt((sumsq[symbol] - sum[symbol]^2 / count[symbol]) / count[symbol])
        record = sprintf("%s,%.2f%%,%.2f%%\n", symbol, avg, stddev)
        
        out[avgstr] = record
    }

    asorti(out, sout)

    j = length(sout)

    for (i = j; i >= 1; i--) {
        printf("%s", out[sout[i]])
    }
}
' $@
# done

