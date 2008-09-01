#!/usr/bin/python

#===============================================================================
# vim: set fileencoding=utf-8
# 
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

"""
exiftools.py

This is an assistance library for PennAve that handles the loading and
caching of exif data.
"""

import EXIF         # Extract EXIF information from file
import logging      # Logging
import cherrypy     # Needed to fetch configuration items
import cPickle      # EXIF information is stored in a Pickle on S3
import urllib       # Needed to be able to download content from S3

NEWTAGS = {"EXIF Flash" : "flash", "Image Make" : "make", "Image Model" : "model",
           "EXIF ExifImageWidth" : "imageWidth", "EXIF ExifImageLength" : "imageLength",
           "Image DateTime" : "dateTime", "Image Orientation" : "orientation"}

class ExifTool:
    def __init__(self):
        self.exifCache = {}
        pass

    def getLocal(self, pictureId=None, versionId=None):
        """
        Not used. The method might work, but getS3 is actually called.
        """
        
        log = logging.getLogger("pennave.py")

        # Überprüfen, ob schon im Cache vorhanden
        if self.exifCache.has_key(str(pictureId) + "," + str(versionId)):
            log.info(str(pictureId) + "," + str(versionId) + ": EXIF Daten im Cache gefunden")
            return self.exifCache[str(pictureId) + "," + str(versionId)]

        log.info(str(pictureId) + "," + str(versionId) + ": EXIF Daten noch nicht im Cache vorhanden")

        # Baue den Pfad zur Pickle Datei zusammen
        pickle_file_path = "%s/ID-%06d_Version-%02d" % (
          cherrypy.config["exifPath"], pictureId, versionId)
        
        # Rückgabewert initialisieren
        exifDict = {}
        
        try:
            # Versuche die Pickle Datei zu öffnen - kann fehlschlagen!
            pickle_file_handle = open(pickle_file_path, "r")
            try:
                # Lese nun die ge-Pickle-ten Daten aus der Datei
                exif = cPickle.load(pickle_file_handle)
                
                log.info(str(pictureId) + "," + str(versionId) + ": EXIF Daten aus Pickle Datei '" + pickle_file_path + "' gelesen.")
                
                # Speichere nur die "interessanten" EXIF Daten im Cache
                x = exif.keys()
                x.sort()
                for i in x:
                    if i in ('JPEGThumbnail', 'TIFFThumbnail'):
                        # Thumbnails interessieren uns *NIE*
                        continue
                    try:
                        # Überprüfen, ob der aktuelle Key bei den "interessanten"
                        # Keys (also Dict NEWTAGS) vorkommt.
                        if NEWTAGS.has_key(i):
                            # Ja, kommt da vor -> Speichere die "druckbare"
                            # Version des Tags ab.
                            exifDict[NEWTAGS[i]] = exif[i].printable
                    except:
                        # FIXME: need some sort of logging here
                        print 'error', i, '"', exif[i], '"'
                # Speichere die EXIF Daten auch im Cache ab.
                self.exifCache[str(pictureId) + "," + str(versionId)] = exifDict
                # Die eingelesenen Daten werden nicht mehr benötigt
                del(exif)
                
            finally:
                # Sicher gehen, das der Dateihandle geschlossen wird.
                pickle_file_handle.close()
        except IOError, (errno, strerror):
            if errno == 2:
                # Die Pickle Datei konnte nicht gefunden werden.
                log.warning(str(pictureId) + "," + str(versionId) + u": EXIF Pickle Datei '" + pickle_file_path + u"' konnte nicht geöffnet werden! " + strerror)
            else:
                # Anderer I/O-Error -> Fehler durchreichen!
                log.error(str(pictureId) + "," + str(versionId) + ": I/O-Fehler: #" + str(errno) + ", " + strerror)
                raise IOError, (errno, strerror)

        return exifDict

    def getS3(self, pictureId=None, versionId=None):
        """
        Holt von S3 die extrahierten EXIF Informationen, sofern nicht schon
        im Cache vorhanden.
        """

        log = logging.getLogger("pennave.py")

        # Überprüfen, ob schon im Cache vorhanden
        if self.exifCache.has_key(str(pictureId) + "," + str(versionId)):
            log.debug("%s,%s: EXIF Daten im Cache gefunden" % (str(pictureId), str(versionId)))
            return self.exifCache[str(pictureId) + "," + str(versionId)]

        url = "http://s3.amazonaws.com/%s/%s/ID-%06d_Version-%02d_Size-exif" % (
          cherrypy.config["aws_s3_bucket"], cherrypy.config["aws_s3_path"],
          pictureId, versionId)
        
        log.debug("%s,%s: EXIF Daten noch nicht im Cache vorhanden. Von %s downloaden." % (str(pictureId), str(versionId), url))

        # Initialize the dict, which will hold the EXIF cntent
        exifDict = {}
        # Create a handle to the stuff on the URL (pointing to S3)
        handle = urllib.urlopen(url)
        try:
            self.exifCache[str(pictureId) + "," + str(versionId)] = exifDict
            # Decode the Pickle
            exif = cPickle.load(handle)
            # Get all the keys
            x = exif.keys()
            # Sort them
            x.sort()
            # Loop over the keys
            for i in x:
                # Ignore JPEG or TIFF Thumbnails
                if i in ('JPEGThumbnail', 'TIFFThumbnail'):
                    continue
                try:
                    if NEWTAGS.has_key(i):
                        exifDict[NEWTAGS[i]] = exif[i].printable
                except:
                    # FIXME: need some sort of logging here
                    print 'error', i, '"', exif[i], '"'
            self.exifCache[str(pictureId) + "," + str(versionId)] = exifDict
        finally:
            handle.close()
        return exifDict

    def get(self, filename):
        """
        Not used. getS3 is used instead.
        
        Given a filename, returns a dict with the exif tags paired up
        
        @param filename: the filename to examine - OR a file like object (like StringIO)
        @return: a dict of pairs of exif tags and values
        """
        # if the cache has already looked up the exif information for this
        # file, then return the cached data
        if self.exifCache.has_key(filename):
            return self.exifCache[filename]

        exifDict = {}
        # Check if "filename" is of type "str"(ing). If so, try to open
        # it.
        # If it's not a string, hope that it is a file like object.
        if type(filename) is str:
            # cherrypy.log("exiftools.get. filename string = %s" % (filename), severity=logging.DEBUG)
            try:
                f = open(filename, "rb")
            except UnicodeEncodeError:
                f = open(filename.encode("UTF-8"), "rb")
        else:
            # "filename" is not a string - hope it's a file like object.
            # cherrypy.log("exiftools.get. filename nicht string -> type: %s" % (type(filename)), severity=logging.DEBUG)
            f = filename
        tags = EXIF.process_file(f)
        x = tags.keys()
        x.sort()
        for i in x:
            if i in ('JPEGThumbnail', 'TIFFThumbnail'):
                continue
            try:
                if NEWTAGS.has_key(i):
                    exifDict[NEWTAGS[i]] = tags[i].printable
            except:
                # FIXME: need some sort of logging here
                print 'error', i, '"', tags[i], '"'
        self.exifCache[filename] = exifDict
        return exifDict
