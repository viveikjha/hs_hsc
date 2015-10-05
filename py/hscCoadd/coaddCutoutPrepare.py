#!/usr/bin/env python
# encoding: utf-8

from __future__ import division

import os
import copy
import glob
import argparse
import numpy as np
import scipy

# Astropy
from astropy.io import fits
from astropy    import units as u
from astropy.stats import sigma_clip
# AstroML
from astroML.plotting import hist

# SEP
import sep

# Cubehelix color scheme
import cubehelix  # Cubehelix color scheme from https://github.com/jradavenport/cubehelix
# For high-contrast image
cmap1 = cubehelix.cmap(start=0.5, rot=-0.8, gamma=1.0,
                       minSat=1.2, maxSat=1.2,
                       minLight=0.0, maxLight=1.0)
cmap1.set_bad('k',1.)
# For Mask
cmap2 = cubehelix.cmap(start=2.0, rot=-1.0, gamma=2.5,
                       minSat=1.2, maxSat=1.2,
                       minLight=0.0, maxLight=1.0, reverse=True)
# For Sigma
cmap3 = cubehelix.cmap(start=0.5, rot=-0.8, gamma=1.2,
                       minSat=1.2, maxSat=1.2,
                       minLight=0.0, maxLight=1.0)

# Matplotlib related
import matplotlib as mpl
mpl.use('Agg')
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
import matplotlib.pyplot as plt
plt.ioff()
from matplotlib.patches import Ellipse

# Personal
import hscUtils as hUtil


def objToGalfit(objs, rad=None, concen=None, zp=27.0, rbox=8.0,
                dimX=None, dimY=None):
    """
    Empirical code that convert the SEP parameters of detected objects
    into initial guess of parameters for 1-Sersic GALFIT fit

    """
    # Number of objects
    nObj = len(objs)
    # Define a dictionary includes the necessary information
    galfit1C = np.recarray((nObj,), dtype=[('xcen', float), ('ycen', float),
                                   ('mag', float), ('re', float),
                                   ('n', float), ('ba', float), ('pa', float),
                                   ('lowX', int), ('lowY', int),
                                   ('uppX', int), ('uppY', int),
                                   ('truncate', bool), ('small', bool)])
    # Effective radius used for GALFIT
    if rad is None:
        rad = objs['a'] * 3.0
    # Go through all the objects
    for ii, obj in enumerate(objs):
        galfit1C[ii]['xcen'] = obj['x']
        galfit1C[ii]['ycen'] = obj['y']
        galfit1C[ii]['mag'] = -2.5 * np.log10(obj['cflux'] * 2.5) + zp
        galfit1C[ii]['re']  = rad[ii]
        galfit1C[ii]['ba']  = (obj['b'] / obj['a'])
        galfit1C[ii]['pa']  = (obj['theta'] * 180.0 / np.pi)
        # Initial guess for the Sersic index
        # Make it as simple as possible at first
        if concen is not None:
            if concen[ii] > 2.2:
                galfit1C[ii]['n'] = 2.5
            else:
                galfit1C[ii]['n'] = 1.0
        else:
            galfit1C[ii]['n'] = 1.5
        # Define a fitting box
        lowX = int(obj['x'] - rbox * rad[ii])
        lowY = int(obj['y'] - rbox * rad[ii])
        uppX = int(obj['x'] + rbox * rad[ii])
        uppY = int(obj['y'] + rbox * rad[ii])
        galfit1C[ii]['truncate'] = False
        small = 0
        if lowX < 0:
            lowX = 0
            galfit1C[ii]['truncate'] = True
            small += 1
        if lowY < 0:
            lowY = 0
            galfit1C[ii]['truncate'] = True
            small += 1
        if (dimX is not None) and (uppX > dimX):
            uppX = dimX
            galfit1C[ii]['truncate'] = True
            small += 1
        if (dimY is not None) and (uppY > dimY):
            uppY = dimY
            galfit1C[ii]['truncate'] = True
            small += 1
        if small >= 3:
            galfit1C[ii]['small'] = True
        galfit1C[ii]['lowX'] = lowX
        galfit1C[ii]['lowY'] = lowY
        galfit1C[ii]['uppX'] = uppX
        galfit1C[ii]['uppY'] = uppY

    return galfit1C


def showObjects(objs, dist, rad=None, outPNG='sep_object.png',
                cenInd=None, prefix=None, r1=None, r2=None, r3=None,
                fluxRatio1=None, fluxRatio2=None, highlight=None):
    """
    Plot the properties of objects detected on the images

    """
    # Choice of radius to plot
    if rad is not None:
        r = rad
    else:
        r = objs['a']
    # Set up the plot
    fig, axes = plt.subplots(2, 2, figsize=(14, 14))
    fig.subplots_adjust(hspace=0.20, wspace=0.20,
                        left=0.08, bottom=0.06,
                        top=0.98, right=0.98)

    fontsize = 18
    #  Fig1
    if fluxRatio1 is not None:
        axes[0, 0].axvline(np.log10(objs[cenInd]['flux']*fluxRatio1),
                           linestyle='--', lw=2.0)
    if fluxRatio2 is not None:
        axes[0, 0].axvline(np.log10(objs[cenInd]['flux']*fluxRatio2),
                           linestyle=':', lw=2.0)
    axes[0, 0].scatter(np.log10(objs['flux']), np.log10(r),
                       facecolors='g', edgecolors='gray',
                       alpha=0.30, s=(500.0 / np.sqrt(dist)))
    axes[0, 0].set_xlabel('log(Flux)', fontsize=22)
    axes[0, 0].set_ylabel('log(Radius/pixel)', fontsize=22)
    if highlight is not None:
        axes[0, 0].scatter(np.log10(objs[highlight]['flux']),
                           np.log10(r[highlight]),
                           color='b', alpha=0.50,
                           s=(500.0 / np.sqrt(dist[highlight])))
    if cenInd is not None:
        axes[0, 0].scatter(np.log10(objs[cenInd]['flux']),
                           np.log10(r[cenInd]),
                           color='r', alpha=0.60,
                           s=(500.0 / np.sqrt(dist[cenInd])))
    axes[0, 0].text(0.60, 0.06, 'Size: Approximity', fontsize=25,
                    transform=axes[0,0].transAxes, ha='center')

    #  Fig2
    axes[0, 1].scatter(np.log10(objs['flux']/(objs['a'] * objs['b'])),
                       np.log10(r), facecolors='g', edgecolors='gray',
                       alpha=0.30, s=(500.0 / np.sqrt(dist)))
    axes[0, 1].set_xlabel('log(Flux/Area)', fontsize=22)
    axes[0, 1].set_ylabel('log(Radius/pixel)', fontsize=22)
    if highlight is not None:
        axes[0, 1].scatter((np.log10(objs[highlight]['flux']/
                           (objs[highlight]['a'] * objs[highlight]['b']))),
                           np.log10(r[highlight]), color='b',
                           alpha=0.50, s=(500.0 / np.sqrt(dist[highlight])))
    if cenInd is not None:
        axes[0, 1].scatter((np.log10(objs[cenInd]['flux']/
                            (objs[cenInd]['a'] * objs[cenInd]['b']))),
                           np.log10(r[cenInd]), color='r',
                           alpha=0.60, s=(500.0 / np.sqrt(dist[cenInd])))
    axes[0, 1].text(0.60, 0.06, 'Size: Approximity', fontsize=25,
                    transform=axes[0,1].transAxes, ha='center')
    if prefix is not None:
        axes[0, 1].text(0.50, 0.91, prefix, fontsize=20, ha='center',
                        transform=axes[0,0].transAxes)

    #  Fig3
    if fluxRatio1 is not None:
        axes[1, 0].axhline(np.log10(objs[cenInd]['flux']*fluxRatio1),
                           linestyle='--', lw=2.0)
    if fluxRatio2 is not None:
        axes[1, 0].axhline(np.log10(objs[cenInd]['flux']*fluxRatio2),
                           linestyle=':', lw=2.0)
    if r1 is not None:
        axes[1, 0].axvline(r1, linestyle='-', lw=2.0)
    if r2 is not None:
        axes[1, 0].axvline(r2, linestyle='--', lw=2.0)
    if r3 is not None:
        axes[1, 0].axvline(r3, linestyle=':', lw=2.0)
    axes[1, 0].scatter(dist, np.log10(objs['flux']),
                       facecolors='g', edgecolors='gray',
                       alpha=0.30, s=(r*3.0))
    axes[1, 0].set_xlabel('Central Distance (pixels)', fontsize=22)
    axes[1, 0].set_ylabel('log(Flux)', fontsize=22)
    if highlight is not None:
        axes[1, 0].scatter(dist[highlight],
                           np.log10(objs[highlight]['flux']),
                           color='b', alpha=0.50,
                           s=(r[highlight]*3.0))
    if cenInd is not None:
        axes[1, 0].scatter(dist[cenInd],
                           np.log10(objs[cenInd]['flux']),
                           color='r', alpha=0.60,
                           s=(r[cenInd]*3.0))
    axes[1, 0].text(0.60, 0.06, 'Size: Object Size', fontsize=25,
                    transform=axes[1,0].transAxes, ha='center')

    #  Fig4
    if r1 is not None:
        axes[1, 1].axvline(r1, linestyle='-', lw=2.0)
    if r2 is not None:
        axes[1, 1].axvline(r2, linestyle='--', lw=2.0)
    if r3 is not None:
        axes[1, 1].axvline(r3, linestyle=':', lw=2.0)
    axes[1, 1].scatter(dist, np.log10(r), facecolors='g',
                       edgecolors='gray', alpha=0.30,
                       s=(np.log10(objs['flux']) ** 4.0 + 10.0))
    axes[1, 1].set_xlabel('Central Distance (pixels)', fontsize=22)
    axes[1, 1].set_ylabel('log(Radius/pixel)', fontsize=22)
    if highlight is not None:
        axes[1, 1].scatter(dist[highlight], np.log10(r[highlight]),
                           color='b', alpha=0.50,
                           s=(np.log10(objs[highlight]['flux']) ** 4.0 + 10.0))
    if cenInd is not None:
        axes[1, 1].scatter(dist[cenInd], np.log10(r[cenInd]),
                           color='r', alpha=0.60,
                           s=(np.log10(objs[cenInd]['flux']) ** 4.0 + 10.0))
    axes[1, 1].text(0.60, 0.06, 'Size: Object Flux', fontsize=25,
                    transform=axes[1,1].transAxes, ha='center')

    # Adjust the figure
    for ax in axes.flatten():
        ax.minorticks_on()
        for tick in ax.xaxis.get_major_ticks():
            tick.label1.set_fontsize(fontsize)
        for tick in ax.yaxis.get_major_ticks():
            tick.label1.set_fontsize(fontsize)
    # Save the figure
    fig.savefig(outPNG)
    plt.close(fig)


def showSEPImage(image, contrast=0.2, size=10, cmap=cmap1,
                 title='Image', pngName='sep.png', titleInside=True,
                 ellList1=None, ellList2=None, ellList3=None,
                 ellColor1='b', ellColor2='r', ellColor3='g',
                 ell1=None, ell2=None, ell3=None,
                 ax=None, mask=None):
    """
    Visualization of the results

    """
    fig = plt.figure(figsize=(size, size))
    fig.subplots_adjust(hspace=0.0, wspace=0.0,
                        bottom=0.08, left=0.08,
                        top=0.92, right=0.98)
    ax = fig.add_axes([0.000, 0.002, 0.996, 0.996])
    fontsize = 16
    ax.minorticks_on()

    for tick in ax.xaxis.get_major_ticks():
        tick.label1.set_fontsize(fontsize)
    for tick in ax.yaxis.get_major_ticks():
        tick.label1.set_fontsize(fontsize)

    ax.set_title(title, fontsize=28, fontweight='bold', color='r')
    if not titleInside:
        ax.title.set_position((0.5, 1.01))
    else:
        ax.title.set_position((0.5, 0.90))

    imcopy = copy.deepcopy(image)
    imin, imax = hUtil.zscale(imcopy, contrast=contrast, samples=500)
    if mask is not None:
        imcopy[mask > 0] = np.nan

    ax.imshow(np.arcsinh(imcopy), interpolation="none",
               vmin=imin, vmax=imax, cmap=cmap)

    if ellList1 is not None:
        for e in ellList1:
            ax.add_artist(e)
            e.set_clip_box(ax.bbox)
            e.set_alpha(0.8)
            e.set_edgecolor(ellColor1)
            e.set_facecolor('none')
            e.set_linewidth(1.5)

    if ellList2 is not None:
        for e in ellList2:
            ax.add_artist(e)
            e.set_clip_box(ax.bbox)
            e.set_alpha(0.8)
            e.set_edgecolor(ellColor2)
            e.set_facecolor('none')
            e.set_linewidth(1.5)

    if ellList3 is not None:
        for e in ellList3:
            ax.add_artist(e)
            e.set_clip_box(ax.bbox)
            e.set_alpha(0.8)
            e.set_edgecolor(ellColor3)
            e.set_facecolor('none')
            e.set_linewidth(1.5)

    if ell1 is not None:
        ax.add_artist(ell1)
        ell1.set_clip_box(ax.bbox)
        ell1.set_alpha(0.8)
        ell1.set_edgecolor('r')
        ell1.set_facecolor('none')
        ell1.set_linewidth(2.0)
        ell1.set_linestyle('dashed')

    if ell2 is not None:
        ax.add_artist(ell2)
        ell2.set_clip_box(ax.bbox)
        ell2.set_alpha(0.8)
        ell2.set_edgecolor('k')
        ell2.set_facecolor('none')
        ell2.set_linewidth(2.0)
        ell2.set_linestyle('dashed')

    if ell3 is not None:
        ax.add_artist(ell3)
        ell3.set_clip_box(ax.bbox)
        ell3.set_alpha(0.8)
        ell3.set_edgecolor('k')
        ell3.set_facecolor('none')
        ell3.set_linewidth(2.0)
        ell3.set_linestyle('dashed')

    fig.savefig(pngName)
    plt.close(fig)


def addFlag(dictName, flagName, flagValue):
    """
    Add a flag to a dictionary

    """
    # If the dictionary for flags has not been defined, make a new one
    try:
        dictName
    except NameError:
        dictName = np.array([], dtype=[('name', 'a20'), ('value', 'i1')])
    # Assign a new flag
    newFlag = (str(flagName), flagValue)
    newDict = np.insert(dictName, 0, newFlag)

    return newDict


def objList2Reg(objs, regName='ds9.reg', color='Blue'):
    """
    Save the Object List to DS9 Region File

    """
    # DS9 region file header
    head1 = '# Region file format: DS9 version 4.1\n'
    head2 = 'global color=%s width=2\n' % color
    head3 = 'image\n'
    # Open the output file and write the header
    regFile = open(regName, 'w')
    regFile.write(head1)
    regFile.write(head2)
    regFile.write(head3)
    # Save the data
    # The format for ellipse is: "ellipse x y radius radius angle"
    for obj in objs:
        ellLine = 'ellipse ' + str(obj['x']) + ' ' + str(obj['y']) + ' ' + \
                  str(obj['a'] / 2.0) + ' ' + str(obj['b'] / 2.0) + ' ' + \
                  str(obj['theta'] * 180.0 / np.pi) + '\n'
        regFile.write(ellLine)
    # Close the file
    regFile.close()


def saveFits(img, fitsName, head=None, clobber=True):
    """
    Save an image to FITS file

    """
    imgHdu = fits.PrimaryHDU(img)
    if head is not None:
        imgHdu.header = head
    imgHdu.writeto(fitsName, clobber=clobber)


def saveSEPObjects(objs, prefix='sep_objects', csv=True,
                   reg=True, verbose=True, color='red'):
    """
    Save the properties of objects that are extracted by SEP into
    a cPickle file or .csv file, .deg file

    """
    # 1. Save a .pkl file
    pklFile = prefix + '.pkl'
    hUtil.saveToPickle(objs, pklFile)
    if os.path.isfile(pklFile):
        if verbose:
            print "###     Save object list to .pkl file: %s" % pklFile
    else:
        raise Exception("### Something is wrong with the .pkl file")
    # 2. Save a .csv file
    if csv:
        csvFile = prefix + '.csv'
        hUtil.saveToCSV(objs, csvFile)
        if os.path.isfile(csvFile):
            if verbose:
                print "###     Save object list to .csv file: %s" % csvFile
        else:
            raise Exception("### Something is wrong with the .csv file")
    # 3. Save a .deg file
    if reg:
        regFile = prefix + '.reg'
        objList2Reg(objs, regName=regFile, color=color)
        if os.path.isfile(regFile):
            if verbose:
                print "###     Save object list to .reg file: %s" % regFile
        else:
            raise Exception("### Something is wrong with the .reg file")


def adaptiveMask(objC, a=2.0, b=1.5, c=4.0, seeing=1.0,
                 pix=0.168, verbose=False):
    """
    Scale the size of mask for different objects according to their
    flux and major axis radii

    XXX This is still very empirical!
    We adopt the form of: Ratio = a*((log(A)-thrA) <= 0 ? 0) + b*logRho + c
    logRho = log10(Flux/(A*B));  and thrA=log10(seeing_fwhm/(2.0*pixscale))

    """
    # Corresponding to the pixel size of a seeing disk
    # Use as a threshold to select "point-ish" objects
    thrA = np.log10(seeing / (2.0 * pix))
    # "Flux density" like properties
    logRho = np.log10(objC['cflux']/(objC['a'] * objC['b']))
    # Logrithmic difference between the major axis radii and
    # the threshold size
    logA = (np.log10(np.sqrt(objC['a'])) - thrA )
    # Ignore all the "point-ish" objects
    logA[(logA < 0) | (logRho < 1.5)] = 0
    # Empirical function to get the mask size ratio
    rAdRatio = logA * a + logRho * b + c
    if verbose:
        print "### rAdRatio "
        print np.nanmin(rAdRatio)
        print np.nanmax(rAdRatio)
        print np.median(rAdRatio)

    return rAdRatio


def combMskImage(msk1, msk2):
    """
    Combine two mask images

    """
    if (msk1.shape[0] != msk2.shape[0]) or (msk1.shape[1] != msk2.shape[1]):
        raise Exception("### The two masks need to have the same shape!")
    mskComb = np.zeros(msk1.shape, dtype='uint8')
    mskComb[(msk1 > 0) | (msk2 >0)] = 1

    return mskComb


def combObjCat(objCold, objHot, tol=2.0, cenDistC=None, rad=80.0):
    """
    Merge the object lists from cold and hot run

    tol = 1.0  : Tolerance of central difference in unit of pixel
    """
    # Make a copy of the objects array
    objC = copy.deepcopy(objCold)
    objH = copy.deepcopy(objHot)
    # The central coordinates of each objects
    objCX = objC['xpeak']
    objCY = objC['ypeak']
    objHX = objH['xpeak']
    objHY = objH['ypeak']

    # Get the minimum separation between each Hot run object and all the
    # Cold run objects
    minDistH = np.asarray(map(lambda x, y: np.min(np.sqrt((x-objCX)**2.0
                                                         + (y-objCY)**2.0)),
                             objHX, objHY))
    # Locate the matched objects
    indMatchH = np.where(minDistH < tol)
    # Delete the matched objects from the Hot run list
    objHnew = copy.deepcopy(objH)
    objHnew = np.delete(objHnew, indMatchH)

    if cenDistC is not None:
        # Locate objects witin certain radii
        indObjCen = np.where(cenDistC < rad)
        objCnew = copy.deepcopy(objC)
        objCnew = np.delete(objCnew, indObjCen)
    else:
        objCnew = None

    # Try to account for the difference in size and area of the same
    # object from Cold and Hot run
    objMatchH = objH[(minDistH < tol) & (np.log10(objH['npix']) < 2.6)]

    # Do something similar to the Cold run list
    minDistC = np.asarray(map(lambda x, y: np.min(np.sqrt((x-objHX)**2.0
                                                         + (y-objHY)**2.0)),
                             objCX, objCY))
    indMatchC = np.where(minDistC < tol)
    objMatchC = objC[(minDistC < tol) & (np.log10(objC['npix']) < 2.6)]

    # This is designed to be only a rough match
    # Only works for not very big galaxies, will fail for stars
    aRatio = (np.nanmedian(objMatchC['a']) /
              np.nanmedian(objMatchH['a']))
    objHnew['a'] *= aRatio
    objHnew['b'] *= aRatio
    objH['a'] *= aRatio
    objH['b'] *= aRatio

    nRatio = (np.nanmedian(objMatchC['npix']) /
              np.nanmedian(objMatchH['npix']))
    objHnew['npix'] *= nRatio
    objH['npix'] *= nRatio

    if cenDistC is None:
        objComb = np.concatenate((objC, objHnew))
    else:
        objComb = np.concatenate((objH, objCnew))

    return objComb, objHnew, objCnew


def getConvKernel(kernel):
    """
    Convolution kernel for the SEP detections
    """
    if kernel is 1:
        # Tophat_3.0_3x3
        convKer = np.asarray([[0.560000, 0.980000, 0.560000],
                              [0.980000, 1.000000, 0.980000],
                              [0.560000, 0.980000, 0.560000]])
    elif kernel is 2:
        # Topcat_4.0_5x5
        convKer = np.asarray([[0.000000, 0.220000, 0.480000, 0.220000, 0.000000],
                              [0.220000, 0.990000, 1.000000, 0.990000, 0.220000],
                              [0.480000, 1.000000, 1.000000, 1.000000, 0.480000],
                              [0.220000, 0.990000, 1.000000, 0.990000, 0.220000],
                              [0.000000, 0.220000, 0.480000, 0.220000, 0.000000]])
    elif kernel is 3:
        # Topcat_5.0_5x5
        convKer = np.asarray([[0.150000, 0.770000, 1.000000, 0.770000, 0.150000],
                              [0.770000, 1.000000, 1.000000, 1.000000, 0.770000],
                              [1.000000, 1.000000, 1.000000, 1.000000, 1.000000],
                              [0.770000, 1.000000, 1.000000, 1.000000, 0.770000],
                              [0.150000, 0.770000, 1.000000, 0.770000, 0.150000]])
    elif kernel is 4:
        # Gaussian_3.0_5x5
        convKer = np.asarray([[0.092163, 0.221178, 0.296069, 0.221178, 0.092163],
                              [0.221178, 0.530797, 0.710525, 0.530797, 0.221178],
                              [0.296069, 0.710525, 0.951108, 0.710525, 0.296069],
                              [0.221178, 0.530797, 0.710525, 0.530797, 0.221178],
                              [0.092163, 0.221178, 0.296069, 0.221178, 0.092163]])
    elif kernel is 5:
        # Gaussian_4.0_7x7
        convKer = np.asarray([[0.047454, 0.109799, 0.181612, 0.214776, 0.181612, 0.109799, 0.047454],
                              [0.109799, 0.254053, 0.420215, 0.496950, 0.420215, 0.254053, 0.109799],
                              [0.181612, 0.420215, 0.695055, 0.821978, 0.695055, 0.420215, 0.181612],
                              [0.214776, 0.496950, 0.821978, 0.972079, 0.821978, 0.496950, 0.214776],
                              [0.181612, 0.420215, 0.695055, 0.821978, 0.695055, 0.420215, 0.181612],
                              [0.109799, 0.254053, 0.420215, 0.496950, 0.420215, 0.254053, 0.109799],
                              [0.047454, 0.109799, 0.181612, 0.214776, 0.181612, 0.109799, 0.047454]])
    elif kernel is 6:
        # Gaussian_5.0_9x9
        convKer = np.asarray([[0.030531, 0.065238, 0.112208, 0.155356, 0.173152, 0.155356, 0.112208, 0.065238, 0.030531],
                              [0.065238, 0.139399, 0.239763, 0.331961, 0.369987, 0.331961, 0.239763, 0.139399, 0.065238],
                              [0.112208, 0.239763, 0.412386, 0.570963, 0.636368, 0.570963, 0.412386, 0.239763, 0.112208],
                              [0.155356, 0.331961, 0.570963, 0.790520, 0.881075, 0.790520, 0.570963, 0.331961, 0.155356],
                              [0.173152, 0.369987, 0.636368, 0.881075, 0.982004, 0.881075, 0.636368, 0.369987, 0.173152],
                              [0.155356, 0.331961, 0.570963, 0.790520, 0.881075, 0.790520, 0.570963, 0.331961, 0.155356],
                              [0.112208, 0.239763, 0.412386, 0.570963, 0.636368, 0.570963, 0.412386, 0.239763, 0.112208],
                              [0.065238, 0.139399, 0.239763, 0.331961, 0.369987, 0.331961, 0.239763, 0.139399, 0.065238],
                              [0.030531, 0.065238, 0.112208, 0.155356, 0.173152, 0.155356, 0.112208, 0.065238, 0.030531]])
    else:
        raise Exception("### More options will be available in the future")

    return convKer


def getEll2Plot(objects, radius=None):
    """
    Generate the ellipse shape for each object to plot
    """
    x  = objects['x'].copy()
    y  = objects['y'].copy()
    pa = objects['theta'].copy() # in unit of radian

    if radius is not None:
        a = radius.copy()
        b = radius.copy()*(objects['b'].copy()/objects['a'].copy())
    else:
        a  = objects['a'].copy()
        b  = objects['b'].copy()

    ells = [Ellipse(xy=np.array([x[i], y[i]]),
                    width=np.array(2.0 * b[i]),
                    height=np.array(2.0 * a[i]),
                    angle=np.array(pa[i]*180.0/np.pi + 90.0))
            for i in range(x.shape[0])]

    return ells


def getSbpValue(flux, pixX, pixY, zp=None):
    """
    Convert flux into surface brightness value

    TODO: Right now only support log-magnitude,
    In the future, should also support asinh-magnitude
    See:
    http://www.astro.washington.edu/users/ajc/ssg_page_working/elsst/opsim.shtml?lightcurve_mags
    """
    sbp = -2.5 * np.log10(flux/(pixX * pixY))
    if zp is not None:
        sbp += zp
    return sbp


def getFluxRadius(img, objs, maxSize=25.0, subpix=5, byteswap=True,
                  mask=None):
    """
    Given the original image, the detected objects, using SEP
    to measure different flux radius: R20, R50, R90

    """
    # TODO: Mask is not working now
    # Make a copy of the image, and byteswap it if necessary
    imgOri = copy.deepcopy(img)
    if byteswap:
        imgOri = imgOri.byteswap(True).newbyteorder()
        if mask is not None:
            mskArr = copy.deepcopy(mask)
            mskArr = mskArr.byteswap(True).newbyteorder()
    else:
        imgOri = img
        if mask is not None:
            mskArr = mask
    # Get the flux radius
    if mask is not None:
        rflux, flag = sep.flux_radius(imgOri, objs['x'], objs['y'],
                                      maxSize*objs['a'], [0.2, 0.5, 0.9],
                                      normflux=objs['cflux'], subpix=subpix,
                                      mask=mskArr, maskthresh=0)
    else:
        rflux, flag = sep.flux_radius(imgOri, objs['x'], objs['y'],
                                      maxSize*objs['a'], [0.2, 0.5, 0.9],
                                      normflux=objs['cflux'], subpix=subpix)
    if isinstance(objs['x'], (int, long, float)):
        r20, r50, r90 = rflux[0], rflux[1], rflux[2]
    else:
        r20 = np.array([rr[0] for rr in rflux])
        r50 = np.array([rr[1] for rr in rflux])
        r90 = np.array([rr[2] for rr in rflux])

    return r20, r50, r90


def objDistTo(objs, cenX, cenY, usePeak=False, convol=False, ellipse=True,
        pa=0.0, q=0.99):
    """
    Get the distance of objects from SEP to a reference point on the image

    """
    if usePeak:
        if convol:
            xc, yc = objs['xcpeak'], objs['ycpeak']
        else:
            xc, yc = objs['xpeak'], objs['ypeak']
    else:
        xc, yc = objs['x'], objs['y']

    if ellipse:
        theta = (pa * np.pi / 180.0)
        distA = ((xc - cenX) * np.cos(theta) + (yc - cenY) * np.sin(theta)) ** 2.0
        distB = (((yc - cenY) * np.cos(theta) - (xc - cenX) * np.sin(theta)) / q) ** 2.0
        return np.sqrt(distA + distB)
    else:
        return np.sqrt((xc - cenX)**2 + (yc - cenY)**2)


def readCutoutHeader(imgHead, pixDefault=0.168,
                     zpDefault=27.0):
    """
    Read the pixel scale, image size, and photometric zeropoint form
    the image header

    TODO: Make it more generic, right now it is only for HSC
     * pixel scale can be read from the WCS information
    XXX: Right now, the TOTEXPT is not working for HSC
    """
    # Get the pixel scale of the image
    try:
        pixScaleX = pixScaleY = imgHead['PIXEL']
    except:
        print "### Pixel scale keyword is not available in the header"
        print "### Default %6.3f arcsec/pixel value is adopted" % pixDefault
        pixScaleX = pixScaleY = pixDefault
    # Get the image size
    imgSizeX = imgHead['NAXIS1']
    imgSizeY = imgHead['NAXIS2']
    # Get the photometric zeropoint
    try:
        photZP = imgHead['PHOTZP']
    except:
        print "### PHOZP keyword is not available in the header"
        print "### Default value of %5.2f is adopted!" % zpDefault
        photZP = zpDefault
    # Total exptime
    try:
        expTot = imgHead['TOTEXPT']
    except:
        print "### TOTEXPT keyword is not available in the header"
        print "### Use 1.0 sec instead"
        expTot = 1.0

    return pixScaleX, pixScaleY, imgSizeX, imgSizeY, photZP, expTot


def imgByteSwap(data):
    """
    Byte Swap before sending image to SEP
    """
    dataCopy = copy.deepcopy(data)
    return dataCopy.byteswap(True).newbyteorder()


def sepGetBkg(img, mask=None, bkgSize=None, bkgFilter=None):
    """
    Wrapper of SEP.Background function
    """
    if bkgSize is None:
        dimX, dimY = img.shape
        bkgX = imt(dimX / 15)
        bkgY = imt(dimY / 15)
    else:
        bkgX = bkgY = int(bkgSize)
    if bkgFilter is None:
        bkgFilter = 4

    bkg = sep.Background(img, mask, bkgX, bkgY, bkgFilter, bkgFilter)
    # Subtract the Background off
    bkg.subfrom(img)

    return bkg, img


def readCutoutImage(prefix, root=None, variance=False):

    # Get the names of necessary input images
    imgFile = prefix + '_img.fits'
    mskFile = prefix + '_bad.fits'
    detFile = prefix + '_det.fits'
    if not variance:
        sigFile = prefix + '_sig.fits'
    else:
        sigFile = prefix + '_var.fits'

    if root is not None:
        imgFile = os.path.join(root, imgFile)
        mskFile = os.path.join(root, mskFile)
        detFile = os.path.join(root, detFile)
        sigFile = os.path.join(root, sigFile)

    # Image Data
    if os.path.islink(imgFile):
        imgOri = os.readlink(imgFile)
        imgFile = imgOri
    if os.path.isfile(imgFile):
        imgHdu = fits.open(imgFile)
        imgArr = imgHdu[0].data
    else:
        raise Exception("### Can not find the Input Image File : %s !" % imgFile)
    # Header
    imgHead = imgHdu[0].header

    # TODO: Should also make this optional
    # Bad mask
    if os.path.islink(mskFile):
        mskOri = os.readlink(mskFile)
        mskFile = mskOri
    if os.path.isfile(mskFile):
        mskHdu = fits.open(mskFile)
        mskArr = mskHdu[0].data
    else:
        raise Exception("### Can not find the Input Mask File : %s !" % mskFile)

    # Optional detection plane
    if os.path.islink(detFile):
        detOri = os.readlink(detFile)
        detFile = detOri
    if os.path.isfile(detFile):
        detHdu = fits.open(detFile)
        detArr = detHdu[0].data
    else:
        print "### Can not find the coadd DetectionPlane file!"
        detArr = None

    # Optional sigma plane
    if os.path.islink(sigFile):
        sigOri = os.readlink(sigFile)
        sigFile = sigOri
    if os.path.isfile(sigFile):
        sigHdu = fits.open(sigFile)
        sigArr = sigHdu[0].data
    else:
        print "### Can not find the coadd sigectionPlane file!"
        sigArr = None

    return imgArr, imgHead, mskArr, detArr, sigArr


def coaddCutoutPrepare(prefix, root=None, srcCat=None, verbose=True,
                       bSizeH=8, bSizeC=80, thrH=2.5, thrC=1.2, mask=1,
                       growC=6.8, growW=4.0, growH=1.8, kernel=4, central=1,
                       galX=None, galY=None, galR1=None, galR2=None, galR3=None,
                       galQ=None, galPA=None, visual=True, suffix='',
                       combBad=True, combDet=False, noBkgC=False, noBkgH=False,
                       minDetH=5.0, minDetC=5.0, debThrH=20.0, debThrC=32.0,
                       debConH=0.01, debConC=0.01, useSigArr=False,
                       minCenDist=20.0, rerun=None):
    """
    The structure of the cutout has been changed.  Now the cutout procedure
    will generate separated files for Image, Bad Mask, Detection Plane, and
    Variance (also Sigma) images.  Souce catalogs can also be made available.

    Right now, this new format is only available for the coaddImageCutFull()
    function; coaddImageCutout() will be modified later to also adopt this
    format

    """
    # 0. Get necessary information
    # Read the input cutout image
    imgArr, imgHead, mskArr, detArr, sigArr = readCutoutImage(prefix, root=root)
    if (root is not None) and (root[-1] != '/'):
        root += '/'
    if root is None:
        root = ''
    if verbose:
        print "##########################################################################"
        print "### DEAL WITH IMAGE : %s" % (root + prefix + '_img.fits')

    if rerun is not None:
        rerunDir = os.path.join(root, rerun.strip())
        if not os.path.isdir(rerunDir):
            os.makedirs(rerunDir)
    else:
        rerunDir = root

    fitsList = glob.glob(root + '*.fits')
    for fitsFile in fitsList:
        seg = fitsFile.split('/')
        link = os.path.join(rerunDir, seg[-1])
        os.symlink(fitsFile, link)

    if detArr is None:
        detFound = False
    else:
        detFound = True
    # Flags
    sepFlags = np.array([], dtype=[('name', 'a20'), ('value', 'i1')])

    # Sometimes NaN pixels exist for the image. Replace them, and make sure that they are
    #    masked out
    indImgNaN = np.isnan(imgArr)
    if verbose:
        print "###   %6d NaN pixels have been replaced and masked out!" % len(np.where(
            indImgNaN)[0])
    if len(np.where(indImgNaN)[0] > 0):
        sepFlags = addFlag(sepFlags, 'NAN_PIX', True)
        imgArr[indImgNaN] = 0.0
    else:
        sepFlags = addFlag(sepFlags, 'NAN_PIX', False)

    ### TODO: expTot is still not working
    pixX, pixY, dimX, dimY, photZP, expTot = readCutoutHeader(imgHead)
    if verbose:
        print "###    The pixel scale in X/Y directions " + \
                "are %7.4f / %7.4f arcsecs" % (pixX, pixY)
        print "###    The image size in X/Y directions " + \
                "are %d / %d pixels" % (dimX, dimY)
        print "###                      %10.2f / %10.2f arcsecs" % (dimX * pixX,
                dimY * pixY)
        print "###    The photometric zeropoint is %6.2f " % photZP
        #print "### The total exposure time for the center is %6.1f secs" % expTot
    # Whether the center of the galaxy is provided; If not, assume that
    # galaxy center is located at the image center
    if galX is None:
        galX = (dimX / 2.0)
    if galY is None:
        galY = (dimY / 2.0)
    if verbose:
        print "###    The Galaxy Center is assumed at %6.1f, %6.1f" % (galX, galY)
    # Suffix
    if (suffix is not '') and (suffix[-1] is not '_'):
        suffix = suffix + '_'

    # 1. Get the backgrounds
    """
    Construct "background" images with different size and filters using SEP,
    and subtract these background off before extract objects

    The SEP detections will be run in two-modes:
        Cold: relative global background; low-detection threshold
        Hot:  very local background; median-detection threshold
    """
    if verbose:
        print "### 1a. BACKGROUND SUBTRACTION USING SEP -- COLD RUN"
    # Cold Background Run
    fSizeC = int(bSizeC / 2)
    imgC = imgByteSwap(imgArr)
    bkgC, imgSubC = sepGetBkg(imgC, bkgSize=bSizeC, bkgFilter=fSizeC)
    rmsC = bkgC.globalrms
    if verbose:
        print "###     Cold Background -- Avg: %9.5f " % bkgC.globalback + \
              "       RMS: %9.5f " % bkgC.globalrms
    if noBkgC:
        if verbose:
            print "### SKIP THE BACKGROUND SUBTRACTION FOR THE COLD RUN!"
        imgSubC = imgByteSwap(imgArr)
        sepFlags = addFlag(sepFlags, 'NO_CBKG', True)
    else:
        sepFlags = addFlag(sepFlags, 'NO_CBKG', False)

    if visual:
        # Fig.a
        bkgPNG1 = os.path.join(rerunDir, (prefix + '_' + suffix + 'bkgC.png'))
        showSEPImage(bkgC.back(), contrast=0.3, title='Background - Cold Run',
                     pngName=bkgPNG1)

    if verbose:
        print "### 1b. BACKGROUND SUBTRACTION USING SEP -- HOT RUN"
    # Hot Background Run
    fSizeH = int(bSizeH / 2)
    imgH = imgByteSwap(imgArr)
    bkgH, imgSubH = sepGetBkg(imgH, bkgSize=bSizeH, bkgFilter=fSizeH)
    rmsH = bkgH.globalrms
    if verbose:
        print "###     Hot Background  -- Avg: %9.5f " % bkgH.globalback + \
              "       RMS: %9.5f " % bkgH.globalrms

    if noBkgH:
        if verbose:
            print "### 1b. SKIP THE BACKGROUND SUBTRACTION FOR THE COLD RUN!"
        imgSubH = imgByteSwap(imgArr)
        sepFlags = addFlag(sepFlags, 'NO_HBKG', True)
    else:
        sepFlags = addFlag(sepFlags, 'NO_HBKG', False)

    if visual:
        # Fig.b
        bkgPNG2 = os.path.join(rerunDir, (prefix + '_' + suffix + 'bkgH.png'))
        showSEPImage(bkgH.back(), contrast=0.3, title='Background - Hot Run',
                     pngName=bkgPNG2)

    # 2. Object detections
    """
    Use SEP to extract information of detected objects
    """
    """ Cold Run """
    if verbose:
        print "### 2. DETECT OBJECTS USING SEP"
    # Parameters for cold run
    if verbose:
        print "###  2.1. OBJECT DETECTION: COLD RUN"
        print "###     Cold run detection threshold: %4.1f" % thrC
    convKerC = getConvKernel(kernel)
    # Cold Run
    if useSigArr and (sigArr is not None):
        errArr = imgByteSwap(sigArr)
        detThrC = thrC
        objC = sep.extract(imgSubC, detThrC, minarea=minDetC, conv=convKerC,
                           deblend_nthresh=debThrC, deblend_cont=debConC,
                           err=errArr)
    else:
        detThrC = rmsC * thrC
        objC = sep.extract(imgSubC, detThrC, minarea=minDetC, conv=convKerC,
                           deblend_nthresh=debThrC, deblend_cont=debConC)
    if verbose:
        print "###    %d objects have been detected in the Cold Run" % objC['x'].shape[0]

    # Save objects list to different format of files
    prefixC = os.path.join(rerunDir, (prefix + '_' + suffix + 'objC'))
    saveSEPObjects(objC, prefix=prefixC, color='Blue')

    # Calculate the object-galaxy center distance
    cenDistC = objDistTo(objC, galX, galY)

    ## Get first estimations of basic parameters for central galaxy
    # Center; Add a flag about this
    cenObjIndexC = np.argmin(cenDistC)
    # Get its shape and size
    galFlux = objC[cenObjIndexC]['cflux']
    galCenX = objC[cenObjIndexC]['x']
    galCenY = objC[cenObjIndexC]['y']
    if verbose:
        print "###  2.2. ESTIMATE THE B/A AND PA OF THE GALAXY"
    if galQ is None:
        galQ  = (objC[cenObjIndexC]['b'] / objC[cenObjIndexC]['a'])
    if galPA is None:
        galPA = (objC[cenObjIndexC]['theta'] * 180.0 / np.pi)
    if verbose:
        print "###    (b/a) of the galaxy: %6.2f" % galQ
        print "###      PA  of the galaxy: %6.1f" % galPA
    galR20, galR50, galR90 = getFluxRadius(imgArr, objC[cenObjIndexC], maxSize=20.0,
            subpix=5)
    if np.isnan(galR20):
        sepFlags = addFlag(sepFlags, 'R20_FAIL', True)
        galR20 = objC[cenObjIndexC]['a']
    else:
        sepFlags = addFlag(sepFlags, 'R20_FAIL', False)
    if np.isnan(galR50):
        sepFlags = addFlag(sepFlags, 'R50_FAIL', True)
        galR50 = objC[cenObjIndexC]['a'] * 1.5
    else:
        sepFlags = addFlag(sepFlags, 'R50_FAIL', False)
    if np.isnan(galR90):
        sepFlags = addFlag(sepFlags, 'R90_FAIL', True)
        galR90 = objC[cenObjIndexC]['a'] * 3.0
    else:
        sepFlags = addFlag(sepFlags, 'R90_FAIL', False)

    if verbose:
        print "###    R20 Cen: %7.2f" % galR20
        print "###    R50 Cen: %7.2f" % galR50
        print "###    R90 Cen: %7.2f" % galR90
    if (galR90 > (dimX / 3.0) or galR90 > (dimY / 3.0)):
        sepFlags = addFlag(sepFlags, 'R90_BIG', True)
    else:
        sepFlags = addFlag(sepFlags, 'R90_BIG', False)
    # Scale r50 to galR1, r90 to galR2 and galR3
    if verbose:
        print "###  2.3. ESTIMATING THE GAL_R1/R2/R3"
    ### TODO: Not perfect parameters
    if galR1 is None:
        galR1 = (galR50 * 2.5)
    if galR2 is None:
        galR2 = (galR90 * 2.5)
    if galR3 is None:
        galR3 = (galR90 * 5.0)
    if verbose:
        print "###    galR1: %7.2f" % galR1
        print "###    galR2: %7.2f" % galR2
        print "###    galR3: %7.2f" % galR3
    # Make a flag if the galR3 is too large
    if (galR3 >= dimX / 1.4):
        sepFlags = addFlag(sepFlags, 'R3_BIG', True)
    else:
        sepFlags = addFlag(sepFlags, 'R3_BIG', False)

    # New estimations of central distance using elliptical coordinates
    cenDistC = objDistTo(objC, galX, galY, pa=galPA, q=galQ)

    """ Hot Run """
    # Parameters for hot run
    if verbose:
        print "###  2.4. OBJECT DETECTION: HOT RUN"
        print "###     Hot run detection threshold: %4.1f" % thrH
    convKerH = getConvKernel(kernel)
    # Hot Run
    if useSigArr and (sigArr is not None):
        detThrH = thrH
        objH = sep.extract(imgSubH, detThrH, minarea=minDetH, conv=convKerH,
                           deblend_nthresh=debThrH, deblend_cont=debConH,
                           err=errArr)
    else:
        detThrH = rmsH * thrH
        objH = sep.extract(imgSubH, detThrH, minarea=minDetH, conv=convKerH,
                           deblend_nthresh=debThrH, deblend_cont=debConH)
    if verbose:
        print "###    %d objects have been detected in the Hot Run" % objH['x'].shape[0]
    # Save objects list to different format of files
    prefixH = os.path.join(rerunDir, (prefix + '_' + suffix + 'objH'))
    saveSEPObjects(objH, prefix=prefixH, color='Red')
    # Calculate the object-galaxy center distance
    cenDistH = objDistTo(objH, galX, galY, pa=galPA, q=galQ)

    # Visualize these detections
    if visual:
        # Fig.c
        objPNG1 = os.path.join(rerunDir, (prefix + '_' + suffix + 'objC.png'))
        objEllC = getEll2Plot(objC, radius=(objC['a'] * growH))
        showSEPImage(imgSubC, contrast=0.06, title='Detections - Cold Run',
                     pngName=objPNG1, ellList1=objEllC, ellColor1='b')
        # Fig.d
        objPNG2 = os.path.join(rerunDir, (prefix + '_' + suffix + 'objH.png'))
        objEllH = getEll2Plot(objH, radius=(objH['a'] * growH))
        showSEPImage(imgSubH, contrast=0.10, title='Detections - Hot Run',
                     pngName=objPNG2, ellList1=objEllH, ellColor1='r')

    # 3. Merge the objects from Cold and Hot runs together
    if verbose:
        print "### 3. COMBINE OBJECTS FROM COLD AND HOT RUN "
    # Merge the object lists from Cold and
    objComb, objHnew, objCnew = combObjCat(objC, objH, cenDistC=cenDistC,
            rad=galR90, tol=2.0)

    # Also save the combined object lists
    prefixComb = os.path.join(rerunDir, (prefix + '_' + suffix + 'objComb'))
    saveSEPObjects(objComb, prefix=prefixComb, color='Green')
    # Calculate the object-galaxy center distance
    cenDistComb = objDistTo(objComb, galX, galY, pa=galPA, q=galQ)
    cenObjIndex = np.argmin(cenDistComb)
    if verbose:
        print "###    %d objects are left in the combined list" % len(objComb)
    if visual:
        # Fig.e
        objPNG3 = os.path.join(rerunDir, (prefix + '_' + suffix + 'objComb.png'))
        objEllComb = getEll2Plot(objComb, radius=(objComb['a'] * growH))
        showSEPImage(imgSubC, contrast=0.06, title='Detections - Combined',
                     pngName=objPNG3, ellList1=objEllComb, ellColor1='orange')

    # 4. Extract Different Flux Radius: R20, R50, R90 for every objects
    if verbose:
        print "### 4. EXTRACTING R20, R50, R90 OF EACH OBJECTS "
    # XXX: imgArr or imgSubC
    r20, r50, r90 = getFluxRadius(imgArr, objComb, maxSize=25.0, subpix=5)
    rPhoto = objComb['a']
    # Some objects at the edge could have failed R50/R90, replace then with 'a'
    r20[np.isnan(r20)] = rPhoto[np.isnan(r20)]
    r50[np.isnan(r50)] = rPhoto[np.isnan(r50)]
    r90[np.isnan(r90)] = rPhoto[np.isnan(r90)]

    # Concentration index
    concen = (r90 / r50)
    if visual:
        # Fig.f
        objPNG4 = os.path.join(rerunDir, (prefix + '_' + suffix + 'objRad.png'))
        objEllR20 = getEll2Plot(objComb, radius=r20)
        objEllR50 = getEll2Plot(objComb, radius=r50)
        objEllR90 = getEll2Plot(objComb, radius=r90)
        # Add three ellipses to highlight galR1, R2, & R3
        ell1 = Ellipse(xy=(galX, galY),
                       width=(2.0 * galR90 * galQ),
                       height=(2.0 * galR90),
                       angle=(galPA + 90.0))
        ell2 = Ellipse(xy=(galX, galY),
                       width=(2.0 * galR2 * galQ),
                       height=(2.0 * galR2),
                       angle=(galPA + 90.0))
        ell3 = Ellipse(xy=(galX, galY), width=(2.0 * galR3 * galQ),
                       height=(2.0 * galR3),
                       angle=(galPA + 90.0))
        showSEPImage(imgSubC, contrast=0.20, title='Flux Radius: R20/R50/R90',
                     pngName=objPNG4,
                     ellList1=objEllR20, ellColor1='r',
                     ellList2=objEllR50, ellColor2='orange',
                     ellList3=objEllR90, ellColor3='b',
                     ell1=ell1, ell2=ell2, ell3=ell3)


    # 5. Mask all objects on the image
    growConcenIndex = 0.8  ## XXX: Very, very empirical right now

    if verbose:
        print "### 5. MASKING OUT ALL OBJECTS ON THE IMAGE "
    mskAll = np.zeros(imgSubC.shape, dtype='uint8')
    objMskAll = copy.deepcopy(objC)
    if mask == 1:
        # TODO: This is still not idea, even using flux radius, should take
        #       the compactness (R90/R50) and (R50/R20) into account
        # Make a ALL_OBJECT mask using the r90
        rMajor = objMskAll['a']
        rMinor = objMskAll['b']
        growMsk = growC * 1.5
        sep.mask_ellipse(mskAll, objC['x'], objC['y'],
                         rMajor, rMinor, objC['theta'], r=growMsk)
        # Make a new objList, and change the size
        objMskAll['a'] = rMajor * growMsk
        objMskAll['b'] = rMinor * growMsk
    elif mask == 2:
        # Grow the cold run detections using the adaptive method
        # Use the new size to mask out all objects
        adGrowC = adaptiveMask(objC, a=2.2)
        # Build a ALL_OBJECT Mask
        sep.mask_ellipse(mskAll, objC['x'], objC['y'],
                rMajor, rMinor, objC['theta'], r=adGrowC)
        # Make a new objList, and change the size
        objMskAll['a'] = adGrowC * rMajor
        objMskAll['b'] = adGrowC * rMinor
    else:
        raise Exception("mask == 1 or mask == 2")
    if combBad:
        mskAll = combMskImage(mskAll, mskArr)
    if combDet and detFound:
        mskAll = combMskImage(mskAll, detArr)
    # Also mask out the NaN pixels
    mskAll[indImgNaN] = 1

    # Save the mask to FITS
    mskAllFile = os.path.join(rerunDir, (prefix + '_' + suffix + 'mskall.fits'))
    saveFits(mskAll, mskAllFile, head=imgHead)
    # Save the Objlist using the growed size
    prefixM = os.path.join(rerunDir, (prefix + '_' + suffix + 'mskall'))
    saveSEPObjects(objMskAll, prefix=prefixM, color='Blue')
    if visual:
        # Fig.f
        mskPNG1 = os.path.join(rerunDir, (prefix + '_' + suffix + 'mskall.png'))
        showSEPImage(imgSubC, contrast=0.75, title='Mask - All Objects',
                     pngName=mskPNG1, mask=mskAll)


    # 6. Remove the central object (or clear the central region)
    #    Separate the objects into different group and mask them out using
    #    different growth ratio
    if verbose:
        print "### 6. CLEAR THE CENTRAL REGION AROUND THE GALAXY"
        print "###  6.2. CLEAR A REGION AROUND CENTRAL GALAXY"
    objNoCen  = copy.deepcopy(objComb)
    r90NoCen  = copy.deepcopy(r90)
    distNoCen = copy.deepcopy(cenDistComb)
    if central == 1:
        indCen = np.where(cenDistComb < minCenDist)
        if verbose:
            print "###    %d objects are found in the central region of the CombList" % len(indCen[0])
        # Remove the central objects from the list and r90 array
        objNoCen  = np.delete(objNoCen,  indCen)
        r90NoCen  = np.delete(r90NoCen,  indCen)
        distNoCen = np.delete(distNoCen, indCen)
    elif central == 2:
        # Remove all objects within certain radii to the center of galaxy
        # TODO: Not perfect parameter choice
        indCen = np.where(cenDistComb < galR2)
        if verbose:
            print "###    %d objects are found in the central region" % len(indCen[0])
        objNoCen  = np.delete(objNoCen,  indCen)
        r90NoCen  = np.delete(r90NoCen,  indCen)
        distNoCen = np.delete(distNoCen, indCen)
    if len(indCen[0]) > 1:
        sepFlags = addFlag(sepFlags, 'MULTICEN', True)
    else:
        sepFlags = addFlag(sepFlags, 'MULTICEN', False)

    # Put the central objects from hot run to the mask
    if verbose:
        print "###  6.3. REMOVE THE CENTRAL OBJECT FROM THE HOT RUN"
    indCenH = np.where(cenDistH < minCenDist)
    objNoCenH = copy.deepcopy(objH)
    objNoCenH = np.delete(objNoCenH, indCenH)

    # 7. Convert the list of SEP detections to initial guess of 1-Comp
    #     GALFIT model
    if verbose:
        print "### 7. INITIAL GUESS OF PARAMETERS FOR 1-SERSIC MODEL OF GALAXIES"
        print "###  7.1. SELECTING OBJECTS NEED TO BE FIT"
    # Group 1: Objects that are too close to the galaxy center
    #          Could be star or galaxy
    group1 = np.where(cenDistComb <= galR50)
    if len(group1[0]) > 1:
        sepFlags = addFlag(sepFlags, 'G1_EXIST', True)
    else:
        sepFlags = addFlag(sepFlags, 'G1_EXIST', False)
    if verbose:
        print "###    %d objects are found in Group1" % len(group1[0])
    # Group 2: Objects that are within certain radius, and flux is larger
    #          than certain fraction of the main galaxy (Near)
    fluxRatio1 = 0.20
    group2 = np.where((cenDistComb > galR50) & (cenDistComb <= galR90) & (objComb['cflux'] >
        fluxRatio1 * galFlux))
    if len(group2[0]) != 0:
        sepFlags = addFlag(sepFlags, 'G2_EXIST', True)
    else:
        sepFlags = addFlag(sepFlags, 'G2_EXIST', False)
    if verbose:
        print "###    %d objects are found in Group2" % len(group2[0])
    # Group 3: Objects that are within certain radius, and flux is larger
    #          than certain fraction of the main galaxy (Far)
    fluxRatio2 = 0.50
    group3 = np.where((cenDistComb > galR90) & (cenDistComb <= galR90 * 3.0) & (objComb['cflux'] >
        fluxRatio2 * galFlux))
    if len(group3[0]) != 0:
        sepFlags = addFlag(sepFlags, 'G3_EXIST', True)
    else:
        sepFlags = addFlag(sepFlags, 'G3_EXIST', False)
    if verbose:
        print "###    %d objects are found in Group3" % len(group3[0])
    # Number of galaxies which should be considering fitting
    nObjFit = (len(group1[0]) + len(group2[0]) + len(group3[0]))
    iObjFit = np.concatenate((group1[0], group2[0], group3[0]))
    if verbose:
        print "###    %d objects that should be fitted" % nObjFit
        print "###  7.2. CONVERT THE SEP PARAMETERS TO INITIAL GUESSES OF 1-SERSIC MODEL"
    objSersic = objToGalfit(objComb, rad=r90, concen=concen, zp=photZP,
                            rbox=3.0, dimX=dimX, dimY=dimY)
    sersicAll = os.path.join(rerunDir, (prefix + '_' + suffix + 'sersic'))
    saveSEPObjects(objSersic, prefix=sersicAll, reg=False,
                   color='blue')
    sersicFit = os.path.join(rerunDir, (prefix + '_' + suffix + 'sersic_fit'))
    saveSEPObjects(objSersic[iObjFit], prefix=sersicFit, reg=False,
                   color='blue')

    # 8. Separate the rest objects into different groups according to
    #    their distance to the central galaxy
    if verbose:
        print "### 8. GENERATING THE FINAL MASK"
    # Index of objects in different groups
    # TODO: Not perfect parameter choice
    indG1 = (distNoCen <= galR2)
    indG2 = (distNoCen > galR2) & (distNoCen < galR3)
    indG3 = (distNoCen > galR3)
    # Isolate them into different group
    objG1 = objNoCen[indG1]
    objG2 = objNoCen[indG2]
    objG3 = objNoCen[indG3]
    # Generating final mask
    mskG1 = np.zeros(imgArr.shape, dtype='uint8')
    mskG2 = np.zeros(imgArr.shape, dtype='uint8')
    mskG3 = np.zeros(imgArr.shape, dtype='uint8')
    #sep.mask_ellipse(mskG1, objG1['x'], objG1['y'], r90NoCen[indG1],
                    #(r90NoCen[indG1] * objG1['b'] / objG1['a']),
                     #objG1['theta'], r=growH)
    #sep.mask_ellipse(mskG2, objG2['x'], objG2['y'], r90NoCen[indG2],
                    #(r90NoCen[indG2] * objG2['b'] / objG2['a']),
                     #objG2['theta'], r=growW)
    #sep.mask_ellipse(mskG3, objG3['x'], objG3['y'], r90NoCen[indG3],
                    #(r90NoCen[indG3] * objG3['b'] / objG3['a']),
                     #objG3['theta'], r=growC)
    sep.mask_ellipse(mskG1, objG1['x'], objG1['y'], objG1['a'],
                     objG1['b'], objG1['theta'], r=growH)
    sep.mask_ellipse(mskG2, objG2['x'], objG2['y'], objG2['a'],
                     objG2['b'], objG2['theta'], r=growW)
    sep.mask_ellipse(mskG3, objG3['x'], objG3['y'], objG3['a'],
                     objG3['b'], objG3['theta'], r=growC)

    # Hot run mask
    mskHot = np.zeros(imgArr.shape, dtype='uint8')
    sep.mask_ellipse(mskHot, objNoCenH['x'], objNoCenH['y'],
            objNoCenH['a'], objNoCenH['b'], objNoCenH['theta'], r=5.0)

    # Combine them into the final mask
    mskFinal = (mskG1 | mskG2 | mskG3 | mskHot)
    # Save the mask to FITS file
    # Have the option to combine with HSC BAD MASK
    if combBad:
        mskFinal = combMskImage(mskFinal, mskArr)
    if combDet and detFound:
        mskIn = np.zeros(imgArr.shape, dtype='uint8')
        sep.mask_ellipse(mskIn, np.array([galCenX]),
                np.array([galCenY]), np.array([galR3*1.6]),
                np.array([galR3*galQ*1.6]),
                np.array([galPA*np.pi/180.0]))
        """ TODO: Blow the detection array a little bit"""
        detArr[np.where(mskIn > 0)] = 0
        mskFinal = combMskImage(mskFinal, detArr)
    # Mask out all the NaN pixels
    mskFinal[indImgNaN] = 1
    mskFinFile = os.path.join(rerunDir, (prefix + '_' + suffix + 'mskfin.fits'))

    # See if the center of the image has been masked out
    sumMskR20, dump1, dump2 = sep.sum_ellipse(np.float32(mskFinal), galCenX, galCenY,
                                galR20, (galR20 * galQ), (galPA * np.pi / 180.0), r=1.0)
    if sumMskR20 > 0:
        sepFlags = addFlag(sepFlags, 'MSK_R20', True)
        print "###    %d pixels within R20 have been masked out" % sumMskR20
    else:
        sepFlags = addFlag(sepFlags, 'MSK_R20', False)
    sumMskR50, dump1, dump2 = sep.sum_ellipse(np.float32(mskFinal), galCenX, galCenY,
                                galR50, (galR50 * galQ), (galPA * np.pi / 180.0), r=1.0)
    if sumMskR50 > 0:
        sepFlags = addFlag(sepFlags, 'MSK_R50', True)
        print "###    %d pixels within R50 have been masked out" % sumMskR50
    else:
        sepFlags = addFlag(sepFlags, 'MSK_R50', False)

    # Add a few information about the central galaxy to the header
    mskHead = copy.deepcopy(imgHead)
    mskHead.set('GAL_X', galX)
    mskHead.set('GAL_Y', galY)
    mskHead.set('GAL_CENX', galCenX)
    mskHead.set('GAL_CENY', galCenY)
    mskHead.set('GAL_FLUX', galFlux)
    mskHead.set('GAL_Q', galQ)
    mskHead.set('GAL_PA', galPA)
    mskHead.set('GAL_R20', galR20)
    mskHead.set('GAL_R50', galR50)
    mskHead.set('GAL_R90', galR90)
    mskHead.set('GAL_R1', galR1)
    mskHead.set('GAL_R2', galR2)
    mskHead.set('GAL_R3', galR3)
    mskHead.set('NUM_FIT', nObjFit)
    # Put the Flags into the header
    for flag in sepFlags:
        if visual:
            print "###      %s : %1d" % (flag['name'], flag['value'])
        mskHead.set(flag['name'], flag['value'])

    saveFits(mskFinal, mskFinFile, head=mskHead)

    # Save the Objlist
    # Replace the object size with R90
    prefixF = os.path.join(rerunDir, (prefix + '_' + suffix + 'objAll'))
    objFin = copy.deepcopy(objNoCen)
    baNoCen = copy.deepcopy(objFin['b'] / objFin['a'])
    objFin['a'] = r90NoCen
    objFin['b'] = r90NoCen * baNoCen
    saveSEPObjects(objFin, prefix=prefixF, color='Green')

    if visual:
        # Fig.g
        mskPNG2 = os.path.join(rerunDir, (prefix + '_' + suffix + 'mskfin.png'))
        showSEPImage(imgArr, contrast=0.75, title='Mask - Final',
                     pngName=mskPNG2, mask=mskFinal)

    # 9. Visualize the detected objects, and find the ones need to be fit
    # Make a few plots
    if verbose:
        print "### 9. VISULIZATION OF THE DETECTED OBJECTS"
    if visual:
        # Fig.h
        objPNG = os.path.join(rerunDir, (prefix + '_' + suffix + 'objs.png'))
        showObjects(objComb, cenDistComb, rad=r90, outPNG=objPNG,
                    cenInd=cenObjIndex, r1=galR50, r2=galR90, r3=(3.0 * galR90),
                    fluxRatio1=fluxRatio1, fluxRatio2=fluxRatio2,
                    prefix=prefix, highlight=iObjFit)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", help="Prefix of the cutout image files")
    parser.add_argument('-r', '--root', dest='root', help='Path to the image files',
                        default=None)
    parser.add_argument('-rerun', '--rerun', dest='rerun', help='Name of the rerun',
                        default=None)
    parser.add_argument('-k', dest='kernel', help='SExtractor detection kernel',
                       type=int, default=4, choices=range(1, 7))
    parser.add_argument('-c', dest='central', help='Method to clean the central region',
                       type=int, default=1, choices=range(1, 3))
    parser.add_argument('-m', dest='mask', help='Method to grow the object mask',
                       type=int, default=1, choices=range(1, 3))
    parser.add_argument('--bkgH', dest='bSizeH', help='Background size for the Hot Run',
                       type=int, default=10)
    parser.add_argument('--bkgC', dest='bSizeC', help='Background size for the Cold Run',
                       type=int, default=80)
    parser.add_argument('--thrH', dest='thrH', help='Detection threshold for the Hot Run',
                       type=float, default=2.5)
    parser.add_argument('--thrC', dest='thrC', help='Detection threshold for the Cold Run',
                       type=float, default=1.2)
    parser.add_argument('--growC', dest='growC', help='Ratio of Growth for the Cold Objects',
                       type=float, default=6.8)
    parser.add_argument('--growW', dest='growW', help='Ratio of Growth for the Warm Objects',
                       type=float, default=4.0)
    parser.add_argument('--growH', dest='growH', help='Ratio of Growth for the Hot Objects',
                       type=float, default=1.5)
    parser.add_argument('--minDetC', dest='minDetC',
                       help='Minimum pixels for Cold Detections',
                       type=float, default=8.0)
    parser.add_argument('--minDetH', dest='minDetH',
                       help='Minimum pixels for Hot Detections',
                       type=float, default=5.0)
    parser.add_argument('--debThrC', dest='debThrC',
                       help='Deblending threshold for the Cold Run',
                       type=float, default=32.0)
    parser.add_argument('--debThrH', dest='debThrH',
                       help='Deblending threshold for the Hot Run',
                       type=float, default=16.0)
    parser.add_argument('--debConC', dest='debConC',
                       help='Deblending continuum level for the Cold Run',
                       type=float, default=0.015)
    parser.add_argument('--debConH', dest='debConH',
                       help='Deblending continuum level for the Hot Run',
                       type=float, default=0.004)
    parser.add_argument('--noBkgC', dest='noBkgC', action="store_true", default=False)
    parser.add_argument('--noBkgH', dest='noBkgH', action="store_true", default=False)
    parser.add_argument('--useSigArr', dest='useSigArr', action="store_true",
                        default=False)
    parser.add_argument('--combBad', dest='combBad', action="store_true",
                        default=True)
    parser.add_argument('--combDet', dest='combDet', action="store_true",
                        default=True)

    args = parser.parse_args()

    coaddCutoutPrepare(args.prefix, root=args.root,
                       bSizeH=args.bSizeH, bSizeC=args.bSizeC,
                       thrH=args.thrH, thrC=args.thrC,
                       growH=args.growH, growW=args.growW, growC=args.growC,
                       kernel=args.kernel, central=args.central,
                       mask=args.mask, useSigArr=args.useSigArr,
                       noBkgC=args.noBkgC, noBkgH=args.noBkgH,
                       minDetH=args.minDetH, minDetC=args.minDetC,
                       debThrH=args.debThrH, debThrC=args.debThrC,
                       debConH=args.debConH, debConC=args.debConC,
                       combBad=args.combBad, combDet=args.combDet,
                       rerun=args.rerun)

#def coaddCutoutPrepare(prefix, root=None, srcCat=None, verbose=True,
                       #bSizeH=8, bSizeC=80, thrH=3.5, thrC=1.5, mask=1,
                       #growC=6.0, growW=3.0, growH=1.5, kernel=4, central=1,
                       #galX=None, galY=None, galR1=None, galR2=None, galR3=None,
                       #galQ=None, galPA=None, visual=True, suffix='',
                       #combBad=True, combDet=False, noBkgC=False, noBkgH=False,
                       #minDetH=5.0, minDetC=5.0, debThrH=20.0, debThrC=32.0,
                       #debConH=0.01, debConC=0.01, useSigArr=False,
                       #minCenDist=20.0):
