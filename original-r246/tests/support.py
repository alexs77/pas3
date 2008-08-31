# support.py
#
# this module contains general support scripts that help create a test
# database harness.  Mainly, it creates a sample database and some images.
#

import sys
import os
sys.path.append(".." + os.sep + "src")
from dbobjects import *
import Image
import time
import tempfile

def createTables():
    """Creates the tables in the database"""
    for x in [Photo, PhotoVersion, Tag]: x.createTable()
    
def createTags():
    for x in xrange(1,10):
        t = Tag(name="Tag%d" % x)

def createPhotos():
    for x in xrange(1,10):
        # create the dummy file for the filenae
        fd, fn = tempfile.mkstemp(suffix=".jpg")
        fdir, fname = os.path.split(fn)
        p = Photo(time=time.time(), directoryPath=fdir, name=fname)
        # add the random tags to the collection
        for y in xrange(1,x+1):
            t = Tag.byName("Tag%d" % x)
            p.addTag(t)
            
# this creates a dummy database and some silly image files
def createDummyDatabase():
    databaseURI = "sql:/:memory:"
    conn = connect(databaseURI, debug=False, cache=None, process=None)
    createTables()
    createTags()
    
def cleanupDummyDatabase():
    pass
