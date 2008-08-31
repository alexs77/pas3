#!/usr/bin/python
# vim: set fileencoding=utf-8

import logging
from optparse import OptionParser
import cherrypy
from sqlobject import *
import os

# set up the connection hub
from dbobjects import *
import libxml2
import libxslt
import urllib
import subprocess
import math
import StringIO
import time
import datetime
from sets import Set
import codecs
import re

# various modules we need for pennave
import slides
import feeds
import images
import exiftools
import pprint

#
# IMPORTANT: run these commands on your database first!
# sqlite> create index photo_tags_tag_id_idx on photo_tags(tag_id);
# sqlite> create index photo_tags_photo_id_idx on photo_tags(photo_id);
#

VERSION = "0.5svn"
TAG_LEVELS = 6
ORDERBY_NORMAL=1
ORDERBY_REVERSE=2
ORDERBY_CHRON = ORDERBY_REVERSE

class PennAveWeb:
    def __init__(self):
        self.sql = SQLCache()
        self.photoCache = PhotoCache()
        self.exifTool = exiftools.ExifTool()
        self.childTags = self.buildChildTags()
        self.staticWelcomeLastRead = None
        self.buildStaticWelcome()
        self.root = self
        self.styleCache = {}
        
    def setLastModified(self, mtime=time.time()):
        """sets the last modified header
        """
        strModifTime = cherrypy.lib.http.HTTPDate(mtime)
        cherrypy.response.headers['Last-Modified'] = strModifTime

    def validateSince(self):
        """checks to see if we should send this back or not

        newer versions of CherryPy have this function built in.
        """
        lastmod = cherrypy.response.headers.get('Last-Modified')
        if lastmod:
            since = cherrypy.request.headers.get('If-Modified-Since')
            if since and since == lastmod:
                raise cherrypy.HTTPRedirect([],304)

    def getVersion(self):
        """Simple function that returns the current version of PennAve"""
        return VERSION

    def checkStaticWelcome(self):
        """Checks to see if the static welcome page has been updated since
        the last time it was read in.  If it has been, then this will take
        care of reading in and reparsing the file again.  Basically, we
        do a file stat to ensure that the file is up-to-date.  It's a small
        price to pay I guess.

        returns True if file was reread
                False if not
        """
        fn = cherrypy.config.get("welcomeHtml",None)
        if not fn:
            return False
        if not self.staticWelcomeLastRead:
            self.buildStaticWelcome()
            return True
        if os.stat(cherrypy.config["tools.staticdir.root"] + os.sep + "html" + os.sep + fn).st_mtime > self.staticWelcomeLastRead:
            self.buildStaticWelcome()
            return True
        return False
        
    def buildStaticWelcome(self):
        """Reads in and parses the static welcome file.

        The static welcome is then stored as a string in self.staticWelcome.
        The last updated time is stored in self.staticWelcomeLastRead

        This function is a mess, and will most likely be changed once we give
        PennAve a real templating engine.
        """
        fn = cherrypy.config.get("welcomeHtml",None)
        # if there isn't a default filename, then return nothing
        if not fn:
            self.staticWelcome = None
            return
        fn = cherrypy.config["tools.staticdir.root"] + os.sep + "html" + os.sep + fn
        self.staticWelcomeLastRead = time.time()
        self.staticWelcomeMtime = os.stat(fn).st_mtime
        onLoadString = "";
        canvasCtr = 0;
        divCtr = 0;

        staticWelcome = open(fn).read()

        bodyRe = re.compile(r'<body([^>]*)>')
        
        keyRe = re.compile(r' ([^=]+)="([^"]+)"')   
        r = re.compile("<paImg ([^>/]*)/?>")
        linkRe = re.compile("<paLink([^>/]*)>")
        
        # we can't use finditer here because we're doing some modifications of the string
        while r.search(staticWelcome):
            match = r.search(staticWelcome)
            start, end = match.span()
            keyDict = {}
            killTags = ["type"]
            map(lambda x: keyDict.__setitem__(x[0],x[1]), keyRe.findall(staticWelcome[start:end]))
            if not keyDict.has_key("type"): continue
            replaceString = '<div class="canvasDiv" id="canvasDiv%d"><noscript>' % (divCtr)
            if keyDict["type"].lower() == "thumbnail":
                killTags.append("idNum")
                if not keyDict.has_key("idNum"):
                    cherrypy.log('ERROR: tag calls for thumbnail but none present -- "%s"' % (staticWelcome[start:end]))
                replaceString = replaceString + '<img src="::PREFIX::/images/thumbnail/%s"' % (imgId)
                for key,val in keyDict.iteritems():
                    if key in killTags: continue
                    replaceString = replaceString + ' %s="%s"' % (key, val)
                    killTags.append(key)
                replaceString = replaceString + "/>"
            elif keyDict["type"].lower() == "stacked":
                try:
                    categories = keyDict["categories"].split(",")
                except Exception, e:
                    categories = []
                killTags.append("categories")
                tagIds = []
                for catName in categories:
                    allChildren = False
                    if catName[-1] == "+":
                        allChildren = True
                        catName = catName[:-1]
                    tagId = "%d" % (Tag.byName(catName).id)
                    if allChildren:
                        tagId = tagId + "+"
                    tagIds.append(tagId)
                replaceString = replaceString + '<img src="::PREFIX::/images/stacked/' + "/".join(tagIds) + '"'
                for key,val in keyDict.iteritems():
                    if key in killTags: continue
                    replaceString = replaceString + ' %s="%s"' % (key, val)
                    killTags.append(key)
                replaceString = replaceString + "/>"
                onLoadString = onLoadString + "insertCanvas('canvasDiv%d', %d, '%s');" % (divCtr, divCtr, "/".join(tagIds))
                                
            replaceString = replaceString + "</noscript></div>"
            staticWelcome = staticWelcome[:start] + replaceString + staticWelcome[end:]
            divCtr = divCtr + 1

        # we can't use finditer here because we're doing some modifications of the string
        while linkRe.search(staticWelcome):
            match = linkRe.search(staticWelcome)
            start, end = match.span()
            keyDict = {}
            killTags = ["type"]
            map(lambda x: keyDict.__setitem__(x[0],x[1]), keyRe.findall(staticWelcome[start:end]))
            if not keyDict.has_key("type"):
                cherrypy.log("ERROR: paLink tags need a type tag - " + staticWelcome[start:end])
                continue
            if keyDict["type"] == "browse":
                tagIds = []
                try:
                    categories = keyDict["categories"].split(",")
                except:
                    categories = []
                killTags.append("categories")
                for catName in categories:
                    allChildren = False
                    if catName[-1] == "+":
                        allChildren = True
                        catName = catName[:-1]
                    tagId = "%d" % (Tag.byName(catName).id)
                    if allChildren:
                        tagId = tagId + "+"
                    tagIds.append(tagId)
                    
                href="::PREFIX::/tags/" + "/".join(tagIds)
                if href[-1] != "/": href = href + "/"
                replaceString='<a href="%s"' % href
                for key,val in keyDict.iteritems():
                    if key in killTags: continue
                    replaceString = replaceString + ' %s="%s"' % (key, val)
                    killTags.append(key)
                replaceString = replaceString + ">"
            else:
                cherrypy.log("ERROR: unknown type of paLink node: " + staticWelcome[start:end])
            staticWelcome = staticWelcome[:start] + replaceString + staticWelcome[end:]

        staticWelcome = staticWelcome.replace("</paLink>","</a>",-1)

        # replace the onload
        match = bodyRe.search(staticWelcome)
        if match:
            start, end = match.span()
            keyDict = {}
            map(lambda x: keyDict.__setitem__(x[0],x[1]), keyRe.findall(staticWelcome[start:end]))
            if keyDict.has_key("onLoad"):
                keyDict["onLoad"] = keyDict["onLoad"] + " " + onLoadstring
            else:
                keyDict["onLoad"] = onLoadString
            replaceString = "<body"
            for key,val in keyDict.iteritems():
                replaceString = replaceString + ' %s="%s"' % (key, val)
            replaceString = replaceString + ">"
            staticWelcome = staticWelcome[:start] + replaceString + staticWelcome[end:]
        self.staticWelcome = staticWelcome
        return


    def outputDoc(self, doc, prefix=True, transform=None, imgPrefix = True, contentType = None):
        """Outputs an XML document.  Optionally, depending on the configuration,
        this will also do the stylesheet transformation on the document."""

        if transform == None: transform = cherrypy.config.get("xsltRender")

        rootElement = doc.getRootElement()
        if prefix:
            rootElement.newProp("prefix", codecs.encode(self.getPrefix(), "UTF-8"))
        if imgPrefix:
            prefixes = self.getImgPrefix()
            rootElement.newProp("imgprefixA", codecs.encode(prefixes[0], "UTF-8"))
            rootElement.newProp("imgprefixB", codecs.encode(prefixes[1], "UTF-8"))

        if transform:
            try:
                import libxslt
                tn = doc.children
                stylesheet = None
                while tn != None:
                    if tn.name == "xml-stylesheet":
                        pairs = [(x.split("=")[0], x.split("=")[1][1:-1]) for x in tn.content.split()]
                        for key, val in pairs:
                            if key == "href":
                                stylesheet = cherrypy.config["tools.staticdir.root"] + os.path.sep + cherrypy.config["/xslt"]["tools.staticdir.dir"] + os.path.sep + val.split("/")[-1]
                        break
                    tn = tn.next

                if stylesheet:
                    if self.styleCache.has_key(stylesheet):
                        style = self.styleCache[stylesheet]
                    else:
                        styledoc = libxml2.parseFile(stylesheet)
                        style = libxslt.parseStylesheetDoc(styledoc)
                        self.styleCache[stylesheet] = style
                    result = style.applyStylesheet(doc, {})
                    content = style.saveResultToString(result)
		    if contentType is None:
                        cherrypy.response.headers["Content-Type"] = "text/html"
		    else:
			cherrypy.response.headers["Content-Type"] = contentType
                    result.freeDoc()
                    doc.freeDoc()
                    return content
            except Exception, e:
                cherrypy.log("Error while rendering stylesheet: %s" % (e), severity=logging.WARN, traceback=True)

	if contentType is None:
	    cherrypy.response.headers["Content-Type"] = "text/xml"
	else:
            cherrypy.response.headers["Content-Type"] = contentType
        rv = doc.serialize(format=1)
        doc.freeDoc()
        return rv


    def getPrefix(self):
        if cherrypy.config.get("modpython_prefix", None):
            servername = cherrypy.config.get("modpython_server") 
            prefix = cherrypy.config.get("modpython_prefix")
            if servername[-1] == '/' and prefix[0] == '/': prefix = prefix[1:]
            return servername + prefix

        prefix = cherrypy.request.headers.get("Cp-Location", "")
        host = cherrypy.request.headers.get("X-Forwarded-Host", cherrypy.request.headers.get("Host", None))
        # return "HOST: " + host + "  PREFIX: " + prefix + "MAP: " + "::".join([x[0]+":"+x[1] for x in cherrypy.request.headerMap.items()])
        if host != None and prefix != None:
            return "http://" + host + prefix
        else:
            return ""

    def getImgPrefix(self):
        bucket = cherrypy.config.get("aws_s3_bucket", None)
        path = cherrypy.config.get("aws_s3_path", None)
        
        log = logging.getLogger("pennave.py")
        
        if not (bucket is None) and not (path is None):
            # Für eine bessere Lastverteilung sollte "abwechselnd"
            # http://$BUCKET.s3.amazonaws.com/ und
            # http://s3.amazonaws.com/$BUCKET vom Browser
            # angesprochen werden.
            prefix1 = "http://%s.s3.amazonaws.com/%s" % (bucket, path)
            prefix2 = "http://s3.amazonaws.com/%s/%s" % (bucket, path)
                
            return (prefix1, prefix2)
        else:
            return None

    @cherrypy.expose
    def index(self):
        """Checks if there is a static welcome page, if so return it.
        If no static welcome, redirect right to the tags page."""
        cherrypy.response.headers["Content-Type"] = "text/html; charset=utf-8"
        self.checkStaticWelcome()
        if not self.staticWelcome:
            raise cherrypy.HTTPRedirect(self.getPrefix() + "/tags/")
        self.setLastModified(self.staticWelcomeMtime)
        self.validateSince()
        # in most of the cases the static welcome will have everything replaced
        # before being sent out, however, that is not the case with the prefix
        # which must be calculated from the request
        return self.staticWelcome.replace("::PREFIX::", self.getPrefix())

    def getExifTags(self, filename):
        return self.exifTool.get(filename)
        
    def photoToXml(self, p, parent, tags=True, exif=True, versions=True, currentVersion=1, ns={}):
        """Takes a photo object and creates a set of XML nodes for it"""
        pn = parent.newChild(None, "photo", None)
        if len(p.description.strip()) > 0:
            try:
                pn.newChild(None, "description", codecs.encode(p.description.strip(),'UTF-8'))
            except UnicodeDecodeError:
                pn.newChild(None, "description", p.description.strip())
        pn.newProp("id", codecs.encode(str(p.id), "UTF-8"))
        pn.newProp("date", codecs.encode(str(p.time), "UTF-8"))
        pn.newProp("asctime", codecs.encode(time.asctime(time.localtime(p.time)), "UTF-8"))
        pn.newProp("name", codecs.encode(os.path.split(urlparse.urlparse(p.uri)[2])[1], "UTF-8"))
        if versions: pn.newProp("version", codecs.encode(str(currentVersion),"UTF-8"))
        try:
            size = self.photoCache.get(p).size
            pn.newProp("width", codecs.encode(str(size[0]), "UTF-8"))
            pn.newProp("height", codecs.encode(str(size[1]), "UTF-8"))
        except:
            pass
        
        if tags:
            tagNode = pn.newChild(None, "tags", None)
            for tag in [x for x in p.tags if x.id not in cherrypy.config.get("requiredTagIds", [])]:
                self.tagToXml(tag, tagNode)
        # if EXIF tags are selected, we attempt to have the output conform to the RDF syntax for EXIF tags
        # http://www.w3.org/2003/12/exif/
        if exif:
            try:
                #exifTags = self.getExifTags(self.getFilename(p))
                exifTags = self.exifTool.getS3(pictureId = p.id, versionId = currentVersion)
                #exifTags = self.exifTool.getLocal(pictureId = p.id, versionId = currentVersion)
            except Exception, e:
                cherrypy.log("Exif error: %s" % (e), severity=logging.WARN, traceback=True)
                exifTags = {}
            if len(exifTags):
                en = pn.newChild(ns.get("exif", None), "IFD", None)
                for key, val in exifTags.iteritems():
                    thisTag = en.newChild(ns.get("exif", None), key, codecs.encode(val,'UTF-8'))
        
        # handle encoding of different versions of photos
        if versions:
            vers = p.getVersions(cache=self.sql)
            if vers:
                vn = pn.newChild(None,"versions",None)
                cvn = vn.newChild(None, "version", None)
                cvn.newProp("id", codecs.encode(str(1),"UTF-8"))
                cvn.newProp("name", codecs.encode(str("Original"), "UTF-8"))
                if p.defaultVersionId == 1: cvn.newProp("default","true")
                if currentVersion == 1: cvn.newProp("shown","true")
                for v in vers.itervalues():
                    cvn = vn.newChild(None, "version", None)
                    cvn.newProp("id", str(v.id))
                    try:
                        cvn.newProp("name", str(v.name))
                    except UnicodeEncodeError:
                        cvn.newProp("name", str(codecs.encode(v.name, 'utf-8')))
                    if currentVersion == v.id: cvn.newProp("shown", "true")
                    if p.defaultVersionId == v.id: cvn.newProp("default", "true")
        return pn


    def tagToXml(self, t, parent):
        tn = parent.newChild(None, "tag", codecs.encode(t.name, "UTF-8"))
        tn.newProp("id", codecs.encode(str(t.id), "UTF-8"))
        return tn


    def validateAccess(self, photo):
        """Validates whether or not a given photo has the proper tags to be
        viewed on the web."""
        query = "select tag_id from photo_tags where photo_id=%d" % (photo.id)
        s1 = Set([x[0] for x in self.sql.execute(query)])
        s2 = Set(cherrypy.config["requiredTagIds"])
        if s1.union(s2) != s1:
            raise Exception("That photograph does not have the proper tags to be viewed from this interface")
       
    def newDoc(self, rootTag):
        """Simple helper function to create a new XML document with a root node
        while setting the XML namespaces as required.

        This function returns three values.  A new XML document, a dictionary of
        namespace mappings, and a pointer to the root element.
        
        @param rootTag: the root tag to set in the new XML document
        """
        doc = libxml2.newDoc("1.0")
        ns = {}
        root = doc.newChild(None, rootTag, None)
        pi = libxml2.newPI("xml-stylesheet", 'type="text/xsl" href="%s/xslt/pennave.xsl"' % (self.getPrefix()))
        root.addPrevSibling(pi)
        ns["pennave"] = root.newNs("http://patrick.wagstrom.net/projects/pennave/1", None)
        ns["exif"] = root.newNs("http://www.w3.org/2003/12/exif/ns", "exif")
        ns["rdf"] = root.newNs("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf")
        root.setNs(ns["pennave"])
        return doc, ns, root

    @cherrypy.expose
    def view(self, *args):
        pid = int(args[0])
        args = [x.lower() for x in args]
        tags = []
        if "tags" in args:
            ctr = args.index("tags")
            while True:
                ctr += 1
                try:
                    tags.append(int(args[ctr]))
                except:
                    break
        tags.sort()
        tags = [x for x in self.addRequiredTags(tags) if x in cherrypy.config["validTagIds"]]
    
        
        p = Photo.get(int(pid))
        try:
            self.validateAccess(p)
        except:
            return "That photograph does not have the proper tags to be viewed from this interface"

        # set the version of the image
        try: version = int(args[args.index("version")+1])
        except: version = p.defaultVersionId

        doc, ns, root = self.newDoc("photoView")

        # set some properties telling the size of the thumbnails and what not
        root.newProp("thumbnailWidth", codecs.encode(str(cherrypy.config.get("thumbnailPhotoSize",(120,80))[0]),"UTF-8"))
        root.newProp("thumbnailHeight", codecs.encode(str(cherrypy.config.get("thumbnailPhotoSize",(120,80))[1]),"UTF-8"))
        root.newProp("displayWidth", codecs.encode(str(cherrypy.config.get("mediumPhotoSize",(640,480))[0]),"UTF-8"))
        root.newProp("displayHeight", codecs.encode(str(cherrypy.config.get("meidumPhotoSize",(640,480))[1]),"UTF-8"))

        rootTags = root.newChild(None, "rootTags", None)
        # FIXME: put this in a subroutine
        for tagId in [x for x in tags if x not in cherrypy.config["requiredTagIds"]]:
            t = Tag.get(int(tagId))
            nc = rootTags.newChild(None, "tag", codecs.encode(t.name,'UTF-8'))
            nc.newProp("id", codecs.encode(str(t.id), "UTF-8"))

        pn = self.photoToXml(p, root, tags=False, exif=True, versions=True, currentVersion=version, ns=ns)

        # FIXME: perhaps this modified version should somehow be rolled into photoToXml
        # this modified version adds in counts to each of the tags for home many photos have
        # each tag and the size they should be
        tagsNode = pn.newChild(None, "tags", None)
        query = "select a.tag_id from photo_tags a, tags b where b.id = a.tag_id and a.photo_id=%d order by b.name" % (p.id)
        tagIds = [x[0] for x in self.sql.execute(query) if x[0] not in tags and x[0] not in cherrypy.config["hiddenTagIds"]]
        tagInfos = self.getTags(tags)
        tagCounts = {}
        for tagInfo in tagInfos:
            tagCounts[tagInfo.id] = tagInfo.numPhotos

        maxTagged = math.log(max(tagCounts.values() + [1])) + 1
        for tagId in tagIds:
            try:
                t = Tag.get(tagId)
                tn = self.tagToXml(t, tagsNode)
                tn.newProp("count", codecs.encode(str(tagCounts[tagId]), "UTF-8"))
                size = int((math.log(tagCounts[tagId])/maxTagged)*TAG_LEVELS)+1
                tn.newProp("size", codecs.encode(str(size), "UTF-8"))
            except:
                cherrypy.log("Hidden Tags: %s" % (cherrypy.config["hiddenTagIds"]))
                cherrypy.log("Error in rendering tag: %s" % (t.name), severity=logging.ERROR, traceback=True)

        # get the set of photo id's for the next and previous images in this set
        appendStr1 = ""
        appendStr2 = ""
        ctr = 0
        for tagId in tags:
            appendStr1 += ", photo_tags %s" % (self.generateTableRef(ctr))
            appendStr2 += " and %s.tag_id = %d and %s.photo_id = a.id" % (self.generateTableRef(ctr), tagId,
                                                                               self.generateTableRef(ctr))
            ctr = ctr + 1
        if cherrypy.session.get("order") == ORDERBY_REVERSE:
            orderBy = "a.time"
        else:
            orderBy = "a.time desc"
        query = "select distinct(a.id) from photos a, photo_tags b, tags c %s \
                 where a.id = b.photo_id and b.tag_id != c.id and c.name = 'Hidden' %s order by %s" % (appendStr1, appendStr2, orderBy)
        res = [x[0] for x in self.sql.execute(query)]
        i = res.index(pid)
        if i != 0:
            # get the previous
            pp = Photo.get(res[i-1])
            prevPhoto = root.newChild(None, "previousPhoto", None)
            self.photoToXml(pp, prevPhoto, versions=False, ns=ns)
        if i != len(res)-1:
            # get the next
            np = Photo.get(res[i+1])
            nextPhoto = root.newChild(None, "nextPhoto", None)
            self.photoToXml(np, nextPhoto, versions=False, ns=ns)
            
        
        return self.outputDoc(doc)
        
    def generateTableRef(self, count):
        """This is used as a helper function when generate SQL statements"""
        if count < 23:
            return chr(ord('d')+count)
        else:
            count = count + 3
            fc = chr(ord('a') + int(count/26) - 1)
            sc = chr(ord('a') + count%26)
            return fc+sc

    def getPhotos(self, tags, orTags=None, orderBy=None, extraFields=None):
        """Returns a list of photo ids for a given set of tags"""
        appendStr1 = ""
        appendStr2 = ""
        hiddenQuery = ""
        if orderBy == None:
            orderBy = cherrypy.session.get("order")

        # yup, ORDERBY_REVERSE actually does it in chronological order
        # that's why you can also use ORDERBY_CHRON
        if orderBy == ORDERBY_REVERSE:
            orderBy = "a.time"
        if orderBy == None or orderBy == ORDERBY_NORMAL:
            orderBy = "a.time desc"
            
        ctr = 0
        for tagId in tags:
            appendStr1 += ", photo_tags %s" % (self.generateTableRef(ctr))
            appendStr2 += " and %s.tag_id = %d and %s.photo_id = a.id" % (self.generateTableRef(ctr), tagId,
                                                                               self.generateTableRef(ctr))
            ctr = ctr + 1
        # now iterate over all the sets of orTags
        for tagSet in orTags:
            tableRef = self.generateTableRef(ctr)
            ctr  = ctr + 1
            joinTags = []
            appendStr1 += ", photo_tags %s" % (tableRef)
            appendStr2 += " and %s.photo_id = a.id and ( " % (tableRef)
            for tagId in tagSet:
                joinTags.append("%s.tag_id = %d" % (tableRef, tagId))
            appendStr2 += " or ".join(joinTags) + ")"

        # work out issues with extra fields
        if not extraFields:
            extraFields = ""
        elif extraFields.__class__ == str:
            extraFields = ", " + extraFields
        else:
            extraFields = ", " + ",".join(str(x) for x in extraFields)
            
        # build the subquery for all of the hidden strings
        hiddenStr = " or ".join(["tag_id=%d" % x for x in cherrypy.config.get("hiddenTagIds")])
        if hiddenStr:
            hiddenQuery = "and a.id not in (select distinct photo_id from photo_tags where %s)" % (hiddenStr)
        query = "select distinct(a.id) %s from photos a, photo_tags b %s \
                 where a.id = b.photo_id %s %s order by %s" % (extraFields, appendStr1, hiddenQuery, appendStr2, orderBy)
        # startTime = time.time()
        if not extraFields:
            res = [x[0] for x in self.sql.execute(query)]
            return res
        else:
            # print query
            return self.sql.execute(query)

    def getTags(self, tags, orTags=None, parents=None):
        """
        This function still needs to figure out something to do with the orTags...
        """
        appendStr1 = ""
        appendStr2 = ""
        hiddenQuery = ""

        ctr = 0
        for tagId in tags:
            appendStr1 += ", photo_tags %s" % (self.generateTableRef(ctr))
            appendStr2 += " and %s.tag_id=%d and %s.photo_id = a.photo_id and a.tag_id != %d" % (self.generateTableRef(ctr), int(tagId),
                                                                                                 self.generateTableRef(ctr), int(tagId))
            ctr = ctr + 1

        # build the subquery for all of the hidden strings
        hiddenStr = " and ".join(["b.id != %d" % x for x in cherrypy.config.get("hiddenTagIds",[])])
        if hiddenStr:
            hiddenQuery = " and " + hiddenStr
        query = "select a.tag_id, b.name, b.category_id, count(*) from photo_tags a, tags b %s where b.id = a.tag_id %s %s group by a.tag_id" % (appendStr1, hiddenQuery, appendStr2)
        # startTime = time.time()
        res = self.sql.execute(query)
        return [TagRepr(id=x[0], name=x[1], categoryId=x[2], numPhotos=x[3]) for x in res]

    def addRequiredTags(self, tags):
        s1 = Set(tags)
        s2 = Set(cherrypy.config.get("requiredTagIds",[]))
        return list(s1.union(s2))

    def processTags(self, args):
        andTags = [int(x) for x in args if not x[-1] == "+"]
        orTags = []
        for x in [y for y in args if y[-1] == "+"]:
            orTags.append([int(x[:-1])] + self.childTags[int(x[:-1])])
        andTags = self.addRequiredTags(andTags)
        andTags = [x for x in andTags if x in cherrypy.config["validTagIds"]]
        orTags = [x for x in orTags if x in cherrypy.config["validTagIds"]]
        return andTags, orTags
    
    def processHookArgs(self, root, args, ns):
        """
        Takes the arguments that are passed on the hook and encodes them in the XML so
        we can avoid some more of the superfluous and unnecessary javascript
        
        @param root: root element to append the hookArgs tag to
        @param args: a dict containing key-value pairs
        @param ns: the namespaces to examine
        """
        hookArgs = root.newChild(None, "hookArgs", None)
        for key,value in args.iteritems():
            thisElem = hookArgs.newChild(None, "arg", None)
            thisElem.newProp("name", codecs.encode(key, 'UTF-8'))
            thisElem.newProp("value", codecs.encode(value, 'UTF-8'))
        return hookArgs
    
    @cherrypy.expose
    def tags(self, *args, **kwargs):
        andTags, orTags = self.processTags(args)

        # v0.4
        # NOTE: this is a compatability breaker...
        # now we start counting at 1
        startPhoto = max(int(kwargs.get("start", 0))-1,0)
        numPhotosPerPage = int(kwargs.get("perPage", cherrypy.config.get("photosPerPage", 24)))
        stopPhoto = startPhoto + numPhotosPerPage

        res = self.getTags(andTags, orTags)

        doc, ns, root = self.newDoc("tagBrowse")
        self.processHookArgs(root, kwargs, ns=ns)
        
        rootTags = root.newChild(None, "rootTags", None)
        # FIXME: put this in a subroutine
        for tagId in [x for x in andTags if x not in cherrypy.config["requiredTagIds"]]:            
            t = Tag.get(int(tagId))
            nc = rootTags.newChild(None, "tag", codecs.encode(t.name,'UTF-8'))
            nc.newProp("id", codecs.encode(str(t.id), "UTF-8"))
        photoTags = root.newChild(None, "photos", None)
        photoIds = self.getPhotos(andTags, orTags)
        photoTags.newProp("startPhoto", codecs.encode(str(startPhoto+1), "UTF-8"))
        stopPhoto = min(stopPhoto, len(photoIds))
        photoTags.newProp("stopPhoto", codecs.encode(str(stopPhoto), "UTF-8"))
        photoTags.newProp("numPhotos", codecs.encode(str(len(photoIds)), "UTF-8"))
        photoTags.newProp("perPage", codecs.encode(str(numPhotosPerPage), "UTF-8"))
        # FIXME: this probably is not the most robust way to encode these values
        photoTags.newProp("thumbnailWidth", codecs.encode(str(cherrypy.config.get("thumbnailPhotoSize",(120,80))[0]),"UTF-8"))
        photoTags.newProp("thumbnailHeight", codecs.encode(str(cherrypy.config.get("thumbnailPhotoSize",(120,80))[1]),"UTF-8"))
        
        for pid in photoIds[startPhoto:stopPhoto]:
            p = Photo.get(pid)
            self.photoToXml(p, photoTags, ns=ns, exif=False)

        maxTagged = math.log(max([thisTag.numPhotos for thisTag in res] + [1])) + 1

        # this builds the ranking of the tags
        res.sort(key=lambda x: x.numPhotos)
        res.reverse()
        ranking = {}
        for t in xrange(0,len(res)):
            ranking[res[t].id] = t

        # create a tagcloud node
        tagCloud = root.newChild(None, "tagCloud", None)
        
        # this reorders the ranking of the tags
        res.sort(key=lambda x: x.name)
        for thisTag in res:
            try:
                tt = self.serializeTag(Tag.get(thisTag.id), tagCloud);
                tt.newProp("count", codecs.encode(str(thisTag.numPhotos), "UTF-8"))
                size = int((math.log(thisTag.numPhotos)/maxTagged)*TAG_LEVELS)+1
                tt.newProp("size", codecs.encode(str(size), "UTF-8"))
                tt.newProp("rank", codecs.encode(str(ranking[thisTag.id]), "UTF-8"))
            except Exception, e:
                cherrypy.log("Unable to render tag \"%s\": %s" % (thisTag.name, e), severity=logging.WARN, traceback=True)
        return self.outputDoc(doc)

    @cherrypy.expose
    def timeline(self, *args, **kwargs):
        """Produces a timeline of the sets of tags.  Right now this takes the
        same arguments as tags."""
        andTags, orTags = self.processTags(args)
        vals = self.getPhotos(andTags, orTags, extraFields="a.time", orderBy=ORDERBY_CHRON)
        timelineDict = {}
        for x in xrange(0,len(vals)):
            objDate = apply(datetime.datetime,time.localtime(vals[x][1])[:6])
            key = "%04d-%02d" % (objDate.year, objDate.month)
            timelineDict[key] = timelineDict.get(key,0) + 1
            
            
        return str(timelineDict)
        
    def serializeTag(self, tag, parent):
        tt = parent.newChild(None, "tag", codecs.encode(tag.name,'UTF-8'))
        tt.newProp("id", codecs.encode(str(tag.id), "UTF-8"))
        tt.newProp("parent", codecs.encode(str(tag.categoryId), "UTF-8"))
        if len(tag.children):
            tt.newProp("hasChildren", codecs.encode("1","UTF-8"))
        else:
            tt.newProp("hasChildren", codecs.encode("0", "UTF-8"))
        return tt

    def getFilename(self, p, version=None):
        filename = getFilename(p, version=version, cache=self.sql)
        # Files are *ALL* stored on S3 -> No STATing possible.
        return urlparse.urlparse(filename)[2]
        # Check if the system is able to stat the file.
        # If we get a UnicodeEncodeError, we'll return the
        # UTF-8 encoded version of the filename. Else, ie.
        # if everything is fine, we'll return the "plain"
        # version of the filename.
        # try:
           # os.stat(filename).st_mtime
           # return filename
        # except UnicodeEncodeError:
           # return filename.encode("utf-8")
    
    def buildChildTags(self):
        """Does a cache of all the child tags.  Useful for group selects"""
        query = "SELECT id, category_id FROM tags"
        res = self.sql.execute(query)
        tagParents = {}
        childTags = {}
        for tag,cat in res:
            tagParents[tag] = cat
            childTags[tag] = []
        for key in tagParents.iterkeys():
            tempKey = key
            while tagParents.has_key(tagParents[tempKey]):
                childTags[tagParents[tempKey]].append(key)
                tempKey = tagParents[tempKey]
        return childTags

    @cherrypy.expose
    def getRandomPhotos(self, *args, **kwargs):
        """This is an ajaxy sorta function, I'm not 100% sure if it belongs
        here or not."""
        import random
        numPhotos = cherrypy.config.get('numRandomPhotos',3)
        tags, orTags = self.processTags(args)
        res = self.getPhotos(tags, orTags)
        random.shuffle(res)
        rv = []
        for x in res[0:numPhotos]:
            rv.append(self.getPrefix() + "/images/thumbnail/%d" % x)
        return "\n".join(rv)

    @cherrypy.expose
    def setOrder(self, order=None, returnPage=None):
        """Sets the order of the photos to be used

        order is an integer value to use for the ordering"""
        if order==None:
            if cherrypy.session.get("order") == ORDERBY_REVERSE:
                cherrypy.session['order'] = ORDERBY_NORMAL
            else:
                cherrypy.session['order'] = ORDERBY_REVERSE
        elif order==ORDERBY_REVERSE:
            cherrpy.sesion['order'] = ORDERBY_REVERSE
        else:
            cherrpy.sesion['order'] = ORDERBY_NORMAL
        if returnPage:
            raise cherrypy.HTTPRedirect(returnPage)
        elif cherrypy.request.headers.get('referer'):
            raise cherrypy.HTTPRedirect(cherrypy.request.headers.get('referer'))

class PhotoCache:
    """This caches some information about photos"""
    def __init__(self):
        self.cache = {}

    def get(self, photo):
        """Gets information for a photo"""
        if self.cache.has_key(photo.id):
            return self.cache[photo.id]
        else:
            self.cache[photo.id] = PhotoCacheItem(photo)
            return self.cache[photo.id]
        
import Image
class PhotoCacheItem:
    """This is the cache for a single photo"""
    def __init__(self, photo):
        image = Image.open(getFilename(photo))
        self.size = image.size
        del image
    
    
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

def getFilename(p, version=None, cache=None):
    fn = p.getFilename(forceOriginal=cherrypy.config.get("defaultImage", True), version=version, cache=cache)
    if cherrypy.config.has_key("filenameRewrite"):
        fn = fn.replace(cherrypy.config["filenameRewrite"][0],
                        cherrypy.config["filenameRewrite"][1])
    return fn

def connectWrapper(threadIndex):
    """ Function to create a connection at the start of the thread """
    global databaseUri, databaseDebug
    cherrypy.log("invoking connection for thread %d" % (threadIndex), "CONNECTWRAPPER")
    conn.threadConnection = connect(databaseUri, databaseDebug, cache=None, process=False)

def start(config=None, dburi=None, dbdebug=False, mod_python=False):
    global databaseUri, databaseDebug, conn
    if config: cherrypy.config.update(config)
    if mod_python: prefix = cherrypy.config["modpython_prefix"]
    else: prefix = ""

    gbs = cherrypy.config
    if not gbs.has_key("thumbnailPath"):
        gbs["thumbnailPath"] = gbs["scaledPath"] + os.sep + "thumbs"
    if not gbs.has_key("mediumPath"):
        gbs["mediumPath"] = gbs["scaledPath"] + os.sep + "medium"
    if not gbs.has_key("tinyPath"):
        gbs["tinyPath"] = gbs["scaledPath"] + os.sep + "tiny"
    if not gbs.has_key("stackedPath"):
        gbs["stackedPath"] = gbs["scaledPath"] + os.sep + "stacked"
    for d in gbs["scaledPath"], gbs["thumbnailPath"], gbs["mediumPath"], gbs["tinyPath"], gbs["stackedPath"]:
        if not os.path.isdir(d):
            os.makedirs(d)

    # this next line is a hack to give us early access to the database
    if gbs.has_key("dblocation"):
        dburi = "sqlite://" + gbs.get("dblocation")
        from pysqlite2 import dbapi2 as sqlite

    if mod_python:
        conn = connect(dburi, debug=dbdebug, cache=None, process=False)
        setConnection(conn)
    else:
        conn.threadConnection = connect(dburi, debug=dbdebug, cache=None, process=False)
    databaseDebug = dbdebug
    databaseUri = dburi

    gbs["requiredTagIds"] = []
    if gbs.has_key("requiredTags"):
        for t in gbs["requiredTags"]:
            try:
                gbs["requiredTagIds"].append(Tag.byName(t).id)
            except:
                cherrypy.log("***** unable to force required tag: %s" % (t), severity=logging.ERROR, traceback=True)


    gbs["hiddenTagIds"] = []
    if gbs.has_key("hiddenTags"):
        for t in gbs["hiddenTags"]:
            try:
                gbs["hiddenTagIds"].append(Tag.byName(t).id)
            except:
                cherrypy.log("***** unable to force required hidden tag: %s" % (t), severity=logging.ERROR, traceback=True)

    # create the root instance
    root = PennAveWeb()

    # establish what tags are viewable through the interface
    hiddenQuery = ""
    appendStr1 = ""
    appendStr2 = ""
    ctr = 0
    for tagId in gbs["requiredTagIds"]:
        appendStr1 += ", photo_tags %s" % (root.generateTableRef(ctr))
        appendStr2 += " and %s.tag_id = %d and %s.photo_id = a.id" % (root.generateTableRef(ctr), tagId,
                                                                      root.generateTableRef(ctr))
        ctr = ctr + 1
    hiddenStr = " or ".join(["tag_id=%d" % x for x in cherrypy.config.get("hiddenTagIds")])
    if hiddenStr:
        hiddenQuery = "and a.id not in (select distinct photo_id from photo_tags where %s)" % (hiddenStr)
    query = """SELECT DISTINCT tag_id FROM photo_tags WHERE photo_id in \
                      (SELECT distinct(a.id) from photos a, photo_tags b %s \
                      where a.id = b.photo_id %s %s)""" % (appendStr1, hiddenQuery, appendStr2)
    res = [x[0] for x in root.sql.execute(query)]
    validTags = {}
    for nextTag in res:
        while nextTag != None and nextTag != 0:
            if validTags.has_key(nextTag): break
            validTags[nextTag] = 1
            nextTag = Tag.get(nextTag).categoryId
    gbs["validTagIds"] = validTags.keys()

    if not mod_python:
        # Tell cherrypy to run the connect() function when creating threads
        cherrypy.engine.on_start_thread_list.append(connectWrapper)

    # setup the entire CherryPy tree
    cherrypy.tree.mount(images.PennAveImages(root), prefix + "/images", config={'':''})
    cherrypy.tree.mount(slides.PennAveSlides(root), prefix + "/slides", config={'':''})
    cherrypy.tree.mount(feeds.PennAveFeeds(root), prefix + "/feeds", config={'':''})
    rootConfig = {}
    for x in ['xslt', 'css', 'js']:
        rootConfig["/"+x] = {'tools.staticdir.on' : True, 'tools.staticdir.dir' : x, 'tools.staticdir.root':gbs['tools.staticdir.root']}

    if mod_python:
        cherrypy.engine.SIGHUP = None
        cherrypy.engine.SIGTERM = None
        cherrypy.tree.mount(root, prefix, config=rootConfig)
        cherrypy.engine.start(blocking=False)
    else:
        cherrypy.quickstart(root, config=rootConfig)

def start_modpython():
    """Specialized start routine for mod_python servers"""
    cherrypy.config.update({
        'log.screen': False,
        'log.error_file': '/tmp/cpdeploy.log',
        'environment': 'production',
        'request.show_tracebacks': False,
        # Turn off signal handlers when CP does not control the OS process
        'engine.SIGTERM': None,
        'engine.SIGHUP': None,
        })
    cherrypy.log("starting mod_python server instance")
    start(mod_python=True)

logging.basicConfig()
log = logging.getLogger("pennave.py")
log.setLevel(logging.INFO)

if __name__ == "__main__":
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
                      action="store", default="default.conf")

    log.debug("parsing command line arguments")
    (options, args) = parser.parse_args()

    if options.debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(getattr(logging,options.loglevel.upper()))

    conn = dbconnection.ConnectionHub()
    setConnection(conn)
    start(config=options.configuration, dburi=options.uri, dbdebug=options.debug)
