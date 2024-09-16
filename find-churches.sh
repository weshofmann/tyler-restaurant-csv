#!/bin/bash

RADIUS=5
DISTANCE=2.5
BUSINESS_TYPE=church

function divider() {
  echo ""
  echo ""
  echo "=================================================================================================================="
  echo ""
  echo ""

}
./find-businesses.py --search-center 'Norman, OK' -n 100 --bearing 0 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Bethany, OK' -n 150 --bearing 45 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Midwest City, OK' -n 150 --bearing 270 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Quail Springs Mall, OK' -n 150 --bearing 165 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Scissortail Park, OK' -n 150 --bearing 315 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Moore, OK' -n 200 --bearing 0 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center '10145 Northwest Expy, Yukon, OK 73099' -n 50 --bearing 75 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Edmond, OK' -n 200 --bearing 225 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Yukon, OK' -n 300 --bearing 100 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'Oklahoma City, OK' -n 50 --bearing 170 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./find_businesses.py --search-center 'The Village, OK' -n 300 --bearing 165 --search-radius $RADIUS -d $DISTANCE -t $BUSINESS_TYPE
divider
./make_csv.py -t $BUSINESS_TYPE
