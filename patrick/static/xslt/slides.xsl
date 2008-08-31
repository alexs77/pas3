<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output doctype-public="-//W3C/DTD XHTML 1.0 Strict//EN" indent="yes" method="html"/>

  <!-- The photoview template is used when viewing a single photo -->
  <!-- it also provides forward and backward links -->
  <xsl:template match="slideshow">
    <html>
      <head>
        <title>Viewing Slideshow</title>
        <link rel="stylesheet" type="text/css" href="{/*/@prefix}/css/slides.css"/>
        <script language="javascript">
          var prefix="<xsl:value-of select="/*/@prefix"/>";
          var tagPrefix="<xsl:for-each select="rootTags/tag">/<xsl:value-of select="@id"/></xsl:for-each>";
          var nextImage = 1;
          var currentImage = -1;
        </script>
        <script type="text/javascript" src="{/*/@prefix}/js/slides.js"/>
      </head>
      <body onload="startSlideShow();">
        <div class="picture" id="frame1">
        </div>
        <div class="picture" id="frame2">
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>

