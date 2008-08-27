#! /bin/sh

# This is a dangerous command, so give the users a chance to bail out.

echo -n "Running this program will destroy and recreate the database.\n\nAre you sure? [Ny] "
read ans
echo $ans | egrep -i "y$|yes$" > /dev/null
if [ $? -ne 0 ]; then
	echo "Exiting without altering database."
	exit 0
fi

dropdb fetegeo > /dev/null 2> /dev/null
dropuser root > /dev/null 2> /dev/null
createuser -I -l -r -d -s root || exit 1
createdb -U root fetegeo || exit 1
./geonames.py || exit 1
./postcodes.py || exit 1