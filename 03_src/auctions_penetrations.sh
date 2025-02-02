#!/bin/bash

seeds=(42 1812 9698 424 820 75 98 65535 16383 513)
pens=(1 2 3 4 5 6 7 8 9)

for p in ${pens[@]}; do
    for s in ${seeds[@]}; do
        python3 auction_measurement.py $s --name pen$p:$s --penetration $p &
    done
    wait
done
