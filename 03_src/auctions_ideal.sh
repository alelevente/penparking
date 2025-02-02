#!/bin/bash

seeds=(42 1812 9698 424 820 75 98 65535 16383 513)

for s in ${seeds[@]}; do
    python3 auction_measurement.py $s --name ideal$s &
done
