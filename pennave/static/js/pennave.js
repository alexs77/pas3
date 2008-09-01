/*
 * $LastChangedDate$
 * $LastChangedRevision$
 * $LastChangedBy$
 * $HeadURL$
 * $Id$
 */

var photoThumbnailHeight = 80;
var photoThumbnailWidth = 120;
var spinnerHeight = 16;
var spinnerWidth = 16;
var currentTags = new Array();
var currentPhotos = new Array();
var currentMode = "tags";


function updateLocationHash() {
    var tagSuffix = "";
    currentTags.each(function(tag) { tagSuffix = tagSuffix + "/" + tag.id; });
    window.location.hash = currentMode + tagSuffix;
}

function centerImage(elem, width, height) {
    elem.style.paddingTop = Math.floor((photoThumbnailHeight - height)/2);
    elem.style.paddingBottom = Math.ceil((photoThumbnailHeight - height)/2);
    elem.style.paddingLeft = Math.floor((photoThumbnailWidth - width)/2);
    elem.style.paddingRight = Math.ceil((photoThumbnailWidth - width)/2);
    elem.style.width = width; elem.style.height = height;
}

function clearChildNodes(elem) {
    while (elem.childNodes.length) { elem.removeChild(elem.firstChild); }
}

function addTag(tag) {
    currentTags.push(tag);
    updateCurrentTags();
    doPhotos();
}

function removeTag(tag) {
    currentTags = currentTags.without(tag);
    updateCurrentTags();
    doPhotos();
}

function onlyTag(tag) {
    currentTags = new Array();
    currentTags.push(tag);
    updateCurrentTags();
    doPhotos();
}

function updateCurrentTags() {
    var tagDiv = document.getElementById("current_tags");
    clearChildNodes(tagDiv);
    $A(currentTags).each(function(tag, index) {
        if (index != 0) { d = document.createElement("span"); $(d).addClassName("current_tags_sep"); d.innerHTML="&#x2022;"; tagDiv.appendChild(d); }
        tagDiv.appendChild(tag.toBarElem());
    });
}

function highlightPhotos(tmpId) {
    currentPhotos.each(function(p) { if (p.hasTag(tmpId) == true) { p.highlight(); }});
}

var Tag = Class.create({
    initialize: function(id, name, extraArgs) {
        this.id = id;
        this.name = name;
        if (extraArgs != null) {
            this.size = extraArgs["size"];
            this.count = extraArgs["count"];
        }
    },
    toLi: function() {
        var liElement = document.createElement("li");
        liElement.innerHTML = this.name;
        return liElement;
    },
    unhighlightAllPhotos: function() {
        currentPhotos.each(function(p) {p.unhighlight();});
    },
    toSpan: function() {
        var spanElement = document.createElement("span");
        $(spanElement).addClassName("tag-" + this.size);
        var linkElement = document.createElement("a");
        linkElement.innerHTML = this.name;
        linkElement.setAttribute("href","#");
        var tmpElem = this;
        Event.observe(linkElement, 'click', function(event){addTag(tmpElem);});
        Event.observe(linkElement, 'mouseover', function(event){highlightPhotos(tmpElem.id);});
        Event.observe(linkElement, 'mouseout', function(event){tmpElem.unhighlightAllPhotos();});
        spanElement.appendChild(linkElement);
        spanElement.appendChild(document.createTextNode(" "));
        spanElement.setAttribute("id", "tag_" + this.id);
        spanElement.setAttribute("rank", this.rank);
        return spanElement;
    },
    toBarElem: function() {
        var spanElement = document.createElement("span");
        logger.l("setting bar size = " + this.size + " " + this["size"]);
        $(spanElement).addClassName("bar-elem" + this.size);
        var linkElement = document.createElement("a");
        linkElement.innerHTML = this.name;
        linkElement.setAttribute("href","#");
        var tmpElem = this;
        Event.observe(linkElement, 'click', function(event){onlyTag(tmpElem);});
        spanElement.appendChild(linkElement);

        var removeSpanElement = document.createElement("span");
        $(removeSpanElement).addClassName("bar-elem-remove");

        removeSpanElement.appendChild(document.createTextNode("["));

        var linkElement2 = document.createElement("a");
        linkElement2.innerHTML = "-";
        linkElement2.setAttribute("href", "#");
        var tmpElem2 = this;
        Event.observe(linkElement2, 'click', function(event){removeTag(tmpElem2);});
        removeSpanElement.appendChild(linkElement2);
        removeSpanElement.appendChild(document.createTextNode("]"));
        spanElement.appendChild(removeSpanElement);

        spanElement.setAttribute("id", "tag_" + this.id);
        spanElement.setAttribute("rank", this.rank);
        return spanElement;
    }
})

var Version = Class.create({
    initialize: function(id, name, shown, isDefault) {
        this.id = id;
        this.name = name;
        if (shown == "true") { this.shown = true; } else { this.shown = false; }
        if (isDefault == "true") { this.isDefault = true; } else { this.isDefault = false; }
    },
    toLi: function() {
        var liElement = document.createElement("li");
        liElement.innerHTML = this.name;
        return liElement;
    },
})

var TagCloud = Class.create({
    initialize: function() {
        this.tags = new Array();
    },
    addTag: function(tag) {
        this.tags[this.tags.length] = tag;
    },
    toDiv: function() {
        var divElem = document.createElement("div");
        $(divElem).addClassName("tagCloud");
        this.tags.each(function(t) { divElem.appendChild(t.toSpan()); });
        return divElem;
    },
});

var Photo = Class.create({
    initialize: function(id, name, url, width, height) {
        this.name = name;
        this.id = id;
        this.url = url;
        // this.url = "http://patrick.wagstrom.net/gallery/images/original/2074/version/1/";
        if (width == null) width = 120;
        if (height == null) height = 80;
        this.width = width;
        this.height = height;
        this.versions = new Array();
        this.tags = new Array();
    },
    addVersion: function(version) {
        this.versions[this.versions.length] = version;
    },
    addTag: function(tag) {
        this.tags[this.tags.length] = tag;
    },
    toDiv: function() {
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
        img2.onload = function() { centerImage(img2, img2.width, img2.height); imgElem.parentNode.replaceChild(img2, imgElem); delete imgElem;}
        divElem.appendChild(imgElem);
        /* we need this to get around some issues with prototype thinking "this" refers to the div element */
        var tmpPhotoRef = this;
        Event.observe(divElem, 'click', function(event){tmpPhotoRef.showPhoto();});
        Event.observe(divElem, 'mouseover', function(event){tmpPhotoRef.highlight(); tmpPhotoRef.showPhotoInfo();});
        Event.observe(divElem, 'mouseout', function(event){tmpPhotoRef.unhighlight(); tmpPhotoRef.hidePhotoInfo();});
        return divElem; 
    },
    showPhoto: function() {
        alert(this.id);
    },
    showPhotoInfo: function() {
        var contentDiv = document.getElementById("side_content");
        clearChildNodes(contentDiv);
        var nameElem = document.createElement("div");
        $(nameElem).addClassName("photoName");
        nameElem.innerHTML = this.name;
        var descElem = document.createElement("div");
        $(descElem).addClassName("photoDescription");
        descElem.innerHTML = this.description;
        
        var tagList = document.createElement("ul");
        $(tagList).addClassName("photoTags");
        this.tags.each(function(t) { tagList.appendChild(t.toLi()); });

        var versionList = document.createElement("ul");
        $(versionList).addClassName("photoVersions");
        this.versions.each(function(v) { versionList.appendChild(v.toLi()); });
        
        contentDiv.appendChild(nameElem);
        contentDiv.appendChild(descElem);
        contentDiv.appendChild(tagList);
        contentDiv.appendChild(versionList);
    },
    hidePhotoInfo: function() {
        clearChildNodes(document.getElementById("side_content"));
    },
    highlight: function() {
        var divElem = document.getElementById("photo_"+this.id+"_div");
        divElem.style.borderWidth = "2px";
        divElem.style.borderColor = "red";
        divElem.style.margin = "4px";
    },
    unhighlight: function() {
        var divElem = document.getElementById("photo_"+this.id+"_div");
        divElem.style.borderWidth = "1px";
        divElem.style.borderColor = "black";
        divElem.style.margin = "5px";
    },
    hasTag: function(tagId) {
        var rv=false;
        this.tags.each(function(t) { if (t.id == tagId) rv=true; });
        return rv;
    }
});

function processPhotos(transport) {
    // remove the current photos from the list
    currentPhotos = new Array();

    var xmlDoc = transport.responseXML;
    var photos = xmlDoc.getElementsByTagName("photo");
    var contentDiv = document.getElementById("main_content");
    logger.l(photos.length + " photos retrieved", logger.INFO);
    clearChildNodes(contentDiv);
    for (var i = 0; i < photos.length; i ++) {
        logger.l("processing photo " + i, logger.INFO);
        var photoNode = photos[i];
        var photoId = photoNode.getAttribute("id");
        var photoName = photoNode.getAttribute("name");
        var photoURL = "http://localhost:8000/images/thumbnail/" + photoId;
        var photo = new Photo(photoId, photoName, photoURL);
        // add the photo to the list of current photos
        currentPhotos.push(photo);
        var thisElem = photoNode.firstChild;
        logger.l("processing child elements", logger.INFO);
        while (thisElem != null) {
            logger.l("processing tag: " + thisElem.nodeName, logger.DEBUG);
            if (thisElem.nodeName == "description") {
                photo.description = thisElem.childNodes[0].nodeValue;
            } else if (thisElem.nodeName == "tags") {
                logger.l("checking tags", logger.DEBUG);
                $A(thisElem.childNodes).each(function(t) {
                    if (t.nodeName == "tag") {
                        var tag = new Tag(t.getAttribute("id"), t.childNodes[0].nodeValue);
                        photo.addTag(tag);
                    }
                });
            } else if (thisElem.nodeName == "versions") {
                logger.l("checking versions", logger.DEBUG);
                $A(thisElem.childNodes).each(function(t) {
                    if (t.nodeName == "version") { 
                        var version = new Version(t.getAttribute("id"), t.getAttribute("name"),
                                                  t.getAttribute("shown"), t.getAttribute("default"));
                        photo.addVersion(version);
                    }});
            }
            thisElem = thisElem.nextSibling;
        }
        // iterate over the tags
        contentDiv.appendChild(photo.toDiv());
    }
}

function processTags(transport) {
    logger.l("tag request returned", logger.INFO);
    var xmlDoc = transport.responseXML;
    logger.l("so far so good 1", logger.DEBUG);
    var tags = $A(xmlDoc.getElementsByTagName("tag"));
    logger.l("so far so good 2", logger.DEBUG);
    var contentDiv = $("tag_window");
    logger.l("so far so good 3", logger.DEBUG);
    var tagCloud = new TagCloud();
    logger.l("so far so good 4", logger.DEBUG);

    tags.each(function(t) {
        var tag = new Tag(t.getAttribute("id"), t.childNodes[0].nodeValue, 
            { parent: t.getAttribute("parent"), hasChildren: t.getAttribute("hasChildren"),
              count: t.getAttribute("count"), size: t.getAttribute("size"),
              rank: t.getAttribute("rank")});
        tagCloud.addTag(tag);
    });

    logger.l("woot...all good", logger.DEBUG);
    clearChildNodes(contentDiv);

    if (tags.length == 0) {
        var noTagElem = document.createElement("span");
        $(noTagElem).addClassName("noTagSpan");
        noTagElem.appendChild(document.createTextNode("No more tags found"));
        contentDiv.appendChild(noTagElem);
        alert("no tags");
    }

    contentDiv.appendChild(tagCloud.toDiv());
    logger.l("ALL RIGHT!", logger.INFO);
    updateLocationHash();
}

function doPhotos() {
    var tagSuffix = "";
    currentTags.each(function(tag) { tagSuffix = tagSuffix + "/" + tag.id; });

    var contentDiv = $("main_content");
    clearChildNodes(contentDiv);
    var imgNode = document.createElement("img");
    imgNode.src = "/html/spinner.gif";
    imgNode.width = 16;
    imgNode.height = 16;
    imgNode.style.display = "block";
    imgNode.style.paddingTop = "120px";
    imgNode.style.paddingBottom = "120px";
    imgNode.style.marginLeft = "auto";
    imgNode.style.marginRight = "auto";
    imgNode.style.textAlign="center";
    contentDiv.appendChild(imgNode);

    var url = "/ajaxPhotos" + tagSuffix;
    logger.l("posting request to " + url, logger.INFO);
    new Ajax.Request(url, {
        method: 'get',
        onSuccess: processPhotos,
        onFailure: function() { alert("something went wrong with the request"); },
        onException: function(ev) { logger.l("exception loading ajax: " + ev, logger.FATAL); alert("exception while loading Ajax"); }
    });

    var contentDiv = $("tag_window");
    clearChildNodes(contentDiv);
    var imgNode = document.createElement("img");
    imgNode.src = "/html/spinner.gif";
    imgNode.width = 16;
    imgNode.height = 16;
    imgNode.style.display = "block";
    imgNode.style.paddingTop = "120px";
    imgNode.style.paddingBottom = "120px";
    imgNode.style.marginLeft = "auto";
    imgNode.style.marginRight = "auto";
    imgNode.style.textAlign="center";
    contentDiv.appendChild(imgNode);

    var url = "/ajaxTags" + tagSuffix;
    logger.l("posting request to " + url, logger.INFO);
    new Ajax.Request(url, {
        method: 'get',
        onSuccess: processTags,
        onFailure: function() { logger.l("failed request to " + url, logger.FATAL); alert("something went wrong with the request"); },
    });
}
