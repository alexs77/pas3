#===============================================================================
# vim: set fileencoding=utf-8
# 
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

import Image
import ImageFont
import ImageDraw
import ImageOps
import StringIO
import cStringIO
import cherrypy
import os
import imageops
import random
import md5
import urllib
import codecs
import logging
import pprint
import time

from dbobjects import *

Image.preinit()
import TiffImagePlugin

class PennAveImages:
    def __init__(self, root):
        self.root = root

        # use the settings from PIL for handling this stuff
        self.formats = Image.EXTENSION
        Image.register_mime("BMP","image/bmp")
        Image.register_mime("PPM","image/x-portable-pixmap")
        self.ctypes = {}
        for key,val in self.formats.iteritems():
            self.ctypes[key] = Image.MIME[val]
            
        self.regenKey = cherrypy.config.get("regenKey",None)
        self.mediumPhotoSize = cherrypy.config.get("mediumPhotoSize",(640,480))
        self.thumbnailPhotoSize = cherrypy.config.get("thumbnailPhotoSize",(200,150))
        self.tinyPhotoSize = cherrypy.config.get("tinyPhotoSize",(32,32))
        self.s3bucket = cherrypy.config.get("aws_s3_bucket","n/a")
        self.s3path = cherrypy.config.get("aws_s3_path","n/a")
        self.img_path_prefix_strip = cherrypy.config.get("img_path_prefix_strip", "n/a")

    @cherrypy.expose
    def index(self):
        # FIXME: the index should do something more useful
        return "this is a little test!"

    def createErrorMessagePng(self, size, message):
        s = StringIO.StringIO()
        i = Image.new("RGB", size)
        font = ImageFont.truetype(cherrypy.config["font"], 15)
        draw = ImageDraw.Draw(i)
        draw.text((0, 0), message, font=font)
        i.save(s, "png")
        s.seek(0)
        cherrypy.response.headers["Content-Type"] = "image/png"
        return s.read()

    def createAccessDenied(self, p, size):
        return self.createErrorMessagePng(size, "access denied")

    def createErrorPng(self, p, size=(2000, 200), version=None):
        s = StringIO.StringIO()
        i = Image.new("RGB", size)
        font = ImageFont.truetype(cherrypy.config["font"], 15)
        draw = ImageDraw.Draw(i)
        draw.text((0, 0), "cannot open image:", font=font)
        x,y = font.getsize("cannot open image:")
        # printPath = p.directoryPath + os.sep + p.name
        printPath = self.root.get_filename(p,version=version)
        nx, ny = font.getsize(printPath)
        part1 = printPath[:len(printPath)/2]
        part2 = printPath[len(printPath)/2:]
        while nx > i.size[0]:
            part1 = part1[:-1]
            part2 = part2[1:]
            printPath = part1 + "..." + part2
            nx, ny = font.getsize(printPath)
        draw.text((0,y), printPath, font=font)
        i.save(s, "png")
        s.seek(0)
        cherrypy.response.headers["Content-Type"] = "image/png"
        return s.read()

    def getURL(self, pictureId, versionNumber = 1, size = "original", subdomain = True):
        pathSuffix = "%s/ID-%06d_Version-%02d_Size-%s" % ( self.s3path, pictureId, versionNumber, size)
        s3host = "s3.amazonaws.com" ; protocol = "http"
        if subdomain:
            return "%s://%s.%s/%s" % (protocol, self.s3bucket, s3host, pathSuffix)
        else:
            return "%s://%s/%s/%s" % (protocol, s3host, self.s3bucket, pathSuffix)

    def getThumbnail(self, p, size, indir, version=None):
        """Attempts to create at thumnail for an image"""
        filename = self.root.get_filename(p, version=version)
        cherrypy.log("getting thumbnail for %d: filename=%s, version=%s" % (p.id, filename, version))
        fnu8 = filename.encode("utf-8")
        ext = os.path.splitext(fnu8)[-1].lower()
        md5fnhexext = md5.new(fnu8).hexdigest() + ext
        thumbnailName = indir + os.sep + md5fnhexext
        if os.path.isfile(thumbnailName):
            mtime_thumb = os.stat(thumbnailName).st_mtime
            self.root.setLastModified(mtime_thumb)
            if os.path.isfile(filename):
                mtime_orig = os.stat(filename).st_mtime
                if mtime_thumb > mtime_orig:
                    self.root.validateSince()
                    cherrypy.response.headers["Content-Type"] = self.ctypes[ext]
                    return open(thumbnailName).read()
            else:
                cherrypy.response.headers["Content-Type"] = self.ctypes[ext]
                return open(thumbnailName).read()
            
        try:
            i = Image.open(filename)
            i.thumbnail(size, Image.ANTIALIAS)
        except Exception, e:
            cherrypy.log("Error opening image: %s: %s" % (filename, e), severity=logging.WARN, traceback=True)
            return self.getThumbnailFallback(ext, self.ctypes, p, size)
            
        try:
            #see if we can get the exif information
            exif = self.root.exifTool.get(filename)
            # detect the orientation of the image, and rotate accordingly
            if exif.has_key("orientation"):
                if exif["orientation"] == "Rotated 90 CCW":
                    i = i.rotate(90)
                elif exif["orientation"] == "Mirrored horizontal":
                    i = ImageOps.mirror(i) 
                elif exif["orientation"] == "Rotated 90 CW":
                    i = i.rotate(270)
                elif exif["orientation"] == "Mirrored vertical":
                    i = ImageOps.flip(i)
                elif exif["orientation"] == "Mirrored horizontal then rotated 90 CCW":
                    i = ImageOps.mirror(i).rotate(90)
                elif exif["orientation"] == "Mirrored horizontal then rotated 90 CW":
                    i = ImageOps.mirror(i).rotate(270)
                elif exif["orientation"] == "Rotated 180":
                    i = ImageOps.rotate(180)
                # strictly speaking this is a little sloppy, but it's the best way to ensure that
                # images that are rotated are handled properly
                i.thumbnail(size, Image.ANTIALIAS)
        except Exception, e:
            cherrypy.log("Error reading Exif data: %s: %s" % (filename, e), severity=logging.WARN, traceback=True)
        
        try:
            i.save(thumbnailName, self.formats[ext])
            self.root.setLastModified(os.stat(thumbnailName).st_mtime)
            cherrypy.response.headers["Content-Type"] = self.ctypes[ext]         
            s = StringIO.StringIO()
            i.save(s, self.formats[ext])
            s.seek(0)
            return s.read()
        except Exception, e:
            # FIXME: this probably should be decoupled from cherrypy
            cherrypy.log("Error saving image: %s: %s" % (filename, e), severity=logging.WARN, traceback=True)
        
        return getThumbnailFallback(ext, ctypes, p, size)
    
    def getThumbnailFallback(self, ext, ctypes, p, size):
        try:
            cherrypy.response.headers["Content-Type"] = self.ctypes[ext]
            return open(thumbnailName).read()
        except:
            cherrypy.log("No cached version of image thumbnail, generating error graphic", severity=logging.WARN)
            return self.createErrorPng(p, size)

    def getVersionFromURL(self, args):
        args = [x.lower() for x in args]
        try: return int(args[args.index("version")+1])
        except: return None
    
    def getImageId(self, arg):
        try:
            return int(arg.split(".")[0])
        except Exception, e:
            cherrypy.log("Exception: %s" % (e))
            return int(arg)
        
    @cherrypy.expose
    def original(self, *args, **kwargs):
        """Returns the original image

        FIXME: we should add X-SendFile and X-Accel-Redirect support to this
        so cherrypy doesn't have to open the file itself."""
        p = Photo.get(self.getImageId(args[0]))
        try:
            self.root.validateAccess(p)
        except:
            return self.createAccessDenied(p, self.mediumPhotoSize)
        version = self.getVersionFromURL(args)
        
        fn = self.root.get_filename(p, version=version)
        try:
            self.root.setLastModified(os.stat(fn).st_mtime)
        except:
            return self.createErrorPng(p, self.mediumPhotoSize)
        
        self.root.validateSince()
        cherrypy.response.headers["Content-Type"] = self.ctypes[os.path.splitext(fn)[-1].lower()]
        return open(fn).read()

    def scaledImage(self, args, scaledSize, scaledPath):
        p = Photo.get(self.getImageId(args[0]))
        version = self.getVersionFromURL(args)
        try:
            self.root.validateAccess(p)
        except:
            return self.createAccessDenied(p, scaledSize)
        return self.getThumbnail(p, scaledSize, scaledPath, version=version)
        
    @cherrypy.expose
    def tiny(self, *args, **kwargs):
        return self.scaledImage(args=args, scaledSize=self.tinyPhotoSize, scaledPath=cherrypy.config["tinyPath"])
    
    @cherrypy.expose
    def medium(self, *args, **kwargs):
        return self.scaledImage(args=args, scaledSize=self.mediumPhotoSize, scaledPath=cherrypy.config["mediumPath"])
    
    @cherrypy.expose
    def thumbnail(self, *args, **kwargs):
        return self.scaledImage(args=args, scaledSize=self.thumbnailPhotoSize, scaledPath=cherrypy.config["thumbnailPath"])

    @cherrypy.expose
    def stacked(self, *args, **kwargs):
        """Creates a stacked image of a category"""
        args = list(args)
        # snap off the extension
        if len(args[-1].split(".")) > 1: 
            args[-1] = args[-1].split(".")[0]
        if (args[-1].lower() == "default"): args = args[:-1]
        andTags, orTags = self.root.processTags(args)

        # this hokeyness builds the filename, or'd tags are appended with p
        allTags = [x for x in andTags]
        allTags.sort()
        otherTags = [x[0] for x in orTags]
        otherTags.sort()
        otherTags = ["%dp"%x for x in otherTags]
        fn = cherrypy.config["stackedPath"] + os.sep + "stacked_" + "_".join([str(x) for x in allTags + otherTags]) + ".png"
        
        cherrypy.response.headers["Content-Type"] = self.ctypes[os.path.splitext(fn)[-1]]
        try:
            if not kwargs.has_key(self.regenKey):
                # check to see if the image needs to be updated
                self.root.setLastModified(os.stat(fn).st_mtime)
                self.root.validateSince()
                return open(fn).read()
        except OSError, e:
            # OSErrors are raised if we can't actually stat the file
            pass
        photos = self.root.getPhotos(andTags, orTags)
        imageIds = []
        for x in xrange(0,min(len(photos),3)):
            imgId = random.randint(0,len(photos))
            while imgId in imageIds:
                imgId = random.randint(0,len(photos)-1)
            imageIds.append(imgId)
        # create the image
        try:
            img = imageops.stackImages([self.root.get_filename(Photo.get(photos[p])) for p in imageIds], fn, 6, shadow=True)
        except:
            return self.createErrorMessagePng((250,100), "No photos in tag selection")

        # set the last modified header on the image
        self.root.setLastModified(os.stat(fn).st_mtime)
        s = StringIO.StringIO()
        img.save(s, self.formats[os.path.splitext(fn)[-1]])
        s.seek(0)
        return s.read()
