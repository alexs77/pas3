#!/usr/bin/python
"""
exiftools.py

This is an assistance library for PennAve that handles the loading and
caching of exif data.
"""

import EXIF

NEWTAGS = {"EXIF Flash" : "flash", "Image Make" : "make", "Image Model" : "model",
           "EXIF ExifImageWidth" : "imageWidth", "EXIF ExifImageLength" : "imageLength", 
           "Image DateTime" : "dateTime", "Image Orientation" : "orientation"}

class ExifTool:
    def __init__(self):
        self.exifCache = {}
        pass

    def get(self, filename):
        """
        Given a filename, returns a dict with the exif tags paired up
        
        @param filename: the filename to examine
        @return: a dict of pairs of exif tags and values
        """
        # if the cache has already looked up the exif information for this
        # file, then return the cached data
        if self.exifCache.has_key(filename):
            return self.exifCache[filename]

        exifDict = {}
        f = open(filename, "rb")
        tags = EXIF.process_file(f)
        x=tags.keys()
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
