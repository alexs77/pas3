<?xml version="1.0"?>
<xsl:stylesheet version="1.0" 
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:variable name="pennaveBrowsePageTitle">PennAve - Übersichtsmodus</xsl:variable>
  <xsl:variable name="pennaveViewPageTitle">PennAve - Photoanzeige</xsl:variable>
  <xsl:variable name="pennaveYouAreOnTheFirstPhoto">Du bist auf dem ersten Photo</xsl:variable>
  <xsl:variable name="pennaveYouAreOnTheLastPhoto">Du bist auf dem letzten Photo</xsl:variable>

  <xsl:variable name="pennavePhotoFlickerPhotos">Photos&#32;</xsl:variable>
  <xsl:variable name="pennavePhotoFlickerTo">&#32;bis&#32;</xsl:variable>
  <xsl:variable name="pennavePhotoFlickerOf">&#32;von&#32;</xsl:variable>
    
  <xsl:variable name="pennavePhotoInfoFilename">Dateiname:&#32;</xsl:variable>
  <xsl:variable name="pennavePhotoInfoSize">Größe:&#32;</xsl:variable>
  <xsl:variable name="pennavePhotoInfoTags">Schlagwörter:&#32;</xsl:variable>
  <xsl:variable name="pennavePhotoInfoDescription">Beschreibung:&#32;</xsl:variable>
  <xsl:variable name="pennavePhotoInfoDate">Datum:&#32;</xsl:variable>
  
  <xsl:variable name="pennaveAdditionalTags">Weitere Schlagwörter:</xsl:variable>
  <xsl:variable name="pennaveAddTagFilterPre">&quot;</xsl:variable>
  <xsl:variable name="pennaveAddTagFilterPost">&quot; als zusätzlich zu filterndes Schlagwort hinzufügen</xsl:variable>
  
  <xsl:variable name="pennaveViewingVersion">Angezeigte Version:</xsl:variable>
  <xsl:variable name="pennaveAdditionalVersions">Weitere Versionen:</xsl:variable>
  
  <xsl:variable name="pennaveViewingOptions">Optionen:</xsl:variable>
  <xsl:variable name="pennaveUnselectAllTags">Alle Schlagwörter abwählen</xsl:variable>
  <xsl:variable name="pennaveLaunchSlideShow">Diashow starten</xsl:variable>
  
  <xsl:variable name="pennaveReturnToBrowseMode">Zum Übersichtsmodus zurückkehren</xsl:variable>
  <xsl:variable name="pennaveReturnToBrowseModeAlt">Zur Seite mit vielen Bildern zurückkehren, um schneller zu durchsuchen</xsl:variable>
  
  <xsl:variable name="pennaveTakenWithA">Aufgenommen mit einer&#32;</xsl:variable>
  <xsl:variable name="pennaveTakenWithAOn">&#32;am&#32;</xsl:variable>
  <xsl:variable name="pennaveTakenOn">Aufgenommen am&#32;</xsl:variable>
  
  <xsl:variable name="pennaveTags">Schlagwörter</xsl:variable>
  <xsl:variable name="pennaveShowAllTags">Alle Schlagwörter anzeigen</xsl:variable>
  <xsl:variable name="pennaveShowTop30Tags">Die 30 Top-Schlagwörter anzeigen</xsl:variable>
  
  <xsl:variable name="pennaveViewingTags">Angezeigte Schlagwörter:&#32;</xsl:variable>
  <xsl:variable name="pennaveVisitThePennaveHomePage">Die PennAve Home Page besuchen</xsl:variable>
  <xsl:variable name="pennavePoweredByPennavePre">Powered by&#32;</xsl:variable>
  <xsl:variable name="pennavePoweredByPennavePost"></xsl:variable>
  
  <xsl:variable name="pennaveShowOnlyTheTagPre">Nur das Schlagwort &quot;</xsl:variable>
  <xsl:variable name="pennaveShowOnlyTheTagPost">&quot; anzeigen</xsl:variable>
  <xsl:variable name="pennaveRemoveTheTagPre">Das Schlagwort &quot;</xsl:variable>
  <xsl:variable name="pennaveRemoveTheTagPost">&quot; entfernen</xsl:variable>
</xsl:stylesheet>