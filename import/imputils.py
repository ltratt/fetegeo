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


import os, tempfile, urllib

#
# Extract the file 'extract_path' from the URL-to-download 'url', and return the path of the
# extracted file.
#

def zipex(url, extract_path):

    zip_fno, zip_path = tempfile.mkstemp()
    u = urllib.urlopen(url)
    os.write(zip_fno, u.read())
    u.close()
    os.close(zip_fno)

    unzip_fno, unzip_path = tempfile.mkstemp()
    # Close the handle to the unzip dest temp file (required under Windows so that the system call
    # can write to the file)
    os.close(unzip_fno)
    os.system("unzip -p %s %s > %s" % (zip_path, extract_path, unzip_path))

    # Delete the downloaded file which is no longer needed.
    os.remove(zip_path)

    return unzip_path