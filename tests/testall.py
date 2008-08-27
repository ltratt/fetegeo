#! /usr/bin/env python

# Copyright (c) 2008 Laurence Tratt http://tratt.net/laurie/
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


import glob, os, subprocess, sys




PY_EXT = ".py"

COMMENT_PREFIX = "#"
SHELL_PREFIX = "$ "
NO_MATCH = "No match found."




if len(sys.argv) == 1:
    paths = glob.glob("*")
    paths.sort()
else:
    paths = sys.argv[1:]

for path in paths:
    if path.endswith(PY_EXT):
        continue

    print path
    
    f = open(path, "r")
    f_lines = [x.strip() for x in f if not x.startswith(COMMENT_PREFIX)]
    if not f_lines[0].startswith(SHELL_PREFIX):
        XXX

    rest = f.read()

    sp = subprocess.Popen(f_lines[0][len(SHELL_PREFIX):].split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sp.wait()
    stdout_lines = [x.strip() for x in sp.stdout]
    stderr_lines = [x.strip() for x in sp.stderr]

    if f_lines[1] == NO_MATCH and sp.returncode == 1:
        continue
    
    for l in f_lines[1:]:
        if not l in stdout_lines:
            if l.startswith("id:"):
                continue
            
            print "Not found:\n  %s\nin:  " % l
            print "\n  ".join(stdout_lines)
            sys.exit(1)
