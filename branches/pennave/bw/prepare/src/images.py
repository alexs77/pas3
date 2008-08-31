# vim: set fileencoding=utf-8

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

    def createErrorPng(self, p, size, version=None):
        s = StringIO.StringIO()
        size = 2000, 200
        i = Image.new("RGB", size)
        font = ImageFont.truetype(cherrypy.config["font"], 15)
        draw = ImageDraw.Draw(i)
        draw.text((0, 0), "cannot open image:", font=font)
        x,y = font.getsize("cannot open image:")
        # printPath = p.directoryPath + os.sep + p.name
        printPath = self.root.getFilename(p, version=version)
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
        import pprint

        if version is None:
            versionNumber = 01
        else:
            versionNumber = version
        
        url = self.getURL(pictureId=p.id, versionNumber=versionNumber, size="medium")
        
        try:
            # Lese die Daten vom http Server / "aus URL")
            cherrypy.log("Picture #%06d: Trying to load image from <%s>" % (p.id, url), severity=logging.INFO)
            urlobj = urllib.urlopen(url)
            urldata = urlobj.read()
            urlheaders = urlobj.info()
            urlobj.close()
            
            # Erzeuge nun ein StringIO Objekt daraus
            urlfile = StringIO.StringIO(urldata)
            # Image Objekt erzeugen
            i = Image.open(urlfile)
            i.thumbnail(size, Image.ANTIALIAS)
            #cherrypy.log("Picture #%06d: Resized to size (x, y) = %s" % (p.id, size), severity=logging.DEBUG)
        except Exception, e:
            cherrypy.log("Error opening image: %s: %s" % (filename, e), severity=logging.WARN, traceback=True)
            return self.getThumbnailFallback(ext, self.ctypes, p, size)
            
        try:
            # See if we can get the exif information
            
            cherrypy.log("Picture #%06d: Trying to get EXIF information" % p.id, severity=logging.DEBUG)
            # Reset the "filepointer" in the StringIO object to the beginning
            # of the "file".
            urlfile.seek(0)
            exif = self.root.exifTool.get(urlfile)
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
            cherrypy.log("Picture #%06d: Error reading Exif data: %s" % (p.id, e), severity=logging.WARN, traceback=True)
        
        try:
            # The image will be "saved" in a file-like object of type cStringIO.
            # -> Should this be stored on disk to speed things up?
            resizedImage = cStringIO.StringIO()
            # Image Type is derived from Content-Type. It's the word after
            # the 1st /. Eg. image/jpeg -> jpeg.
            cherrypy.log("Picture #%06d: urlheaders: %s" % (p.id, pprint.pformat(urlheaders)))
            content_type = urlheaders.gettype() ; ct_major = content_type.split('/')[0] ; ct_minor = content_type.split('/')[1]
            cherrypy.log("Picture #%06d: Going to save image of type %s/%s" % (p.id, ct_major, ct_minor))
            i.save(resizedImage, ct_minor)
            
            # Return as much from the original header data as possible.
            cherrypy.log("Picture #%06d: Setting Headers. Content-Type=%s, Last-Modified=%s" % (p.id, urlheaders["content-type"], urlheaders["last-modified"]))
            #cherrypy.response.headers["Content-Length"] = urlheaders["content-length"]
            #cherrypy.response.headers["Content-Disposition"] = urlheaders["content-disposition"]
            cherrypy.response.headers["Last-Modified"] = urlheaders["last-modified"]
            #cherrypy.response.headers["ETag"] = urlheaders["etag"]
            cherrypy.response.headers["Content-Type"] = urlheaders["content-type"]
            
            cherrypy.log("Picture #%06d: Seeking to beginning of image" % p.id)
            resizedImage.seek(0)
            returnValue = resizedImage.read()
            cherrypy.log("Picture #%06d: Returning image. Size: %s" % (p.id, len(returnValue)))
            return returnValue
        except Exception, e:
            # FIXME: this probably should be decoupled from cherrypy
            cherrypy.log("Picture #%06d: Error saving image: %s" % (p.id, e), severity=logging.WARN, traceback=True)
        
        return getThumbnailFallback(ext, ctypes, p, size)


    def getThumbnailLocal(self, p, size, indir, version=None):
        """Attempts to create at thumnail for an image"""
        filename = self.root.getFilename(p, version=version)
        cherrypy.log("getting thumbnail for %d: filename=%s, version=%s" % (p.id, filename, version))

        url = self.getURL(pictureId=p.id, versionNumber=versionNumber, size="medium")
        
        #filename_utf8 = filename.encode("utf-8")
        #filename_utf8 = filename
        filename_utf8 = codecs.encode(filename, "UTF-8")
        ext = os.path.splitext(filename_utf8)[-1].lower()
        try:
            md5fn = md5.new(filename)
        except UnicodeEncodeError:
            md5fn = md5.new(filename_utf8)
        md5fnhex = md5fn.hexdigest()
        md5fnhexext = md5fnhex + ext
        #md5fnhexext = md5.new(filename_utf8).hexdigest() + ext
        thumbnailName = indir + os.sep + md5fnhexext
                
        try:
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
        except UnicodeEncodeError:
            if os.path.isfile(thumbnailName):
                mtime_thumb = os.stat(thumbnailName).st_mtime
                self.root.setLastModified(mtime_thumb)
                if os.path.isfile(filename_utf8):
                    mtime_orig = os.stat(filename_utf8).st_mtime
                    if mtime_thumb > mtime_orig:
                        self.root.validateSince()
                        cherrypy.response.headers["Content-Type"] = self.ctypes[ext]
                        return open(thumbnailName).read()
                else:
                    cherrypy.response.headers["Content-Type"] = self.ctypes[ext]
                    return open(thumbnailName).read()
        
        try:
            try:
                i = Image.open(filename)
            except UnicodeEncodeError:
                i = Image.open(filename_utf8)
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
        
        filename = self.root.getFilename(p, version=version)

        try:
            self.root.setLastModified(os.stat(filename).st_mtime)
        except:
            return self.createErrorPng(p, self.mediumPhotoSize)
        
        self.root.validateSince()
        cherrypy.response.headers["Content-Type"] = self.ctypes[os.path.splitext(filename)[-1].lower()]
        return open(filename).read()

    @cherrypy.expose
    def original_aws(self, *args, **kwargs):
        """Redirects the request to Amazon AWS, where the original
        image is hosted"""
        
        p = Photo.get(self.getImageId(args[0]))
        try:
            self.root.validateAccess(p)
        except:
            return self.createAccessDenied(p, self.mediumPhotoSize)
        version = self.getVersionFromURL(args)

        filename = self.root.getFilename(p, version=version)
        s3suffix = urllib.quote_plus(filename.split(self.img_path_prefix_strip)[1], "/")

        raise cherrypy.HTTPRedirect("http://s3.amazonaws.com/%s/%s/%s" % 
          (self.s3bucket, self.s3path, s3suffix))

        return

    @cherrypy.expose
    def tiny(self, *args, **kwargs):
        p = Photo.get(self.getImageId(args[0]))
        version = self.getVersionFromURL(args)
        try:
            self.root.validateAccess(p)
        except:
            return self.createAccessDenied(p, self.tinyPhotoSize)
        return self.getThumbnail(p, self.tinyPhotoSize, cherrypy.config["tinyPath"], version=version)
    
    @cherrypy.expose
    def medium(self, *args, **kwargs):
        """This is basically like thumbnail, only it produces a 640x480 image"""
        p = Photo.get(self.getImageId(args[0]))
        version = self.getVersionFromURL(args)
        try:
            self.root.validateAccess(p)
        except:
            return self.createAccessDenied(p, self.mediumPhotoSize)
        return self.getThumbnail(p, self.mediumPhotoSize, cherrypy.config["mediumPath"], version=version)
    
    @cherrypy.expose
    def thumbnail(self, *args, **kwargs):
        """This first checks to see if there if the file exists.  Then validates
        the thumbnail.  If the thumbnail is newer than the source, then it shows
        the image.  Otherwise it creates the thumbnail.  In the event it cannot
        open the source image, it makes a dummy message that is 200x150 that says
        it cannot open the file."""
        p = Photo.get(self.getImageId(args[0]))
        version = self.getVersionFromURL(args)
        try:
            self.root.validateAccess(p)
        except:
            return self.createAccessDenied(p, self.thumbnailPhotoSize)
        return self.getThumbnail(p, self.thumbnailPhotoSize, cherrypy.config["thumbnailPath"], version=version)

    @cherrypy.expose
    def stacked(self, *args, **kwargs):
        """Creates a stacked image of a category"""
        log = cherrypy.log
        args = list(args)
        # snap off the extension
        if len(args[-1].split(".")) > 1: 
            args[-1] = args[-1].split(".")[0]
        if (args[-1].lower() == "default"): args = args[:-1]
        andTags, orTags = self.root.processTags(args)
        allTags = [andTags, orTags]
        #log("%s: Tags" % allTags)
        
        cherrypy.response.headers["Content-Type"] = self.ctypes['.png']
        
        #try:
        #    if not kwargs.has_key(self.regenKey):
        #        # check to see if the image needs to be updated
        #        self.root.setLastModified(os.stat(fn).st_mtime)
        #        self.root.validateSince()
        #        return open(fn).read()
        #except OSError, e:
        #    # OSErrors are raised if we can't actually stat the file
        #    pass
        
        photos = self.root.getPhotos(andTags, orTags)
        #log("%s: Photos -> %s" % (allTags, photos))
        
        imageIds = []
        for x in xrange(0,min(len(photos),3)):
            imgId = random.randint(1,len(photos))
            while imgId in imageIds:
                imgId = random.randint(1,len(photos))
            imageIds.append(imgId)
        #log("%s: imageIdIndexes -> %s" % (allTags,imageIds))
        # create the image
        try:
            urls = [self.getURL(size = "medium", pictureId = photos[p-1]) for p in imageIds]
            log("urls: %s" % urls)
            # Creating the stacked images from S3 sources takes about 2 seconds,
            # because of download times.
            # It would be better, if the download, which is done in stackS3Images,
            # could be made "asynchron", so that all 3 (or whatever) images are downloaded
            # in parallel.
            img = imageops.stackS3Images(urls = urls, numImages = 6, shadow = True)
            #log("danach")
        except:
            return self.createErrorMessagePng((250,100), "No photos in tag selection")

        # set the last modified header on the image
        self.root.setLastModified()
        # Set the ETag header, using the md5 of the image - this goes *VERY* fast!
        #   DEBUG:cherrypy.error.4146816780:[29/Feb/2008:15:15:51]  25_60: (1204294551.11) Werde MD5 Summe für ETag erzeguen
        #   DEBUG:cherrypy.error.4146816780:[29/Feb/2008:15:15:51]  25_60: (1204294551.11) MD5 Summe erzeugt -> 38ff70bf54bef783013abe48a80cf732
        # It's calculated in the same split second (1204294551.11)!
        img.seek(0)
        cherrypy.response.headers["ETag"] = '"%s"' % md5.new(img.read()).hexdigest()
        img.seek(0)
        return img.read()

    def local_stacked_NOT_IN_USE(self, *args, **kwargs):
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
            img = imageops.stackImages([self.root.getFilename(Photo.get(photos[p])) for p in imageIds], fn, 6, shadow=True)
        except:
            return self.createErrorMessagePng((250,100), "No photos in tag selection")

        # set the last modified header on the image
        self.root.setLastModified(os.stat(fn).st_mtime)
        s = StringIO.StringIO()
        img.save(s, self.formats[os.path.splitext(fn)[-1]])
        s.seek(0)
        return s.read()

