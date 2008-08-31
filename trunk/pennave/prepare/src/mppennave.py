# mycpapp.py
from cherrypy import _cpmodpy
import cherrypy

_isSetUp = False
def mphandler(req):
    global _isSetUp
    if not _isSetUp:
        # load_conf_file(req.get_options().get['pennave.config_file'])
        cherrypy.config.update(req.get_options()['pennave.config_file'])
        cherrypy.config.update({"modpython_prefix": req.get_options()['pennave.prefix']})
        cherrypy.config.update({"modpython_server": req.get_options()['pennave.server']})
        _isSetUp = True
    return _cpmodpy.handler(req)
