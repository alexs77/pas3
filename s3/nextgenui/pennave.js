var photoThumbnailHeight = 150;
var photoThumbnailWidth = 200;
var spinnerHeight = 16;
var spinnerWidth = 16;

function centerImage(elem, width, height) {
    elem.style.paddingTop = Math.floor((photoThumbnailHeight - height)/2);
    elem.style.paddingBottom = Math.ceil((photoThumbnailHeight - height)/2);
    elem.style.paddingLeft = Math.floor((photoThumbnailWidth - width)/2);
    elem.style.paddingRight = Math.ceil((photoThumbnailWidth - width)/2);
    elem.style.width = width; elem.style.height = height;
}

var Photo = Class.create({
    initialize: function(id, name, url, width, height) {
        this.name = name;
        this.id = id;
        // this.url = url;
        this.url = "http://patrick.wagstrom.net/gallery/images/original/2074/version/1/";
        if (width == null) width = 200;
        if (height == null) height = 150;
        this.width = width;
        this.height = height;
    },
    toDiv: function(message) {
        var divElem = document.createElement("div");
        $(divElem).addClassName("photo");
        divElem.setAttribute("id", "photo_"+this.id+"_div");
        var imgElem = document.createElement("img");
        $(imgElem).addClassName("photo");
        imgElem.setAttribute("id", "photo_" + this.id + "_spinner");
        imgElem.setAttribute("src","spinner.gif");
        centerImage(imgElem, spinnerWidth, spinnerHeight);

        /* create the image that will replace the spinner */
        var img2 = new Image();
        img2.src = this.url;
        $(img2).addClassName("photo");
        img2.setAttribute("id", "photo_" + this.id);
        centerImage(img2, this.width, this.height);
        img2.onload = function() { imgElem.parentNode.replaceChild(img2, imgElem); delete imgElem;}
        divElem.appendChild(imgElem);
        return divElem; 
    }
});

function processPhotos(transport) {
    alert(transport.responseXML);
    var xmlDoc = transport.responseXML;
    var photos = xmlDoc.getElementsByTagName('photo');
    alert(photos.length);
}

function doPhotos() {
    var url = "/ajax/photos";
    new Ajax.Request(url, {
        method: 'get',
        onSuccess: processPhotos,
        onFailure: function() { alert("something went wrong with the request"); },
        onException: function() { alert("exception while loading Ajax"); }
    });
        
    // while ($('main_content').childNodes[0])
    //     $('main_content').removeChild($('main_content').childNodes[0]);
    // for (i = 0; i < 3; i ++) {
    //     p = new Photo(i, "photo" + i);
    //     $('main_content').appendChild(p.toDiv());
    // }
}
