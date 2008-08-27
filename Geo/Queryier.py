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


import Free_Text, Temp_Cache
import UK, US




TYPE_STATE = 0
TYPE_COUNTY = 1
TYPE_PLACE = 2

# For countries we record as a pair (print county, print state).

_DEFAULT_FORMAT = (True, True)
_COUNTRY_FORMATS = {"GB" : (True, False), "DE" : (False, True), "FR" : (False, True),
  "US" : (False, True)}




class Queryier:

    def __init__(self):
    
        self.flush_caches()



    def flush_caches(self):
    
        self.country_id_iso2_cache = {} # These are both too small 
        self.country_iso2_id_cache = {} # to bother with a cached dict.
        self.country_name_cache = {}
        self.place_cache = Temp_Cache.Cached_Dict(Temp_Cache.LARGE_CACHE_SIZE)
        self.place_name_cache = Temp_Cache.Cached_Dict(Temp_Cache.LARGE_CACHE_SIZE)
        self.place_pp_cache = Temp_Cache.Cached_Dict(Temp_Cache.LARGE_CACHE_SIZE)
        self.parent_cache = Temp_Cache.Cached_Dict(Temp_Cache.LARGE_CACHE_SIZE)
        self.results_cache = Temp_Cache.Cached_Dict(Temp_Cache.SMALL_CACHE_SIZE)



    def name_to_lat_long(self, db, lang_ids, find_all, allow_dangling, qs, host_country_id):
    
    	return Free_Text.Free_Text().name_to_lat_long(self, db, lang_ids, find_all, allow_dangling, \
          qs, host_country_id)



    #
    # Convenience methods
    #

    def mk_cols_map(self, c):

        map = {}
        i = 0 
        for col in c.description:
            assert not map.has_key(col[0])
            map[col[0]] = i
            i += 1

        return map



    def get_country_id_from_iso2(self, ft, iso2):
    
        if not self.country_id_iso2_cache.has_key(iso2):
            c = ft.db.cursor()
            c.execute("SELECT id FROM country WHERE iso2=%(iso2)s", dict(iso2=iso2))
            assert c.rowcount == 1
            self.country_id_iso2_cache[iso2] = c.fetchone()[0]

        return self.country_id_iso2_cache[iso2]



    def get_country_iso2_from_id(self, ft, country_id):
    
        if not self.country_iso2_id_cache.has_key(country_id):
            c = ft.db.cursor()
            c.execute("SELECT iso2 FROM country WHERE id=%(id)s", dict(id=country_id))
            assert c.rowcount == 1
            self.country_iso2_id_cache[country_id] = c.fetchone()[0]

        return self.country_iso2_id_cache[country_id]



    def country_name_id(self, ft, country_id):
    
        cache_key = (ft.lang_ids[0], country_id)
        if self.country_name_cache.has_key(cache_key):
            return self.country_name_cache[cache_key]
    
        c = ft.db.cursor()
    
        # Since we have country name data for every language, we can simply pluck the first language
        # from the list.
    
        c.execute("""SELECT name FROM country_name
          WHERE country_id=%(country_id)s AND lang_id=%(lang_id)s AND is_official=TRUE""",
          dict(country_id=country_id, lang_id=ft.lang_ids[0]))

        assert c.rowcount == 1
        
        name = c.fetchone()[0]
        
        self.country_name_cache[cache_key] = name
        
        return name



    def name_place_id(self, ft, place_id):
    
        cache_key = (tuple(ft.lang_ids), ft.host_country_id, place_id)
        if self.place_name_cache.has_key(cache_key):
            return self.place_name_cache[cache_key]
    
        c = ft.db.cursor()
    
        for lang_id in ft.lang_ids:
            c.execute("""SELECT name FROM place_name
              WHERE place_id=%(place_id)s AND lang_id=%(lang_id)s AND is_official=TRUE""",
              dict(place_id=place_id, lang_id=lang_id))

            if c.rowcount == 0:
                c.execute("""SELECT name FROM place_name
                  WHERE place_id=%(place_id)s AND lang_id=%(lang_id)s""",
                  dict(place_id=place_id, lang_id=lang_id))

            if c.rowcount == 1:
                name = c.fetchone()[0]
                self.place_name_cache[cache_key] = name
                return name

        # We couldn't find anything in the required languages.

        c.execute("SELECT name FROM place_name WHERE place_id=%(place_id)s AND is_official=TRUE",
          dict(place_id=place_id))

        if c.rowcount == 0:
            c.execute("SELECT name FROM place_name WHERE place_id=%(place_id)s",
               dict(place_id=place_id))

        name = c.fetchone()[0]
        self.place_name_cache[cache_key] = name

        return name



    def pp_place_id(self, ft, place_id):

        cache_key = (tuple(ft.lang_ids), ft.host_country_id, place_id)
        if self.place_pp_cache.has_key(cache_key):
            return self.place_pp_cache[cache_key]

        c = ft.db.cursor()
        
        pp = self.name_place_id(ft, place_id)
        
        c.execute("SELECT parent_id, country_id, type from place WHERE id=%(id)s", dict(id=place_id))
        assert c.rowcount == 1
        
        parent_id, country_id, type = c.fetchone()
        
        iso2 = self.get_country_iso2_from_id(ft, country_id)
        if iso2 in _COUNTRY_FORMATS:
            format = _COUNTRY_FORMATS[iso2]
        else:
            format = _DEFAULT_FORMAT
        
        while parent_id is not None:
            c.execute("""SELECT parent_id, type from place WHERE id=%(id)s""", dict(id=parent_id))
            new_parent_id, type = c.fetchone()
            if format[0] and type == TYPE_COUNTY or format[1] and type == TYPE_STATE:
                pp = "%s, %s" % (pp, self.name_place_id(ft, parent_id))
            parent_id = new_parent_id

        if country_id != ft.host_country_id:
            pp = "%s, %s" % (pp, self.country_name_id(ft, country_id))

        self.place_pp_cache[cache_key] = pp

        return pp