#!/usr/bin/env bash

# before running script, run the following command "chmod +x Test_on_all_boards.sh"
# Call script using "./Test_on_all_boards.sh [feature used 1] [feature used 2] ...""
# example:  "./Test_on_all_boards.sh FC"



SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#clear output file
> test_results.txt

for board in "3_3" "3_4" "4_4" "5_5"; do
    for run in $(seq 0 4); do
        python3 "$SCRIPT_DIR/bin/Main.pyc" "$@" "$SCRIPT_DIR/../Sudoku_Generator/Boards/${board}_boards_${run}.txt" >> test_results.txt
    done
done
