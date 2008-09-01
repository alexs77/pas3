#===============================================================================
# vim: set fileencoding=utf-8
# 
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

import libxml2
import cherrypy
from dbobjects import *
import time
import codecs
import urllib
import os.path

# Debug
import logging

class PennAveFeeds:
    """The feeds module of pennave provides the ability to create a photo
    stream or a small sidebar of the latest photos, like what Flickr allows
    one to do."""
    
    def __init__(self, root):
        self.root = root

    @cherrypy.expose
    def rss(self, *args, **kwargs):
        tags, orTags = self.root.processTags(args)
        res = self.root.getPhotos(tags, orTags)
        doc = libxml2.newDoc("1.0")
        ns = {}
        root = doc.newChild(None, "rss", None)
        root.newProp("version",codecs.encode("2.0", "UTF-8"))
        title = cherrypy.config.get("feedTitle","F-Spot Photo Stream")
        tmpTags = [x for x in tags if x not in cherrypy.config["requiredTagIds"] and x in cherrypy.config["validTagIds"]]
        if tmpTags:
            title = title + " (tags: " + ",".join(Tag.get(ti).name for ti in tmpTags) + ")"
            
        # create the channel properties
        channel = root.newChild(None,"channel", None)
        aboutURL = self.root.getPrefix() + "/feeds/rss/%s" % ("/".join(["%d" % x for x in tags]))
        channel.newChild(None, "title", codecs.encode(title,'UTF-8'))
        channel.newChild(None, "generator", codecs.encode("PennAve %s" % (self.root.getVersion()), "UTF-8"))
        tagURL = self.root.getPrefix() + "/tags/%s" % ("/".join(["%d" % x for x in tags]))
        channel.newChild(None, "link", codecs.encode(tagURL,"UTF-8"))
        channel.newChild(None, "description", codecs.encode(cherrypy.config.get("feedDescription", ""),"UTF-8"))

        # iterate over each of the images
        for pid in res[:15]:
            pitem = channel.newChild(None,"item", None)
            linkURL = self.root.getPrefix() + "/view/%d/tags/%s" % (pid, "/".join(["%d" % x for x in tags]))
            viewLink = self.root.getPrefix() + "/images/medium/%d" % (pid)
            guid = pitem.newChild(None, "guid", codecs.encode(linkURL, "UTF-8"))
            p = Photo.get(pid)
            # Gab es früher irgendwann mal eine Spalte "name" in der Photos Tabelle?
            #pitem.newChild(None, "title", codecs.encode(p.name, "UTF-8"))

            # Extract the picture name from URI (p.uri).
            # To do that, cut away all "directories" and
            # the extension.
            # The will serve as the title.
            # Eg.
            # file:///home/askwar/Desktop/My Pictures/Photos/Kategorien/Ausflüge/Wild- und Freizeitpark Allensbach/2008-08-03/[2008-08-02--14.39.04] (cimg5700) Alexander%2C Cassandra%2C Cédric%2C Füttern Ziegen%2C Allensbach%2C Wild- und Freizeitpark - Allensbach%2C {2.6 MB}.jpg
            title = p.uri
            # split title on all the "/". We only care about everything after
            # the last "/" (ie. everything starting from [2008...])
            title = title.split("/")[-1]
            # ie.:
            # title = "[2008-08-02--14.39.04] (cimg5700) Alexander%2C Cassandra%2C Cédric%2C Füttern Ziegen%2C Allensbach%2C Wild- und Freizeitpark - Allensbach%2C {2.6 MB}.jpg"
            # Dump the extension. To do that, split on ".", but from reverse
            # and only return 2 parts. We then only care about the 1st part
            # from the beginning
            # >>> s.split("/")[-1].rsplit(".", 1)
            # ['[2008-08-02--14.39.04] (cimg5700) Alexander%2C Cassandra%2C C\xc3\xa9dric%2C F\xc3\xbcttern Ziegen%2C Allensbach%2C Wild- und Freizeitpark - Allensbach%2C {2.6 MB}', 'jpg']
            title = title.rsplit(".", 1)[0]
            # F-Spot stores the URI "quoted"; this meanst instead of ",", there
            # will be %2C.
            title = urllib.unquote_plus(title)
            # For safety, code the whole lot in UTF-8
            title_u8 = codecs.encode(title, "UTF-8")
            # And finally use this as the title.
            pitem.newChild(None, "title", title_u8)

            descriptionText='<img src="%s"/><br/>%s' % (viewLink, p.description)

    	    try:
                description = pitem.newChild(None,"description", codecs.encode(descriptionText, "UTF-8"))
    	    except UnicodeDecodeError:
                description = pitem.newChild(None,"description", descriptionText)

            link = pitem.newChild(None,"link", codecs.encode(linkURL, "UTF-8"))
            pubDate = pitem.newChild(None, "pubDate", codecs.encode(time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime(p.time)), "UTF-8"))

            for tag in p.tags:
                pitem.newChild(None,"category", codecs.encode(tag.name, "UTF-8"))
        return self.root.outputDoc(doc, prefix=False, contentType="application/rss+xml; charset=utf-8")

    @cherrypy.expose
    def block(self, *args, **kwargs):
        # res = self.root.getPhotos(self.root.processTags(args))
        pass
