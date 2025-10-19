#!/bin/bash

seeds=(42 1812 9698 424 820 75 98 65535 16383 513)
mixes=("mix10" "mix25" "mix50")
penetrations=(2 4 6 8 10)

for m in ${mixes[@]}; do
    python3 ./generate_demand.py probs.dst.xml
    ./generate.sh
    
    for p in ${penetrations[@]}; do
        for s in ${seeds[@]}; do
            python3 information_measurement.py $s ../01_simulation/02_scenario/configurations/$m.json $p --name $m/information$p/$s &
        done
        wait
    done
done
