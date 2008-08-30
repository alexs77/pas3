# vim: set fileencoding=UTF-8

""" Erweitere die Methoden von einigen der Original S3 Klasse."""

from S3 import *
import threading
import logging

def create_s3_key(path, pictureId, version, size, ext):
    """
        # Name/URL der Datei auf s3:
        # http://$bucket.s3.amazonaws.com/$key
        # key = $pfad/$größe/$photo_id/version/$version_id
        # NEU:
        # key = $pfad/$photo_id-$version_id_$größe.$ext
        # $photo_id ist IMMER 6-stellig und von links mit 0 aufgefüllt; $version_id ist 2-stellig.
        # z.B.:
        # bucket = bilder.alexander.skwar.name, pfad = images, größe = original, photo_id = 5303, version_id = 1
        # -> http://bilder.alexander.skwar.name.s3.amazonaws.com/images/original/5303/version/1
        # NEU:
        # -> http://bilder.alexander.skwar.name.s3.amazonaws.com/images/005303.01.original.jpeg
    """
    # Beginnt "ext" mit "."? Wenn ja, abschneiden
    if ext[0] == ".":
        ext = ext[1:len(ext)]
    return "%s/%s-%s_%s.%s" % (path, str(pictureId).zfill(6), str(version).zfill(2), size, ext)

class AsyncUpload(threading.Thread):
    def __init__(self, s3_connection, bucket, key, s3object, headers = {}):
        threading.Thread.__init__(self, name = 'AsyncUploadThread-' + bucket + '_' + key)
        self.s3_connection = s3_connection
        self.bucket = bucket
        self.key = key
        self.s3object = s3object
        self.headers = headers
        
    def run(self):
        # Logger holen
        log = logging.getLogger('prepare.py')
        
        log.info("%s: Upload nach Bucket %s" % (self.key, self.bucket))
        #print "Upload von %s in Bucket %s" % (self.key, self.bucket)
        s3_response = self.s3_connection.put(self.bucket, self.key, self.s3object, self.headers)
        info  = "%s: Upload abgeschlossen." % self.key
        info += " Status: %s" % s3_response.http_response.status
        info += ", Reason: %s" % s3_response.http_response.reason
        info += ", Body: %s" % s3_response.body
        log.info(info)
        del(info)

        #print "\tnach Upload von %s -> Status: %s, Reason: %s, body: %s" % (self.key, s3_response.http_response.status, s3_response.http_response.reason, s3_response.body)
        return s3_response

class MyAWSAuthConnection(AWSAuthConnection):
    def __init__(self, aws_access_key_id, aws_secret_access_key, is_secure=True,
            server=DEFAULT_HOST, port=None, calling_format=CallingFormat.REGULAR):
        AWSAuthConnection.__init__(self, aws_access_key_id, aws_secret_access_key, is_secure, server, port, calling_format)

    def list_all_bucket_keys(self, bucket, options={}, headers={}):
        """Bei der Original-Methode werden nur max. 1000 Keys zurückgegeben.
        Diese Methode erweitert das Original so, das *ALLE* Keys zurückgegeben
        werden."""
        
        log = logging.getLogger('prepare.py')
        
        responses = []
        LBR = AWSAuthConnection.list_bucket(self, bucket, options, headers)
        responses.extend(LBR.entries)
        while LBR.is_truncated:
            log.debug("%s Keys aus Bucket %s ausgelesen" % (len(responses), bucket))
            
            options['marker'] = LBR.entries[-1].key
            LBR = AWSAuthConnection.list_bucket(self, bucket, options, headers)
            responses.extend(LBR.entries)
        return responses
