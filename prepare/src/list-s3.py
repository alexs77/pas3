#!/usr/bin/python
# vim: set fileencoding=utf-8

# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$

aws_s3_access_key_id = "0C5GNE198PW7Y9SRJ5G2"
aws_s3_secret_access_key = "ETUqgOouvw74IjKl2HhLv9UubV0BEq5k5M9lJo9t"
aws_s3_bucket = "bilder.alexander.skwar.name"
#aws_s3_bucket = "public-files.askwar"

import S3
import MyS3
import logging
import cPickle

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
                        level=logging.DEBUG)
    log = logging.getLogger("prepare.py")
    log.setLevel(logging.INFO)


    s3_conn = MyS3.MyAWSAuthConnection(aws_s3_access_key_id, aws_s3_secret_access_key)
    s3_gen = S3.QueryStringAuthGenerator(aws_s3_access_key_id, aws_s3_secret_access_key, is_secure=False, calling_format=S3.CallingFormat.SUBDOMAIN)

    # Get a listing of all the Keys ("files") in this "bucket"
    s3_bucket_keys = s3_conn.list_all_bucket_keys(aws_s3_bucket)
    log.info("Erzeuge Listing des Buckets '%s'. Dies kann etwas dauern..." % aws_s3_bucket)
    s3_contents = dict(map(lambda x: (x.key, x.etag.strip('"')), s3_bucket_keys))

    cPickle.dump(s3_contents, open(aws_s3_bucket + ".pickle", "w"), cPickle.HIGHEST_PROTOCOL)
