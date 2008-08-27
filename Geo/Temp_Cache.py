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


import threading


#
# This class implements a simple "don't fill up beyond a certain point" dictionary cache. Effectively
# it maintains a current dictionary and an old dictionary; when the current dictionary overfills the
# old dictionary is overwritten with the current dictionary and a blank current dictionary is then
# used. Lookups and so on first try the current cache and, if that fails, look at the old cache. This
# means that frequently used items will continuously stay in the cache (as they make their way from
# the old to the current cache), while not taking up too much memory.
#


SMALL_CACHE_SIZE = 1000
LARGE_CACHE_SIZE = 5000

class Cached_Dict:

    def __init__(self, max_size):
    
        self._max_size = max_size
    
        self._lock = threading.Lock()
    
        self._current = {}
        self._old = {}



    def has_key(self, k):
    
        self._lock.acquire()
        try:
            if self._current.has_key(k) or self._old.has_key(k):
                return True
        finally:
            self._lock.release()
        
        return False



    def __getitem__(self, k):
    
        self._lock.acquire()
        try:
            try:
                return self._current[k]
            except KeyError:
                pass

            try:
                o = self._old[k]
                self._current[k] = o
                return o
            except KeyError:
                pass
        finally:
            self._lock.release()

        raise KeyError(k)



    def __setitem__(self, k, i):
    
        self._lock.acquire()
        try:
            if len(self._current) > self._max_size:
                self._old = self._current
                self._current = {}

            self._current[k] = i
        finally:
            self._lock.release()