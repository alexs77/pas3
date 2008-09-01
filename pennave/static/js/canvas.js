/*
 * $LastChangedDate$
 * $LastChangedRevision$
 * $LastChangedBy$
 * $HeadURL$
 * $Id$
 */

/*
 * canvas.js
 * Copyright (c) 2006-2007 Patrick Wagstrom <pwagstro@andrew.cmu.edu>
 * Released under the GNU General Public License
 *
 * This file provides some PennAve's support for dynamically creating canvas
 * objects to display sets of photos.  This method reduces the amount of
 * bandwidth required to transmit the image as it allows them to be loaded
 * from cache.  However, I have not yet figured out a way to make the nice
 * blur shadows from the server side graphics version.
 */
var imgBorder = 8;
var imgMaxAngle = 22;
var imgMaxJitter = 75;
var imgLineWidth = 2;
function FramedImage() {
	this.image = null;
	this.rotation = randomAngle(-1*imgMaxAngle,imgMaxAngle);
	this.jitter = [Math.floor(imgMaxJitter*Math.random() - imgMaxJitter/2), Math.floor(imgMaxJitter*Math.random() - imgMaxJitter/2)];
	// calculate the bounds of the image
	this.bounds = null;	
	this.calculateBounds = calculateBounds;
	this.draw = draw;
	
	function calculateBounds() {
		// calculates the bounds for this particular image
	    var maxX = -9999; var minX = 9999; var maxY=-9999; var minY=9999;
	    var rv = Array(6);
    	var border = imgBorder + imgLineWidth;
        rv[0] = [-1*(this.image.width/2+border), -1*(this.image.height/2+border)]
		rv[1] = [(this.image.width/2+border), (this.image.height/2+border)]
		rv[2] = translate(-1*(this.image.width/2+border), -1*(this.image.height/2+border), this.rotation);
        rv[3] = translate((this.image.width/2+border), -1*(this.image.height/2+border), this.rotation);
	    rv[4] = translate(-1*(this.image.width/2+border), (this.image.height/2+border), this.rotation);
    	rv[5] = translate((this.image.width/2+border), (this.image.height/2+border), this.rotation);
    	// alert([this.image.width, this.image.height, this.rotation, rv]);
       	for (var j = 0; j < 6; j ++) {
        	xval = rv[j][0] + this.jitter[0];
	        yval = rv[j][1] + this.jitter[1];
    	    if (xval < minX) { minX = xval; }
        	if (xval > maxX) { maxX = xval; }
            if (yval < minY) { minY = yval; }
	        if (yval > maxY) { maxY = yval; }
		}
	    this.bounds = [Math.floor(minX), Math.ceil(maxX),
	                   Math.floor(minY), Math.ceil(maxY)];	                   
	    return this.bounds;		
	}
	
	function draw(ctx, extents) {
		// draws a given element
        ctx.save();
		// ctx.translate(-1*extents[0], -1*extents[2]);
		var cWidth = (extents[1] - extents[0])/2;
		var cHeight = (extents[3] - extents[2])/2;
		
		var bWidth = (extents[1] + extents[0]) / 2;
		var bHeight = (extents[2] + extents[3]) / 2;

		ctx.translate(cWidth, cHeight);
		ctx.translate(this.jitter[0]-bWidth, this.jitter[1]-bHeight);
		ctx.rotate(this.rotation);
        ctx.fillStyle = 'rgb(255,255,255)';
        ctx.strokeStyle = 'rgb(0,0,0)';
        ctx.lineWidth = imgLineWidth;
        ctx.fillRect(-1*(this.image.width/2)-imgBorder, -1*(this.image.height/2)-imgBorder, this.image.width+imgBorder*2, this.image.height+imgBorder*2);
        ctx.rect(-1*(this.image.width/2)-imgBorder, -1*(this.image.height/2)-imgBorder, this.image.width+imgBorder*2, this.image.height+imgBorder*2);
        ctx.stroke();
        ctx.drawImage(this.image, -1*(this.image.width/2), -1*(this.image.height/2));
        ctx.restore();
	}
}

function randomAngle(min, max) {
    /* generates a random angle in radians for us */
    max = max/180*Math.PI;
    min = min/180*Math.PI;
    var rv = ((max-min)*Math.random()) + min;
    return rv;
}

function translate(x, y, angle) {
    /* translates an angle for us -- input in radians*/
    newX = Math.cos(angle)*x+y*Math.sin(angle);
    newY = -1*Math.sin(angle)*x + y*Math.cos(angle);
    return [newX, newY];
}

function getImages(string, canvas) {
    /* gets a set of random photos for tags from the server */
    var url = prefix + "/getRandomPhotos/" + string;
    var request = false;
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
    request.onreadystatechange = function() { requestStateChanged(request, canvas); };
    request.send(null);
}

function requestStateChanged(request, canvas) {
    if (request.readyState == 4) {
        if (request.status == 200) {
            var images = request.responseText.split("\n");
            var numImages = images.length;
            var imgArr = new Array(numImages);
            var imagesLoaded = 0;
            for (var i = 0; i < numImages; i ++) {
                imgArr[i] = new Image();
                imgArr[i].src = images[i];
                imgArr[i].onload = function() {
                    imagesLoaded = imagesLoaded + 1;
                    if (imagesLoaded == numImages) {
                        drawOnCanvas(imgArr, canvas);
                    }
                }
                    }
        } else if (request.status == 404) {
            alert("Request URL does not exist");
        } else {
            alert("Error: status code is " + request.status);
        }
    }
}

function getExtents(imageObjects) {
	// takes in a list of FramedImages and returns the maximum extents needed
	var minX=9999; var minY=9999; var maxX=-9999; var maxY=-9999;
	for (var i=0; i < imageObjects.length; i ++) {
		if (imageObjects[i].bounds[0] < minX) { minX = imageObjects[i].bounds[0]; }		
		if (imageObjects[i].bounds[1] > maxX) { maxX = imageObjects[i].bounds[1]; }
		if (imageObjects[i].bounds[2] < minY) { minY = imageObjects[i].bounds[2]; }
		if (imageObjects[i].bounds[3] > maxY) { maxY = imageObjects[i].bounds[3]; }
	}
	return [minX, maxX, minY, maxY];
}

function drawOnCanvas(imgArr, canvas) {
    /* calculate the maximum extents we need first */
    transArr = []
    var imageObjects = new Array(imgArr.length);
    for (var i = 0; i < imgArr.length; i ++) {
    	imageObjects[i] = new FramedImage();
    	imageObjects[i].image = imgArr[i];
    	imageObjects[i].calculateBounds();
   	}
    var extents = getExtents(imageObjects);
    var canvWidth = extents[1] - extents[0];
    var canvHeight = extents[3] - extents[2];
    var ctx = document.getElementById(canvas).getContext('2d');
    document.getElementById(canvas).height = canvHeight;
    document.getElementById(canvas).width = canvWidth;
    
    for (var i = 0; i < imgArr.length; i ++) {
    	imageObjects[i].draw(ctx, extents);
    }
}
 
function draw() {
    getImages("15","canvas");
}

function insertCanvas(div, ctr, tags) {
    /* this works by first getting the div specified, then creating
       a canvas element, and finally placing it in the document and
       populating it */
     
    if (tags) {
      defaultImageString = "<img src=\""+ prefix + "/images/stacked/" + tags + ".png\"/>";
    } else {
      defaultImageString = "<img src=\""+ prefix + "/images/stacked/default.png\"/>";
    }
    div = document.getElementById(div);


    /* silently fail if for some reason it couldn't find the div element */
    if (div == null) { return; }

    /* opera's canvas is broken, so we show the default PNG files */
    if (window.opera) {
    	div.innerHTML = defaultImageString;
    	return;
    }


    newEl = document.createElement("canvas");
    newEl.id = "canvas" + ctr;
    div.appendChild(newEl);
    /* this is my ghetto way of checking to see if the canvas is actually supported */
    try {
        newEl.getContext('2d');
    } catch (noCanvas) {
        div.innerHTML= defaultImageString;
        return;
    }
    getImages(tags, "canvas" + ctr);
}
