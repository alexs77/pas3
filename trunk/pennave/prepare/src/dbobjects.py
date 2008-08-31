import logging
import sys
import gc
import os
import urlparse

logging.basicConfig()
log = logging.getLogger("dbobjects")
log.setLevel(logging.INFO)

if (sys.version_info[0] == 2 and sys.version_info[1] < 4) or sys.version_info[0] < 2:
    log.exception("Unable to load library.  This library requires Python 2.4 or newer")
    raise Exception("Incorrect python version - use python 2.4 or higher")

from sqlobject import *
from sqlobject.sqlbuilder import *

# CREATE TABLE imports ( id INTEGER PRIMARY KEY NOT NULL, time INTEGER );

# CREATE TABLE meta ( id INTEGER PRIMARY KEY NOT NULL, name TEXT UNIQUE
#                                 NOT NULL, data TEXT );

# CREATE TABLE photo_tags ( photo_id INTEGER, tag_id INTE GER );

# CREATE TABLE photo_versions ( photo_id INTEGER, version _id INTEGER,
# name STRING );

# CREATE TABLE photos ( id INTEGER PRIMARY KEY NOT NULL, time INTEGER
# NOT NULL, d irectory_path STRING NOT NULL, name STRING NOT NULL,
# description TEXT NOT NU LL, default_version_id INTEGER NOT NULL );

# CREATE TABLE tags ( id INTEGER PR IMARY KEY NOT NULL, name TEXT
# UNIQUE, cate gory_id INTEGER, is_category BOOLEAN, sort_priority
# INTEGER, icon TEXT );

class PhotoVersion:
    def __init__(self, id, name, photo):
        self.id = id
        self.name = name
        self.photo = photo
        self.isDefault = id == photo.defaultVersionId
    
    def getFilename(self):
        return urlparse.urlparse(self.uri)[2]
    
class Photo(SQLObject):
    class sqlmeta:
        table = "photos"
    time = IntCol()
    #directoryPath = UnicodeCol(notNone=True)
    #name = UnicodeCol(notNone=True)
    uri = UnicodeCol(notNone=True)
    description = StringCol(notNone=True)
    defaultVersionId = IntCol(notNone=True)
    tags = RelatedJoin('Tag', intermediateTable='photo_tags', joinColumn='photo_id', otherColumn='tag_id')
    versions = None

    def getFilename(self, forceOriginal=False, version=None, cache=None):
        if version:
            try: return self.getVersions(cache)[int(version)].getFilename()
            except: pass
        if self.defaultVersionId > 1 and not forceOriginal:
            return self.getVersions(cache)[self.defaultVersionId].getFilename()
        else:
            return urlparse.urlparse(self.uri)[2]
    
    # we can't have a photo_versions object because the column has no id
    def getVersions(self, cache=None):
        """
        Performs an SQL query to get all of the versions of this file.  After this
        has been called once, it will store the data for future instances.
        
        @param cache:  an SQLCache object if desired. This allows saving some of the
        results in RAM for future use.
        """
        if self.versions: return self.versions
        self.versions = {}
        query = """SELECT version_id, name FROM photo_versions WHERE photo_id=%d""" % (self.id)
        if not cache:
            res = self._connection.queryAll(query)
        else:
            res = cache.execute(query)
        for r in res:
            self.versions[r[0]] = PhotoVersion(r[0], r[1], self)
        return self.versions

class TagRepr:
    """Representation of a tag that is not dependent on SQLObject.
    
    This class is used when we do things with tags that don't require the
    SQLObject interface but still need an object oriented interface
    """
    def __init__(self, id=None, name=None, categoryId=None, numPhotos=None):
        self.id = id
        self.name = name
        self.categoryId = categoryId
        self.numPhotos=numPhotos
        
class Tag(SQLObject):
    class sqlmeta:
        table = "tags"
    name = UnicodeCol(notNone=True, alternateID=True)
    categoryId = IntCol()
    isCategory = BoolCol()
    sortPriority = IntCol()
    icon = StringCol()
    children = MultipleJoin('Tag', joinColumn='category_id')
    def toTagRepr(self):
        return TagRep(it=self.id, name=self.name, categoryId=self.categoryId)
    
def expire_all():
    """Simple function to expire the cache from everything.  Call
    it periodically to keep stuff happy

    taken from: http://mikewatkins.net/categories/technical/2004-07-14-1.html
    """
    c = Study._connection
    for k in c.cache.caches.keys():
        c.cache.caches[k].expireAll()
    gc.collect()

def setConnection(conn):
    for x in [y for y in globals().values() if hasattr(y,'setConnection')
              and y.__class__.__name__ == 'DeclarativeMeta'
              and not y.__module__.startswith('sqlobject')]:
        x.setConnection(conn)
        print "setting connection on ", x

def connect(uri, debug=False, cache=None, process=True):
    global connection
    global sqlhub
    
    connection = connectionForURI(uri)
    if process:
        sqlhub.processConnection = connection

    if debug:
        connection.debug = True
    if cache != None:
        connection.cache = cache
    return connection

