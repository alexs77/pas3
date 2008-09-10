#! /usr/bin/env python2.5
# vim: set fileencoding=utf-8

#===============================================================================
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

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
import cStringIO
import urllib
import urlparse

# Die EXIF Informationen werden als "Pickle" in einer Datei gespeichert.
import cPickle
import EXIF
import pprint

VERSION = "0.5svn"
TAG_LEVELS = 6
ORDERBY_NORMAL=1
ORDERBY_REVERSE=2
ORDERBY_CHRON = ORDERBY_REVERSE
sql = None


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


def open_u8(filePath, mode = 'rb'):
    """Öffne eine Datei. Falls es einen Unicode Error gibt, versuche den Pfad in UTF-8 zu verwenden."""
    try:
        fh = open(filePath, mode)
    except UnicodeEncodeError:
        fh = open(codecs.encode(filePath, "UTF-8"), mode)
    return fh


def upload_images(data, config, s3_connection, s3_generator):
    """Bilder zu S3 heraufladen."""
    
    # Logger holen
    log = logging.getLogger('prepare.py')
    
    images = data['images']
    ids = data['ids']
    original_name = data['images']['original']['name']
    for key in images.keys():
        log.info(u"%s: Werde Bild in Größe %s uploaden" % (original_name, key))
        if images[key] is None:
            log.warning("%s: Keine Daten vorhanden - KEIN Upload!" % original_name)
            continue
        s3_key = create_s3_key(config["aws_s3_path"], ids['picture'], ids['version'], key, images[key]['ext'])
        url = s3_generator.make_bare_url(config['aws_s3_bucket'], s3_key)
        name = os.path.basename(images[key]['name'])
        s3data = S3.S3Object(images[key]['data'])
        s3header = {
          'x-amz-acl': 'public-read',
          'Content-Type': images[key]['mime'],
          'Content-Disposition': 'inline; filename="%s"' % codecs.encode(name, "UTF-8")
        }
        size = len(images[key]['data'])
        log.info(u"%s: Werde Daten für '%s' zu S3 heraufladen. Key: %s. Größe: %s" % (original_name, key, s3_key, size))
        #s3_response = s3_connection.put(config["aws_s3_bucket"], s3_key, s3data, s3header)
        #hr = s3_response.http_response
        #log.info("%s: Upload fertig. Status: %s, Reason: %s, Body: %s. URL: <%s>" % (original_name, hr.status, hr.reason, s3_response.body, url))
        
        async_upload_thread = MyS3.AsyncUpload(s3_connection = s3_connection, 
                                               bucket = config["aws_s3_bucket"],
                                               key = s3_key, 
                                               s3object = s3data, 
                                               headers = s3header)
        async_upload_thread.start()
        log.info(u"%s: Upload läuft im Hintergrund. URL: <%s>" % (original_name, url))
    
    log.info("%s: Upload der Datei beendet." % original_name)
    return


def process_image(original_image, resize_sizes):
    """Erzeuge Thumbnail, Medium und Tiny Versionen des Bildes,
    und lese zusätzlich EXIF Informationen aus"""
    
    # Logger holen
    log = logging.getLogger('prepare.py')
    
    # Dictionary mit den Rückgabewerten initialisieren.
    returnData = {'original': original_image}
    
    # Öffne die Bilddatei von S3
    # -> In data['images']['original']['handle'] -> original_image['handle'] ist
    # ein offener Handle zu finden.
    
    # Lese das Bild von S3 ein
    log.info("%s: Lese Bild von S3 %s" % (original_image['name'], original_image['handle'].geturl()))
    returnData['original']['data'] = original_image['handle'].read()
    # Erzeuge ein StringIO Objekt daraus
    sio = cStringIO.StringIO(returnData['original']['data'])
    
    # Es wird später auch der Dateiname zerlegt werden müssen.
    (fileRoot, fileExt) = os.path.splitext(os.path.basename(original_image['name']))
    # Und auch in UTF 8 kodieren
    (fileRoot_U8, fileExt_U8) = (codecs.encode(fileRoot, 'UTF-8'), codecs.encode(fileExt, 'UTF-8'))
    
    # EXIF Informationen auslesen, sofern möglich
    try:
        # Sicherheitshalber wieder an den Anfang der Datei springen
        sio.seek(0)
        ext = '.exif.pickle'
        exif = EXIF.process_file(sio)
        exifs = cPickle.dumps(exif, cPickle.HIGHEST_PROTOCOL)
        returnData['exif'] = {'data': exifs,
          'mime': "application/octet-stream",
          'name': original_image['name'] + ext, 'ext': ext}
        log.info("%s: EXIF Informationen ausgelesen" % original_image['name'])
    except:
        log.exception("%s: Konnte EXIF Informationen nicht auslesen" % original_image['name'])
        returnData['exif'] = None
        
    # In der Größe angepasste Bilder erzeugen
    log.info("%s: Lese Bild ein" % original_image['name'])
    # Versuche die Bilddatei auszulesen - kann mit Exception
    # abbrechen, falls das Bildformat nicht unterstützt wird.
    try:
        # An den Anfang der "Datei" springen
        sio.seek(0)
        img = Image.open(sio)
        img.load()
        error = False
    except IOError, details:
        error = True
        if str(details) == "cannot read interlaced PNG files":
            log.warning(u"%s: Interlaced PNG Datei. Wird nicht von PIL unterstützt... Überspringen!" % original_image['name'])
        elif str(details) == "decoder group4 not available":
            log.warning(u"%s: TIF G4 Bilder werden nicht unterstützt... Überspringen!" % original_image['name'])
        elif str(details) == "cannot identify image file":
            log.warning(u"%s: Bildtyp konnte nicht bestimmt werden... Überspringen!" % original_image['name'])
        else:
            log.exception("%s: I/O Error!" % original_image['name'])
            raise
            
    # Sofern das Bild ausgelesen werden konnte, passe es in der Größe an.
    if not error:
        if img.mode not in ['RGB', 'RGBA']:
            log.info("%s: Konvertiere Bild von Modus '%s' zu RGB" % (original_image['name'], img.mode))
            img = img.convert('RGB')
        log.info(u"%s: Passe Bild in der Größe an" % original_image['name'])
        for sizeType in resize_sizes.keys():
            size = resize_sizes[sizeType]
            log.info(u"%s: Erzeuge Arbeitskopie für Größe %s" % (original_image['name'], sizeType))
            workImg = img.copy()
            log.info(u"%s: Skaliere das Bild zu '%s'-Größe %s" % (original_image['name'], sizeType, str(size)))
            workImg.thumbnail(size, Image.ANTIALIAS)
            # Das Bild muss in eine "Datei" gespeichert werden.
            # Da keine lokale Datei gewünscht sein kann, wird eine
            # Pseudo Datei vom Typ StringIO verwendet weden.
            mime = 'image/jpeg' ; ext = '.jpeg'
            try:
                name = fileRoot + " (" + sizeType + ")" + fileExt + ext
            except UnicodeEncodeError:
                name = fileRoot_U8 + " (" + sizeType + ")" + fileExt_U8 + ext
            log.info("%s: Speichere Bild als JPEG ab mit Name %s" % (original_image['name'], name))
            # Pseudodatei erzeugen
            sio = StringIO.StringIO()
            # Bild speichern
            workImg.save(sio, 'JPEG')
            returnData[sizeType] = {'data': sio.getvalue(), 'mime': mime, 'name': name, 'ext': ext}
            # Daten im sio verwerfen
            sio.close()
            log.info(u"%s: Bild erfolgreich in Größe %s skaliert und gespeichert" % (original_image['name'], sizeType))

    else:
        log.info(u"%s: Bild konnte nicht ausgelesen werden und wird somit auch nicht in der Größe angepasst werden" % original_image['name'])
        for sizeType in resize_sizes.keys():
            returnData[sizeType] = None

    log.info("%s: Bearbeitung des Bildes abgeschlossen" % original_image['name'])
    return returnData

def getAllPhotos():
    """Returns a list of paths to all photos"""
    hiddenQuery = ""
    sql = SQLCache()

    # build the subquery for all of the hidden strings
    hiddenStr = " or ".join(["tag_id=%d" % x for x in cherrypy.config.get("hiddenTagIds")])
    if hiddenStr:
        hiddenQuery = "and a.id not in (select distinct photo_id from photo_tags where %s)" % (hiddenStr)
    
    if cherrypy.config.has_key("processIds"):
        minId = cherrypy.config.get("processIds")[0]
        maxId = cherrypy.config.get("processIds")[1]
    else:
        minId = "(SELECT ((%s-1) * (MAX(id)/%s)) FROM photos)" % (cherrypy.config.get("instanceNumber"), cherrypy.config.get("instanceCount"))
        maxId = "(SELECT ((%s * (MAX(id) / %s))-1) FROM photos)" % (cherrypy.config.get("instanceNumber") , cherrypy.config.get("instanceCount"))
    processIdsQuery = "and a.id BETWEEN %s AND %s" % (minId, maxId)

    query = "SELECT distinct(a.id), a.uri, 1 as version_id, NULL as version_name \
      from photos a, photo_tags b \
      where a.id = b.photo_id \
      %s \
      %s \
      order by a.id" % (processIdsQuery, hiddenQuery)
    
    # print "query in getAllPhotos: “%s”" % (query)
    
    return sql.execute(query)

def getAllPhotoVersions():
    """Returns a list of paths to all "modified" versions of the photos."""
    
    hiddenQuery = ""
    sql = SQLCache()

    # build the subquery for all of the hidden strings
    hiddenStr = " or ".join(["tag_id=%d" % x for x in cherrypy.config.get("hiddenTagIds")])
    if hiddenStr:
        hiddenQuery = "and a.id not in (select distinct photo_id from photo_tags where %s)" % (hiddenStr)

    if cherrypy.config.has_key("processIds"):
        minId = cherrypy.config.get("processIds")[0]
        maxId = cherrypy.config.get("processIds")[1]
    else:
        minId = "(SELECT ((%s-1) * (MAX(id)/%s)) FROM photos)" % (cherrypy.config.get("instanceNumber"), cherrypy.config.get("instanceCount"))
        maxId = "(SELECT ((%s * (MAX(id) / %s))-1) FROM photos)" % (cherrypy.config.get("instanceNumber") , cherrypy.config.get("instanceCount"))
    processIdsQuery = "and a.id BETWEEN %s AND %s" % (minId, maxId)

    query = "SELECT distinct(a.id), c.uri, c.version_id as version_id, c.name as version_name \
      from photos a, photo_tags b, photo_versions c \
      where a.id = b.photo_id \
      and a.id = c.photo_id \
      %s \
      %s \
      order by a.id" % (processIdsQuery, hiddenQuery)

    # print "query in getAllPhotoVersions: “%s”" % (query)

    return sql.execute(query)

def create_s3_key(path, pictureId, version, size, ext):
    """
        # Name/URL der Datei auf s3:
        # http://$bucket.s3.amazonaws.com/$key
        # key = $pfad/$größe/$photo_id/version/$version_id
        # NEU:
        # key = $pfad/$photo_id-$version_id_$größe.$ext
        # $photo_id ist IMMER 6-stellig und von links mit 0 aufgefüllt; $version_id ist 2-stellig.
        # z.B.:
        # bucket = bilder.alexander.skwar.name, pfad = images, größe = original, photo_id = 5303, version_id = 1
        # -> http://bilder.alexander.skwar.name.s3.amazonaws.com/images/original/5303/version/1
        # NEU:
        # -> http://bilder.alexander.skwar.name.s3.amazonaws.com/images/005303.01.original.jpeg
    """
    # Beginnt "ext" mit "."? Wenn ja, abschneiden
    if ext[0] == ".":
        ext = ext[1:len(ext)]
    #return "%s/%s-%s_%s.%s" % (path, str(pictureId).zfill(6), str(version).zfill(2), size, ext)
    return "%s/ID-%s_Version-%s_Size-%s" % (path, str(pictureId).zfill(6), str(version).zfill(2), size)

def start(config=None, dburi=None, dbdebug=False):
    global databaseUri, databaseDebug, conn
    
    #log = logging.getLogger("pennave.py")
    log = logging.getLogger('prepare.py')
    log.info("Starte Vorbereitung der Bilder")
    
    cherrypy.config.update(config)
    cherrypy.config = cherrypy.config

    # Größe der Thumbnailbilder aus der Konfiguration auslesen
    resizedSizes = {
      'thumbnail': cherrypy.config.get("thumbnailPhotoSize", (200,150)),
      'medium': cherrypy.config.get("mediumPhotoSize", (640,480)),
      'tiny': cherrypy.config.get("tinyPhotoSize", (32,32))
    }

    # Aus irgendeinem Grund scheint's "magic" nicht mehr zu geben?
    # "mimetypes" statt dessen verwenden.
    mt = mimetypes.MimeTypes(strict = False)
    
    # this next line is a hack to give us early access to the database
    if cherrypy.config.has_key("dblocation"):
        dburi = "sqlite://" + cherrypy.config.get("dblocation")
        from pysqlite2 import dbapi2 as sqlite
    conn.threadConnection = connect(dburi, debug=dbdebug, cache=None, process=False)
    databaseDebug = dbdebug
    databaseUri = dburi
    sql = SQLCache()
    
    cherrypy.config["requiredTagIds"] = []
    if cherrypy.config.has_key("requiredTags"):
        for t in cherrypy.config["requiredTags"]:
            try:
                cherrypy.config["requiredTagIds"].append(Tag.byName(t).id)
            except:
                print "***** unable to force required tag: %s (%s)" % (t, sys.exc_info()[0])
    cherrypy.config["hiddenTagIds"] = []
    if cherrypy.config.has_key("hiddenTags"):
        for t in cherrypy.config["hiddenTags"]:
            try:
                cherrypy.config["hiddenTagIds"].append(Tag.byName(t).id)
            except:
                print "***** unable to force required hidden tag: %s (%s)" % (t, sys.exc_info()[0])
    
    # Baue Verbindung(en) zu S3 auf
    log.info("Baue Verbindung(en) zu S3 auf")
    try:
        aws_s3_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
        aws_s3_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
    except KeyError, e:
        logging.exception("Error: Environment Variable " + e + " not defined!")
        raise

    s3_conn = MyS3.MyAWSAuthConnection(aws_s3_access_key_id, aws_s3_secret_access_key, is_secure=False)
    s3_gen = S3.QueryStringAuthGenerator(aws_s3_access_key_id, aws_s3_secret_access_key, is_secure=False, calling_format=S3.CallingFormat.SUBDOMAIN)

    # Get a listing of all the Keys ("files") in this "bucket"
    if "÷ re-use" == "÷ re-use":
        log.info("Werde s3_bucket_keys Pickle aus s3_bucket_keys.pickle lesen")
        f = open("s3_bucket_keys.pickle", "r") ; s3_bucket_keys = cPickle.load(f) ; f.close()
        log.info("Werde s3_contents Pickle aus s3_contents.pickle lesen")
        f = open("s3_contents.pickle", "r") ; s3_contents = cPickle.load(f) ; f.close()
    else:
        log.info("Erzeuge Listing des Buckets '%s'. Dies kann etwas dauern..." % cherrypy.config["aws_s3_bucket"])
        s3_bucket_keys = s3_conn.list_all_bucket_keys(cherrypy.config["aws_s3_bucket"])
        s3_contents = dict(map(lambda x: (x.key, x.etag.strip('"')), s3_bucket_keys))
        #s3_contents = dict()
    
    # Nur für Debug!
    if "!write" == "write":
        print "Werde content_keys.txt schreiben"
        fh_contents = open("contents_keys.txt", "w")
        fh_contents.write( "\n".join(map(str, s3_contents.keys())) )
        fh_contents.close()
        print "Werde contents_etags.txt schreiben"
        fh_contents = open("contents_etags.txt", "w")
        fh_contents.write( "\n".join(map(str, s3_contents.values())) )
        fh_contents.close()
        print "Werde s3_bucket_keys Pickle nach s3_bucket_keys.pickle schreiben"
        cPickle.dump(s3_bucket_keys, open("s3_bucket_keys.pickle", "w"), cPickle.HIGHEST_PROTOCOL)
        print "Werde s3_contents Pickle nach s3_contents.pickle schreiben"
        cPickle.dump(s3_contents, open("s3_contents.pickle", "w"), cPickle.HIGHEST_PROTOCOL)
    # Ende Debug!
    
    # Lese alle Pfad und Name aller Photos aus der Datenbank aus
    # Speichere dabei die ID -> Name Zuordnung in nameDb
    nameDb = []
    # In data{} werden alle Daten *EINES* Bildes gespeichert.
    #data_img = {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None}
    data = {
      'ids': {'picture': None, 'version': None},
      'images': {
        'original': {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None},
        'thumbnail': {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None},
        'medium': {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None},
        'tiny': {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None},
        'exif': {'mime': None, 'data': None, 'hash': None, 'name': None, 'ext': None}
      }
    }
    # Iterriere über alle Bilder
    all_photos = getAllPhotos()
    all_versions = getAllPhotoVersions()
    all_pictures = all_photos + all_versions
    
    cPickle.dump(all_photos, open("all_photos.pickle", "w"), cPickle.HIGHEST_PROTOCOL)
    cPickle.dump(all_versions, open("all_versions.pickle", "w"), cPickle.HIGHEST_PROTOCOL)
    cPickle.dump(all_pictures, open("all_pictures.pickle", "w"), cPickle.HIGHEST_PROTOCOL)
    
	# SELECT distinct(a.id), a.uri, c.version_id as version_id, c.name as version_name
    for data['ids']['picture'], uri, data['ids']['version'], versionName in all_pictures:
        # print "data['ids']['picture'] = %s" % repr(data['ids']['picture'])
        # print 'uri = %s' % repr(uri)
        # print "data['ids']['version'] = %s" % repr(data['ids']['version'])
        # print "versionName = %s" % repr(versionName)
        
        # Einige "Hilfs-"Zeichenketten zusammensetzen
        # -> Aus der uri den Dateinamen extrahieren
        #fileName, h = urllib.urlretrieve(uri)
        # 'file://' am Anfang der URI "abschneiden"
        fileName = urlparse.urlparse(uri)[2]
        directoryPath = os.path.dirname(fileName)
        (fileRoot, fileExt) = os.path.splitext(os.path.basename(fileName))
        
        if versionName is not None:
            filePath = "%s%s%s (%s)%s" % (
                directoryPath, os.sep, fileRoot, versionName, fileExt
            )
        else:
            filePath = fileName

        # Die Bilder liegen auf S3 unterhalb von/im aws_s3_image_bucket.
        # Konstruiere die URL zu dem Bild.

        # 2008-08-05:
        # Seit "kurzem" speichert f-spot die Dateinamen gequotet in der Datenbank
        # ab.
        # Früher hieß es:
        # file:///home/askwar/Desktop/My Pictures/Photos/Kategorien/Cédric/2008-03-03/[2008-03-02--15.53.20] (cimg5226) Sandra, Cédric, Läuft, Winterthur {2.6 MB}.jpg
        # Jetzt heißt es:
        # file:///home/askwar/Desktop/My Pictures/Photos/Kategorien/Cassandras Kamera/(IMG_0001) Cassandras Kamera%2C Zuhause%2C Winterthur.jpg
        # Zu beachten ist, das jetzt die , durch %2C ersetzt wurden.
        # Darum muss der Basename einmal unquoted werden, so das nicht "%2C" gequoted
        # wird und zu "%252C" wird.

        # Alt:
        #fileBaseName = fileName[len(cherrypy.config['img_path_prefix_strip']):]
        # Neu:
        fileBaseName = urllib.unquote_plus(fileName[len(cherrypy.config['img_path_prefix_strip']):])
        data['images']['original']['url'] = 'http://s3.amazonaws.com/' + urllib.quote(
            codecs.encode('%s/%s/%s' % (
                cherrypy.config["aws_s3_image_bucket"], cherrypy.config["aws_s3_image_prefix"], fileBaseName
            ), 'utf-8')
        )
        
        # print "fileName = %s" % repr(fileName)
        # print "directoryPath = %s" % repr(directoryPath)
        # print 'fileRoot = %s' % repr(fileRoot)
        # print 'fileExt = %s' % repr(fileExt)
        # print 'filePath = %s' % repr(filePath)
        # print "data['images']['original']['url'] = %s" % data['images']['original']['url']
        # log.info("%06d,%02d: fileName=%s" % (data['ids']['picture'], data['ids']['version'], repr(fileName)))
        # log.info("%06d,%02d: fileBaseName=%s" % (data['ids']['picture'], data['ids']['version'], repr(fileName)))
        # log.info("%06d,%02d: directoryPath=%s" % (data['ids']['picture'], data['ids']['version'], repr(directoryPath)))
        # log.info("%06d,%02d: fileRoot=%s" % (data['ids']['picture'], data['ids']['version'], repr(fileRoot)))
        # log.info("%06d,%02d: fileExt=%s" % (data['ids']['picture'], data['ids']['version'], repr(fileExt)))
        # log.info("%06d,%02d: filePath=%s" % (data['ids']['picture'], data['ids']['version'], repr(filePath)))
        # log.info("%06d,%02d: data images original url=%s" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
            
        # Öffne die Datei
        data['images']['original']['handle'] = urllib.urlopen(url = data['images']['original']['url'])
        # Pfad zu der Datei und Extension speichern
        data['images']['original']['name'], data['images']['original']['ext'] = (filePath, fileExt)
        
        # log.info("%06d,%02d: data images original handle info()=%s" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['handle'].info()))
        # log.info("%06d,%02d: data images original handle info() etag=%s" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['handle'].info()['etag']))
        
        # MD5 Hash bestimmen -> Wird als ETag Header geliefert, allerdings in "" -> Weg mit den "!
        try:
            data['images']['original']['hash'] = data['images']['original']['handle'].info()['etag'].strip('"')
        except KeyError:
            log.error("%06d,%02d - %s: KeyError aufgetreten. Gibt's das Bild an der angegebenen URL?" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
            raise
        
        # Erzeuge auch UTF-8 kodierte Varianten der Dateinamen
        fileRoot_U8 = codecs.encode(fileRoot, "UTF-8")
        fileExt_U8 = codecs.encode(fileExt, "UTF-8"),
        filePath_U8 = codecs.encode(filePath, "UTF-8")
        fileName_U8 = codecs.encode(fileName, "UTF-8")
        directoryPath_U8 = codecs.encode(directoryPath, "UTF-8")
        
        # Speichere aktuelle ID -> Dateiname in der Namensdatenbank nameDb
        nameDb.append("%s\t%s\t%s\t%s" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url'], filePath_U8))
        
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
        
        # Zuerst wird das Originalbild bearbeitet.
        size = "original"
        # MIME-Type bestimmen
        log.info("%06d,%02d - %s: Bestimme MIME-Type" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
        (mimetype, encoding) = mt.guess_type(url = data['images']['original']['url'], strict = False)
        # Default sei "application/octet-stream"
        if mimetype is None: mimetype = "application/octet-stream"
        # MIME-Type der Originaldatei speichern
        data['images']['original']['mime'] = mimetype
        
        # S3 Key erzeugen
        s3_key = create_s3_key(cherrypy.config["aws_s3_path"], data['ids']['picture'],
          data['ids']['version'], size, mt.guess_extension(data['images']['original']['mime']))
        
        log.info("%06d,%02d - %s: Bearbeite Bild #%s; Key: %s" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url'], data['ids']['picture'], s3_key))
        
        # Sofern der neu erzeugte s3_key (Pfad bei s3) noch NICHT in
        # s3_contents (Listing der Dateien im Bucket) auftaucht, uploade
        # die Datei.
        # Fall der s3_key in s3_contents vorhanden ist, überprüfe, ob
        # die md5sum (hash) mit der md5sum (ETag) auf s3 übereinstimmt.
        # Falls dem nicht so ist (hash != ETag), dann uploade.
        
        # Falls geuploaded wurde (bzw. werden soll), dann auch kleinere
        # Bilder (Thumbnail, Medium, Tiny) erzeugen und uploaden.
        # -> Überprüfen, ob's die Datei schon auf S3 gibt.
        # --> Wenn ja, dann ist die MD5 zu vergleichen
        # --> Wenn nein, dann muss auf jeden Fall geuploaded werden.
        do_upload = not s3_contents.has_key(s3_key)
        if not do_upload:
            log.info("%06d,%02d - %s: Datei bereits auf S3 vorhanden" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
            
            # Bisher sollte NICHT geuploadet werden; dh. die Datei gibt's
            # schon auf s3. Überprüfen, ob Checksummen übereinstimmen.
            
            do_upload = s3_contents[s3_key] != data['images']['original']['hash']
            if do_upload:
                try:
                    log.info(u"%06d,%02d - %s: Checksummen der lokalen Datei (%s) und der S3 Datei (%s) sind nicht identisch -> Upload!" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url'], data['images']['original']['hash'], s3_contents[s3_key]))
                except UnicodeDecodeError:
                    log.info("%06d,%02d - %s: Checksummen der lokalen Datei (%s) und der S3 Datei (%s) sind nicht identisch -> Upload!" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url'], data['images']['original']['hash'], s3_contents[s3_key]))
            else:
                log.info("%06d,%02d - %s: Checksummen identisch -> Kein Upload!" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
        else:
            log.info("%06d,%02d - %s: Datei noch NICHT auf S3 vorhanden -> Upload!" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url'])) 
            
        if do_upload:
            log.info("%06d,%02d - %s: Datei soll geuploadet werden. Bearbeite das Bild zuerst." % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
            # Es soll geuploadet werden.
            # Grund: Entweder gab's die Datei noch nicht oder aber die
            # Checksummen stimmen nicht überein.
            
            # Bearbeite das Bild (verkleinern, EXIF, ...)
            data['images'].update(process_image(data['images']['original'], resizedSizes))
            
            log.info("%06d,%02d - %s: Bilder uploaden" % (data['ids']['picture'], data['ids']['version'], data['images']['original']['url']))
            upload_images(data, cherrypy.config, s3_conn, s3_gen)
            
            # Speicher freigeben
            for key in resizedSizes.keys():
                del(data['images'][key]['data'])
            
        # Bild wird nicht weiter benötigt -> Schließen!
        data['images']['original']['handle'].close()
        
        print "++++++++++ Behandlung der Datei %s (%06d,%02d) abgeschlossen." % (filePath_U8, data['ids']['picture'], data['ids']['version'])
        
    log.info("Alle Dateien hochgeladen. Sende nun TRANSLATION.txt.")
    newFileName = "TRANSLATION.txt"
    fileData = "\n".join(map(str, nameDb))
    s3_key = cherrypy.config["aws_s3_path"] + "/" + newFileName
    s3_headers = {
      'x-amz-acl': 'public-read',
      'Content-Disposition': 'inline; filename="%s"' % newFileName,
      'Content-Type': 'text/plain' 
    }
    s3_response = s3_conn.put(
      cherrypy.config["aws_s3_bucket"], s3_key,
      S3.S3Object(fileData, {'original-file-name': newFileName}), s3_headers
    )
    log.info("\tnach TRANSLATION.txt -> Status: %s, Reason: %s, body: %s" % (s3_response.http_response.status, s3_response.http_response.reason, s3_response.body))
    
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

