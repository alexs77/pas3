# vim: set fileencoding=utf-8

# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$

import random
from dbobjects import *
import libxml2
import cherrypy
import codecs

class PennAveSlides:
    def __init__(self, root):
        self.root = root
        
    @cherrypy.expose
    def index(self, *args, **kwargs):
        tags, orTags = self.root.processTags(args)
        doc = libxml2.newDoc("1.0")
        root = doc.newChild(None, "slideshow", None)
        pi = libxml2.newPI("xml-stylesheet", 'type="text/xsl" href="%s/xslt/slides.xsl"' % (self.root.getPrefix()))
        root.addPrevSibling(pi)

        rootTags = root.newChild(None, "rootTags", None)
        for tagId in tags:
            t = Tag.get(int(tagId))
            nc = rootTags.newChild(None, "tag", codecs.encode(t.name, "UTF-8"))
            nc.newProp("id", codecs.encode(str(t.id), "UTF-8"))

        return self.root.outputDoc(doc)
    
    @cherrypy.expose
    def getNextPhoto(self, *args, **kwargs):
        """This is a VERY simple method that only returns an integer value of
        the next slide number.  It is meant to be used in conjunction with the
        AJAX slideshow

        FIXME: for right now, this uses a hack to get the image size of images,
        not efficient at all."""
        
        tags, orTags = self.root.processTags(args)
        res = self.root.getPhotos(tags, orTags)
        if int(kwargs.get('pid',-1)) != -1:
            try:
                i = res.index(int(kwargs.get('pid'))) + 1
            except:
                i = 0
        else:
            i = 0
        if i == len(res):
            i = 0
        if kwargs.get('random',False):
            i = random.randint(0,len(res))
        return str(res[i])
