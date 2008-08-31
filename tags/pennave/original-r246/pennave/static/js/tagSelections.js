function launchSlideShow () {
    window.open(prefix + "/slides/index" + tagPrefix,"","width=640,height=480,resizable=1")
}

/*
 * showAllTagsToggle
 * toggles the visibility state of the tags in the tagCloud
 *
 * @param string1: the string that is in showAllTags element that indicates
 *                 only the top tags are showing
 * @param string2: the string in the showAllTags elemenet that indicates all
 *                 the tags are showing
 *
 * In the long term, this should be changed so it's a bit more robust.  Perhaps
 * having the javascript calculate the number of tags and passing a reference to
 * the calling element on the page might make it better than having to pass the
 * explicit strings around.
 */
function showAllTagsToggle(string1, string2) {
    elem = document.getElementById("showAllTags");
    elems = document.getElementsByName("nonTopTags");
    if (elem.innerHTML == string1) {
        elem.innerHTML = string2;
        for (i = 0; i < elems.length; i ++) {
            elems[i].style.display="inline";
        }
    } else {
        elem.innerHTML = string1;
        for (i = 0; i < elems.length; i ++) {
            elems[i].style.display="none";
        }
    }
}

/*
 * highlightPhotos
 * called when moving over a tag on the tagCloud to highlight photos with
 * that tag as though we were mousing over them
 *
 * @param tagId: the id of the tag that we just moved over
 */
function highlightPhotos(tagId) {
    for (var i = 0; i < photoTags[tagId].length; i ++) {
        elem = document.getElementById("photoThumbnail"+photoTags[tagId][i]);
        elem.className='photoThumbnailHighlight';
    }
}

/*
 * unhighlightPhotos
 * called when moving off a tag in the tagCloud to return photos to original
 * style.
 *
 * @param tagId: the ID number of the tag we've just moved off
 */
function unhighlightPhotos(tagId) {
    for (var i = 0; i < photoTags[tagId].length; i ++) {
        elem = document.getElementById("photoThumbnail"+photoTags[tagId][i]);
        elem.className='photoThumbnail';
    }
}

/*
 * showPhotoInfo
 * puts the appropriate 
 */
function showPhotoInfoOn(photoId) {
    elem = document.getElementById("photoInfo");
    if (photoInfo[photoId].length > 0) {
        if (photoInfo[photoId][0]) {
            document.getElementById("photoInfoFilenameData").innerHTML = photoInfo[photoId][0];
            document.getElementById("photoInfoFilename").style.display = "block";
        } else { document.getElementById("photoInfoFilename").style.display="none"; }
        if (photoInfo[photoId][1] && photoInfo[photoId][2]) {
            document.getElementById("photoInfoWidthData").innerHTML = photoInfo[photoId][1];
            document.getElementById("photoInfoHeightData").innerHTML = photoInfo[photoId][2];
            document.getElementById("photoInfoSize").style.display = "block";
        } else { document.getElementById("photoInfoSize").style.display = "none"; }
        if (photoInfo[photoId][3]) {
            document.getElementById("photoInfoTagsData").innerHTML = photoInfo[photoId][3];
            document.getElementById("photoInfoTags").style.display = "block";
        } else { document.getElementById("photoInfoTags").style.display = "none"; }
        if (photoInfo[photoId][4]) {
            document.getElementById("photoInfoDescriptionData").innerHTML = photoInfo[photoId][4];
            document.getElementById("photoInfoDescription").style.display = "block";
        } else { document.getElementById("photoInfoDescription").style.display = "none"; }
        if (photoInfo[photoId][5]) {
            document.getElementById("photoInfoDateData").innerHTML = photoInfo[photoId][5];
            document.getElementById("photoInfoDate").style.display = "block";
        } else { document.getElementById("photoInfoDate").style.display = "none"; }
    }
    
    elem.style.display = "block";
}


function showPhotoInfoOff (photoId) {
    elem = document.getElementById("photoInfo");
    elem.style.display = "none";
}
