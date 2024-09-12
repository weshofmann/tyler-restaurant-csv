#!/bin/bash

RADIUS=15
DISTANCE=3

./find-restaurants.py --search-center 'The Village, OK' -n 50 -b 185 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Edmond, OK' -n 60 -b 225 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Yukon, OK' -n 70 -b 90 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Bethany, OK' -n 70 -b 45 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Oklahoma City, OK' -n 100 -b 180 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Norman, OK' -n 50 -b 0 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Moore, OK' -n 50 -b 0 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Midwest City, OK' -n 50 -b 270 -r $RADIUS -d $DISTANCE
echo "======================================================================================================"
./make_csv.py
