import libxml2
import cherrypy
from dbobjects import *
import time
import codecs

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
        channel.newChild(None, "title",
                         codecs.encode(title,'UTF-8'))
        channel.newChild(None, "generator", codecs.encode("PennAve %s" % (self.root.getVersion()), "UTF-8"))
        tagURL = self.root.getPrefix() + "/tags/%s" % ("/".join(["%d" % x for x in tags]))
        channel.newChild(None, "link", codecs.encode(tagURL,"UTF-8"))
        channel.newChild(None, "description",
                         codecs.encode(cherrypy.config.get("feedDescription", ""),"UTF-8"))


        # iterate over each of the images
        for pid in res[:15]:
            pitem = channel.newChild(None,"item", None)
            linkURL = self.root.getPrefix() + "/view/%d/tags/%s" % (pid, "/".join(["%d" % x for x in tags]))
            viewLink = self.root.getPrefix() + "/images/medium/%d" % (pid)
            guid = pitem.newChild(None, "guid", codecs.encode(linkURL, "UTF-8"))
            p = Photo.get(pid)
            pitem.newChild(None,"title", codecs.encode(p.name, "UTF-8"))
            descriptionText='<img src="%s"/><br/>%s' % (viewLink, p.description)
            description = pitem.newChild(None,"description", codecs.encode(descriptionText, "UTF-8"))
            link = pitem.newChild(None,"link", codecs.encode(linkURL, "UTF-8"))
            pubDate = pitem.newChild(None, "pubDate", codecs.encode(time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime(p.time)), "UTF-8"))

            for tag in p.tags:
                pitem.newChild(None,"category", codecs.encode(tag.name, "UTF-8"))
        return self.root.outputDoc(doc, prefix=False)

    @cherrypy.expose
    def block(self, *args, **kwargs):
        # res = self.root.getPhotos(self.root.processTags(args))
        pass
