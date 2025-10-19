#!/bin/bash

seeds=(42 1812 9698 424 820 75 98 65535 16383 513)
mixes=("mix10" "mix25" "mix50")

for m in ${mixes[@]}; do
    python3 ./generate_demand.py probs.dst.xml --betaconf ../01_simulation/02_scenario/configurations/$m.json
    ./generate.sh
    
    for s in ${seeds[@]}; do
        python3 auction_measurement.py $s --name $m/auction0/$s --penetration 0 &
    done
    wait
done
