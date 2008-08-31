# vim: set fileencoding=utf-8

import Image
import ImageDraw
import ImageFilter
import random
import math
import cStringIO
import urllib
import threaded_downloader

def translate((x,y), angle):
    """Calculates the position of a pixel if it was rotate angle degrees

    (x,y) - the original location
    angle - the number of degrees to rotate
    """
    newX = math.cos(math.radians(angle))*x+y*math.sin(math.radians(angle))
    newY = -1*math.sin(math.radians(angle))*x+y*math.cos(math.radians(angle))
    return (newX, newY)

BORDER=15
MAXANGLE=15
SHADOW_BORDER=5


def stackS3Images(urls, numImages, size=(160,160), shadow=False, shadowIterations=3):
    """Given a set of input images, produces a new image that looks like set of
    stacked polaroid photographs.

    urls - list (1 or many) of URLs
    size - size of stacked image ?(?)
    shadow - boolean on whether or not to create a show
    shadowIterations - how many times to apply blur filter to create the shadow
    """
    
    images = []
    if urls.__class__ == str:
        urls = list([urls])
    origImages = []
    
    # Download the images specified in urls in the background.
    # Return value is an array holding the contents of the files.
    remote_images = threaded_downloader.get_files(urls)
    
    for remote_image in remote_images:
        sio = cStringIO.StringIO(remote_image)
        imorig = Image.open(sio)
        imorig.thumbnail(size, Image.ANTIALIAS)
        origImages.append(imorig)

    for ctr in xrange(numImages):
        imorig = origImages[ctr%len(origImages)]
        imold = Image.new("RGBA", (imorig.size[0]+BORDER*2, imorig.size[1]+BORDER*2))
        draw = ImageDraw.Draw(imold)
        draw.rectangle([0,0,imold.size[0]-1,imold.size[1]-1], outline=(0,0,0))
        draw.rectangle([1,1,imold.size[0]-2,imold.size[1]-2], outline=(0,0,0), fill=(255,255,255))
        imold.paste(imorig,(BORDER,BORDER))

        angle = random.randint(-MAXANGLE,MAXANGLE)
        x,y = imold.size
        centX = imold.size[0]/2
        centY = imold.size[1]/2
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = translate((-centX,-centY),-angle), translate((-centX,y-centY),-angle), translate((x-centX,-centY),-angle), translate((x-centX,y-centY),-angle)
        minx = math.floor(min(x1,x2,x3,x4))
        miny = math.floor(min(y1,y2,y3,y4))
        maxx = math.ceil(max(x1,x2,x3,x4))
        maxy = math.ceil(max(y1,y2,y3,y4))

        im3 = Image.new("RGBA", (int(math.ceil(maxx-minx)),int(math.ceil(maxy-miny))))
        im3.paste(imold, (int(im3.size[0]/2-imold.size[0]/2),int(im3.size[1]/2-imold.size[1]/2)))
        im4 = im3.rotate(angle, Image.BICUBIC)
        images.append(im4)

    newWidth = max([x.size[0] for x in images])
    newHeight = max([x.size[1] for x in images])
    finalImage = Image.new("RGBA",(newWidth, newHeight))
    for img in images:
        xcoord = newWidth/2-img.size[0]/2
        ycoord = newHeight/2-img.size[1]/2
        finalImage.paste(img,(xcoord,ycoord), img)
    
    outImage = cStringIO.StringIO()
    if shadow:
        tshadow = Image.new("RGBA", (finalImage.size[0]+SHADOW_BORDER*2, finalImage.size[1]+SHADOW_BORDER*2), (0,0,0,0))
        dshadow = Image.new("RGB", (finalImage.size[0], finalImage.size[1]), (0,0,0))
        tshadow.paste(dshadow, (SHADOW_BORDER,SHADOW_BORDER), finalImage)
        for z in xrange(shadowIterations):
            tshadow = tshadow.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.BLUR)
        tshadow.paste(finalImage,(3,3), finalImage)
        tshadow.save(outImage, "PNG")
        del(tshadow, dshadow)
    else:
        finalImage.save(outImage, "PNG")
    del(origImages, images, finalImage)
    outImage.seek(0)
    return outImage

def stackS3Images_with_debug(urls, numImages, size=(160,160), shadow=False, shadowIterations=3):
    """Given a set of input images, produces a new image that looks like set of
    stacked polaroid photographs.

    urls - list (1 or many) of URLs
    size - size of stacked image ?(?)
    shadow - boolean on whether or not to create a show
    shadowIterations - how many times to apply blur filter to create the shadow
    """
    
    import cherrypy
    import pprint

    log = cherrypy.log
    
    images = []
    if urls.__class__ == str:
        urls = list([urls])
    origImages = []
    
    # Download the images specified in urls in the background.
    # Return value is an array holding the contents of the files.
    log(u'%s: Öffnen' % urls)
    remote_images = threaded_downloader.get_files(urls)
    
    _cnt = 0
    for remote_image in remote_images:
        log(u'%s: #%s StringIO Objekt erzeugen' % (urls, _cnt))
        sio = cStringIO.StringIO(remote_image)
        log(u'%s: #%s Bild Objekt erzeugen' % (urls, _cnt))
        imorig = Image.open(sio)
        log(u'%s: #%s Thumbnail erzeugen' % (urls, _cnt))
        imorig.thumbnail(size, Image.ANTIALIAS)
        origImages.append(imorig)
        _cnt = 1 + _cnt
    
    log(u'%s: Bilder wurden vorbereitet' % urls)

    for ctr in xrange(numImages):
        imorig = origImages[ctr%len(origImages)]
        imold = Image.new("RGBA", (imorig.size[0]+BORDER*2, imorig.size[1]+BORDER*2))
        draw = ImageDraw.Draw(imold)
        draw.rectangle([0,0,imold.size[0]-1,imold.size[1]-1], outline=(0,0,0))
        draw.rectangle([1,1,imold.size[0]-2,imold.size[1]-2], outline=(0,0,0), fill=(255,255,255))
        imold.paste(imorig,(BORDER,BORDER))

        angle = random.randint(-MAXANGLE,MAXANGLE)
        x,y = imold.size
        centX = imold.size[0]/2
        centY = imold.size[1]/2
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = translate((-centX,-centY),-angle), translate((-centX,y-centY),-angle), translate((x-centX,-centY),-angle), translate((x-centX,y-centY),-angle)
        minx = math.floor(min(x1,x2,x3,x4))
        miny = math.floor(min(y1,y2,y3,y4))
        maxx = math.ceil(max(x1,x2,x3,x4))
        maxy = math.ceil(max(y1,y2,y3,y4))

        im3 = Image.new("RGBA", (int(math.ceil(maxx-minx)),int(math.ceil(maxy-miny))))
        im3.paste(imold, (int(im3.size[0]/2-imold.size[0]/2),int(im3.size[1]/2-imold.size[1]/2)))
        im4 = im3.rotate(angle, Image.BICUBIC)
        images.append(im4)

    log(u'%s: Bilder wurden gedreht' % urls)

    newWidth = max([x.size[0] for x in images])
    newHeight = max([x.size[1] for x in images])
    finalImage = Image.new("RGBA",(newWidth, newHeight))
    for img in images:
        xcoord = newWidth/2-img.size[0]/2
        ycoord = newHeight/2-img.size[1]/2
        finalImage.paste(img,(xcoord,ycoord), img)
        
    log(u'%s: Bilder wurden skaliert' % urls)

    outImage = cStringIO.StringIO()
    if shadow:
        tshadow = Image.new("RGBA", (finalImage.size[0]+SHADOW_BORDER*2, finalImage.size[1]+SHADOW_BORDER*2), (0,0,0,0))
        dshadow = Image.new("RGB", (finalImage.size[0], finalImage.size[1]), (0,0,0))
        tshadow.paste(dshadow, (SHADOW_BORDER,SHADOW_BORDER), finalImage)
        for z in xrange(shadowIterations):
            tshadow = tshadow.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.BLUR)
        tshadow.paste(finalImage,(3,3), finalImage)
        log(u"%s -> Als PNG mit Schatten abspeichern" % pprint.pformat(urls))
        tshadow.save(outImage, "PNG")
        del(tshadow, dshadow)
    else:
        log(u"%s -> Als PNG OHNE Schatten abspeichern" % pprint.pformat(urls))
        finalImage.save(outImage, "PNG")
    del(origImages, images, finalImage)
    outImage.seek(0)
    log(u"%s -> ENDE" % pprint.pformat(urls))
    return outImage

def stackImages(fns, of, numImages, size=(160,160), shadow=False, shadowIterations=3):
    """Given a set of input images, produces a new image that looks like set of
    stacked polaroid photographs.

    fns - list of filename, or a single filename
    of - the filename to save as.  Regardless of extension, it will always be a png
    shadow - boolean on whether or not to create a show
    shadowIterations - how many times to apply blur filter to create the shadow
    """
    images = []
    if fns.__class__ == str:
        fns = list([fns])
    origImages = []
    for fn in fns:
        imorig = Image.open(fn)
        imorig.thumbnail(size, Image.ANTIALIAS)
        origImages.append(imorig)

    for ctr in xrange(numImages):
        imorig = origImages[ctr%len(origImages)]
        imold = Image.new("RGBA", (imorig.size[0]+BORDER*2, imorig.size[1]+BORDER*2))
        draw = ImageDraw.Draw(imold)
        draw.rectangle([0,0,imold.size[0]-1,imold.size[1]-1], outline=(0,0,0))
        draw.rectangle([1,1,imold.size[0]-2,imold.size[1]-2], outline=(0,0,0), fill=(255,255,255))
        imold.paste(imorig,(BORDER,BORDER))

        angle = random.randint(-MAXANGLE,MAXANGLE)
        x,y = imold.size
        centX = imold.size[0]/2
        centY = imold.size[1]/2
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = translate((-centX,-centY),-angle), translate((-centX,y-centY),-angle), translate((x-centX,-centY),-angle), translate((x-centX,y-centY),-angle)
        minx = math.floor(min(x1,x2,x3,x4))
        miny = math.floor(min(y1,y2,y3,y4))
        maxx = math.ceil(max(x1,x2,x3,x4))
        maxy = math.ceil(max(y1,y2,y3,y4))

        im3 = Image.new("RGBA", (int(math.ceil(maxx-minx)),int(math.ceil(maxy-miny))))
        im3.paste(imold, (int(im3.size[0]/2-imold.size[0]/2),int(im3.size[1]/2-imold.size[1]/2)))
        im4 = im3.rotate(angle, Image.BICUBIC)
        images.append(im4)

    newWidth = max([x.size[0] for x in images])
    newHeight = max([x.size[1] for x in images])
    finalImage = Image.new("RGBA",(newWidth, newHeight))
    for img in images:
        xcoord = newWidth/2-img.size[0]/2
        ycoord = newHeight/2-img.size[1]/2
        finalImage.paste(img,(xcoord,ycoord), img)
    if shadow:
        tshadow = Image.new("RGBA", (finalImage.size[0]+SHADOW_BORDER*2, finalImage.size[1]+SHADOW_BORDER*2), (0,0,0,0))
        dshadow = Image.new("RGB", (finalImage.size[0], finalImage.size[1]), (0,0,0))
        tshadow.paste(dshadow, (SHADOW_BORDER,SHADOW_BORDER), finalImage)
        for z in xrange(shadowIterations):
            tshadow = tshadow.filter(ImageFilter.SMOOTH_MORE).filter(ImageFilter.BLUR)
        oi = finalImage
        tshadow.paste(finalImage,(3,3), finalImage)
        
        tshadow.save(of, "PNG")
        return tshadow
    else:
        finalImage.save(of,"PNG")
        return finalImage

if __name__ == "__main__":
    stackImages(["IMG_2371.JPG", "IMG_2372.JPG", "IMG_2373.JPG", "testimg.jpg"], "test2.png", 4, shadow=True)
