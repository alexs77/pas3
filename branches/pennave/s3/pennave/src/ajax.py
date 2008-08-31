from dbobjects import *
import cherrypy
import random

class PennAveAjax:
    """
    This is a general container for AJAX utility functions for PennAve
    """
    def __init__(self, root):
        self.root = root

    @cherrypy.expose
    def getRandomPhotos(self, *args, **kwargs):
        cherrypy.log("WARNING: PennAveAjax.getRandomPhotos called, use get_random_photos instead")
        self.get_random_photos(*args, **kwargs) #IGNORE: W0142
    
    @cherrypy.expose
    def get_random_photos(self, *args, **kwargs):
        """This is an ajaxy sorta function, I'm not 100% sure if it belongs
        here or not."""
        numPhotos = cherrypy.config.get('numRandomPhotos',3)
        tags, orTags = self.root.processTags(args)
        res = self.root.getPhotos(tags, orTags)
        random.shuffle(res)
        rv = []
        for x in res[0:numPhotos]:
            rv.append(self.root.getPrefix() + "/images/thumbnail/%d" % x)
        return "\n".join(rv)
