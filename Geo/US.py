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
import Results




_RE_US_ZIP_PLUS4 = re.compile("[0-9]{4}")




def postcode_match(ft, i):

    for match, new_i in _sub_pc_match(ft, i):
        yield match, new_i

    if i > 0 and _RE_US_ZIP_PLUS4.match(ft.split[i]):
        for match, new_i in _sub_pc_match(ft, i - 1):
            yield match, new_i



def _sub_pc_match(ft, i):

    us_id = ft.queryier.get_country_id_from_iso2(ft, "US")

    c = ft.db.cursor()

    c.execute("SELECT * FROM postcode WHERE lower(main)=%(main)s AND country_id=%(us_id)s",
      dict(main=ft.split[i], us_id=us_id))

    cols_map = ft.queryier.mk_cols_map(c)
    for cnd in c.fetchall():
        if cnd[cols_map["area_pp"]] is None:
            pp = cnd[cols_map["main"]]
        else:
            pp = "%s, %s" % (cnd[cols_map["main"]], cnd[cols_map["area_pp"]])

        if us_id != ft.host_country_id:
            pp = "%s, %s" % (pp, ft.queryier.country_name_id(ft, cnd[cols_map["country_id"]]))

        match = Results.RPost_Code(cnd[cols_map["id"]], cnd[cols_map["country_id"]],
          cnd[cols_map["lat"]], cnd[cols_map["long"]], pp)
        yield match, i - 1



#
# Given the string 'pp', add ", United States" after it if the host country isn't set to the US.
#

def mk_pp(ft, pp):

    us_id = ft.queryier.get_country_id_from_iso2(ft, "US")
    
    if ft.host_country_id == us_id:
        return pp

    return "%s, %s" % (pp, ft.queryier.country_name_id(ft, us_id))



def pp_place_id(ft, place_id):

    pp = ft.queryier.name_place_id(ft, place_id)

    c = ft.db.cursor()

    # For US places, the convention is to include the state name but not the county, so we iterate
    # until we find a place without a parent id, assuming that is the US state.

    cnd_id = place_id    
    while True:
        c.execute("SELECT parent_id FROM place WHERE id=%(id)s", dict(id=cnd_id))
        parent_id = c.fetchone()[0]
        
        if parent_id is None:
            pp = "%s, %s" % (pp, ft.queryier.name_place_id(ft, cnd_id))
            return mk_pp(ft, pp)
        
        cnd_id = parent_id
