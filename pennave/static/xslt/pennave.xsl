<?xml version="1.0"?>
<xsl:stylesheet version="1.0" 
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:exif="http://www.w3.org/2003/12/exif/ns"
                xmlns:pa="http://patrick.wagstrom.net/projects/pennave/1">
  <xsl:output doctype-public="-//W3C/DTD XHTML 1.0 Strict//EN" indent="yes" method="html"/>

  <!-- this template taken from: http://www.dpawson.co.uk/xsl/sect2/StringReplace.html -->
  <xsl:template name="cleanQuote">
    <xsl:param name="string" />
    <xsl:if test="contains($string, '&#x22;')"><xsl:value-of
    select="substring-before($string, '&#x22;')" />\"<xsl:call-template
    name="cleanQuote">
    <xsl:with-param name="string"><xsl:value-of
    select="substring-after($string, '&#x22;')" />
    </xsl:with-param>
    </xsl:call-template>
    </xsl:if>
    <xsl:if test="not(contains($string, '&#x22;'))"><xsl:value-of
    select="$string" />
    </xsl:if>
  </xsl:template>

  <xsl:variable name="prefix"><xsl:value-of select="/*/@prefix"/></xsl:variable>
  <xsl:variable name="viewPrefix"><xsl:value-of select="/pa:photoView/@prefix"/>/view/<xsl:value-of select="/pa:photoView/pa:photo/@id"/>/</xsl:variable>
  <xsl:variable name="tagPrefix">tags<xsl:for-each select="/*/pa:rootTags/pa:tag">/<xsl:value-of select="@id"/></xsl:for-each>/</xsl:variable>
  <xsl:variable name="versionPrefix"><xsl:if test="count(/pa:photoView/pa:photo/pa:versions) &gt; 0 and not(/pa:photoView/pa:photo/pa:versions/pa:version[@id=/pa:photoView/pa:photo/@version]/@default = 'true')">version/<xsl:value-of select="/pa:photoView/pa:photo/@version"/>/</xsl:if></xsl:variable>
  
  <!-- include english, other languages will by dynamically inserted.
       the include for English must appear EXACTLY as below.  Also, for
       full support, please set "translate" in the configuration to True -->
  <xsl:include href="lang/en.xsl"/>
  
  <!-- ********* -->
  <!-- tagBrowse -->
  <!-- ********* -->
  <xsl:template match="pa:tagBrowse">
    <html>
      <head>
        <title><xsl:value-of select="$pennaveBrowsePageTitle"/></title>
        <link rel="stylesheet" type="text/css" href="{/*/@prefix}/css/pennave.css"/>
        <xsl:variable name="rssURL"><xsl:value-of select="/*/@prefix"/>/feeds/rss<xsl:for-each select="//pa:rootTags/pa:tag">/<xsl:value-of select="@id"/></xsl:for-each></xsl:variable>
        <link href="{$rssURL}" title="RSS" type="application/rss+xml" rel="alternate"/> 
        <script type="text/javascript" src="{/*/@prefix}/js/tagSelections.js"/>
        <script language="javascript">
          var prefix="<xsl:value-of select="/*/@prefix"/>";
          var tagPrefix="<xsl:for-each select="/pa:tagBrowse/pa:rootTags/pa:tag">/<xsl:value-of select="@id"/></xsl:for-each>";
          var tags=[<xsl:for-each select="/pa:tagBrowse/pa:rootTags/pa:tag"><xsl:value-of select="@id"/><xsl:if test="following-sibling::pa:tag">, </xsl:if></xsl:for-each>];
          var photoTags = [];
          <xsl:for-each select="/pa:tagBrowse/pa:tagCloud/pa:tag">
            <xsl:variable name="tempId"><xsl:value-of select="@id"/></xsl:variable>
            photoTags[<xsl:value-of select="@id"/>] = [<xsl:for-each select="/pa:tagBrowse/pa:photos/pa:photo/pa:tags/pa:tag[@id=$tempId]"><xsl:value-of select="ancestor::pa:tags/ancestor::pa:photo/@id"/>,</xsl:for-each>];</xsl:for-each>
          var photoInfo = [];
          <xsl:for-each select="/pa:tagBrowse/pa:photos/pa:photo">
            photoInfo[<xsl:value-of select="@id"/>] = ["<xsl:value-of select="@name"/>", <xsl:value-of select="@width"/>, <xsl:value-of select="@height"/>,  "<xsl:for-each select="pa:tags/pa:tag"><xsl:value-of select="."/><xsl:if test="following-sibling::pa:tag">, </xsl:if></xsl:for-each>", "<xsl:call-template name="cleanQuote"><xsl:with-param name="string"><xsl:value-of select="pa:description"/></xsl:with-param></xsl:call-template>", "<xsl:value-of select="@asctime"/>"]</xsl:for-each>
        </script>
        <!-- GOOGLE Analytics Stuff -->
        <script type="text/javascript">
          var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
          document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
        </script>
        <script type="text/javascript">
          var pageTracker = _gat._getTracker("UA-3441054-1");
          pageTracker._initData();
          pageTracker._trackPageview();
        </script><!--End Google Analytics -->
      </head>
      <body>
        <xsl:apply-templates select="pa:rootTags"/>

        <div class="content">
          <div class="sidebar">
            <!-- If the number of photos per page is less than the number of photos
                 then show the page flicker -->
            <xsl:if test="pa:photos/@perPage &lt; pa:photos/@numPhotos">
              <xsl:variable name="hookParams">?<xsl:for-each select="/pa:tagBrowse/pa:hookArgs/pa:arg"><xsl:if test="@name != 'start'"><xsl:value-of select="@name"/>=<xsl:value-of select="@value"/>&amp;</xsl:if></xsl:for-each>start=</xsl:variable>
              <xsl:variable name="previousPageStart"><xsl:value-of select="pa:photos/@startPhoto - pa:photos/@perPage"/></xsl:variable>
              <xsl:variable name="nextPageStart"><xsl:value-of select="pa:photos/@startPhoto + pa:photos/@perPage"/></xsl:variable>
              <div class="pageFlicker">
                <xsl:if test="pa:photos/@startPhoto &gt; 1"><a href="{$hookParams}{$previousPageStart}">&lt;&lt;</a> </xsl:if>
                <xsl:value-of select="$pennavePhotoFlickerPhotos"/><xsl:value-of select="pa:photos/@startPhoto"/><xsl:value-of select="$pennavePhotoFlickerTo"/><xsl:value-of select="pa:photos/@stopPhoto"/><xsl:value-of select="$pennavePhotoFlickerOf"/><xsl:value-of select="pa:photos/@numPhotos"/>
          	    <xsl:if test="pa:photos/@stopPhoto &lt; pa:photos/@numPhotos"><a href="{$hookParams}{$nextPageStart}">&gt;&gt;</a></xsl:if>
              </div>
            </xsl:if>
            <xsl:apply-templates select="pa:tagCloud"/>
            <div class="photoInfo" id="photoInfo">
              <span id="photoInfoFilename" class="photoInfoField"><xsl:value-of select="$pennavePhotoInfoFilename"/>&#32;<span class="photoInfoData" id="photoInfoFilenameData"></span></span>
              <span id="photoInfoSize" class="photoInfoField"><xsl:value-of select="$pennavePhotoInfoSize"/>&#32;<span id="photoInfoWidthData" class="photoInfoData"></span> x <span id="photoInfoHeightData" class="photoInfoData"></span></span>
              <span id="photoInfoTags" class="photoInfoField"><xsl:value-of select="$pennavePhotoInfoTags"/>&#32;<span id="photoInfoTagsData" class="photoInfoData"/></span>
              <span id="photoInfoDescription" class="photoInfoField"><xsl:value-of select="$pennavePhotoInfoDescription"/>&#32;<span id="photoInfoDescriptionData" class="photoInfoData"/></span>
              <span id="photoInfoDate" class="photoInfoField"><xsl:value-of select="$pennavePhotoInfoDate"/>&#32;<span id="photoInfoDateData" class="photoInfoData"/></span>
            </div>
          </div>
          <div class="main">
            <xsl:apply-templates select="pa:photos"/>
          </div>
        </div>          
      </body>
    </html>
  </xsl:template>

  <!-- ********* -->
  <!-- photoView -->
  <!-- ********* -->
  <xsl:template match="pa:photoView">
    <xsl:variable name="imageWidth"><xsl:value-of select="/pa:photoView/@displayWidth"/></xsl:variable>
    <xsl:variable name="imageHeight"><xsl:value-of select="/pa:photoView/@displayHeight"/></xsl:variable>
    <xsl:variable name="heightRatio"><xsl:value-of select="/pa:photoView/pa:photo/@height div $imageHeight"/></xsl:variable>
    <xsl:variable name="widthRatio"><xsl:value-of select="/pa:photoView/pa:photo/@width div $imageWidth"/></xsl:variable>
    
    <xsl:variable name="dimRatio"><xsl:value-of select="/pa:photoView/pa:photo/@width div /pa:photoView/pa:photo/@height"/></xsl:variable>
    <xsl:variable name="displayDimRatio"><xsl:value-of select="$imageWidth div $imageHeight"/></xsl:variable>
    
    <!-- go through the process of calculcating the images width and height -->
    <xsl:variable name="displayHeight">
      <xsl:choose>
        <xsl:when test="$dimRatio &lt; $displayDimRatio"><xsl:value-of select="$imageHeight"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="/pa:photoView/pa:photo/@height div $widthRatio"/></xsl:otherwise>
      </xsl:choose>
    </xsl:variable>

    <xsl:variable name="topPadding"><xsl:choose><xsl:when test="/pa:photoView/pa:photo/@height"><xsl:value-of select="round(($imageHeight - $displayHeight) div 2)"/></xsl:when><xsl:otherwise>0</xsl:otherwise></xsl:choose></xsl:variable>

    <html>
      <head>
        <title><xsl:value-of select="$pennaveViewPageTitle"/></title>
        <link rel="stylesheet" type="text/css" href="{/*/@prefix}/css/pennave.css"/>
        <script type="text/javascript" src="{/*/@prefix}/js/tagSelections.js"/>
        <script language="javascript">
          var prefix="<xsl:value-of select="/*/@prefix"/>";
          var tagPrefix="<xsl:for-each select="/*/pa:rootTags/pa:tag">/<xsl:value-of select="@id"/></xsl:for-each>";
        </script>
      </head>
      <body class="photoView">
        <xsl:apply-templates select="/pa:photoView/pa:rootTags"/>
        <table width="100%">
          <tr><th><xsl:value-of select="/pa:photoView/pa:photo/@name"/></th></tr>
          <tr>
            <td class="mainPhoto" align="center" valign="top">
              <xsl:variable name="versionHook"><xsl:if test="/pa:photoView/pa:photo/@version">version/<xsl:value-of select="/pa:photoView/pa:photo/@version"/>/</xsl:if></xsl:variable>
              <span class="mainPhotoCell"  style="padding-top: {$topPadding}px; padding-bottom: {$topPadding}px;"><a href="{/*/@prefix}/images/original/{/pa:photoView/pa:photo/@id}/{$versionHook}"><img src="{/*/@prefix}/images/medium/{/pa:photoView/pa:photo/@id}/{$versionHook}" border="0" alt="{/pa:photoView/pa:photo/pa:description}"/></a></span>
              <xsl:if test="/pa:photoView/pa:photo/pa:description"><span class="photoDescription"><xsl:value-of select="/pa:photoView/pa:photo/pa:description"/></span></xsl:if>

            </td>
            <td class="photoFlicker" valign="top">
              <xsl:choose>
                <xsl:when test="/pa:photoView/pa:previousPhoto/pa:photo">
                  <xsl:apply-templates select="/pa:photoView/pa:previousPhoto/pa:photo"/>
                </xsl:when>
                <xsl:otherwise>
                  <div class="photoThumbnail" style="float: none;"><xsl:value-of select="$pennaveYouAreOnTheFirstPhoto"/></div>
                </xsl:otherwise>
              </xsl:choose>
              <xsl:choose>
                <xsl:when test="/pa:photoView/pa:nextPhoto/pa:photo">
                  <xsl:apply-templates select="/pa:photoView/pa:nextPhoto/pa:photo"/>
                </xsl:when>
                <xsl:otherwise>
                  <div class="photoThumbnail"><xsl:value-of select="$pennaveYouAreOnTheLastPhoto"/></div>
                </xsl:otherwise>
              </xsl:choose>
              <xsl:if test="/pa:photoView/pa:photo/pa:tags/pa:tag">
              <div>
                <span class="photoFlickerTags">
                  <!-- <xsl:variable name="urlPrefix"><xsl:value-of select="/pa:photoView/@prefix"/>/view/<xsl:value-of select="/pa:photoView/pa:photo/@id"/>/tags<xsl:for-each select="/pa:photoView/pa:rootTags/pa:tag">/<xsl:value-of select="@id"/></xsl:for-each></xsl:variable> -->
                  <xsl:variable name="urlPrefix"><xsl:value-of select="$viewPrefix"/><xsl:value-of select="$tagPrefix"/></xsl:variable>

                    <xsl:value-of select="$pennaveAdditionalTags"/>
                    <ul>
                      <xsl:for-each select="/pa:photoView/pa:photo/pa:tags/pa:tag"><li><a href="{$urlPrefix}{@id}/{$versionPrefix}" title="{$pennaveAddTagFilterPre}{.}{$pennaveAddTagFilterPost}"><xsl:value-of select="."/></a></li></xsl:for-each>
                    </ul>
                </span>
              </div>
              </xsl:if>
              <!-- Display multiple versions of the photo -->
			  <xsl:if test="/pa:photoView/pa:photo/pa:versions/pa:version">
                <div>
                  <span class="photoVersions">
                    <xsl:value-of select="$pennaveViewingVersion"/>
                    <ul>
                      <li><xsl:value-of select="/pa:photoView/pa:photo/pa:versions/pa:version[@id=/pa:photoView/pa:photo/@version]/@name"/><xsl:if test="/pa:photoView/pa:photo/pa:versions/pa:version[@id=/pa:photoView/pa:photo/@version]/@default='true'">&#160;(default)</xsl:if></li>
                    </ul>
                    <xsl:value-of select="$pennaveAdditionalVersions"/>
                  	<ul>
                  	  <xsl:for-each select="/pa:photoView/pa:photo/pa:versions/pa:version">
                  	    <xsl:variable name="linkURL"><xsl:value-of select="$viewPrefix"/><xsl:value-of select="$tagPrefix"/><xsl:if test="not(@default='true')">version/<xsl:value-of select="@id"/>/</xsl:if></xsl:variable>
                  	    <xsl:if test="not(@shown='true')"><li><a href="{$linkURL}"><xsl:value-of select="@name"/></a><xsl:if test="@default='true'">&#160;(default)</xsl:if></li></xsl:if>
                  	  </xsl:for-each>
                  	</ul>
                  </span>
                </div>
              </xsl:if>
              <div>
                <span class="viewOptions"> 
                  <xsl:value-of select="$pennaveViewingOptions"/>
                  <ul>
                    <xsl:if test="count(/pa:photoView/pa:rootTags/pa:tag) &gt; 0"><li><a href="{@prefix}/view/{/pa:photoView/pa:photo/@id}"><xsl:value-of select="$pennaveUnselectAllTags"/></a></li></xsl:if>
                    <li><a href="javascript:launchSlideShow();"><xsl:value-of select="$pennaveLaunchSlideShow"/></a></li>
                    <xsl:variable name="browseURL"><xsl:value-of select="//@prefix"/>/tags/<xsl:for-each select="//pa:rootTags/pa:tag"><xsl:value-of select="@id"/>/</xsl:for-each></xsl:variable>
                    <li><a href="{$browseURL}" title="{$pennaveReturnToBrowseModeAlt}"><xsl:value-of select="$pennaveReturnToBrowseMode"/></a></li>
                  </ul>
                </span>
              </div>
              <div>
                <span class="exifTags">
                  <xsl:choose>
                    <xsl:when test="/pa:photoView/pa:photo/exif:IFD/exif:model"><xsl:value-of select="$pennaveTakenWithA"/><xsl:value-of select="/pa:photoView/pa:photo/exif:IFD/exif:model"/><xsl:if test="/pa:photoView/pa:photo/@asctime"> <xsl:value-of select="$pennaveTakenWithAOn"/> <xsl:value-of select="/pa:photoView/pa:photo/@asctime"/></xsl:if>.<br/></xsl:when>
                    <xsl:when test="/pa:photoView/pa:photo/@asctime"><xsl:value-of select="$pennaveTakenOn"/> <xsl:value-of select="/pa:photoView/pa:photo/@asctime"/>.<br/></xsl:when>
                  </xsl:choose>
                </span>
              </div>
            </td>
          </tr>
        </table>
      </body>
    </html>
  </xsl:template>

  <!-- ******** -->
  <!-- tagCloud -->
  <!-- ******** -->
  <xsl:template match="pa:tagCloud">
    <div class="tagCloud" name="tagCloud">
      <span class="tagCloudTitle"><xsl:value-of select="$pennaveTags"/></span>
      <span class="tagCloudTags">
        <xsl:apply-templates select="pa:tag"/>
      </span>
      <xsl:if test="count(//pa:tagCloud/pa:tag) &gt; 30"><span class="tagCloudToggle"><a href="javascript:showAllTagsToggle('{$pennaveShowAllTags}', '{$pennaveShowTop30Tags}');" id="showAllTags"><xsl:value-of select="$pennaveShowAllTags"/></a></span></xsl:if>
      <xsl:if test="count(/pa:tagBrowse/pa:rootTags/pa:tag) &gt; 0"><span class="tagCloudToggle"><a href="{/pa:tagBrowse/@prefix}/tags/"><xsl:value-of select="$pennaveUnselectAllTags"/></a></span></xsl:if>
    </div>
  </xsl:template>

  <!-- *** -->
  <!-- tag -->
  <!-- *** -->
  <xsl:template match="pa:tagCloud/pa:tag">
    <!-- set the class of the span as "topTags" if it's in the top 30 tags, otherwise use "nonTopTags" -->
    <xsl:variable name="defaultStatus">
      <xsl:choose><xsl:when test="@rank &lt; 30">topTags</xsl:when><xsl:otherwise>nonTopTags</xsl:otherwise></xsl:choose>
    </xsl:variable>
    <span class="{$defaultStatus}" name="{$defaultStatus}"><span class="tagCloudSize{@size}"><a href="{/pa:tagBrowse/@prefix}/{$tagPrefix}{@id}/" onMouseOver="highlightPhotos({@id});" onMouseOut="unhighlightPhotos({@id});"><xsl:value-of select="."/><xsl:if test="@hasChildren = 1"><span class="tagCloudHasChildren">+</span></xsl:if></a><span class="tagCloudTip"><xsl:value-of select="@count"/> photo<xsl:if test="@count &gt; 1">s</xsl:if></span></span></span><xsl:text> </xsl:text>
  </xsl:template>

  <!-- ******** -->
  <!-- rootTags -->
  <!-- ******** -->
  <xsl:template match="pa:rootTags">
    <div class="rootTags" id="rootTags">
      <xsl:if test="count(pa:tag) &gt; 0">
        <xsl:value-of select="$pennaveViewingTags"/><xsl:apply-templates/>
      </xsl:if>
      <xsl:if test="count(pa:tag) = 0">&#160;</xsl:if>
      <div class="pennAveFooter">
        <xsl:value-of select="$pennavePoweredByPennavePre"/><a href="http://pennave.sf.net/" title="{$pennaveVisitThePennaveHomePage}">PennAve<xsl:value-of select="$pennavePoweredByPennavePost"/></a>
      </div>

    </div>
  </xsl:template>

  <xsl:template match="pa:rootTags/pa:tag">
  	<xsl:variable name="viewOnlyTagURL">
  		<xsl:if test="/pa:photoView"><xsl:value-of select="/pa:photoView/@prefix"/>/view/<xsl:value-of select="/pa:photoView/pa:photo/@id"/>/tags/<xsl:value-of select="@id"/>/<xsl:value-of select="$versionPrefix"/></xsl:if>
  		<xsl:if test="/pa:tagBrowse"><xsl:value-of select="/pa:tagBrowse/@prefix"/>/tags/<xsl:value-of select="@id"/>/</xsl:if>
  	</xsl:variable>
  	<xsl:variable name="removeTagURL">
  		<xsl:if test="/pa:photoView"><xsl:value-of select="/pa:photoView/@prefix"/>/view/<xsl:value-of select="/pa:photoView/pa:photo/@id"/>/<xsl:if test="count(../pa:tag) - 1 > 0">tags/<xsl:for-each select="preceding-sibling::pa:tag | following-sibling::pa:tag"><xsl:value-of select="@id"/>/</xsl:for-each></xsl:if><xsl:value-of select="$versionPrefix"/></xsl:if>
  		<xsl:if test="/pa:tagBrowse"><xsl:value-of select="/pa:tagBrowse/@prefix"/>/tags/<xsl:for-each select="preceding-sibling::pa:tag | following-sibling::pa:tag"><xsl:value-of select="@id"/>/</xsl:for-each></xsl:if>
  	</xsl:variable>
    <a href="{$viewOnlyTagURL}" title="{$pennaveShowOnlyTheTagPre}{.}{$pennaveShowOnlyTheTagPost}"><xsl:value-of select="."/></a>&#160;<span class="removeTagLink">[<a href="{$removeTagURL}" class="removeTagLink" title="{$pennaveRemoveTheTagPre}{.}{$pennaveRemoveTheTagPost}">-</a>]</span><xsl:if test="following-sibling::pa:tag">&#160;&#x2022;&#160;</xsl:if>
  </xsl:template>

  <!-- ****** -->
  <!-- photos -->
  <!-- ****** -->
  <xsl:template match="pa:photos">
    <div class="photoBlock">
      <xsl:apply-templates select="pa:photo"/>
    </div>
  </xsl:template>

  <!-- ***** -->
  <!-- photo -->
  <!-- ***** -->
  <xsl:template match="pa:photo">
    <!-- this stuff is required to calculate the proper top padding for photos
         in the gallery.  Largely required because CSS does not have a vertical
         center attribute -->
    <xsl:variable name="imageHeight">
      <xsl:choose>
        <xsl:when test="/pa:tagBrowse"><xsl:value-of select="/pa:tagBrowse/pa:photos/@thumbnailHeight"/></xsl:when>
        <xsl:when test="/pa:photoView/@thumbnailHeight"><xsl:value-of select="/pa:photoView/@thumbnailHeight"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="80"/></xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="imageWidth">
      <xsl:choose>
        <xsl:when test="/pa:tagBrowse"><xsl:value-of select="/pa:tagBrowse/pa:photos/@thumbnailWidth"/></xsl:when>
        <xsl:when test="/pa:photoView/@thumbnailWidth"><xsl:value-of select="/pa:photoView/@thumbnailWidth"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="120"/></xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="heightRatio">
      <xsl:value-of select="@height div $imageHeight"/>
    </xsl:variable>
    <xsl:variable name="widthRatio">
      <xsl:value-of select="@width div $imageWidth"/>
    </xsl:variable>
    <xsl:variable name="thumbnailHeight">
      <xsl:choose>
        <xsl:when test="$heightRatio > $widthRatio"><xsl:value-of select="round(@height div $heightRatio)"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="round(@height div $widthRatio)"/></xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="thumbnailWidth">
      <xsl:choose>
        <xsl:when test="$heightRatio > $widthRatio"><xsl:value-of select="round(@width div $heightRatio)"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="round(@width div $widthRatio)"/></xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="topPadding"><xsl:choose><xsl:when test="$thumbnailHeight != 'NaN'"><xsl:value-of select="round(($imageHeight - $thumbnailHeight) div 2)"/></xsl:when><xsl:otherwise>0</xsl:otherwise></xsl:choose></xsl:variable>
	<xsl:variable name="sidePadding"><xsl:choose><xsl:when test="$thumbnailWidth != 'NaN'"><xsl:value-of select="round(($imageWidth - $thumbnailWidth) div 2)"/></xsl:when><xsl:otherwise>0</xsl:otherwise></xsl:choose></xsl:variable>
    <xsl:variable name="tagLinks">
      <xsl:if test="/*/pa:rootTags/pa:tag">
        tags<xsl:for-each select="/*/pa:rootTags/pa:tag">/<xsl:value-of select="@id"/></xsl:for-each>/
      </xsl:if>
    </xsl:variable>
    <xsl:variable name="altText"><xsl:value-of select="@name"/><xsl:if test="pa:description">: <xsl:value-of select="pa:description"/></xsl:if></xsl:variable>
    <xsl:choose>
      <xsl:when test="/pa:photoView">
        <div class="photoThumbnail" id="photoThumbnail{@id}"><a href="{/*/@prefix}/view/{@id}/{normalize-space($tagLinks)}"><img src="{/*/@prefix}/images/thumbnail/{@id}" style="padding-top: {$topPadding}px; padding-bottom: {$topPadding}px; padding-left: {$sidePadding}px; padding-right: {$sidePadding}px;" border="0" alt="{$altText}"/></a></div>
      </xsl:when>
      <xsl:otherwise>
        <div class="photoThumbnail" id="photoThumbnail{@id}" onMouseOver="showPhotoInfoOn({@id})" onMouseOut="showPhotoInfoOff({@id})"><a href="{/*/@prefix}/view/{@id}/{normalize-space($tagLinks)}"><img src="{/*/@prefix}/images/thumbnail/{@id}" style="padding-top: {$topPadding}px; padding-bottom: {$topPadding}px; padding-left: {$sidePadding}px; padding-right: {$sidePadding}px;" border="0" alt="{$altText}"/></a></div>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
</xsl:stylesheet>
