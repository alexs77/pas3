import sys
import os
sys.path.append(".." + os.sep + "src")

import unittest
import pennave
import images
import Image

from dbobjects import *

class TestImages(unittest.TestCase):
    """
    This class tests only the functions related image scaling and resizing
    """
    def setUp(self):
        print "test setup running"
        pass
    
    def tearDown(self):
        print "test teardown running"
        pass
    
    def testImageNotFound(self):
        # FIXME: add in a new test for the case when an image cannot be found
        pass
    
    def testImageScaleMedium(self):
        # FIXME: add in test for medium scaled images
        pass
    
    def testImageOriginal(self):
        # FIXME: add in test for original images
        pass
    
if __name__ == '__main__':
    unittest.main()
    