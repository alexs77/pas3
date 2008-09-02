#!/usr/bin/python
# vim: set fileencoding=utf-8

# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$

# Temporär
import sys

import logging
from optparse import OptionParser
import cherrypy
from sqlobject import *
import os
import S3
import MyS3

# Effiziente Berechnung der md5 Checksumme:
# - http://mail.python.org/pipermail/python-list/2005-February/306749.html
# - http://mail.python.org/pipermail/python-list/2005-February/thread.html#306749
# - http://mail.python.org/pipermail/python-list/2005-February/306758.html

# Für md5 (siehe <http://mail.python.org/pipermail/python-list/2005-February/306749.html>)
#import os, md5, mmap
import md5
import md5sum

from dbobjects import *
import codecs

import mimetypes
import Image
import StringIO

# Die EXIF Informationen werden als "Pickle" in einer Datei gespeichert.
import cPickle
import EXIF

VERSION = "0.5svn"
TAG_LEVELS = 6
ORDERBY_NORMAL=1
ORDERBY_REVERSE=2
ORDERBY_CHRON = ORDERBY_REVERSE
sql = None

def open_u8(filePath, mode = 'rb'):
    """Öffne eine Datei. Falls es einen Unicode Error gibt, versuche den Pfad in UTF-8 zu verwenden."""
    try:
        fh = open(filePath, mode)
    except UnicodeEncodeError:
        fh = open(codecs.encode(filePath, "UTF-8"), mode)
    return fh


class AsyncExifDump(threading.Thread):
    def __init__(self, imgFileName, exifFileName, semaphore):
        try:
            threading.Thread.__init__(self, name = 'AsyncExifDumpThread-' + imgFileName + '_' + exifFileName)
            self.imgFileName = imgFileName
        except UnicodeEncodeError:
            self.imgFileName = codecs.encode(imgFileName, "UTF-8")
            threading.Thread.__init__(self, name = 'AsyncExifDumpThread-' + self.imgFileName + '_' + exifFileName)
        self.exifFileName = exifFileName
        self.semaphore = semaphore
        
    def run(self):
        log = logging.getLogger('prepare.py')
        
        log.info("%s: Lese EXIF Informationen aus" % self.imgFileName)
        
        img = open_u8(self.imgFileName, "r")
        try:
            exif = EXIF.process_file(img)
            log.info("%s: Erzeuge neues Pickle File mit Namen '%s'" % (self.imgFileName, self.exifFileName))
            exif_pickle_file = open(self.exifFileName, "w")
            try:
                log.info("%s: Schreibe Pickle in gerade erzeugte Datei" % self.imgFileName)
                cPickle.dump(exif, exif_pickle_file, cPickle.HIGHEST_PROTOCOL)
                log.info("%s: Schliesse Pickle Datei" % self.imgFileName)
            finally:
                exif_pickle_file.close()
        finally:
            img.close()

        self.semaphore.release()
        


class SQLCache:
    """This is a simple object that caches SQL requests.  Because the database
    is read only, we can get away with this."""

    def __init__(self):
        self.queries = {}

    def execute(self, query, forceUpdate=False):
        if not forceUpdate:
            if self.queries.has_key(query):
                log.debug("Cache hit for query: %s", query)
                return self.queries[query]

        log.debug("Cache miss for query: %s", query)
        res = Photo._connection.queryAll(query)
        self.queries[query] = res
        return res

    def flush(self):
        self.queries = {}


def getAllPhotos():
    """Returns a list of paths to all photos"""
    hiddenQuery = ""
    sql = SQLCache()

    # build the subquery for all of the hidden strings
    hiddenStr = " or ".join(["tag_id=%d" % x for x in cherrypy.config.get("hiddenTagIds")])
    if hiddenStr:
        hiddenQuery = "and a.id not in (select distinct photo_id from photo_tags where %s)" % (hiddenStr)

    query = "SELECT distinct(a.id), a.directory_path, a.name as img_path, 1 as version_id, NULL as version_name \
      from photos a, photo_tags b \
      where a.id = b.photo_id \
      %s \
      order by a.id" % hiddenQuery

    return sql.execute(query)


def getAllPhotoVersions():
    """Returns a list of paths to all "modified" versions of the photos."""
    
    hiddenQuery = ""
    sql = SQLCache()

    # build the subquery for all of the hidden strings
    hiddenStr = " or ".join(["tag_id=%d" % x for x in cherrypy.config.get("hiddenTagIds")])
    if hiddenStr:
        hiddenQuery = "and a.id not in (select distinct photo_id from photo_tags where %s)" % (hiddenStr)

    query = "SELECT distinct(a.id), a.directory_path, a.name as img_path, c.version_id as version_id, c.name as version_name \
      from photos a, photo_tags b, photo_versions c \
      where a.id = b.photo_id \
      and a.id = c.photo_id \
      %s \
      order by a.id" % hiddenQuery

    return sql.execute(query)


def start(config=None, dburi=None, dbdebug=False):
    global databaseUri, databaseDebug, conn
    
    #log = logging.getLogger("pennave.py")
    log = logging.getLogger('prepare.py')
    log.info("Starte Vorbereitung der Bilder")
    
    cherrypy.config.update(config)
    gbs = cherrypy.config

    # Größe der Thumbnailbilder aus der Konfiguration auslesen
    resizedSizes = {'thumbnail': cherrypy.config.get("thumbnailPhotoSize", (200,150)),
      'medium': cherrypy.config.get("mediumPhotoSize", (640,480)),
      'tiny': cherrypy.config.get("tinyPhotoSize", (32,32))
    }
    
    # this next line is a hack to give us early access to the database
    if gbs.has_key("dblocation"):
        dburi = "sqlite://" + gbs.get("dblocation")
        from pysqlite2 import dbapi2 as sqlite
    conn.threadConnection = connect(dburi, debug=dbdebug, cache=None, process=False)
    databaseDebug = dbdebug
    databaseUri = dburi
    sql = SQLCache()
    
    gbs["requiredTagIds"] = []
    if gbs.has_key("requiredTags"):
        print "gbs[requiredTags]: %s" % gbs["requiredTags"]
        for t in gbs["requiredTags"]:
            try:
                gbs["requiredTagIds"].append(Tag.byName(t).id)
            except:
                print "***** unable to force required tag: %s (%s)" % (t, sys.exc_info()[0])
    gbs["hiddenTagIds"] = []
    if gbs.has_key("hiddenTags"):
        for t in gbs["hiddenTags"]:
            try:
                gbs["hiddenTagIds"].append(Tag.byName(t).id)
            except:
                print "***** unable to force required hidden tag: %s (%s)" % (t, sys.exc_info()[0])
                


    # In data{} werden alle Daten *EINES* Bildes gespeichert.
    data_img = {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None}
    data = {
      'ids': {'picture': None, 'version': None},
      'images': {
        'original': data_img, 'thumbnail': data_img, 'medium': data_img, 'tiny': data_img, 'exif': data_img,
      }
    }
    # Iterriere über alle Bilder
    sem = threading.Semaphore(10)
    
    all_photos = getAllPhotos()
    all_versions = getAllPhotoVersions()
    all_pictures = all_photos + all_versions
    
    for  data['ids']['picture'], directoryPath, fileName, data['ids']['version'], versionName in all_pictures:
    #for data['ids']['picture'], directoryPath, fileName in getAllPhotos():
        # Einige "Hilfs-"Zeichenketten zusammensetzen
        (fileRoot, fileExt) = os.path.splitext(os.path.basename(fileName))
        if versionName is None:
            filePath = directoryPath + os.sep + fileName
        else:
            filePath = directoryPath + os.sep + fileRoot + " (" + versionName + ")" + fileExt
        data['images']['original']['name'], data['images']['original']['ext'] = (filePath, fileExt)

        # Erzeuge auch UTF-8 kodierte Varianten der Dateinamen
        (
         fileRoot_U8, fileExt_U8, filePath_U8, fileName_U8, directoryPath_U8) = (
         codecs.encode(fileRoot, "UTF-8"), codecs.encode(fileExt, "UTF-8"),
         codecs.encode(filePath, "UTF-8"), codecs.encode(fileName, "UTF-8"),
         codecs.encode(directoryPath, "UTF-8")
        )

        # Name/URL der Datei auf s3:
        # http://$bucket.s3.amazonaws.com/$key
        # key = $pfad/$größe/$photo_id/version/$version_id
        # NEU:
        # key = $pfad/$photo_id.$version_id.$größe.$ext
        # $photo_id ist IMMER 6-stellig und von links mit 0 aufgefüllt; $version_id ist 2-stellig.
        # z.B.
        # bucket = bilder.alexander.skwar.name, pfad = images, größe = original, photo_id = 5303, version_id = 1
        # -> http://bilder.alexander.skwar.name.s3.amazonaws.com/images/original/5303/version/1
        # NEU:
        # -> http://bilder.alexander.skwar.name.s3.amazonaws.com/images/005303.01.original.jpeg
        #
        # Daneben wird auch noch eine Datei $key.exif.pickle angelegt. Diese Datei
        # beinhaltet die EXIF tags als Pickle.
        # Wenn alle Dateien geuploadet wurden, wird im $pfad auch noch eine Datei
        # TRANSLATION.TXT erzeugt. In dieser Datei wird einer ID der Originaldatei
        # gegenüber gestellt.
        # Bsp.:
        # 5303  /home/askwar/Desktop/My Pictures/Photos/Kategorien/Cassandra/[2007-08-07 08-00-19] (CIMG3685) Cédric, Cassandra, Auf Couch liegend und spielend, Wohnzimmer, Zuhause, Winterthur {2,8 MB}.jpg
        # Die Eleemente werden hierbei intern in einer Liste geführt. Um das ganze
        # dann zu einer durch \n getrennten Zeichenkette umzuwandeln, ist laut
        # http://groups.google.de/group/comp.lang.python/msg/91dda6e695fa6f73
        # (Suche nach "python list elements join") auszuführen:
        #   "\n".join(map(str, list))

        exif_pickle_file_name = "%s/ID-%06d_Version-%02d" % (gbs["exifPath"], data['ids']['picture'], data['ids']['version'])
        if os.path.exists(exif_pickle_file_name):
            log.info("%s: Pickle Datei '%s' schon vorhanden" % (filePath_U8, exif_pickle_file_name))
        else:
            log.info("%s: Bearbeite Bild und werde Pickle Datei '%s' erzeugen" % (filePath_U8, exif_pickle_file_name))
            async_exif_dump_thread = AsyncExifDump(filePath, exif_pickle_file_name, sem)
            sem.acquire()
            async_exif_dump_thread.start()


        print "++++++++++ Behandlung der Datei %s abgeschlossen." % filePath_U8
    
    log.info("=*=*=*=*  FINISHED!!! *=*=*=*=*=")
    return

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
                        level=logging.DEBUG)
    log = logging.getLogger("prepare.py")
    log.setLevel(logging.INFO)

    global conn
    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true",
                      dest="debug", default=False,
                      help="sqlobject debugging messages")
    parser.add_option("-v", "--verbose", action="store_true",
                      dest="verbose", default=False,
                      help="verbose messages")
    parser.add_option("--dburi", "-u", dest="uri",
                      help="database name to connect to",
                      default="sqlite://"+os.getenv("HOME")+"/.gnome2/f-spot/photos.db",
                      action="store")
    parser.add_option("-l", "--loglevel", dest="loglevel",
                      help="Manually specify logging level (DEBUG, INFO, WARN, etc)",
                      default="INFO", action="store")
    parser.add_option("--conf", "-c", dest="configuration",
                      help="load configuration from file",
                      action="store", default="prepare.conf")

    log.debug("parsing command line arguments")
    (options, args) = parser.parse_args()

    if options.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(getattr(logging,options.loglevel.upper()))

    conn = dbconnection.ConnectionHub()
    setConnection(conn)
    start(config=options.configuration, dburi=options.uri, dbdebug=options.debug)

    # Lese Pfad zu *ALLEN* Bildern aus
    # Iteriere über alle Bilder
    #  md5sum für Bilddatei erzeugen
    #  Überprüfen, ob's auf S3 das Bild schon in Originalgröße gibt
    #   Ja -> Überprüfen, ob md5sum übereinstimmt, um evtl. Upload zu vermeiden
    #    Ja -> Nichts machen
    #    Nein -> Upload & Tiny+Medium+Thumbnail erzeugen & Upload
    #   Nein (Bild nicht existent) -> Upload & TMT ^^^
