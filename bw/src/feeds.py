# vim: set fileencoding=utf-8 :

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
	# Debug
	log = logging.getLogger("pennave.py")

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
	    log.info(str(pid) + ": iterate in RSS, tags: %s" % ("/".join(["%d" % x for x in tags])))
	    log.info(str(pid) + ": URLs -> link: “%s”, view: “%s”; guid: “%s”" % (linkURL, viewLink, guid))
            p = Photo.get(pid)
	    log.info(str(pid) + ": p -> “%s”" % (p))
	    # Gab es früher irgendwann mal eine Spalte "name" in der Photos Tabelle?
            #pitem.newChild(None, "title", codecs.encode(p.name, "UTF-8"))

	    # Extrahiere aus der URI (in p.uri) den Namen
	    # des Bildes; dh. alle "Verzeichnisse" abschneiden
	    # und Extension ebenfalls wegwerfen
	    # Das ganze wird dann als title verwendet
	    # uri holen.
	    # Bsp.:
	    # file:///home/askwar/Desktop/My Pictures/Photos/Kategorien/Ausflüge/Wild- und Freizeitpark Allensbach/2008-08-03/[2008-08-02--14.39.04] (cimg5700) Alexander%2C Cassandra%2C Cédric%2C Füttern Ziegen%2C Allensbach%2C Wild- und Freizeitpark - Allensbach%2C {2.6 MB}.jpg
	    title = p.uri
	    # title an "/" aufteilen. Interessant ist nur der letzte Teil, also ab [2008...
	    title = title.split("/")[-1]
	    # title = "[2008-08-02--14.39.04] (cimg5700) Alexander%2C Cassandra%2C Cédric%2C Füttern Ziegen%2C Allensbach%2C Wild- und Freizeitpark - Allensbach%2C {2.6 MB}.jpg"
	    # Extension wegschmeißen. Dazu an "." splitten, aber von hinten und 
	    # max. 2 Teile zurückliefern. Interessant ist dann der erste Teil (von vorne)
	    # 
	    # >>> s.split("/")[-1].rsplit(".", 1)
            # ['[2008-08-02--14.39.04] (cimg5700) Alexander%2C Cassandra%2C C\xc3\xa9dric%2C F\xc3\xbcttern Ziegen%2C Allensbach%2C Wild- und Freizeitpark - Allensbach%2C {2.6 MB}', 'jpg']
	    title = title.rsplit(".", 1)[0]
	    # F-Spot speichert die URI gequoted, dh. statt "," wird %2C gespeichert.
	    title = urllib.unquote_plus(title)
	    # Und nun das ganze noch in UTF-8 kodieren
	    title_u8 = codecs.encode(title, "UTF-8")
	    # Und jetzt den Title setzen
	    pitem.newChild(None, "title", title_u8)

            descriptionText='<img src="%s"/><br/>%s' % (viewLink, p.description)

	    log.info(str(pid) + ": descriptionText -> “%s”" % (descriptionText))

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
