/*
 * slides.js
 *
 * part of PennAve - a dynamic photo gallery application
 *
 * copyright (c) 2006 Patrick Wagstrom <pridkett@users.sf.net>
 *
 * This file is licensed under the GNU General Public License
 */
var fadeInDelay = 0;
var fadeInSteps = 0.18;
var pictureDelay = 3000;

function loadNextImage() {
    /* queries the PennAve application for the next photo to show in the slide
       show */
    var url = prefix + "/slides/getNextPhoto" + tagPrefix + "?pid=" + currentImage;
    var request = false;
    /* for right now we need to try all these different methods to create the
       XMLHttpRequest object.  */
    try {
        request = new XMLHttpRequest();
    } catch (trymicrosoft) {
        try {
            request = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (othermicrosoft) {
            try {
                request = new ActiveXObject("Microsoft.XMLHTTP");
            } catch (failed) {
                request = false;
            }
        }
    }

    request.open("GET", url, true);
    request.onreadystatechange = function() { requestStateChanged(request); };
    request.send(null);

    if (!request)
        alert("Error initializing XMLHttpRequest!");
}

function requestStateChanged(request) {
    if (request.readyState == 4) {
        if (request.status == 200) {
            var frameId = "frame" + nextImage;

            /* update stuff for loading of the next image */
            var rt = request.responseText.split(" ");
            currentImage = rt[0];
            nextImage = nextImage + 1;
            if (nextImage == 3) {
                nextImage = 1;
            }
            var I = document.createElement("img");
            I.style.visibility = "hidden";
            I.src = prefix + "/images/medium/" + currentImage;
            I.alt = "image number " + currentImage;
            I.id = "TempImageId";
            /* wait until picture is loaded before proceeding */
            I.onload = function () { I.onload=null; scaleInsertPicture(frameId, I, 'frame' + nextImage); }
        }
        else if (request.status == 404)
            alert("Request URL does not exist");
        else
            alert("Error: status code is " + request.status);
    }
}


function startSlideShow() {
    loadNextImage();
}

function getDisplayWidth() {
  var myWidth = 0, myHeight = 0;
  if( typeof( window.innerWidth ) == 'number' ) {
    /* Non-IE */
    myWidth = window.innerWidth;
  } else if( document.documentElement && ( document.documentElement.clientWidth || document.documentElement.clientHeight ) ) {
    /* IE 6+ in 'standards compliant mode' */
    myWidth = document.documentElement.clientWidth;
  } else if( document.body && ( document.body.clientWidth || document.body.clientHeight ) ) {
    /* IE 4 compatible */
    myWidth = document.body.clientWidth;
  }
  return myWidth;
}

function getDisplayHeight() {
  var myWidth = 0, myHeight = 0;
  if( typeof( window.innerWidth ) == 'number' ) {
    /* Non-IE */
    myHeight = window.innerHeight;
  } else if( document.documentElement && ( document.documentElement.clientWidth || document.documentElement.clientHeight ) ) {
    /* IE 6+ in 'standards compliant mode' */
    myHeight = document.documentElement.clientHeight;
  } else if( document.body && ( document.body.clientWidth || document.body.clientHeight ) ) {
    /* IE 4 compatible */
    myHeight = document.body.clientHeight;
  }
  return myHeight;
}

function scaleInsertPicture(frameId, newImg, frameId2) {
    var frame = document.getElementById(frameId);
    var displayWidth = getDisplayWidth();
    var displayHeight = getDisplayHeight();
    var widthRatio = getDisplayWidth() / newImg.width;
    var heightRatio = getDisplayHeight() / newImg.height;

    var oldWidth = newImg.width;
    var oldHeight = newImg.height;

    if (heightRatio < widthRatio) {
        newImg.width = oldWidth * heightRatio;
        newImg.height = oldHeight * heightRatio;
    } else {
        newImg.width = oldWidth * widthRatio;
        newImg.height = oldHeight * widthRatio;
    }

    try {
        frame.replaceChild(newImg, frame.firstChild);
    } catch (noChild) {
        frame.appendChild(newImg);
    }
    frame.style.marginLeft = (displayWidth - newImg.width)/2 + "px";
    frame.style.marginRight = (displayWidth - newImg.width)/2 + "px";
    frame.style.marginTop = (displayHeight - newImg.height)/2 + "px";
    frame.style.marginBottom = (displayHeight - newImg.height)/2 + "px";
    frame.style.opacity = 0;
    frame.style.zIndex = 0;
    if (frame.filters) {
        frame.filters.alpha.opacity = 0;
    }
    newImg.style.visibility = "visible";
    newImg.id = "Image_" + frameId;
    setTimeout("crossFadeElements('"+frameId+"','"+frameId2+"',0);", 0);
}

function crossFadeElements(inElem, outElem, opac) {
    /* this function fades one element into another.  Basically it increases
       the opacity gradually on the new image, while decreasing it on the old
       image.  IE needs to have an alpha filter defined in CSS for this to
       function properly */
    var frame2 = document.getElementById(outElem);
    var frame1 = document.getElementById(inElem);

    /* prevent blowing over 1.0, which causes a blink on some browsers */
    opac = opac > 1 ? 1 : opac;

    frame2.style.opacity = (1-opac);
    if (frame2.filters) {
        frame2.filters.alpha.opacity = (1-opac) * 100;
    }
    frame1.style.opacity = opac;
    if (frame1.filters) {
        frame1.filters.alpha.opacity = opac * 100;
    }
    if (opac < 1) {
        opac = opac + fadeInSteps;
        setTimeout("crossFadeElements('"+inElem+"','"+outElem+"'," + opac + ");", fadeInDelay);
   } else {
        frame1.style.zIndex = 1;
        frame2.style.zIndex = 0;
        setTimeout("loadNextImage();",pictureDelay);
    }
}
