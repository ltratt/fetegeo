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


import re
import Results, UK, US




_RE_SPLIT = re.compile("[ ,-/]")

_RE_IRRELEVANT_CHARS = re.compile("[,\\n\\r\\t;()]")
_RE_SQUASH_SPACES = re.compile(" +")
_RE_SPLIT = re.compile("[ ,-/]")




#

class Free_Text:

    def name_to_lat_long(self, queryier, db, lang_ids, find_all, allow_dangling, qs, host_country_id):

        self.queryier = queryier
        self.db = db
        self.lang_ids = lang_ids
        self.find_all = find_all
        self.allow_dangling = allow_dangling
        self.qs = _cleanup(qs)
        self.split, self.split_indices = _split(self.qs)
        self.host_country_id = host_country_id

        results_cache_key = (tuple(lang_ids), find_all, allow_dangling, self.qs, host_country_id)
        if queryier.results_cache.has_key(results_cache_key):
            return queryier.results_cache[results_cache_key]

        # _matches is a list of lists storing all the matched places (and postcodes etc.) at a given
        # point in the split. self._longest_match is a convenience integer which records the longest
        # current match. Note that since we start from the right hand side of the split (see below)
        # and work left, shorter values of _longest_match are "better".

        self._longest_match = len(self.split)
        self._matches = [[] for x in range(len(self.split))]

        # _matched_places is a set storing (place_id, i) pairs recording that a place was found at
        # position 'i' in the split. This weeds out duplicates *unless* we're doing loose matching
        # when we might conceivably match the same place twice but with different bits of "loose"
        # text to the left of the match.
        self._matched_places = set()
        self._matched_postcodes = set() # Analagous to _matched_places.

        # The basic idea of the search is to start from the right hand side of the string and try and
        # match first the country, then any postcodes and places. Note that postcodes and places can
        # come in any order.
        #
        # This is done by splitting the string up into its constituent words and using the current
        # right-hand most word as a candidate match. This copes with the fact that many countries /
        # administrative units have spaces in them.

        for country_id, i in self._iter_country():
            if i == -1:
                # geonames doesn't have lat / long data for countries directly, but includes them as
                # places in the country file. Which is the worst of all possible worlds
                # unfortunately.
                #
                #self._longest_match = 0
                #name = pp = queryier.country_name_id(self, country_id)
                #self._matches[0].append(Results.RCountry(country_id, name, pp))
                continue

            for parent_places, postcode, j in self._iter_places(i, country_id):
                if postcode is not None and j + 1 <= self._longest_match:
                    done_key = (postcode.id, j)
                    if done_key in self._matched_postcodes:
                        continue
                    self._matched_postcodes.add(done_key)

                    self._longest_match = j + 1
                    self._matches[j + 1].append(postcode)

        if self._longest_match == len(self.split):
            # Nothing matched.
            queryier.results_cache[results_cache_key] = []
            return []

        if self._longest_match > 0 and not self.allow_dangling:
            queryier.results_cache[results_cache_key] = []
            return []

        # OK, we've now done all the matching, so we can select the best matches and turn them into
        # full results.

        results = self._matches[self._longest_match]

        if self.host_country_id is not None and not self.find_all:
            for r in results:
                if r.country_id == self.host_country_id:
                    # If we're only trying to find matches within a given country, then remove any
                    # matches that come from other countries. This may seem inefficient, but it's
                    # easier than having this logic every bit of code that adds matches.
                    i = 0
                    while i < len(results):
                        if results[i].country_id != self.host_country_id:
                            del results[i]
                        else:
                            i += 1
                    break

        # Sort the results into alphabetical order.

        results.sort(lambda x, y: cmp(x.pp, y.pp))
        
        # Now we try to find the best match.
        
        found_best = False
        if self.host_country_id is not None:
            # If a host country is specified, we first of all find the best match within the country.
            # If there are no results at all within the country then the generic best finder below
            # will kick into action.
            best_i = None
            for i in range(len(results)):
                if results[i].country_id == self.host_country_id:
                    if best_i is None:
                        best_i = i
                    elif isinstance(results[best_i], Results.RPlace) and \
                      isinstance(results[i], Results.RPlace):
                        if results[best_i].population < results[i].population:
                            best_i = i
                    elif isinstance(results[best_i], Results.RPost_Code) and \
                      isinstance(results[i], Results.RPlace):
                        best_i = i
                    elif isinstance(results[best_i], Results.RPost_Code) and \
                      isinstance(results[i], Results.RPost_Code):
                        pass

            if best_i is not None:
                best = results[best_i]
                del results[best_i]
                results.insert(0, best)
                found_best = True

        if not found_best:
            # Generic 'best finder'.
            best_i = None
            for i in range(len(results)):
                if best_i is None:
                    best_i = i
                elif isinstance(results[best_i], Results.RPlace) and \
                  isinstance(results[i], Results.RPlace):
                    if results[best_i].population < results[i].population:
                        best_i = i
                elif isinstance(results[best_i], Results.RPost_Code) and \
                  isinstance(results[i], Results.RPlace):
                    best_i = i
                elif isinstance(results[best_i], Results.RPost_Code) and \
                  isinstance(results[i], Results.RPost_Code):
                    pass

            if best_i is not None:
                best = results[best_i]
                del results[best_i]
                results.insert(0, best)

        if self._longest_match > 0:
            dangling = self.qs[:self.split_indices[self._longest_match - 1][1]]
        else:
            dangling = ""

        final_results = [Results.Result(m, dangling) for m in results]
        
        queryier.results_cache[results_cache_key] = final_results
        
        return final_results



    def _iter_country(self):

        if self.host_country_id is not None:
            # First of all, we try and do the search as if we're in the host country. This is to
            # catch cases where the name (possibly abbreviated) of an administrative area of the
            # country appears to be the same as another countries name. e.g. California as CA also
            # looks like CA for Canada.

            yield self.host_country_id, len(self.split) - 1

        c = self.db.cursor()

        # Then see if the user has specified an ISO 2 code of a country name.
        
        if len(self.split[-1]) == 2:
            iso2_cnd = self.split[-1]
            if iso2_cnd == "uk":
                # As a bizarre special case, the ISO 2 code for the UK is GB, but people might
                # reasonably be expected to specify "UK" so we hack that in.
                iso2_cnd = "gb"
        
            c.execute("SELECT id FROM country WHERE iso2=%(iso2)s", dict(iso2=iso2_cnd.upper()))
            if c.rowcount > 0:
                assert c.rowcount == 1
                country_id = c.fetchone()[0]
                yield country_id, len(self.split) - 2

        # Finally try and match a full country name. Note that we're agnostic over the language used to
        # specify the country name.

        c.execute("SELECT country_id, name FROM country_name WHERE name_lwdh=%(name_lwdh)s",
          dict(name_lwdh=_hash_wd(self.split[-1])))
        cols_map = self.queryier.mk_cols_map(c)

        done = set()
        for cnd in c.fetchall():
            new_i = _match_end_split(self.split, len(self.split) - 1, cnd[cols_map["name"]])

            country_id = cnd[cols_map["country_id"]]
            done_key = (country_id, new_i)
            if done_key in done:
                continue

            if new_i is not None:
                yield country_id, new_i
                done.add(done_key)

        # Apparently none of the above was a good enough match...

        yield None, len(self.split) - 1



    def _iter_places(self, i, country_id, parent_places=[], postcode=None):
    
        c = self.db.cursor()

        if country_id is not None:
            country_sstr = " AND country_id = %(country_id)s"
        else:
            country_sstr = ""

        for j in range(0, i + 1):
            sub_hash = _hash_list(self.split[j:i + 1])
            
            cache_key = (country_id, sub_hash)
            if self.queryier.place_cache.has_key(cache_key):
                places = self.queryier.place_cache[cache_key]
            else:
                c.execute("""SELECT DISTINCT ON (place.id, name)
                  place.id, name, lat, long, country_id, parent_id, population
                  FROM place, place_name
                  WHERE name_hash=%(name_hash)s AND place.id=place_name.place_id""" + country_sstr,
                  dict(name_hash=sub_hash, country_id=country_id))
                places = c.fetchall()
                self.queryier.place_cache[cache_key] = places

            for place_id, name, lat, long, sub_country_id, parent_id, population in places:
                # Don't get caught out by e.g. a capital city having the same name as a state.            
                if place_id in parent_places:
                    continue

                if postcode is not None:
                    # We've got a match, but we've also previously matched a postcode.

                    # First of all, try and weed out whether the postcode and the place we've
                    # tentatively matched contradict each other. Ideally we'd like to match
                    # parent IDs and so on; at the moment we can only check that the postcode
                    # and place come from the same country.
                    if postcode.country_id != sub_country_id:
                        continue

                # Ensure that if there are parent places, then this candidate is a valid child.
                if len(parent_places) > 0 and not self._find_parent(parent_places[0], place_id):
                    continue

                new_i = _match_end_split(self.split, i, name)
                assert new_i < i

                new_parent_places = [place_id] + parent_places
                record_match = False
                if new_i == -1:
                    record_match = True
                    yield new_parent_places, postcode, new_i
                elif new_i is not None:
                    record_match = True
                    for sub_places, sub_postcode, k in self._iter_places(new_i, sub_country_id, \
                      new_parent_places, postcode):
                        assert k < new_i
                        record_match = False
                        yield sub_places, sub_postcode, k

                    yield new_parent_places, postcode, new_i

                if record_match and postcode is None:
                    if new_i + 1 > self._longest_match:
                        # Although we've got a potential match, it's got more dangling text than some
                        # previous matches, so there's no point trying to go any further with it.
                        continue

                    # OK, we've got a match; check to see if we've matched it before.
                    done_key = (place_id, new_i)
                    if done_key in self._matched_places:
                        continue
                    self._matched_places.add(done_key)

                    local_name = self.queryier.name_place_id(self, place_id)

                    pp = self.queryier.pp_place_id(self, place_id)

                    self._longest_match = new_i + 1
                    self._matches[new_i + 1].append(Results.RPlace(place_id, local_name, lat, long, \
                      sub_country_id, parent_id, population, pp))

            if postcode is None:
                for sub_postcode, k in self._iter_postcode(i, country_id):
                    assert k < i
                    if k == -1:
                        done_key = (sub_postcode.id, k)
                        if done_key in self._matched_postcodes:
                            continue
                        self._matched_postcodes.add(done_key)

                        self._longest_match = 0
                        self._matches[0].append(sub_postcode)
                    else:
                        yield parent_places, sub_postcode, k

                        # Now we need to cope with the fact that "London SW1" is a valid descriptor i.e.
                        # a place can come before a postcode. We therefore need to check the places to
                        # the left of the postcode.

                        for sub_places, sub_sub_postcode, k in self._iter_places(k, country_id, \
                          parent_places, sub_postcode):
                            assert sub_sub_postcode is sub_postcode
                            yield sub_places, sub_sub_postcode, k



    #
    # Return True if 'find_id' is a parent of 'place_id'.
    #

    def _find_parent(self, find_id, place_id):

        cache_key = (find_id, place_id)
        if self.queryier.parent_cache.has_key(cache_key):
            pass
            return self.queryier.parent_cache[cache_key]

        c = self.db.cursor()
        
        c.execute("""SELECT parent_id FROM place WHERE id=%(place_id)s""", dict(place_id=place_id))
        assert c.rowcount == 1
        parent_id = c.fetchone()[0]
        if parent_id is None:
            self.queryier.parent_cache[cache_key] = False
            return False
        elif parent_id == find_id:
            self.queryier.parent_cache[cache_key] = True
            return True
        else:
            r = self._find_parent(find_id, parent_id)
            self.queryier.parent_cache[cache_key] = r
            return r



    def _iter_postcode(self, i, country_id):

        uk_id = self.queryier.get_country_id_from_iso2(self, "GB")
        us_id = self.queryier.get_country_id_from_iso2(self, "US")

        if country_id == uk_id or country_id is None:
            for sub_postcode, j in UK.postcode_match(self, i):
                yield sub_postcode, j

        if country_id == us_id or country_id is None:
            for sub_postcode, j in US.postcode_match(self, i):
                yield sub_postcode, j

        c = self.db.cursor()
        
        if country_id is not None:
            country_sstr = " AND country_id=%(country_id)s"
        else:
            country_sstr = ""
        
        c.execute("SELECT * FROM postcode WHERE lower(main)=%(main)s AND sup IS NULL" + country_sstr,
          dict(main=self.split[i], country_id=country_id))
        
        cols_map = self.queryier.mk_cols_map(c)
        for cnd in c.fetchall():
            if cnd[cols_map["country_id"]] in [uk_id, us_id]:
                # We search for UK/US postcodes elsewhere.
                continue
        
            if cnd[cols_map["area_pp"]] is None:
                pp = cnd[cols_map["main"]]
            else:
                pp = "%s, %s" % (cnd[cols_map["main"]], cnd[cols_map["area_pp"]])

            if country_id is None or country_id != self.host_country_id:
                pp = "%s, %s" % (pp, self.queryier.country_name_id(self,
                  cnd[cols_map["country_id"]]))

            match = Results.RPost_Code(cnd[cols_map["id"]], cnd[cols_map["country_id"]],
              cnd[cols_map["lat"]], cnd[cols_map["long"]], pp)
            yield match, i - 1

        if country_id is not None and country_id != uk_id:
            for sub_postcode, j in UK.postcode_match(self, i):
                yield sub_postcode, j

        if country_id is not None and country_id != us_id:
            for sub_postcode, j in US.postcode_match(self, i):
                yield sub_postcode, j




#
# Cleanup input strings, stripping extraneous spaces etc.
#

def _cleanup(s):

    s = s.strip()
    s = _RE_IRRELEVANT_CHARS.sub(" ", s)
    s = _RE_SQUASH_SPACES.sub(" ", s)

    return s



def _split(s):

    sp = []
    sp_indices = []
    i = 0
    while True:
        m = _RE_SPLIT.search(s, i)
        if m is None:
            break
            
        sp.append(s[i:m.start()].lower())
        sp_indices.append((i, m.start()))
        
        i = m.end()

    sp.append(s[i:].lower())
    
    return sp, sp_indices



def _hash_wd(s):

    return hash(s)



def _hash_list(s):

    return hash("_".join(s))



#
# Given a split name 'split', see if the string 'name' matches the split ending at position i.
# Returns the post-matched position if it succeeds or None if it doesn't. For example:
#
#   _match_end_split(["a", "b", "c", "d", "e"], 3, "c d") == 1
#   _match_end_split(["a", "b", "c", "d", "e"], 3, "a b c") == None
#

def _match_end_split(split, i, name):

    split_name, split_indices = _split(name)
    if split_name == split[i - len(split_name) + 1 : i + 1]:
        return i - len(split_name)

    return None
