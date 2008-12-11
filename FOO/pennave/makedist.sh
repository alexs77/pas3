#!/bin/sh

#===============================================================================
# vim: set fileencoding=utf-8
# 
# $LastChangedDate$
# $LastChangedRevision$
# $LastChangedBy$
# $HeadURL$
# $Id$
#===============================================================================

#
# this script is used for packaging up PennAve.  One of these days I'll get
# around to writing some sort of real python disttools based thing
#

if [ "x$1" = "x" ]; then
	echo "usage: makedist.sh [VERSION]"
	exit
fi

mkdir pennave-$1
for x in AUTHORS COPYING MAINTAINERS TODO ChangeLog INSTALL NEWS; do
	cp $x pennave-$1
done
mkdir pennave-$1/scale
mkdir pennave-$1/scale/medium
mkdir pennave-$1/scale/thumbs
mkdir pennave-$1/src
mkdir pennave-$1/doc

for x in dbobjects.py pennave.py default.conf feeds.py slides.py images.py imageops.py LiberationSans-Regular.ttf exiftools.py EXIF.py; do
	cp src/$x pennave-$1/src
done

mkdir pennave-$1/static
mkdir pennave-$1/static/css
mkdir pennave-$1/static/xslt
mkdir pennave-$1/static/js
mkdir pennave-$1/static/html

cp static/css/pennave.css pennave-$1/static/css
cp static/css/slides.css pennave-$1/static/css
cp static/css/welcome.css pennave-$1/static/css
cp static/xslt/pennave.xsl pennave-$1/static/xslt
cp static/xslt/slides.xsl pennave-$1/static/xslt
cp static/js/tagSelections.js pennave-$1/static/js
cp static/js/slides.js pennave-$1/static/js
cp static/js/canvas.js pennave-$1/static/js
cp static/html/welcome.html pennave-$1/static/html
cp static/html/patrick.html pennave-$1/static/html
cp doc/* pennave-$1/doc

tar -czvf pennave-$1.tar.gz pennave-$1
rm -rf pennave-$1
