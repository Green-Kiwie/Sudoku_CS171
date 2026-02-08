#!/usr/bin/env bash

# before running script, run the following command "chmod +x Test_on_all_boards.sh"
# Call script using "./Test_on_all_boards.sh [feature used 1] [feature used 2] ...""
# example:  "./Test_on_all_boards.sh FC"



SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#clear output file
> test_results.txt

for i in $(seq 3 15); do
    for j in $(seq 0 4); do
        python3 "$SCRIPT_DIR/bin/Main.pyc" "$@" "$SCRIPT_DIR/../Sudoku_Generator/Boards/${i}_${i}_boards_${j}.txt" >> test_results.txt
    done
done

