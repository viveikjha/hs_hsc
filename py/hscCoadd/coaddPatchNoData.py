#!/usr/bin/env python
# encoding: utf-8
"""Generate NoData mask for HSC coadd image."""

from __future__ import division

import os
import glob
import copy
import argparse
import numpy as np
from distutils.version import StrictVersion

import lsst.daf.persistence as dafPersist
# import lsst.afw.coord as afwCoord
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage

# Matplotlib default settings
import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams['figure.figsize'] = 12, 10
mpl.rcParams['xtick.major.size'] = 8.0
mpl.rcParams['xtick.major.width'] = 1.5
mpl.rcParams['xtick.minor.size'] = 4.0
mpl.rcParams['xtick.minor.width'] = 1.5
mpl.rcParams['ytick.major.size'] = 8.0
mpl.rcParams['ytick.major.width'] = 1.5
mpl.rcParams['ytick.minor.size'] = 4.0
# mpl.rcParams['ytick.minor.width'] = 1.5
mpl.rc('axes', linewidth=2)

# Shapely related imports
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import cascaded_union

from scipy import ndimage
from skimage.measure import find_contours, approximate_polygon

# TODO: Need to be more organized
import coaddPatchShape as cdPatch
import coaddTractShape as cdTract


def bboxToRaDec(bbox, wcs):
    """
    Get the corners of a BBox and convert them to lists of RA and Dec.

    From Steve's showVisitSkyMap.py
    """
    corners = []
    for corner in bbox.getCorners():
        p = afwGeom.Point2D(corner.getX(), corner.getY())
        coord = wcs.pixelToSky(p).toIcrs()
        corners.append([coord.getRa().asDegrees(), coord.getDec().asDegrees()])
    ra, dec = zip(*corners)
    return ra, dec


def percent(values, p=0.5):
    """
    Return a faction of the way between the min and max values in a list.

    From Steve's showVisitSkyMap.py
    """
    m = min(values)
    interval = max(values) - m
    return m + p*interval


def imgAddNoise(im, gaussian, factor):
    """Add Gaussian noises."""
    im = ndimage.gaussian_filter(im, gaussian)
    im += factor * np.random.random(im.shape)

    return im


def getPixelRaDec(wcs, xx, yy, xStart=0, yStart=0):
    """Convert pixels coordinates into Ra, Dec."""
    coord = wcs.pixelToSky((xStart + xx - 1),
                           (yStart + yy - 1)).toIcrs()

    ra = coord.getRa().asDegrees()
    dec = coord.getDec().asDegrees()

    return ra, dec


def getPolyLine(polyCoords):
    """
    Convert polygon coordinates into a DS9 region coordinates.

    # The format for Polygon in DS9 is:
    # Usage: polygon x1 y1 x2 y2 x3 y3 ...
    """
    coordShow = map(lambda x: str(x[0]) + ' ' + str(x[1]) + ' ', polyCoords)

    polyLine = 'polygon '
    for p in coordShow:
        polyLine += p

    polyLine += '\n'

    return polyLine


def polySaveReg(poly, regName, listPoly=False, color='blue',
                verbose=True):
    """
    Save the Polygon region into a DS9 .reg file.

    !!! Make sure that the Polygon is simple
    """
    # DS9 region file header
    head1 = '# Region file format: DS9 version 4.1\n'
    head2 = 'global color=%s width=2\n' % color
    head3 = 'icrs\n'
    # Open the output file and write the header
    regFile = open(regName, 'w')
    regFile.write(head1)
    regFile.write(head2)
    regFile.write(head3)

    if listPoly:
        for ii, pp in enumerate(poly):
            if pp.geom_type is "Polygon":
                # Get the coordinates for every point in the polygon
                # Still generate "Multi-part geometries do not provide a
                # coordinate sequence" Error
                try:
                    polyCoords = pp.boundary.coords[:]
                    polyLine = getPolyLine(polyCoords)
                    regFile.write(polyLine)
                except NotImplementedError:
                    # Right now the work-around is to "puff-up" the Polygon a
                    # little bit; This should be fine for small polygon shape
                    # For very rare case, this could fail !!
                    # Lower the tolerance can fix this problem
                    if verbose:
                        print "### Multi-Part Polygon: %d" % ii
                    pp = pp.buffer(1)
                    if verbose:
                        print "### Puff it up a little bit !"
                    polyCoords = pp.exterior.coords[:]
                    polyLine = getPolyLine(polyCoords)
                    regFile.write(polyLine)
            elif pp.geom_type is "MultiPolygon":
                for mm in pp.geoms:
                    try:
                        polyCoords = mm.boundary.coords[:]
                        polyLine = getPolyLine(polyCoords)
                        regFile.write(polyLine)
                    except NotImplementedError:
                        if verbose:
                            print "### Multi-Part Polygon: %d" % ii
                        mm = mm.buffer(1)
                        polyCoords = mm.exterior.coords[:]
                        polyLine = getPolyLine(polyCoords)
                        regFile.write(polyLine)
    else:
        if poly.geom_type is "Polygon":
            try:
                polyCoords = poly.boundary.coords[:]
                polyLine = getPolyLine(polyCoords)
                regFile.write(polyLine)
            except NotImplementedError:
                if verbose:
                    print "### Multi-Part Polygon: %d" % ii
                poly = poly.buffer(1)
                polyCoords = poly.exterior.coords[:]
                polyLine = getPolyLine(polyCoords)
                regFile.write(polyLine)
        elif poly.geom_type is "MultiPolygon":
            for mm in poly.geoms:
                try:
                    polyCoords = mm.boundary.coords[:]
                    polyLine = getPolyLine(polyCoords)
                    regFile.write(polyLine)
                except NotImplementedError:
                    if verbose:
                        print "### Multi-Part Polygon: %d" % ii
                    mm = mm.buffer(1)
                    polyCoords = mm.exterior.coords[:]
                    polyLine = getPolyLine(polyCoords)
                    regFile.write(polyLine)

    regFile.close()


def listAllCatalog(rootDir, filter, checkSize=True, minSize=20.0,
                   tract=None):
    """Find all deepCoadd_ref catalogs."""
    if tract is None:
        tractStr = '*'
    else:
        tractStr = str(tract).strip()

    if rootDir[-1] is '/':
        searchDir = (rootDir + 'deepCoadd-results/merged/' + tractStr +
                     '/*/ref*.fits')
        imgDir = rootDir + 'deepCoadd/' + filter.upper() + '/'
    else:
        searchDir = (rootDir + '/deepCoadd-results/merged/' + tractStr +
                     '/*/ref*.fits')
        imgDir = rootDir + '/deepCoadd/' + filter.upper() + '/'

    fitsList = glob.glob(searchDir)
    if checkSize:
        catList = []
        for fits in fitsList:
            if (os.path.getsize(fits) / 1024.0 / 1024.0) >= minSize:
                catList.append(fits)
            else:
                fileSize = os.path.getsize(fits)
                print "#### WARNING: %s has size %7d Kb " % (fits,
                                                             fileSize)
    else:
        catList = fitsList

    useList = []
    for catName in catList:
        catSeg = os.path.basename(catName).split('-')
        trStr = catSeg[1]
        paStr = catSeg[2].split('.')[0]
        useList.append(imgDir + trStr + '/' + paStr + '.fits')

    catArr = map(lambda x: x, catList)
    useArr = map(lambda x: x, useList)

    return useArr, catArr


def listAllImages(rootDir, filter, checkSize=True, minSize=70.0, tract=None):
    """Find all deepCoadd_calexp images."""
    if tract is None:
        tractStr = '*'
    else:
        tractStr = str(tract).strip()

    """XXX This only works for the new pipeline"""
    if rootDir[-1] is '/':
        searchDir = (rootDir + 'deepCoadd/' + filter.upper() + '/' +
                     tractStr + '/*.fits')
    else:
        searchDir = (rootDir + '/deepCoadd/' + filter.upper() + '/' +
                     tractStr + '/*.fits')

    fitsList = glob.glob(searchDir)
    if checkSize:
        useList = []
        for fits in fitsList:
            if (os.path.getsize(fits) / 1024.0 / 1024.0) >= minSize:
                useList.append(fits)
            else:
                fileSize = os.path.getsize(fits)
                print "#### WARNING: %s has size %7d Kb " % (fits,
                                                             fileSize)
    else:
        useList = fitsList

    return map(lambda x: x, useList)


def coaddPatchNoData(rootDir, tract, patch, filter, prefix='hsc_coadd',
                     savePNG=True, verbose=True, tolerence=4,
                     minArea=10000, clobber=False, butler=None, dataId=None,
                     workDir='', starMask=False, notDeblend=True):
    """
    Generate NoData Mask for one Patch.

    Parameters:
    """
    pipeVersion = dafPersist.eupsVersions.EupsVersions().versions['hscPipe']
    if StrictVersion(pipeVersion) >= StrictVersion('3.9.0'):
        coaddData = "deepCoadd_calexp"
    else:
        coaddData = "deepCoadd"

    # Get the name of the wkb and deg file
    strTractPatch = (str(tract).strip() + '_' + patch + '_' + filter)
    # For all the accepted regions
    if (workDir is not '') and (workDir[-1] is not '/'):
        workDir += '/'
    noDataAllWkb = workDir + prefix + '_' + strTractPatch + '_nodata_all.wkb'
    fileExist1 = os.path.isfile(noDataAllWkb)
    noDataAllReg = workDir + prefix + '_' + strTractPatch + '_nodata_all.reg'
    fileExist2 = os.path.isfile(noDataAllReg)
    # For all the big mask regions
    noDataBigWkb = workDir + prefix + '_' + strTractPatch + '_nodata_big.wkb'
    noDataBigReg = workDir + prefix + '_' + strTractPatch + '_nodata_big.reg'

    # See if all the files have been generated
    fileAllExist = (fileExist1 and fileExist2)

    # Only generate new one when
    #  1) Not all files are available
    #  2) All available, but clobber = True
    if (not fileAllExist) or clobber:

        # Make a butler and specify the dataID
        if butler is None:
            butler = dafPersist.Butler(rootDir)
        if dataId is None:
            dataId = {'tract': tract, 'patch': patch, 'filter': filter}

        # Get the name of the input fits image
        if StrictVersion(pipeVersion) >= StrictVersion('3.9.0'):
            coaddImg = '%s/calexp-%s-%s-%s.fits' % (patch, filter,
                                                    tract, patch)
        else:
            coaddImg = '%s.fits' % (patch)
        if rootDir[-1] is '/':
            fitsName = (rootDir + 'deepCoadd/' + filter + '/' +
                        str(tract).strip() + '/' + coaddImg)
        else:
            fitsName = (rootDir + '/deepCoadd/' + filter + '/' +
                        str(tract).strip() + '/' + coaddImg)
        if not os.path.isfile(fitsName):
            raise Exception('Can not find the input fits image: %s' % fitsName)

        # Get the name of the png file
        titlePng = prefix + strTractPatch + '_NODATA'
        noDataPng = prefix + '_' + strTractPatch + '_nodata.png'

        if verbose:
            print "## Reading Fits Image: %s" % fitsName

        # Get the exposure from the butler
        # TODO Be careful here, some of the coadd image files
        #      on the disk are not useful
        try:
            calExp = butler.get(coaddData, dataId, immediate=True)
        except Exception:
            print "Oops! Can not read this image: %s !" % fitsName
        else:
            # Get the Bounding Box of the image
            bbox = calExp.getBBox(afwImage.PARENT)
            xBegin, yBegin = bbox.getBeginX(), bbox.getBeginY()
            # Get the WCS information
            imgWcs = calExp.getWcs()

            # Get the object for mask plane
            mskImg = calExp.getMaskedImage().getMask()

            # Extract the NO_DATA plane
            noData = copy.deepcopy(mskImg)
            noData.removeAndClearMaskPlane('EDGE', True)
            noData.removeAndClearMaskPlane('CLIPPED', True)
            noData.removeAndClearMaskPlane('CROSSTALK', True)
            noData.removeAndClearMaskPlane('UNMASKEDNAN', True)
            noData.removeAndClearMaskPlane('DETECTED', True)
            noData.removeAndClearMaskPlane('DETECTED_NEGATIVE', True)
            if not notDeblend:
                noData.removeAndClearMaskPlane('NOT_DEBLENDED', True)
            if not starMask:
                noData.removeAndClearMaskPlane('BRIGHT_OBJECT', True)
            # Return the mask image array
            noDataArr = noData.getArray()
            noDataArr[noDataArr > 0] = 10

            # Pad the 2-D array by a little
            noDataArr = np.lib.pad(noDataArr, ((1, 1), (1, 1)), 'constant',
                                   constant_values=0)

            # Try a very different approach: Using the find_contours and
            # approximate_polygon methods from scikit-images package
            maskShapes = []  # For all the accepted mask regions
            maskCoords = []  # For the "corner" coordinates of these regions
            maskAreas = []  # The sizes of all regions

            # Only find the 0-level contour
            contoursAll = find_contours(noDataArr, 0)
            if verbose:
                print "### %d contours have been detected" % len(contoursAll)
            for maskContour in contoursAll:
                # Approximate one extracted contour into a polygon
                # tolerance decides the accuracy of the polygon, hence
                # the number of coords for each polygon.
                # Using large tolerance also means smaller number of final
                # polygons
                contourCoords = approximate_polygon(maskContour,
                                                    tolerance=tolerence)
                # Convert these coordinates into (RA, DEC) using the WCS
                contourSkyCoords = map(lambda x: [x[1], x[0]], contourCoords)
                contourRaDec = map(lambda x: getPixelRaDec(imgWcs, x[0], x[1],
                                                           xStart=xBegin,
                                                           yStart=yBegin),
                                   contourSkyCoords)
                # Require that any useful region must be at least an triangular
                if len(contourCoords) > 3:
                    # Form a lineString using these coordinates
                    maskLine = LineString(contourRaDec)
                    # Check if the lineString is valid and simple,
                    # so can be used to form a closed and simple polygon
                    # if maskLine.is_valid and maskLine.is_simple:
                    if maskLine.is_valid:
                        contourPoly = Polygon(contourRaDec)
                        # Fix the self-intersected polygon !! VERY USEFUL
                        if not contourPoly.is_valid:
                            contourPoly = contourPoly.buffer(0)
                        maskShapes.append(contourPoly)
                        maskCoords.append(contourRaDec)
                        maskAreas.append(Polygon(contourCoords).area)
            if verbose:
                print "### %d regions are useful" % len(maskAreas)

            # Isolate the large ones
            maskBigList = np.array(maskShapes)[np.where(np.array(maskAreas) >
                                                        minArea)]
            maskBigList = map(lambda x: x, maskBigList)

            nBig = len(maskBigList)
            if nBig > 0:
                if verbose:
                    print "### %d regions are large enough: " % nBig
                # Save all the masked regions to a .reg file
                polySaveReg(maskBigList, noDataBigReg, listPoly=True,
                            color='blue')
                # Also create a MultiPolygon object, and save a .wkb file
                maskBig = cascaded_union(maskBigList)
                cdPatch.polySaveWkb(maskBig, noDataBigWkb)
            else:
                maskBig = None
                if verbose:
                    print "### No region is larger than the minimum mask sizes"

            # Save all the masked regions to a .reg file
            polySaveReg(maskShapes, noDataAllReg, listPoly=True, color='red')
            # Also create a MultiPolygon object, and save a .wkb file
            maskAll = cascaded_union(maskShapes)
            cdPatch.polySaveWkb(maskAll, noDataAllWkb)

            if savePNG:
                if maskBig is None:
                    showNoDataMask(noDataAllWkb, title=titlePng,
                                   pngName=noDataPng)
                else:
                    showNoDataMask(noDataAllWkb, large=noDataBigWkb,
                                   title=titlePng, pngName=noDataPng)
    else:
        if verbose:
            print "### %d, %s has been reduced before! Skip!" % (tract, patch)


def saveTractFileList(tr, patch, filter, prefix, suffix):
    """Save a list of Tracts."""
    wkbLis = open(prefix + '_' + str(tr) + '_' + filter +
                  '_' + suffix + '_wkb.lis', 'w')
    regLis = open(prefix + '_' + str(tr) + '_' + filter +
                  '_' + suffix + '_reg.lis', 'w')

    for pp in patch:
        # Get the name of the wkb and deg file
        strTractPatch = (str(tr).strip() + '_' + pp + '_' + filter)
        # For all the accepted regions
        wkbLis.write(prefix + '_' + strTractPatch + '_' + suffix + '.wkb\n')
        regLis.write(prefix + '_' + strTractPatch + '_' + suffix + '.reg\n')

    wkbLis.close()
    regLis.close()


def combineRegFiles(listFile, output=None, check=True, local=True):
    """Combine a list of DS9 region files."""
    regList = open(listFile, 'r').readlines()
    nReg = len(regList)
    print "### Will combine %d .reg files" % nReg

    """ Get the directory for these files """
    regDir = os.path.dirname(os.path.abspath(listFile)) + '/'

    """ Get the name of the combined .reg files """
    if output is None:
        fileComb = os.path.splitext(os.path.split(listFile)[1])[0] + '.reg'
    else:
        fileComb = output
    if not local:
        fileComb = regDir + fileComb

    """ Open a new file to write"""
    regComb = open(fileComb, 'w')

    """ Go through every .reg file """
    for ii, reg in enumerate(regList):

        fileRead = regDir + reg.strip()

        if os.path.exists(fileRead):
            if ii == 0:
                regLines = open(fileRead, 'r').readlines()
                for line in regLines:
                    regComb.write(line)
            else:
                regLines = open(fileRead, 'r').readlines()[3:]
                for line in regLines:
                    regComb.write(line)
        elif not check:
            print "### Can not find the .reg file: %s" % fileRead
        else:
            raise Exception("Can not find the .reg file: %s !" % fileRead)

    regComb.close()


def combineWkbFiles(listFile, output=None, check=True, local=True,
                    listAll=False, allOutput=None):
    """Combine a list of .Wkb region files."""
    wkbList = open(listFile, 'r').readlines()
    nWkb = len(wkbList)
    print "### Will combine %d .wkb files" % nWkb

    """ Get the directory for these files """
    wkbDir = os.path.dirname(os.path.abspath(listFile)) + '/'

    """ Get the name of the combined .reg files """
    if output is None:
        fileComb = os.path.splitext(os.path.split(listFile)[1])[0] + '.wkb'
    else:
        fileComb = output
    if allOutput is None:
        fileList = (os.path.splitext(os.path.split(listFile)[1])[0] +
                    '_list.wkb')
    else:
        fileList = allOutput
    if not local:
        fileComb = wkbDir + fileComb
        fileList = wkbDir + fileList

    """ Go through every .wkb file """
    combWkb = []
    for wkb in wkbList:
        fileRead = wkbDir + wkb.strip()

        if os.path.exists(fileRead):
            wkbRead = cdPatch.polyReadWkb(fileRead)
            if wkbRead.geom_type is 'Polygon':
                combWkb.append(wkbRead)
            elif wkbRead.geom_type is 'MultiPolygon':
                geoms = wkbRead.geoms[:]
                for geom in geoms:
                    combWkb.append(geom)
        elif not check:
            print "### Can not find the .wkb file: %s" % fileRead
        else:
            raise Exception("Can not find the .wkb file: %s !" % fileRead)

    """ Take the cascaded_union of all the mask regions for a tract """
    unionWkb = cascaded_union(combWkb)

    """ Save the .wkb file """
    cdPatch.polySaveWkb(unionWkb, fileComb)

    if listAll:
        combList = MultiPolygon(combWkb)
        cdPatch.polySaveWkb(combList, fileList)


def batchPatchNoData(rootDir, filter='HSC-I', prefix='hsc_coadd',
                     saveList=True, notRun=False, checkCat=False,
                     starMask=False, notDeblend=True):
    """Generate NoData mask in batch mode."""
    # Get the list of coadded images in the direction
    if checkCat:
        imgList, catList = listAllCatalog(rootDir, filter)
    else:
        imgList = listAllImages(rootDir, filter, checkSize=True)
    nImg = len(imgList)
    print '### Will go through %d images !' % nImg

    # Get the list of tract and patch for these images
    tract = map(lambda x: int(x.split('/')[-2]), imgList)
    patch = map(lambda x: x.split('/')[-1].split('.')[0], imgList)

    # Get the uniqe tract
    trUniq = np.unique(tract)
    print "### There are %d unique tracts!" % len(trUniq)
    if saveList:
        for tr in trUniq:
            tArr = np.asarray(tract)
            pArr = np.asarray(patch)
            pMatch = pArr[tArr == tr]
            saveTractFileList(tr, pMatch, filter, prefix, suffix='nodata_all')
            saveTractFileList(tr, pMatch, filter, prefix, suffix='nodata_big')

    if not notRun:
        """ Load the Butler """
        butler = dafPersist.Butler(rootDir)
        # If there are too many images, do not generate the
        # combined region file at first
        for tt, pp in zip(tract, patch):
            dataId = {'tract': tt, 'patch': pp, 'filter': filter}
            try:
                coaddPatchNoData(rootDir, tt, pp, filter, prefix=prefix,
                                 savePNG=False, verbose=True, tolerence=3,
                                 minArea=10000, clobber=False, butler=butler,
                                 dataId=dataId, starMask=starMask,
                                 notDeblend=notDeblend)
            except Exception:
                print "# Can not make NO_DATA mask for: %i %s %s" % (tt,
                                                                     pp,
                                                                     filter)


def coaddPatchShape(rootDir, tract, patch, filter, prefix='hsc_coadd',
                    verbose=True, clobber=False, butler=None, dataId=None):
    """Get the general shape of the Patch."""
    pipeVersion = dafPersist.eupsVersions.EupsVersions().versions['hscPipe']
    if StrictVersion(pipeVersion) >= StrictVersion('3.9.0'):
        coaddData = "deepCoadd_calexp"
    else:
        coaddData = "deepCoadd"
    if verbose:
        print "# Deal with %s dataType here" % coaddData

    # Get the name of the wkb and deg file
    strTractPatch = (str(tract).strip() + '_' + patch + '_' + filter)
    # For all the accepted regions
    shapeWkb = prefix + '_' + strTractPatch + '_shape.wkb'
    fileExist1 = os.path.isfile(shapeWkb)
    shapeReg = prefix + '_' + strTractPatch + '_shape.reg'
    fileExist2 = os.path.isfile(shapeReg)

    # See if all the files have been generated
    fileAllExist = (fileExist1 and fileExist2)

    # Only generate new one when
    #  1) Not all files are available
    #  2) All available, but clobber = True
    if (not fileAllExist) or clobber:

        # Make a butler and specify the dataID
        if butler is None:
            butler = dafPersist.Butler(rootDir)
        if dataId is None:
            dataId = {'tract': tract, 'patch': patch, 'filter': filter}

        # Get the name of the input fits image
        if StrictVersion(pipeVersion) >= StrictVersion('3.9.0'):
            coaddImg = '%s/calexp-%s-%s-%s.fits' % (patch, filter,
                                                    tract, patch)
        else:
            coaddImg = '%s.fits' % (patch)
        if rootDir[-1] is '/':
            fitsName = (rootDir + 'deepCoadd/' + filter + '/' +
                        str(tract).strip() + '/' + coaddImg)
        else:
            fitsName = (rootDir + '/deepCoadd/' + filter + '/' +
                        str(tract).strip() + '/' + coaddImg)

        if not os.path.isfile(fitsName):
            raise Exception('Can not find the input fits image: %s' % fitsName)

        if verbose:
            print "## Reading Fits Image: %s" % fitsName

        # Get the exposure from the butler
        calExp = butler.get(coaddData, dataId, immediate=True)
        # Get the Bounding Box of the image
        bbox = calExp.getBBox(afwImage.PARENT)
        # Get the WCS information
        imgWcs = calExp.getWcs()
        # Get the Ra, Dec of the four corners
        corners = []
        corners.append(imgWcs.pixelToSky(bbox.getMinX(), bbox.getMinY()))
        corners.append(imgWcs.pixelToSky(bbox.getMinX(), bbox.getMaxY()))
        corners.append(imgWcs.pixelToSky(bbox.getMaxX(), bbox.getMaxY()))
        corners.append(imgWcs.pixelToSky(bbox.getMaxX(), bbox.getMinY()))

        raDec = map(lambda x: (x.getLongitude().asDegrees(),
                               x.getLatitude().asDegrees()), corners)
        # Convert the raDec array into a polygon
        patchPoly = Polygon(raDec)

        # Save the Polygon to .wkb and .reg file
        polySaveReg(patchPoly, shapeReg, color='green')
        # Also create a MultiPolygon object, and save a .wkb file
        cdPatch.polySaveWkb(patchPoly, shapeWkb)

        return patchPoly


def batchPatchShape(rootDir, filter='HSC-I', prefix='hsc_coadd',
                    saveList=True, notRun=False, minSize=110, checkCat=False):
    """
    Get the shape of patches in batch mode.

    This is better than the method in coaddPatchShape

    TODO: Merge this into coaddPatchShape later
    """
    pipeVersion = dafPersist.eupsVersions.EupsVersions().versions['hscPipe']
    if StrictVersion(pipeVersion) >= StrictVersion('3.9.0'):
        coaddData = "deepCoadd_calexp"
    else:
        coaddData = "deepCoadd"

    """ Save a list of tract IDs """
    trUniq = cdTract.getTractList(rootDir, filter, imgType=coaddData,
                                  toInt=True, prefix=prefix, toFile=True)
    print "### There are %d unique tracts!" % len(trUniq)
    # Get the list of coadded images in the direction
    if checkCat:
        imgList, catList = listAllCatalog(rootDir, filter)
    else:
        imgList = listAllImages(rootDir, filter, checkSize=True,
                                minSize=minSize)
    nImg = len(imgList)
    print '### Will go through %d images !' % nImg

    # Get the list of tract and patch for these images
    tract = map(lambda x: int(x.split('/')[-2]), imgList)
    patch = map(lambda x: x.split('/')[-1].split('.')[0], imgList)

    if saveList:
        for tr in trUniq:
            tArr = np.asarray(tract)
            pArr = np.asarray(patch)
            pMatch = pArr[tArr == tr]
            saveTractFileList(tr, pMatch, filter, prefix, suffix='shape')

    if not notRun:
        """ Load the Butler """
        butler = dafPersist.Butler(rootDir)
        # If there are too many images, do not generate the combined
        # region file at first
        for tt, pp in zip(tract, patch):
            dataId = {'tract': tt, 'patch': pp, 'filter': filter}
            coaddPatchShape(rootDir, tt, pp, filter, prefix=prefix,
                            verbose=True, clobber=False, butler=butler,
                            dataId=dataId)


def batchNoDataCombine(tractFile, location='.', big=True, showComb=True,
                       verbose=True, check=True):
    """Combine the NoData mask."""
    temp = os.path.basename(tractFile).split('_')
    prefix = temp[0] + '_' + temp[1]
    filter = temp[2]

    """ Get the list of tract IDs """
    if not os.path.isfile(tractFile):
        raise Exception("Can not find the list file: %s" % tractFile)
    tractList = open(tractFile, 'r')
    tractIDs = [int(x) for x in tractList.read().splitlines()]
    tractList.close()

    if location[-1] is not '/':
        location += '/'

    """ Go through these tracts """
    """
        TODO: In the future, there will be too many tracts in one list
              pre-select a group tracts that are close together
    """
    nTract = len(tractIDs)
    print "### Will deal with %d tracts" % nTract

    for tractId in tractIDs:

        if verbose:
            print "### Will deal with tract: %d" % tractId

        """ Get the list file names """
        if not big:
            """ All Region .wkb and .reg list """
            regLis = (location + prefix + '_' + str(tractId) + '_' +
                      filter + '_nodata_all_reg.lis')
            wkbLis = (location + prefix + '_' + str(tractId) + '_' +
                      filter + '_nodata_all_wkb.lis')
            strComb = '_all'
        else:
            """ Big Region .wkb and .reg list """
            regLis = (location + prefix + '_' + str(tractId) + '_' +
                      filter + '_nodata_big_reg.lis')
            wkbLis = (location + prefix + '_' + str(tractId) + '_' +
                      filter + '_nodata_big_wkb.lis')
            strComb = '_big'

        if not os.path.isfile(regLis):
            raise Exception("Can not find the regLis file: %s" % regLis)
        else:
            """ Combine the .reg file, it should be easy """
            outReg = (prefix + '_' + str(tractId) + '_' +
                      filter + '_nodata' + strComb + '.reg')
            if verbose:
                print "### Try to combined their .reg files into %s" % outReg
            combineRegFiles(regLis, output=outReg, check=check)
            if not os.path.isfile(outReg):
                raise Exception("Something is wrong with the output .reg file: \
                                %s" % outReg)

        if not os.path.isfile(wkbLis):
            raise Exception("Can not find the wkbLis file: %s" % wkbLis)
        else:
            """ Combine the .wkb file """
            outWkb = (prefix + '_' + str(tractId) + '_' +
                      filter + '_nodata' + strComb + '.wkb')

            if verbose:
                print "### Try to combined their .wkb files into %s" % outWkb

            combineWkbFiles(wkbLis, output=outWkb, check=check, listAll=True)
            if not os.path.isfile(outWkb):
                raise Exception("Something is wrong with the output .wkb file:\
                                %s" % outWkb)
            else:
                """ Show the results """
                if showComb:
                    pngTitle = (prefix + '_' + str(tractId) + '_' + filter +
                                '_nodata' + strComb)
                    pngName = pngTitle + '.png'
                    showNoDataMask(outWkb, title=pngTitle, pngName=pngName)


def batchPatchCombine(tractFile, location='.', showComb=True, verbose=True,
                      check=True):
    """Combine the Shape masks for a list of Patches."""
    temp = os.path.basename(tractFile).split('_')
    prefix = temp[0] + '_' + temp[1]
    filter = temp[2]

    """ Get the list of tract IDs """
    if not os.path.isfile(tractFile):
        raise Exception("Can not find the list file: %s" % tractFile)
    tractList = open(tractFile, 'r')
    tractIDs = [int(x) for x in tractList.read().splitlines()]
    tractList.close()

    if location[-1] is not '/':
        location += '/'

    """ Go through these tracts """
    """
        TODO: In the future, there will be too many tracts in one list
              pre-select a group tracts that are close together
    """
    nTract = len(tractIDs)
    print "### Will deal with %d tracts" % nTract

    for tractId in tractIDs:

        if verbose:
            print "### Will deal with tract: %d" % tractId

        """ Get the list file names """
        regLis = (location + prefix + '_' + str(tractId) + '_' + filter +
                  '_shape_reg.lis')
        wkbLis = (location + prefix + '_' + str(tractId) + '_' + filter +
                  '_shape_wkb.lis')
        strComb = '_all'

        if not os.path.isfile(regLis):
            raise Exception("Can not find the regLis file: %s" % regLis)
        else:
            """ Combine the .reg file, it should be easy """
            outReg = (prefix + '_' + str(tractId) + '_' + filter +
                      '_shape' + strComb + '.reg')
            if verbose:
                print "### Try to combined their .reg files into %s" % outReg
            combineRegFiles(regLis, output=outReg, check=check)
            if not os.path.isfile(outReg):
                raise Exception("Something is wrong with the output .reg file: \
                                %s" % outReg)

        if not os.path.isfile(wkbLis):
            raise Exception("Can not find the wkbLis file: %s" % wkbLis)
        else:
            """ Combine the .wkb file """
            outWkb = (prefix + '_' + str(tractId) + '_' + filter +
                      '_shape' + strComb + '.wkb')
            outAll = (prefix + '_' + str(tractId) + '_' + filter +
                      '_nodata' + strComb + '_list.wkb')

            if verbose:
                print "### Try to combined their .wkb files into %s" % outWkb

            combineWkbFiles(wkbLis, output=outWkb, check=check, listAll=True,
                            allOutput=outAll)
            if not os.path.isfile(outWkb):
                raise Exception("Something is wrong with the output .wkb file:\
                                %s" % outWkb)
            else:
                """ Show the results """
                if showComb:
                    pngTitle = (prefix + '_' + str(tractId) + '_' + filter +
                                '_shape' + strComb)
                    pngName = pngTitle + '.png'
                    showNoDataMask(outAll, corner=outWkb, title=pngTitle,
                                   pngName=pngName)


def showNoDataMask(wkbFile, large=None, corner=None,
                   title='No Data Mask Plane',
                   pngName='tract_mask.png', xsize=20, ysize=18, dpi=150,
                   saveFile=True, tractMap=None):
    """Visualize the NoData Mask."""
    fig = plt.figure(figsize=(xsize, ysize), dpi=dpi)

    ax = fig.add_subplot(111)
    fontsize = 20
    ax.minorticks_on()

    for tick in ax.xaxis.get_major_ticks():
        tick.label1.set_fontsize(fontsize)
    for tick in ax.yaxis.get_major_ticks():
        tick.label1.set_fontsize(fontsize)

    # Set title
    ax.set_title(title, fontsize=25, fontweight='bold')
    ax.title.set_position((0.5, 1.01))

    maskShow = cdPatch.polyReadWkb(wkbFile, load=True)
    # Outline all the mask regions
    if maskShow.type is "Polygon":
        bounds = maskShow.boundary
        if bounds.type is "LineString":
            x, y = bounds.xy
            ax.plot(x, y, c='r', lw=2.0)
        elif bounds.type is "MultiLineString":
            for bb in bounds:
                x, y = bb.xy
                ax.plot(x, y, lw=2.0, color='r')
    elif maskShow.type is "MultiPolygon":
        for ii, mask in enumerate(maskShow):
            bounds = mask.boundary
            if bounds.type is "LineString":
                x, y = bounds.xy
                ax.plot(x, y, c='r', lw=1.5)
            elif bounds.type is "MultiLineString":
                for bb in bounds:
                    x, y = bb.xy
                    ax.plot(x, y, lw=1.5, color='r')
            else:
                print " !!! Can not plot shape %d - %s !" % (ii, bounds.type)

    # highlight all the large ones
    if large is not None:
        bigShow = cdPatch.polyReadWkb(large, load=True)
        if bigShow.type is "Polygon":
            bounds = bigShow.boundary
            if bounds.type is "LineString":
                x, y = bounds.xy
                ax.plot(x, y, c='b', lw=2.5)
            elif bounds.type is "MultiLineString":
                for bb in bounds:
                    x, y = bb.xy
                    ax.plot(x, y, lw=2.5, color='b')
        elif bigShow.type is "MultiPolygon":
            for ii, mask in enumerate(bigShow):
                bounds = mask.boundary
                if bounds.type is "LineString":
                    x, y = bounds.xy
                    ax.plot(x, y, c='b', lw=2.5)
                elif bounds.type is "MultiLineString":
                    for bb in bounds:
                        x, y = bb.xy
                        ax.plot(x, y, lw=2.5, color='b')
                else:
                    print " !!! Can not plot shape %d - %s !" % (ii,
                                                                 bounds.type)

    # highlight all the tract corner
    if corner is not None:
        cornerShow = cdPatch.polyReadWkb(corner, load=True)
        if cornerShow.type is "Polygon":
            bounds = cornerShow.boundary
            if bounds.type is "LineString":
                x, y = bounds.xy
                ax.plot(x, y, c='g', lw=3.5)
            elif bounds.type is "MultiLineString":
                for bb in bounds:
                    x, y = bb.xy
                    ax.plot(x, y, lw=3.5, color='g')
            else:
                print " !!! Can not plot shape %d - %s !" % (ii, bounds.type)
        elif cornerShow.type is "MultiPolygon":
            for ii, mask in enumerate(cornerShow.geoms[:]):
                bounds = mask.boundary
                if bounds.type is "LineString":
                    x, y = bounds.xy
                    ax.plot(x, y, c='g', lw=3.5)
                elif bounds.type is "MultiLineString":
                    for bb in bounds:
                        x, y = bb.xy
                        ax.plot(x, y, lw=3.5, color='g')
                else:
                    print " !!! Can not plot shape %d - %s !" % (ii,
                                                                 bounds.type)
        else:
            print " !!! Not valid tract_corner Polygon"

    ax.margins(0.04, 0.04, tight=True)

    ax.set_xlabel('R.A.  (deg)', fontsize=25)
    ax.set_ylabel('Decl. (deg)', fontsize=25)

    if tractMap is not None:
        for patch in tractMap:
            print "#### Plot Patch : ", patch.getIndex()
            raPatch, decPatch = bboxToRaDec(patch.getInnerBBox(),
                                            tractMap.getWcs())
            ax.fill(raPatch, decPatch, fill=False, edgecolor='k', lw=1,
                    linestyle='dashed')
            ax.text(percent(raPatch), percent(decPatch, 0.9),
                    str(patch.getIndex()),
                    fontsize=16, horizontalalignment='center',
                    verticalalignment='top')

    fig.subplots_adjust(hspace=0.1, wspace=0.1,
                        top=0.95, right=0.95)

    if saveFile:
        fig.savefig(pngName)
        plt.close(fig)
    else:
        return fig


def tractNoData(rootDir, tractUse, filter='HSC-I', prefix='hsc_coadd',
                saveList=True, notRun=False, combine=True, showPatch=True,
                checkCat=True, starMask=False, notDeblend=True):
    """Wrapper to get the NoData mask for an entire Tract."""
    print '### Will only generate mask files for one Tract: %d ' % tractUse
    # Get the list of coadded images in the direction
    if checkCat:
        imgList, catList = listAllCatalog(rootDir, filter, tract=tractUse)
    else:
        imgList = listAllImages(rootDir, filter, tract=tractUse,
                                checkSize=True, minSize=100)
    nImg = len(imgList)
    print '### Will go through %d images !' % nImg

    # Get the list of tract and patch for these images
    tract = map(lambda x: int(x.split('/')[-2]), imgList)
    patch = map(lambda x: x.split('/')[-1].split('.')[0], imgList)

    # Get the uniqe tract
    trUniq = np.unique(tract)
    print "### There are %d unique tracts!" % len(trUniq)
    if saveList:
        for tr in trUniq:
            tArr = np.asarray(tract)
            pArr = np.asarray(patch)
            pMatch = pArr[tArr == tr]
            saveTractFileList(tr, pMatch, filter, prefix, suffix='nodata_all')
            saveTractFileList(tr, pMatch, filter, prefix, suffix='nodata_big')

    if not notRun:
        """ Load the Butler """
        butler = dafPersist.Butler(rootDir)
        for tt, pp in zip(tract, patch):
            dataId = {'tract': tt, 'patch': pp, 'filter': filter}
            try:
                coaddPatchNoData(rootDir, tt, pp, filter, prefix=prefix,
                                 savePNG=False, verbose=True, tolerence=3,
                                 minArea=10000, clobber=False, butler=butler,
                                 dataId=dataId, starMask=starMask,
                                 notDeblend=notDeblend)
            except Exception:
                print "! Can not make NO_DATA mask for: %i %s %s" % (tt,
                                                                     pp,
                                                                     filter)

        if combine:
            if showPatch:
                skyMap = butler.get('deepCoadd_skyMap', {'tract': tractUse})
                tractMap = None
                for tr in skyMap:
                    if tr.getId() == tractUse:
                        print "#### Find the tract we want : %d" % tractUse
                        tractMap = tr
                tractNoDataCombine(prefix, tractUse, filter=filter,
                                   location='.', big=True, showComb=True,
                                   verbose=True, check=False,
                                   tractMap=tractMap)
                tractNoDataCombine(prefix, tractUse, filter=filter,
                                   location='.', big=False, showComb=True,
                                   verbose=True, check=False,
                                   tractMap=tractMap)
            else:
                tractNoDataCombine(prefix, tractUse, filter=filter,
                                   location='.', big=True, showComb=True,
                                   verbose=True, check=False)
                tractNoDataCombine(prefix, tractUse, filter=filter,
                                   location='.', big=False, showComb=True,
                                   verbose=True, check=False)


def tractNoDataCombine(prefix, tractId, filter='HSC-I', location='.', big=True,
                       showComb=True, verbose=True, check=True, tractMap=None):
    """Combine the NoData masks for an entire Tract."""
    prefix = str(prefix).strip()
    filter = str(filter).strip()

    if location[-1] is not '/':
        location += '/'

    if verbose:
        print "### Will deal with tract: %d" % tractId

    """ Get the list file names """
    if not big:
        """ All Region .wkb and .reg list """
        regLis = (location + prefix + '_' + str(tractId) + '_' + filter +
                  '_nodata_all_reg.lis')
        wkbLis = (location + prefix + '_' + str(tractId) + '_' + filter +
                  '_nodata_all_wkb.lis')
        strComb = '_all'
    else:
        """ Big Region .wkb and .reg list """
        regLis = (location + prefix + '_' + str(tractId) + '_' + filter +
                  '_nodata_big_reg.lis')
        wkbLis = (location + prefix + '_' + str(tractId) + '_' + filter +
                  '_nodata_big_wkb.lis')
        strComb = '_big'

    if not os.path.isfile(regLis):
        raise Exception("Can not find the regLis file: %s" % regLis)
    else:
        """ Combine the .reg file, it should be easy """
        outReg = (prefix + '_' + str(tractId) + '_' + filter +
                  '_nodata' + strComb + '.reg')
        if verbose:
            print "### Try to combined their .reg files into %s" % outReg
        combineRegFiles(regLis, output=outReg, check=check)
        if not os.path.isfile(outReg):
            raise Exception("Something is wrong with the output .reg file: \
                            %s" % outReg)

    if not os.path.isfile(wkbLis):
        raise Exception("Can not find the wkbLis file: %s" % wkbLis)
    else:
        """ Combine the .wkb file """
        outWkb = (prefix + '_' + str(tractId) + '_' + filter +
                  '_nodata' + strComb + '.wkb')

        if verbose:
            print "### Try to combined their .wkb files into %s" % outWkb

        combineWkbFiles(wkbLis, output=outWkb, check=check, listAll=True)
        if not os.path.isfile(outWkb):
            raise Exception("Something is wrong with the output .wkb file:\
                            %s" % outWkb)
        else:
            """ Show the results """
            if showComb:
                pngTitle = (prefix + '_' + str(tractId) + '_' + filter +
                            '_nodata' + strComb)
                pngName = pngTitle + '.png'
                showNoDataMask(outWkb, title=pngTitle, pngName=pngName,
                               tractMap=tractMap)


def tractShape(rootDir, tractId, filter='HSC-I', prefix='hsc_coadd',
               saveList=True, notRun=False, minSize=70, combine=True,
               showPatch=True, checkCat=True):
    """
    Get the shape of patches in batch mode.

    This is better than the method in coaddPatchShape

    TODO: Merge this into coaddPatchShape later
    """
    # Get the list of coadded images in the direction
    if checkCat:
        imgList, catList = listAllCatalog(rootDir, filter, tract=tractId)
    else:
        imgList = listAllImages(rootDir, filter, tract=tractId, checkSize=True,
                                minSize=minSize)
    nImg = len(imgList)
    print '### Will go through %d images !' % nImg

    # Get the list of tract and patch for these images
    tract = map(lambda x: int(x.split('/')[-2]), imgList)
    patch = map(lambda x: x.split('/')[-1].split('.')[0], imgList)

    # Get the uniqe tract
    trUniq = np.unique(tract)
    print "### There are %d unique tracts!" % len(trUniq)
    if saveList:
        for tr in trUniq:
            tArr = np.asarray(tract)
            pArr = np.asarray(patch)
            pMatch = pArr[tArr == tr]
            saveTractFileList(tr, pMatch, filter, prefix, suffix='shape')

    if not notRun:
        """ Load the Butler """
        butler = dafPersist.Butler(rootDir)
        # If there are too many images, do not generate the combined
        # region file at first
        for tt, pp in zip(tract, patch):
            dataId = {'tract': tt, 'patch': pp, 'filter': filter}
            coaddPatchShape(rootDir, tt, pp, filter, prefix=prefix,
                            verbose=True, clobber=False, butler=butler,
                            dataId=dataId)

        if combine:
            if showPatch:
                skyMap = butler.get('deepCoadd_skyMap', {'tract': tractId})
                tractMap = None
                for tr in skyMap:
                    if tr.getId() == tractId:
                        print "#### Find the tract we want : %d" % tractId
                        tractMap = tr
                tractShapeCombine(prefix, tractId, filter=filter,
                                  location='.',
                                  showComb=True, verbose=True, check=False,
                                  tractMap=tractMap)
            else:
                tractShapeCombine(prefix, tractId, filter=filter,
                                  location='.',
                                  showComb=True, verbose=True, check=False)


def tractShapeCombine(prefix, tractId, filter='HSC-I', location='.',
                      showComb=True, verbose=True, check=True, tractMap=None):
    """Combine the Shape for an entire Tract."""
    prefix = str(prefix).strip()
    filter = str(filter).strip()

    if location[-1] is not '/':
        location += '/'

    """ Go through these tracts """
    """
        TODO: In the future, there will be too many tracts in one list
              pre-select a group tracts that are close together
    """
    if verbose:
        print "### Will deal with tract: %d" % tractId

    """ Get the list file names """
    regLis = (location + prefix + '_' + str(tractId) + '_' + filter +
              '_shape_reg.lis')
    wkbLis = (location + prefix + '_' + str(tractId) + '_' + filter +
              '_shape_wkb.lis')
    strComb = '_all'

    if not os.path.isfile(regLis):
        raise Exception("Can not find the regLis file: %s" % regLis)
    else:
        """ Combine the .reg file, it should be easy """
        outReg = (prefix + '_' + str(tractId) + '_' + filter +
                  '_shape' + strComb + '.reg')
        if verbose:
            print "### Try to combined their .reg files into %s" % outReg
        combineRegFiles(regLis, output=outReg, check=check)
        if not os.path.isfile(outReg):
            raise Exception("Something is wrong with the output .reg file: \
                            %s" % outReg)

    if not os.path.isfile(wkbLis):
        raise Exception("Can not find the wkbLis file: %s" % wkbLis)
    else:
        """ Combine the .wkb file """
        outWkb = (prefix + '_' + str(tractId) + '_' + filter +
                  '_shape' + strComb + '.wkb')
        outAll = (prefix + '_' + str(tractId) + '_' + filter +
                  '_shape' + strComb + '_list.wkb')

        if verbose:
            print "### Try to combined their .wkb files into %s" % outWkb

        combineWkbFiles(wkbLis, output=outWkb, check=check, listAll=True,
                        allOutput=outAll)

        if not os.path.isfile(outWkb):
            raise Exception("Something is wrong with the output .wkb file:\
                            %s" % outWkb)
        else:
            """ Show the results """
            if showComb:
                pngTitle = (prefix + '_' + str(tractId) + '_' + filter +
                            '_shape' + strComb)
                pngName = pngTitle + '.png'
                showNoDataMask(outAll, corner=outWkb, title=pngTitle,
                               pngName=pngName, tractMap=tractMap)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("root",   help="Root directory of data repository")
    parser.add_argument("filter", help="HSC filter")
    parser.add_argument('-p', '--prefix', dest='prefix',
                        help='Prefix of the output file',
                        default='hsc_coadd')
    args = parser.parse_args()

    batchPatchNoData(args.root, args.filter, prefix=args.prefix)
