#!/usr/bin/python
# vim: set fileencoding=utf-8

import urllib, threading
from Queue import Queue

class FileGetter(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url
        self.result = None
	
    def get_result(self):
        return self.result
	
    def run(self):
        try:
            f = urllib.urlopen(self.url)
            contents = f.read()
            f.close()
            self.result = contents
        except IOError:
            print "Could not open document: %s" % url

def get_files(files):
    def producer(q, files):
        for file in files:
            thread = FileGetter(file)
            thread.start()
            q.put(thread, True)
    
    finished = []
    def consumer(q, total_files):
        while len(finished) < total_files:
            thread = q.get(True)
            thread.join()
            finished.append(thread.get_result())
    
    q = Queue(20)
    prod_thread = threading.Thread(target=producer, args=(q, files))
    cons_thread = threading.Thread(target=consumer, args=(q, len(files)))
    prod_thread.start()
    cons_thread.start()
    prod_thread.join()
    cons_thread.join()
    return finished
    
def main():
    urls = ["http://artfulcode.nfshost.com/files/multi-threading-in-python.html", "http://forum.spiegel.de/showthread.php?postid=2022174"]
    #urls = ["http://race.da.rtr/RACE/", "http://nms.da.rtr/cgi-bin/nst.cgi"]
    files = get_files(urls)
    
    
if __name__ == "__main__":
    main()
