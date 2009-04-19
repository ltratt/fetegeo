#! /usr/bin/env python

# Copyright (C) 2008 Laurence Tratt http://tratt.net/laurie/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.




import codecs, os, urllib
import imputils

try:
    import pgdb as dbmod
except ImportError:
    import psycopg2 as dbmod




def get_country_id(iso2):

    c.execute("SELECT id FROM country WHERE iso2=%(iso2)s", dict(iso2=iso2))

    return c.fetchone()[0]



db = dbmod.connect(user="root", database="fetegeo")
c = db.cursor()


# UK post codes

print "===> Importing UK postcodes"

uk_id = get_country_id("GB")
f = urllib.urlopen("http://www.npemap.org.uk/data/fulllist")
for l in codecs.EncodedFile(f, "utf-8"):
    if l[0] == "#":
        continue
    sp = l.strip().split(",")
    main=sp[0]
    sup=sp[1]
    if sup == "":
        sup = None
    c.execute("""INSERT INTO postcode (country_id, main, sup, lat, long) VALUES
      (%(uk_id)s, %(main)s, %(sup)s, %(lat)s, %(long)s)""",
      dict(uk_id=uk_id, main=main, sup=sup, lat=sp[4], long=sp[5]))

f.close()
db.commit()


# German post codes

print "===> Importing German postcodes"

de_id = get_country_id("DE")
f = urllib.urlopen("http://fa-technik.adfc.de/code/opengeodb/PLZ.tab")
for l in f:
    if l[0] == "#":
        continue
    sp = l.strip().split("\t")
    main = sp[1].decode("latin-1").encode("utf-8")
    lat = float(sp[3])
    long = float(sp[2])
    area_pp = sp[4].decode("latin-1").encode("utf-8")
    c.execute("""INSERT INTO postcode (country_id, main, lat, long, area_pp) VALUES
      (%(de_id)s, %(main)s, %(lat)s, %(long)s, %(area_pp)s)""",
      dict(de_id=de_id, main=main, lat=lat, long=long, area_pp=area_pp))

f.close()
db.commit()

# US zip codes

print "===> Downloading US zipcodes"

us_zip_path = imputils.zipex("http://mappinghacks.com/data/zipcode.zip", "zipcode.csv")

print "===> Importing US zipcodes"

us_id = get_country_id("US")
f = codecs.open(us_zip_path, "rt", "utf-8")
f.readline() # Skip the first line which contains the column names
for l in f:
    if l.strip() == "":
        continue
    # Lines in the US zipcode file are quoted CSV e.g.:
    #   "00210","Portsmouth","NH","43.005895","-71.013202","-5","1"
    sp = [x[1:-1] for x in l.strip().split(",")]
    main = sp[0]
    lat = float(sp[3])
    long = float(sp[4])
    area_pp = "%s %s" % (sp[1], sp[2])
    c.execute("""INSERT INTO postcode (country_id, main, lat, long, area_pp) VALUES
      (%(us_id)s, %(main)s, %(lat)s, %(long)s, %(area_pp)s)""",
      dict(us_id=us_id, main=main, lat=lat, long=long, area_pp=area_pp))

f.close()
os.remove(us_zip_path)


db.commit()