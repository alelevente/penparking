#!/bin/bash

python3 ./generate_demand.py probs.dst.xml --betaconf ../01_simulation/02_scenario/configurations/mix10.json
    
./generate.sh
    
python3 auction_measurement.py 42 --name mix10/baseline/42 --penetration 0
