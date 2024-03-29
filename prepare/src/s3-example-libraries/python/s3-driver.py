#!/usr/bin/env python
# vim: set fileencoding=utf-8

#===============================================================================
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

#  This software code is made available "AS IS" without warranties of any
#  kind.  You may copy, display, modify and redistribute the software
#  code either by itself or as incorporated into your code; provided that
#  you do not remove any proprietary notices.  Your use of this software
#  code is at your own risk and you waive any claim against Amazon
#  Digital Services, Inc. or its affiliates with respect to your use of
#  this software code. (c) 2006 Amazon Digital Services, Inc. or its
#  affiliates.

import S3
import time
import sys

aws_s3_access_key_id = "xyz"
aws_s3_secret_access_key = "xyz"

AWS_ACCESS_KEY_ID = aws_s3_access_key_id
AWS_SECRET_ACCESS_KEY = aws_s3_secret_access_key

# remove these next two lines when you've updated your credentials.
#print "update s3-driver.py with your AWS credentials"
#sys.exit();

# convert the bucket to lowercase for vanity domains
# the bucket name must be lowercase since DNS is case-insensitive
BUCKET_NAME = AWS_ACCESS_KEY_ID.lower() + '-test-bucket'
KEY_NAME = 'test-key2'

conn = S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
generator = S3.QueryStringAuthGenerator(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

print '----- creating bucket -----'
print conn.create_bucket(BUCKET_NAME).http_response.reason

print '----- listing bucket -----'
print map(lambda x: x.key, conn.list_bucket(BUCKET_NAME).entries)

print '----- putting object (with content type) -----'
print conn.put(
        BUCKET_NAME,
        KEY_NAME,
        S3.S3Object('this is a test'),
        { 'Content-Type': 'text/plain' }).http_response.reason

print '----- listing bucket -----'
print map(lambda x: x.key, conn.list_bucket(BUCKET_NAME).entries)

print '----- getting object -----'
print "conn.get: %s" % conn.get(BUCKET_NAME, KEY_NAME)
print "conn.get metadata: %s" % conn.get(BUCKET_NAME, KEY_NAME).object.metadata
print conn.get(BUCKET_NAME, KEY_NAME).object.data

print '----- query string auth example -----'
print "\nTry this url out in your browser (it will only be valid for 60 seconds).\n"

generator = S3.QueryStringAuthGenerator(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, False)
generator.set_expires_in(60);
url = generator.get(BUCKET_NAME, KEY_NAME)
print url
print '\npress enter> ',
sys.stdin.readline()

print "\nNow try just the url without the query string arguments.  it should fail.\n"
print generator.make_bare_url(BUCKET_NAME, KEY_NAME)
print '\npress enter> ',
sys.stdin.readline()


print '----- putting object with metadata and public read acl -----'
print conn.put(
    BUCKET_NAME,
    KEY_NAME + '-public',
    S3.S3Object('this is a publicly readable test'),
    { 'x-amz-acl': 'public-read' , 'Content-Type': 'text/plain' }
).http_response.reason

print '----- anonymous read test ----'
print "\nYou should be able to try this in your browser\n"
public_key = KEY_NAME + '-public'
print generator.make_bare_url(BUCKET_NAME, public_key)
print "\npress enter> ",
sys.stdin.readline()

print "----- getting object's acl -----"
print conn.get_acl(BUCKET_NAME, KEY_NAME).object.data

print "----- vanity domain example -----"
print "\nThe bucket can also be specified as part of the domain.  Any vanity domain that is CNAME'd to s3.amazonaws.com is also valid."
print "Try this url out in your browser (it will only be valid for 60 seconds).\n"
generator.calling_format = S3.CallingFormat.SUBDOMAIN
url = generator.get(BUCKET_NAME, KEY_NAME)
print url
print "\npress enter> ",
sys.stdin.readline()

print '----- deleting objects -----'
print conn.delete(BUCKET_NAME, KEY_NAME).http_response.reason
print conn.delete(BUCKET_NAME, KEY_NAME + '-public').http_response.reason

print '----- listing bucket -----'
print map(lambda x: x.key, conn.list_bucket(BUCKET_NAME).entries)

print '----- listing all my buckets -----'
print map(lambda x: x.name, conn.list_all_my_buckets().entries)

print '----- deleting bucket ------'
print conn.delete_bucket(BUCKET_NAME).http_response.reason

