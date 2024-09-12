#!/bin/bash

RADIUS=4
DISTANCE=2

./find-restaurants.py --search-center 'Moore, OK' -n 100 --bearing 0 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center '10145 Northwest Expy, Yukon, OK 73099' -n 50 --bearing 75 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Scissortail Park, OK' -n 50 --bearing 315 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'The Village, OK' -n 75 --bearing 165 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Edmond, OK' -n 100 --bearing 225 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Yukon, OK' -n 70 --bearing 90 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Bethany, OK' -n 70 --bearing 45 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Oklahoma City, OK' -n 100 --bearing 180 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Norman, OK' -n 50 --bearing 0 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./find-restaurants.py --search-center 'Midwest City, OK' -n 50 --bearing 270 --search-radius $RADIUS -d $DISTANCE
echo "======================================================================================================"
./make_csv.py
