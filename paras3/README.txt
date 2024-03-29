This is "paras3" - "Parallel S3 sync"

This is a python that easily transfers whole directory trees to (and from) an
Amazon AWS S3 bucket. It's "inspired" by the Ruby program s3sync.rb, which you
can find at http://s3sync.net/.

Just like s3sync.rb, paras3 "goes out of its way to mirror the directory
structure on S3". When you use some other tool to browse an S3 bucket:prefix
synched with paras3, you'll easily recognize the directory structure which was
present on the source.

paras3 is developed on Linux and Sun Solaris 10. It might run on other
platforms (like Windows), but I don't know that for sure :)

paras3 is released under GPLv3.

Examples

(this assumes a S3 bucket called mybucket and a prefix pre.)

  • Put the local /etc directory itself into S3

        paras3.py -r /etc mybucket:pre

    (This will yield S3 keys named pre/etc/…)

  • Put the contents of the local /etc dir into S3, and rename dir:

        paras3.py -r /etc/ mybucket:pre/etcbackup

    (This will yield S3 keys named pre/etcbackup/…)

  • Put contents of S3 "directory" etc into local dir

        paras3.py -r mybucket:pre/etc/ /root/etcrestore

    (This will yield local files at /root/etcrestore/…)

  • Put the contents of S3 "directory" etc into a local dir named etc in the /
    root directory

        paras3.py -r mybucket:pre/etc /root

    (This will yield local files at /root/etc/…)

  • Put S3 nodes under the key pre/etc/ to the local dir /root/etcrestore and
    create local dirs even if S3 side lacks dir nodes

        paras3.py -r --make-dirs mybucket:pre/etc/ /root/etcrestore

    (This will yield local files at /root/etcrestore/…)

Prerequisites

You need a functioning Python (>=2.3) installation. Additionally, you'll need
to install the ssl module, unless you're using Python 2.6+ (ssl is part of
Python 2.6 and up). IMO the easiest way to install "ssl" is using the ssl egg,
with the help of easy_install, which comes with setuptools. For a guide on how
to install EasyInstall, see http://peak.telecommunity.com/DevCenter/EasyInstall
. Quick reference:

easy_install ssl

If you don't have easy_install, you'll need to install it first:

wget -qO - wget http://peak.telecommunity.com/dist/ez_setup.py | python -

Setup

Configurable settings

paras3 needs to know several interesting values to work right..

Required settings:

 1. AWS_ACCESS_KEY_ID
 2. AWS_SECRET_ACCESS_KEY

If you don't know what these are, then paras3 is probably not the right tool
for you to be starting out with... :) Anyway, you might want to check out the
S3 documentation at http://s3.amazonaws.com/.

Optional:

  • THREADS: This sets in how many parallel threads down-/uploads are to be
    done. Keep it in a reasonable range - probably not higher than 10. Default
    is 5.
  • HTTP_PROXY_HOST, HTTP_PROXY_PORT, HTTP_PROXY_USER, HTTP_PROXY_PASSWORD:
    Proxy settings
  • SSL_CERT_DIR: Where your Cert Authority keys live; for verification
  • SSL_CERT_FILE: If you have just one PEM file for CA verification
  • S3SYNC_RETRIES: How many HTTP errors to tolerate before exiting
  • S3SYNC_WAITONERROR: How many seconds to wait after an http error
  • S3SYNC_MIME_TYPES_FILE: Where is your mime.types file
  • S3SYNC_NATIVE_CHARSET: For example Windows-1252. Defaults to ISO-8859-1.
  • AWS_S3_HOST: I don't see why the default would ever be wrong, but you never
    know… :)
  • AWS_CALLING_FORMAT: Defaults to REGULAR. Possible values:
     1. REGULAR: http://s3.amazonaws.com/bucket/key
     2. SUBDOMAIN: http://bucket.s3.amazonaws.com/key
     3. VANITY: http://<vanity_domain>/key

 1. Important: For EU-located buckets you should set the calling format to
    SUBDOMAIN.
 2. Important: For US buckets with CAPS or other weird traits set the calling
    format to REGULAR.

Settings

To set the aforementioned settings, you can either set environment variables or
use a configuration file.

Environment

One "popular" of setting the environment variables is with the help of envdir
from the daemontools package. See http://cr.yp.to/daemontools/envdir.html.

Example:

envdir $HOME/.paras3 $HOME/bin/paras3.py …

In the $HOME/.paras3 dir, there would then be a file called AWS_ACCESS_KEY_ID
with the "proper" value.

Alternatively, you could write a "wrapper" script, in which you set and export
the environment variables.

Example:

#!/bin/sh
AWS_ACCESS_KEY_ID="…"
export AWS_ACCESS_KEY_ID
paras3.py …
# EOF #

Finally, you could of course also use $HOME/.profile (or $HOME/.bash_profile),
or more generally speaking: your shell initialization file, to set those env.
vars. Doing that, each and every program run using your user account gets
access to these vars. This might not be the best way.

Configuration file

Alternatively to the environment way, you can make use of a configuration file.
The program looks for in the following locations, in order:

 1. $HOME/.paras3.ini
 2. /etc/paras3.ini
 3. <PARAS3_DIR>/paras3.ini

Have a look at the sample ini file shipped paras3, to get a feeling for the
format. It resembles the Windows INI file format.

This might be the easiest way to use paras3, because that way, you don't have
to do anything else. You just run "paras3" and you're all set. With the env
vars, you'll have to make sure that the env vars are set prior to invoking
paras3. But the env vars are quite handy if you just want to override a value
for a single run. You could then do:

S3SYNC_WAITONERROR=42 paras3.py …

About Directories, the bane of any S3 sync-er

In S3 there's no actual concept of folders, just keys and nodes. So, every tool
uses its own proprietary way of storing dir info (my scheme being the best
naturally) and in general the methods are not compatible.

If you populate S3 by some means other than paras3 and then try to use paras3
to "get" the S3 stuff to a local filesystem, you will want to use the
--make-dirs option. This causes the local dirs to be created even if there is
no s3sync-compatible directory node info stored on the S3 side. In other words,
local folders are conjured into existence whenever they are needed to make the
"get" succeed.

About MD5 hashes

paras3's normal operation is to compare the file size and MD5 hash of each item
to decide whether it needs syncing. On the S3 side, these hashes are stored and
returned to us as the ETag of each item when the bucket is listed, so it's very
easy. On the local side, the MD5 must be calculated by pushing every byte in
the file through the MD5 algorithm. This is CPU and IO intensive!

Thus you can specify the option --no-md5. This will compare the upload time on
S3 to the last modified time on the local item, and not do md5 calculations
locally at all. This might cause more transfers than are absolutely necessary.

For example if the file is "touched" to a newer modified date, but its contents
didn't change. Conversely if a file's contents are modified but the date is not
updated, then the sync will pass over it. Lastly, if your clock is very
different from the one on the S3 servers, then you may see unanticipated
behavior.

Getting started

Invoke by typing paras3.rb and you should get a nice usage screen. Options can
be specified in short or long form.

ALWAYS TEST NEW COMMANDS using --dryrun (-n) if you want to see what will be
affected before actually doing it. ESPECIALLY if you use --delete. Otherwise,
do not be surprised if you misplace a '/' or two and end up deleting all your
precious, precious files.

If you use the --public-read (-p) option, items sent to S3 will be ACL'd so
that anonymous web users can download them, given the correct URL. This could
be useful if you intend to publish directories of information for others to
see.

If you use --ssl (-s) then your connections with S3 will be encrypted.
Otherwise your data will be sent in clear form, i.e. easy to intercept by
malicious parties.

If you want to prune items from the destination side which are not found on the
source side, you can use --delete (-d). Always test this with -n first to make
sure the command line you specify is not going to do something terrible to your
cherished and irreplaceable data.

Updates and other discussion

The latest version of paras3 is at http://code.google.com/p/pas3/wiki/paras3

Change Log

 1. 2008-09-06: Initial conception

Alexander

 $URL$
 $Author$
 $Date$
 $Rev$
 $Id$

