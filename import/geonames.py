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


import codecs, os, re, sys, tempfile, urllib
import imputils

try:
    import pgdb as dbmod
except ImportError:
    import psycopg2 as dbmod
    import psycopg2.extensions
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)



# On some of the huge database inserts, we try and bundle up large numbers of inserts and do them in
# one go; this variable controls how many are bundled up in each go. Setting this value too low or
# too high impacts performance; exactly what is the best possible value is probably system dependent.

EXEC_MANY = 1024

TYPE_STATE = 0
TYPE_COUNTY = 1
TYPE_PLACE = 2

ADMIN1_ABBRVS = {
    # Australia
    "AU.01" : "ACT", "AU.02" : "NSW", "AU.03" : "NT", "AU.04" : "QLD", "AU.05" : "SA",
    "AU.06" : "TAS", "AU.07" : "VIC", "AU.08" : "WA",
    # Canada
    "CA.01" : "AB", "CA.02" : "BC", "CA.03" : "MB", "CA.04" : "NB", "CA.05" : "NL", "CA.07" : "NS",
    "CA.08" : "ON", "CA.09" : "PE", "CA.10" : "QC", "CA.11" : "SK", "CA.12" : "YT", "CA.13" : "NT",
    "CA.14" : "NU",
    # US
    "US.AL" : "AL", "US.AK" : "AK", "US.AZ" : "AZ", "US.AR" : "AR", "US.CA" : "CA", "US.CO" : "CO",
    "US.CT" : "CT", "US.DE" : "DE", "US.DC" : "DC", "US.FL" : "FL", "US.GA" : "GA", "US.HI" : "HI",
    "US.ID" : "ID", "US.IL" : "IL", "US.IN" : "IN", "US.IA" : "IA", "US.KS" : "KS", "US.KY" : "KY",
    "US.LA" : "LA", "US.ME" : "ME", "US.MD" : "MD", "US.MA" : "MA", "US.MI" : "MI", "US.MN" : "MN",
    "US.MS" : "MS", "US.MO" : "MO", "US.MT" : "MT", "US.NE" : "NE", "US.NV" : "NV", "US.NH" : "NH",
    "US.NJ" : "NJ", "US.NM" : "NM", "US.NY" : "NY", "US.NC" : "NC", "US.ND" : "ND", "US.OH" : "OH",
    "US.OK" : "OK", "US.OR" : "OR", "US.PA" : "PA", "US.RI" : "RI", "US.SC" : "SC", "US.SD" : "SD",
    "US.TN" : "TN", "US.TX" : "TX", "US.UT" : "UT", "US.VT" : "VT", "US.VA" : "VA", "US.WA" : "WA",
    "US.WV" : "WV", "US.WI" : "WI", "US.WY" : "WY"
}

# Some countries are commonly called by names other than their official names. The form of this is
# [<main geonames name>, <iso 2 language code>, <alternative names 1>, ..., <alternative names n>].

ALT_COUNTRY_NAMES = [["United States", "en", "America"], ["United Kingdom", "en", "Great Britain", "Great Britain"]]
    

_RE_SPLIT = re.compile("[ ,-/]")

def _split(s):

    return [x.lower() for x in _RE_SPLIT.split(s)]


def _hash_wd(s):

    return hash(s)



def _hash_list(s):

    return hash("_".join(s))



print "===> Connecting to database"

db = dbmod.connect(user="root", database="fetegeo")
if hasattr(db, "set_client_encoding"):
    db.set_client_encoding("utf-8")



print "===> Creating tables"

f = file("tables", "rt")
c = db.cursor()
c.execute(f.read())
f.close()



print "===> Importing language codes"

langs_map = {}
f = urllib.urlopen("http://download.geonames.org/export/dump/iso-languagecodes.txt")
for l in codecs.EncodedFile(f, "utf-8"):
    iso639_3, iso639_2, iso639_1, iso_name = l.strip().split("\t")
    if iso_name == "Language Name":
        continue

    c.execute("""INSERT INTO lang (iso639_1, iso639_3, iso_name)
      VALUES (%(iso639_1)s, %(iso639_3)s, %(iso_name)s) RETURNING id;""",
      dict(iso639_1=iso639_1, iso639_3=iso639_3, iso_name=iso_name))
    id = int(c.fetchone()[0])
    langs_map[iso639_1] = id
    langs_map[iso639_2] = id
    langs_map[iso639_3] = id
f.close()



print "===> Importing country codes"

f = codecs.open("country_codes", "rt", "utf-8")
countries_map = {}
for l in f:
    iso3, iso2 = l.strip().split("\t")
    c.execute("""INSERT INTO country (iso2, iso3)
      VALUES (%(iso2)s, %(iso3)s) RETURNING id;""",
      dict(iso2=iso2, iso3=iso3))
    countries_map[iso2] = int(c.fetchone()[0])



print "===> Importing country names"

langs = langs_map.keys()
langs.sort()
for iso639_1 in langs:
    if len(iso639_1) != 2:
        # For the time being, we only use ISO 639_1 language codes.
        continue

    print iso639_1,
    sys.stdout.flush()
    for r in urllib.urlopen("http://www.geonames.org/countryInfoCSV?lang=%s" % iso639_1):
        sp = r.split("\t")

        if sp[0].find("iso alpha2") != -1 or r.strip() == "":
            continue

        country_id = countries_map[sp[0].upper()]
        name = sp[4]
        lang_id = langs_map[iso639_1.lower()]

        lwd = _split(name)[-1].lower() # Last word in name
        lwdh = _hash_wd(lwd)
        c.execute("""INSERT INTO country_name (country_id, lang_id, is_official, name, name_lwdh)
          VALUES (%(country_id)s, %(lang_id)s, TRUE, %(name)s, %(name_lwdh)s)""", 
          dict(country_id=country_id, lang_id=lang_id, name=name, name_lwdh=lwdh))

for alts in ALT_COUNTRY_NAMES:
    c.execute("SELECT country_id FROM country_name WHERE name=%(name)s", dict(name=alts[0]))
    country_id = c.fetchone()[0]
    lang_id = langs_map[alts[1]]
    for alt in alts[2:]:
        lwd = _split(alt)[-1].lower() # Last word in name
        lwdh = _hash_wd(lwd)
        c.execute("""INSERT into country_name (country_id, lang_id, is_official, name, name_lwdh)
          VALUES  (%(country_id)s, %(lang_id)s, FALSE, %(name)s, %(name_lwdh)s)""",
          dict(country_id=country_id, lang_id=lang_id, name=alt, name_lwdh=lwdh))

print
f.close()
db.commit()


print "===> Importing admin1 areas"

# In theory, Geoname's Admin1 areas are roughly equivalent to a state within a country.
#
# Unfortunately this isn't uniform. For example UK counties are in both Admin1 and Admin2. I can't
# explain why.

f = urllib.urlopen("http://download.geonames.org/export/dump/admin1Codes.txt")
admin1_map = {}
for l in codecs.EncodedFile(f, "utf-8"):
    r = [x.strip() for x in l.split("\t")]
    if len(r) == 1:
        # Some rows have dodgy data... sigh.
        continue

    # Admin1 IDs are of the form "GB.A4" and so on. Notice the second part of the identifier is of
    # variable length.
    country_id = countries_map[r[0][:2]]

    c.execute("INSERT INTO place (country_id, type) VALUES (%(country_id)s, %(type)s) RETURNING id",
      dict(country_id=country_id, type=TYPE_STATE))
    id = int(c.fetchone()[0])
    admin1_map[r[0]] = id

    lang_id = None
    name_hash = _hash_list(_split(r[1]))
    c.execute("""INSERT INTO place_name (place_id, lang_id, name, name_hash, is_official)
      VALUES (%(place_id)s, %(lang_id)s, %(name)s, %(name_hash)s, TRUE)""",
      dict(place_id=id, lang_id=lang_id, name=r[1], name_hash=name_hash))

    if ADMIN1_ABBRVS.has_key(r[0]):
        # This admin1 area also has an abbreviation
        name_hash = _hash_list(_split(ADMIN1_ABBRVS[r[0]]))
        c.execute("""INSERT INTO place_name (place_id, lang_id, name, name_hash, is_official)
          VALUES (%(place_id)s, %(lang_id)s, %(name)s, %(name_hash)s, FALSE)""",
          dict(place_id=id, lang_id=lang_id, name=ADMIN1_ABBRVS[r[0]], name_hash=name_hash))

f.close()
db.commit()


print "===> Importing admin2 areas"

# In theory, Geoname's Admin2 areas are roughly equivalent to a county within a state.

f = urllib.urlopen("http://download.geonames.org/export/dump/admin2Codes.txt")
admin2_map = {}
for l in codecs.EncodedFile(f, "utf-8"):
    r = [x.strip() for x in l.split("\t")]
    if r[0][0 : 2] == "GB" and r[1].startswith("County of "):
        # For British data, geonames stores the name as e.g. "County of Somerset" so strip it down to
        # "Somerset" as no-one is going to type in "County of Somerset". Note that this intentionally
        # doesn't catch "County Durham" which must stay as it is.
        name=asciiname=r[1][len("County of ") : ]
    elif r[0][0 : 2] == "AU" and r[1].startswith("State of "):
        name=asciiname=r[1][len("State of ") : ]
    else:
        name=r[1]
        asciiname=r[2]

    # Admin2 IDs are of the form "GB.ENG.M3" and so on. Any that aren't are considered invalid.
    if len(r[0].split(".")[0]) != 2:
        print "Admin2 area with incorrect Admin1 code:", r
        continue
    country_id = countries_map[r[0][:2]]
    admin1_code = r[0][:r[0].index(".", r[0].index(".") + 1)]
    if not admin1_map.has_key(admin1_code):
        print "Admin2 area with incorrect Admin1 code:", r
        continue
    admin1_id = admin1_map[admin1_code]

    c.execute("""INSERT INTO place (country_id, parent_id, type) VALUES (%(country_id)s,
      %(admin1_id)s, %(type)s) RETURNING id""",
      dict(country_id=country_id, admin1_id=admin1_id, type=TYPE_COUNTY))
    id = int(c.fetchone()[0])
    admin2_map[r[0]] = id

    lang_id = None
    name_hash = _hash_list(_split(name))
    c.execute("""INSERT INTO place_name (place_id, lang_id, name, name_hash, is_official)
      VALUES (%(place_id)s, %(lang_id)s, %(name)s, %(name_hash)s, TRUE)""",
      dict(place_id=id, lang_id=lang_id, name=name, name_hash=name_hash))

    if asciiname != name:
        name_hash = _hash_list(_split(asciiname))
        c.execute("""INSERT INTO place_name (place_id, lang_id, name, name_hash, is_official)
          VALUES (%(place_id)s, %(lang_id)s, %(name)s, %(name_hash)s, FALSE)""",
          dict(place_id=id, lang_id=lang_id, name=asciiname, name_hash=name_hash))

f.close()
db.commit()


print "===> Importing country codes"

GEONAMEID = 0
NAME = 1
ASCIINAME = 2
ALTERNATENAMES = 3
LATITUDE = 4
LONGITUDE = 5
FEATURE_CLASS = 6
FEATURE_CODE = 7
COUNTRY_CODE = 8
CC2 = 9
ADMIN1_CODE = 10
ADMIN2_CODE = 11
ADMIN3_CODE = 12
ADMIN4_CODE = 13
POPULATION = 14
ELEVATION = 15
GTOPO30 = 16
TIMEZONE = 17
MODIFICATION_DATE = 18

name_sql = """INSERT INTO place_name (place_id, lang_id, name, name_hash, is_official)
  VALUES (%(place_id)s, %(lang_id)s, %(name)s, %(name_hash)s, %(is_official)s)"""

c.execute("SELECT nextval('place_id_seq')");
place_id = c.fetchone()[0]
for iso2 in countries_map.keys():
    sys.stdout.write("===> Processing %s data... downloading... " % iso2)
    sys.stdout.flush()
    cn_path = imputils.zipex("http://download.geonames.org/export/dump/%s.zip" % iso2, "%s.txt" % iso2)
    
    sys.stdout.write("collating... ")
    sys.stdout.flush()
    f = codecs.open(cn_path, "rt", "utf-8")
    place_buf = []
    name_buf = []
    tmp_place_hndl, tmp_place_path = tempfile.mkstemp()
    tmp_place_name_hndl, tmp_place_name_path = tempfile.mkstemp()
    for l in f:
        r = [x.strip() for x in l.split("\t")]
        
        geonames_id = r[GEONAMEID]

        if r[COUNTRY_CODE] == "GB" and r[NAME].startswith("County of "):
            # For British data, geonames stores the name as e.g. "County of Somerset" so strip it down to
            # "Somerset" as no-one is going to type in "County of Somerset". Note that this intentionally
            # doesn't catch "County Durham" which must stay as it is.
            name=asciiname=r[ASCIINAME][len("County of ") : ]
        elif r[COUNTRY_CODE] == "AU" and r[NAME].startswith("State of "):
            name=asciiname=r[ASCIINAME][len("State of ") : ]
        elif r[COUNTRY_CODE] == "US" and r[NAME].endswith(", City of"):
            name=asciiname="City of %s" % r[ASCIINAME][ : len(", City of")]
        else:
            name=r[NAME]
            asciiname=r[ASCIINAME]

        country_id = countries_map[r[COUNTRY_CODE]]
        parent_id = "\\N" # postgres's way of saying "NULL"
        admin2_code = "%s.%s.%s" % (r[COUNTRY_CODE], r[ADMIN1_CODE], r[ADMIN2_CODE])
        if admin2_map.has_key(admin2_code):
            parent_id = str(admin2_map[admin2_code])
        else:
            admin1_code = "%s.%s" % (r[COUNTRY_CODE], r[ADMIN1_CODE])
            if admin1_map.has_key(admin1_code):
                parent_id = str(admin1_map[admin1_code])

        place_tsv = u"\t".join([str(place_id), geonames_id, str(country_id), parent_id, \
          r[LATITUDE], r[LONGITUDE], str(TYPE_PLACE), r[POPULATION]])
        os.write(tmp_place_hndl, place_tsv.encode("utf-8") + "\n")

        lang_id = "\\N"
        name_hash = _hash_list(_split(name))
        place_name_tsv = "\t".join([str(place_id), lang_id, name, str(name_hash), "TRUE"])
        os.write(tmp_place_name_hndl, place_name_tsv.encode("utf-8") + "\n")

        if asciiname != name:
            asciiname_hash = _hash_list(_split(asciiname))
            place_name_tsv = "\t".join([str(place_id), lang_id, asciiname, \
              str(asciiname_hash), "FALSE"])
            os.write(tmp_place_name_hndl, place_name_tsv.encode("utf-8") + "\n")

        place_id += 1

    f.close()
    os.remove(cn_path)

    os.close(tmp_place_hndl)
    os.close(tmp_place_name_hndl)
    sys.stdout.write("importing places... ")
    sys.stdout.flush()
    c.execute("""COPY place (id, geonames_id, country_id, parent_id, lat, long, type, population)
      FROM %(path)s""", dict(path=tmp_place_path))
    sys.stdout.write("importing place names...")
    sys.stdout.flush()
    c.execute("COPY place_name (place_id, lang_id, name, name_hash, is_official) FROM %(path)s", \
      dict(path=tmp_place_name_path))
    os.remove(tmp_place_path)
    os.remove(tmp_place_name_path)
    db.commit()
    print

c.execute("SELECT setval ('place_id_seq', %(place_id)s)", dict(place_id=place_id));
db.commit()


print "===> Downloading alternative names"

alt_path = imputils.zipex("http://download.geonames.org/export/dump/alternateNames.zip",
  "alternateNames.txt")

print "===> Importing alternative names"

ALTERNATENAMEID = 0
GEONAMEID = 1
ISOLANGUAGE = 2
ALTERNATE_NAME = 3
ISPREFERREDNAME = 4
ISSHORTNAME = 5

place_name_query = """INSERT INTO place_name (place_id, lang_id, name, name_hash, is_official)
  VALUES (%(place_id)s, %(lang_id)s, %(name)s, %(name_hash)s, %(is_official)s)"""
place_name_buf = []

f = codecs.open(alt_path, "rt", "utf-8")
last_geonames_id = None
last_id = None
i = 0
for l in f:
    i += 1
    if i % EXEC_MANY == 0:
        c.executemany(place_name_query, place_name_buf)
        place_name_buf = []
        sys.stdout.write(".")
        sys.stdout.flush()
        db.commit()

    r = [x.strip() for x in l.split("\t")]

    geonames_id = int(r[GEONAMEID])
    if last_geonames_id == geonames_id:
        if last_id is None:
            continue
        place_id = last_id
    else:
        last_geonames_id = geonames_id
        c.execute("SELECT id FROM place WHERE geonames_id=%(geonames_id)s",
          dict(geonames_id=geonames_id))
        if c.rowcount == 0:
            last_id = None
            continue
        last_id = place_id = c.fetchone()[0]
    
    if r[ISOLANGUAGE] == "":
        lang_id = None
    elif not langs_map.has_key(r[ISOLANGUAGE]):
        lang_id = None
    else:
        lang_id = langs_map[r[ISOLANGUAGE]]

    name_hash = _hash_list(_split(r[ALTERNATE_NAME]))

    place_name_buf.append(dict(place_id=place_id, lang_id=lang_id, name=r[ALTERNATE_NAME],
      name_hash=name_hash, is_official=False))

c.executemany(place_name_query, place_name_buf)
place_name_buf = []

print



print "===> Final commit"

db.commit()