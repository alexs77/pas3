“prepare.py” is used to “prepare” images, so that they can be used
by pas3.
To do so, it reads the F-Spot “photos.db” and fetches image files
from an Amazon AWS S3 bucket. It then extracts EXIF information
and scales the image to a “medium” and “thumbnail” size. The result
is then stored on another (or the same) S3 bucket.

