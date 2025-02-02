#!/bin/bash

netgenerate --grid -o ../02_scenario/grid.net.xml --grid.number 6 --tls.guess --tls.default-type actuated --no-turnarounds.except-deadend --grid.attach-length 0 --fringe.guess --default-junction-type traffic_light --tls.guess.joining

python $SUMO_HOME/tools/randomTrips.py -n ../02_scenario/grid.net.xml -e 14400 --period 1.25 --weights-prefix probs

python $SUMO_HOME/tools/generateParkingAreas.py -n ../02_scenario/grid.net.xml --space-length 6.7 --min 15 --max 15  --seed 42 --length 6.7 --output-file ../02_scenario/parking_areas.add.xml

$SUMO_HOME/tools/generateParkingAreaRerouters.py -n ../02_scenario/grid.net.xml -a ../02_scenario/parking_areas.add.xml -o ../02_scenario/parking_rerouters.add.xml --max-distance-alternatives 750

python3 ./add_stops.py

duarouter -n ../02_scenario/grid.net.xml -r ../02_scenario/trips_with_stops.trips.xml -o ../02_scenario/trips.rou.xml --ignore-errors -a ../02_scenario/parking_areas.add.xml

