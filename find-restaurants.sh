#!/bin/bash

RADIUS=4
DISTANCE=1.5
BUSINESS_TYPE=restaurant

function divider() {
  echo ""
  echo ""
  echo "=================================================================================================================="
  echo ""
  echo ""

}

./find-businesses.py --search-center 'Norman, OK' -n 50 --bearing 0 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Midwest City, OK' -n 200 --bearing 270 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'The Village, OK' -n 500 --bearing 165 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Quail Springs Mall, OK' -n 150 --bearing 165 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Scissortail Park, OK' -n 150 --bearing 315 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Moore, OK' -n 175 --bearing 0 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Edmond, OK' -n 150 --bearing 225 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Yukon, OK' -n 150 --bearing 90 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Bethany, OK' -n 100 --bearing 45 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find-businesses.py --search-center 'Oklahoma City, OK' -n 100 --bearing 170 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./make_csv.py -t $BUSINESS_TYPE
