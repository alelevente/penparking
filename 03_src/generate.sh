#!/bin/bash

netgenerate --grid -o ../01_simulation/02_scenario/grid.net.xml --grid.number 6 --tls.guess --tls.default-type actuated --no-turnarounds.except-deadend --grid.attach-length 0 --fringe.guess --default-junction-type traffic_light --tls.guess.joining

python $SUMO_HOME/tools/randomTrips.py -n ../01_simulation/02_scenario/grid.net.xml -e 14400 --period 1.25 --weights-prefix probs -o ../01_simulation/02_scenario/trips.trips.xml

python $SUMO_HOME/tools/generateParkingAreas.py -n ../01_simulation/02_scenario/grid.net.xml --space-length 6.6 --min 15 --max 15  --seed 42 --length 6.6 --output-file ../01_simulation/02_scenario/parking_areas.add.xml

$SUMO_HOME/tools/generateParkingAreaRerouters.py -n ../01_simulation/02_scenario/grid.net.xml -a ../01_simulation/02_scenario/parking_areas.add.xml -o ../01_simulation/02_scenario/parking_rerouters.add.xml --max-distance-alternatives 750

python3 ./add_stops.py

duarouter -n ../01_simulation/02_scenario/grid.net.xml -r ../01_simulation/02_scenario/trips_with_stops.trips.xml -o ../01_simulation/02_scenario/trips.rou.xml --ignore-errors -a ../01_simulation/02_scenario/parking_areas.add.xml

