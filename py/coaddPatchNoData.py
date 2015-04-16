#!/usr/bin/env python

from __future__ import division

import copy
import os
import argparse
import numpy as np

import lsst.daf.persistence   as dafPersist
import lsst.afw.image         as afwImage

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
mpl.rcParams['ytick.minor.width'] = 1.5
mpl.rc('axes', linewidth=2)

# Shapely related imports
from shapely.geometry import Polygon, LineString
from shapely          import wkb
from shapely.ops      import cascaded_union

from scipy import ndimage
from skimage.measure import find_contours, approximate_polygon

def showNoDataMask(wkbFile, large=None, corner=None, title='No Data Mask Plane',
                  pngName='tract_mask.png', xsize=20, ysize=18, dpi=150):


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
    ax.title.set_position((0.5,1.01))

    maskShow = polyReadWkb(wkbFile, load=True)
    # Outline all the mask regions
    if maskShow.type is "Polygon":
        bounds = maskShow.boundary
        if bounds.type is "LineString":
            x, y = bounds.xy
            ax.plot(x, y, c='r', lw=2.5)
        elif bounds.type is "MultiLineString":
            for bb in bounds:
                x, y = bb.xy
                ax.plot(x, y, lw=2.5, color='r')
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
        bigShow = polyReadWkb(large, load=True)
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
                        ax.plot(x, y, c='b', lw=2.0)
                    elif bounds.type is "MultiLineString":
                        for bb in bounds:
                            x, y = bb.xy
                            ax.plot(x, y, lw=2.0, color='b')
                    else:
                        print " !!! Can not plot shape %d - %s !" % (ii,
                                                                     bounds.type)

    # highlight all the tract corner
    if corner is not None:
        cornerShow = polyReadWkb(corner, load=True)
        if cornerShow.type is "Polygon":
            bounds = cornerShow.boundary
            if bounds.type is "LineString":
                x, y = bounds.xy
                ax.plot(x, y, c='g', lw=2.5)
            elif bounds.type is "MultiLineString":
                for bb in bounds:
                    x, y = bb.xy
                    ax.plot(x, y, lw=2.5, color='g')
            else:
                print " !!! Can not plot shape %d - %s !" % (ii, bounds.type)
        elif cornerShow.type is "MultiPolygon":
            for ii, mask in enumerate(cornerShow.geoms[:]):
                bounds = mask.boundary
                if bounds.type is "LineString":
                    x, y = bounds.xy
                    ax.plot(x, y, c='g', lw=2.5)
                elif bounds.type is "MultiLineString":
                    for bb in bounds:
                        x, y = bb.xy
                        ax.plot(x, y, lw=2.5, color='g')
                else:
                    print " !!! Can not plot shape %d - %s !" % (ii, bounds.type)
        else:
            print " !!! Not valid tract_corner Polygon"

    ax.margins(0.02, 0.02, tight=True)

    ax.set_xlabel(r'RA (deg)',  fontsize=22)
    ax.set_ylabel(r'DEC (deg)', fontsize=22)

    fig.subplots_adjust(hspace=0.1, wspace=0.1,
                        top=0.95, right=0.95)

    fig.savefig(pngName)
    plt.close(fig)


def imgAddNoise(im, gaussian, factor):

    im = ndimage.gaussian_filter(im, gaussian)
    im += factor * np.random.random(im.shape)

    return im

def getPixelRaDec(wcs, xx, yy, xStart=0, yStart=0):

    coord = wcs.pixelToSky((xStart + xx - 1),
                           (yStart + yy - 1)).toIcrs()

    ra  = coord.getRa().asDegrees()
    dec = coord.getDec().asDegrees()

    return ra, dec

def polySaveWkb(poly, wkbName):

    polyWkb = wkb.dumps(poly)

    wkbFile = open(wkbName, 'w')
    wkbFile.write(polyWkb.encode('hex'))
    wkbFile.close()


# Save the Polygon region into a DS9 .reg file
def getPolyLine(polyCoords):

    coordShow = map(lambda x: str(x[0]) + ' ' + str(x[1]) + ' ', polyCoords)

    # The format for Polygon in DS9 is:
    # Usage: polygon x1 y1 x2 y2 x3 y3 ...
    polyLine = 'polygon '
    for p in coordShow:
        polyLine += p

    polyLine += '\n'

    return polyLine

# !!! Make sure that the Polygon is simple
def polySaveReg(poly, regName, listPoly=False, color='blue'):

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
        for pp in poly:
            if pp.geom_type is "Polygon":
            # Get the coordinates for every point in the polygon
                polyCoords = pp.boundary.coords[:]
                polyLine = getPolyLine(polyCoords)
                regFile.write(polyLine)
            elif pp.geom_type is "MultiPolygon":
                for mm in pp.geoms:
                    polyCoords = mm.boundary.coords[:]
                    polyLine = getPolyLine(polyCoords)
                    regFile.write(polyLine)
    else:
        if poly.geom_type is "Polygon":
            polyCoords = poly.boundary.coords[:]
            polyLine = getPolyLine(polyCoords)
            regFile.write(polyLine)
        elif poly.geom_type is "MultiPolygon":
            for mm in poly.geoms:
                polyCoords = mm.boundary.coords[:]
                polyLine = getPolyLine(polyCoords)
                regFile.write(polyLine)

    regFile.close()


def listAllImages(rootDir, filter):

    import glob

    if rootDir[-1] is '/':
        searchDir = rootDir + 'deepCoadd/' + filter.upper() + '/*/*.fits'
    else:
        searchDir = rootDir + '/deepCoadd/' + filter.upper() + '/*/*.fits'

    return map(lambda x: x, glob.glob(searchDir))


def coaddPatchNoData(rootDir, tract, patch, filter, prefix='hsc_coadd',
                     savePNG=True, verbose=True, tolerence=4,
                     minArea=10000, clobber=False, butler=None, dataId=None):

    # Get the name of the wkb and deg file
    strTractPatch = (str(tract).strip() + '_' + patch + '_' + filter)
    ## For all the accepted regions
    noDataAllWkb = prefix + '_' + strTractPatch + '_nodata_all.wkb'
    fileExist1 = os.path.isfile(noDataAllWkb)
    noDataAllReg = prefix + '_' + strTractPatch + '_nodata_all.reg'
    fileExist2 = os.path.isfile(noDataAllReg)
    ## For all the big mask regions
    noDataBigWkb = prefix + '_' + strTractPatch + '_nodata_big.wkb'
    noDataBigReg = prefix + '_' + strTractPatch + '_nodata_big.reg'

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
            dataId = {'tract':tract, 'patch':patch, 'filter':filter}

        # Get the name of the input fits image
        if rootDir[-1] is '/':
            fitsName = rootDir + 'deepCoadd/' + filter + '/' + str(tract).strip() \
                    + '/' + patch + '.fits'
        else:
            fitsName = rootDir + '/deepCoadd/' + filter + '/' + str(tract).strip() \
                    + '/' + patch + '.fits'
            if not os.path.isfile(fitsName):
                raise Exception('Can not find the input fits image: %s' % fitsName)

        # Get the name of the png file
        titlePng = prefix + strTractPatch + '_NODATA'
        noDataPng = prefix + '_' + strTractPatch + '_nodata.png'

        if verbose:
            print "## Reading Fits Image: %s" % fitsName

        # Get the exposure from the butler
        calExp = butler.get('deepCoadd', dataId, immediate=True)
        # Get the Bounding Box of the image
        bbox = calExp.getBBox(afwImage.PARENT)
        xBegin, yBegin = bbox.getBeginX(), bbox.getBeginY()
        # Get the WCS information
        imgWcs = calExp.getWcs()

        # Get the object for mask plane
        mskImg = calExp.getMaskedImage().getMask()

        # Extract the NO_DATA plane
        # TODO: NO_DATA is not a system mask, maybe should use INTRP later
        noData = copy.deepcopy(mskImg)
        noData &= noData.getPlaneBitMask('NO_DATA')
        # Return the mask image array
        noDataArr = noData.getArray()

        # Set all masked pixels to be 1
        #noDataArr /= 256
        # Pad the 2-D array by a little
        noDataArr = np.lib.pad(noDataArr, ((1, 1), (1, 1)), 'constant',
                               constant_values=0)

        # Try a very different approach: Using the find_contours and
        # approximate_polygon methods from scikit-images package
        maskShapes = []  # For all the accepted mask regions
        maskCoords = []  # For the "corner" coordinates of these regions
        maskAreas  = []  # The sizes of all regions

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
            # Convert these coordinates into (RA, DEC) using the WCS information
            contourSkyCoords = map(lambda x: [x[1], x[0]], contourCoords)
            contourRaDec     = map(lambda x: getPixelRaDec(imgWcs, x[0], x[1],
                                                          xStart=xBegin,
                                                          yStart=yBegin),
                                   contourSkyCoords)
            #contourRaDec     = imgWcs.wcs_pix2world(contourSkyCoords, 1)
            # Require that any useful region must be at least an triangular
            if len(contourCoords) > 3:
                # Form a lineString using these coordinates
                maskLine = LineString(contourRaDec)
                # Check if the lineString is valid and simple, so can be used
                # to form a closed and simple polygon
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
                print "### %d regions are larger than the minimum mask sizes" % nBig
            # Save all the masked regions to a .reg file
            polySaveReg(maskBigList, noDataBigReg, listPoly=True, color='blue')
            # Also create a MultiPolygon object, and save a .wkb file
            maskBig = cascaded_union(maskBigList)
            polySaveWkb(maskBig, noDataBigWkb)
        else:
            maskBig = None
            if verbose:
                print "### No region is larger than the minimum mask sizes"

        if savePNG:
            if maskBig is None:
                showNoDataMask(noDataAllWkb, title=titlePng,
                               pngName=noDataPng)
            else:
                showNoDataMask(noDataAllWkb, large=noDataBigWkb, title=titlePng,
                               pngName=noDataPng)

        # Save all the masked regions to a .reg file
        polySaveReg(maskShapes, noDataAllReg, listPoly=True, color='red')
        # Also create a MultiPolygon object, and save a .wkb file
        maskAll = cascaded_union(maskShapes)
        polySaveWkb(maskAll, noDataAllWkb)

    else:
        if verbose:
            print "### %d, %s has been reduced before! Skip!" % (tract, patch)


def saveTractFileList(tr, patch, filter, prefix):

    allWkbLis = open(prefix + '_' + str(tr) + '_' + filter +
                     '_nodata_all_wkb.lis', 'w')
    allRegLis = open(prefix + '_' + str(tr) + '_' + filter +
                     '_nodata_all_reg.lis', 'w')
    bigWkbLis = open(prefix + '_' + str(tr) + '_' + filter +
                     '_nodata_big_wkb.lis', 'w')
    bigRegLis = open(prefix + '_' + str(tr) + '_' + filter +
                     '_nodata_big_reg.lis', 'w')

    for pp in patch:
        # Get the name of the wkb and deg file
        strTractPatch = (str(tr).strip() + '_' + pp + '_' + filter)
        ## For all the accepted regions
        allWkbLis.write(prefix + '_' + strTractPatch + '_nodata_all.wkb\n')
        allRegLis.write(prefix + '_' + strTractPatch + '_nodata_all.reg\n')
        ## For all the big mask regions
        bigWkbLis.write(prefix + '_' + strTractPatch + '_nodata_big.wkb\n')
        bigRegLis.write(prefix + '_' + strTractPatch + '_nodata_big.reg\n')

    allWkbLis.close()
    allRegLis.close()
    bigWkbLis.close()
    bigRegLis.close()


def combineRegFiles(listFile, output=None):

    """ Get the list of .reg files """
    regList = open(listFile, 'r').readlines()
    nReg = len(regList)
    print "### Will combine %d .reg files" % nReg

    """ Get the directory for these files """
    regDir = os.path.dirname(os.path.abspath(listFile)) + '/'

    print regDir

    """ Get the name of the combined .reg files """
    if output is None:
        fileComb = regDir + os.path.splitext(os.path.split(listFile)[1])[0] + '.reg'
    else:
        fileComb = regDir + output
    """ Open a new file to write"""
    regComb = open(fileComb, 'w')

    """ Go through every .reg file """
    for ii, reg in enumerate(regList):

        fileRead = regDir + reg.strip()
        if os.path.exists(fileRead) is False:
            raise Exception("Can not find the .reg file: %s !" % fileRead)

        if ii == 0:
            regLines = open(fileRead, 'r').readlines()
            for line in regLines:
                regComb.write(line)
        else:
            regLines = open(fileRead, 'r').readlines()[3:]
            for line in regLines:
                regComb.write(line)

    regComb.close()


# Read a .wkb file into a Polygon shape
def polyReadWkb(wkbName, load=True):

    wkbFile = open(wkbName, 'r')
    polyWkb = wkbFile.read().decode('hex')
    wkbFile.close()

    if load is True:
        return wkb.loads(polyWkb)
    else:
        return polyWkb

def combineWkbFiles(listFile, output=None):

    """ Get the list of .wkb files """
    wkbList = open(listFile, 'r').readlines()
    nWkb = len(wkbList)
    print "### Will combine %d .reg files" % nWkb

    """ Get the directory for these files """
    wkbDir = os.path.dirname(os.path.abspath(listFile)) + '/'

    """ Get the name of the combined .reg files """
    if output is None:
        fileComb = wkbDir + os.path.splitext(os.path.split(listFile)[1])[0] + '.wkb'
    else:
        fileComb = wkbDir + output

    """ Go through every .wkb file """
    combWkb = []
    for wkb in wkbList:
        fileRead = wkbDir + wkb.strip()

        if os.path.exists(fileRead) is False:
            raise Exception("Can not find the .wkb file: %s !" % fileRead)

        wkbRead = polyReadWkb(fileRead)
        if wkbRead.geom_type is 'Polygon':
            combWkb.append(wkbRead)
        elif wkbRead.geom_type is 'MultiPolygon':
            geoms = wkbRead.geoms[:]
            for geom in geoms:
                combWkb.append(geom)

    """ Take the cascaded_union of all the mask regions for a tract """
    combWkb = cascaded_union(combWkb)

    """ Save the .wkb file """
    polySaveWkb(combWkb, fileComb)


def batchPatchNoData(rootDir, filter='HSC-I', prefix='hsc_coadd',
                     saveList=True):

    # Get the list of coadded images in the direction
    imgList = listAllImages(rootDir, filter)
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
            saveTractFileList(tr, patch, filter, prefix)

    butler = dafPersist.Butler(rootDir)

    # If there are too many images, do not generate the combined region file at
    # first
    for tt, pp in zip(tract, patch):
        dataId = {'tract':tt, 'patch':pp, 'filter':filter}
        coaddPatchNoData(rootDir, tt, pp, filter, prefix=prefix,
                         savePNG=False, verbose=True, tolerence=4,
                         minArea=10000, clobber=False, butler=butler,
                         dataId=dataId)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("root",   help="Root directory of data repository")
    parser.add_argument("filter", help="HSC filter")
    parser.add_argument('-p', '--prefix', dest='prefix',
                        help='Prefix of the output file',
                        default='hsc_coadd')
    args = parser.parse_args()

    batchPatchNoData(args.root, args.filter, prefix=args.prefix)
