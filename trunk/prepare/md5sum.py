#!/usr/bin/python
# vim: set fileencoding=UTF-8

"""
Re-implementation of md5sum in python
http://mail.python.org/pipermail/python-list/2005-February/306758.html
by Nick Craig-Wood nick at craig-wood.com , Tue Feb 8 18:30:58 CET 2005
"""

import sys
import md5

def md5file(filename):
    """Return the hex digest of a file without loading it all into memory"""
    fh = open(filename)
    digest = md5.new()
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        digest.update(buf)
    fh.close()
    return digest.hexdigest()

def md5sum(files):
    for filename in files:
        try:
            print "%s  %s" % (md5file(filename), filename)
        except IOError, e:
            print >> sys.stderr, "Error on %s: %s" % (filename, e)

if __name__ == "__main__":
    md5sum(sys.argv[1:])
