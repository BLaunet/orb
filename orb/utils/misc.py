#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca>
# File: misc.py

## Copyright (c) 2010-2016 Thomas Martin <thomas.martin.1@ulaval.ca>
## 
## This file is part of ORB
##
## ORB is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## ORB is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
## or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
## License for more details.
##
## You should have received a copy of the GNU General Public License
## along with ORB.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np
import math
import warnings

import orb.cutils
                       

def get_axis_from_hdr(hdr, axis_index=1):
    """Return axis from a classic FITS header

    :param hdr: FITS header

    :param axis_index: (Optional) Index of the axis to retrieve
      (default 1)
    """
    naxis = int(hdr['NAXIS{}'.format(axis_index)])
    crpix = float(hdr['CRPIX{}'.format(axis_index)])
    crval = float(hdr['CRVAL{}'.format(axis_index)])
    cdelt = float(hdr['CDELT{}'.format(axis_index)])
    return (np.arange(naxis, dtype=float) + 1. - crpix) * cdelt + crval
    
    
def get_mask_from_ds9_region_line(reg_line, x_range=None, y_range=None):
    """Read one line of a ds9 region file and return the list of
    pixels in the region.

    :param reg_line: Line of the ds9 region file
    
    :param x_range: (Optional) Range of x image coordinates
        considered as valid. Pixels outside this range are
        rejected. If None, no validation is done (default None).

    :param y_range: (Optional) Range of y image coordinates
        considered as valid. Pixels outside this range are
        rejected. If None, no validation is done (default None).

    .. note:: The returned array can be used like a list of
        indices returned by e.g. numpy.nonzero().

    .. note:: Coordinates can be image coordinates (x,y) or sky
        coordinates in degrees (ra, dec)
    """
    x_list = list()
    y_list = list()

    if len(reg_line) <= 3:
        warnings.warn('Bad region line')
        return None
        
    if reg_line[:3] == 'box':
        reg_line = reg_line.split('#')[0]
        reg_line = reg_line[4:]
        if '"' in reg_line:
            reg_line = reg_line[:-3]
        else:
            reg_line = reg_line[:-2]

        if ',' in reg_line:
            box_coords = np.array(reg_line.split(","), dtype=float)
        else:
            raise Exception('Bad coordinates, check if coordinates are in pixels')

        x_min = round(box_coords[0] - (box_coords[2] / 2.) - 1.5)
        x_max = round(box_coords[0] + (box_coords[2] / 2.) + .5)
        y_min = round(box_coords[1] - (box_coords[3] / 2.) - 1.5) 
        y_max = round(box_coords[1] + (box_coords[3] / 2.) + .5)        
        if x_range is not None:
            if x_min < np.min(x_range) : x_min = np.min(x_range)
            if x_max > np.max(x_range) : x_max = np.max(x_range)
        if y_range is not None:
            if y_min < np.min(y_range) : y_min = np.min(y_range)
            if y_max > np.max(y_range) : y_max = np.max(y_range)

        for ipix in range(int(x_min), int(x_max)):
            for jpix in range(int(y_min), int(y_max)):
                x_list.append(ipix)
                y_list.append(jpix)

    if reg_line[:6] == 'circle':
        reg_line = reg_line.split('#')[0]
        reg_line = reg_line[7:]
        if '"' in reg_line:
            reg_line = reg_line[:-3]
        else:
            reg_line = reg_line[:-2]
        cir_coords = np.array(reg_line.split(","), dtype=float)
        x_min = round(cir_coords[0] - (cir_coords[2]) - 1.5)
        x_max = round(cir_coords[0] + (cir_coords[2]) + .5)
        y_min = round(cir_coords[1] - (cir_coords[2]) - 1.5)
        y_max = round(cir_coords[1] + (cir_coords[2]) + .5)
        if x_range is not None:
            if x_min < np.min(x_range) : x_min = np.min(x_range)
            if x_max > np.max(x_range) : x_max = np.max(x_range)
        if y_range is not None:
            if y_min < np.min(y_range) : y_min = np.min(y_range)
            if y_max > np.max(y_range) : y_max = np.max(y_range)


        for ipix in range(int(x_min), int(x_max)):
            for jpix in range(int(y_min), int(y_max)):
                if (math.sqrt((ipix - cir_coords[0] + 1.)**2
                             + (jpix - cir_coords[1] + 1.)**2)
                    <= round(cir_coords[2])):
                    x_list.append(ipix)
                    y_list.append(jpix)

    if reg_line[:7] == 'polygon':
        reg_line = reg_line.split('#')[0]
        reg_line = reg_line[8:-2]
        reg_line = np.array(reg_line.split(',')).astype(float)
        if np.size(reg_line) > 0:
            poly = [(reg_line[i], reg_line[i+1]) for i in range(
                0,np.size(reg_line),2)]
            poly_x = np.array(poly)[:,0]
            poly_y = np.array(poly)[:,1]
            x_min = np.min(poly_x)
            x_max = np.max(poly_x)
            y_min = np.min(poly_y)
            y_max = np.max(poly_y)
            if x_range is not None:
                if x_min < np.min(x_range) : x_min = np.min(x_range)
                if x_max > np.max(x_range) : x_max = np.max(x_range)
            if y_range is not None:
                if y_min < np.min(y_range) : y_min = np.min(y_range)
                if y_max > np.max(y_range) : y_max = np.max(y_range)

            for ipix in range(int(x_min), int(x_max)):
                for jpix in range(int(y_min), int(y_max)):
                    if orb.cutils.point_inside_polygon(ipix, jpix, poly):
                         x_list.append(ipix)
                         y_list.append(jpix)

    x_list = np.array(x_list)
    y_list = np.array(y_list)

    return list([x_list, y_list])

                        
def get_mask_from_ds9_region_file(reg_path, x_range=None,
                                  y_range=None):
    """Return the indices of the elements inside 'box', 'circle' and
    'polygon' regions.

    :param reg_path: Path to a ds9 region file

    :param x_range: (Optional) Range of x image coordinates
        considered as valid. Pixels outside this range are
        rejected. If None, no validation is done (default None).

    :param y_range: (Optional) Range of y image coordinates
        considered as valid. Pixels outside this range are
        rejected. If None, no validation is done (default None).

    .. note:: The returned array can be used like a list of
        indices returned by e.g. numpy.nonzero().

    .. note:: Coordinates can be image coordinates (x,y) or sky
        coordinates in degrees (ra, dec)
    """
    f = open(reg_path, 'r')
    x_list = list()
    y_list = list()
                    
    for iline in f:
        if len(iline) > 3:
            mask = get_mask_from_ds9_region_line(iline, x_range=x_range,
                                                 y_range=y_range)
            x_list += list(mask[0])
            y_list += list(mask[1])
                            
    x_list = np.array(x_list)
    y_list = np.array(y_list)

    return list([x_list, y_list])

def compute_obs_params(nm_min_filter, nm_max_filter,
                       theta_min=5.01, theta_max=11.28):
    """Compute observation parameters (order, step size) given the
    filter bandpass.

    :param nm_min_filter: Min wavelength of the filter in nm.

    :param nm_max_filter: Max wavelength of the filter in nm.
    
    :param theta_min: (Optional) Min angle of the detector (default
      5.01).

    :param theta_max: (Optional) Max angle of the detector (default
      11.28).

    :return: A tuple (order, step size, max wavelength)
    """
    def get_step(nm_min, n, cos_min):
        return int(nm_min * ((n+1.)/(2.*cos_min)))

    def get_nm_max(step, n, cos_max):
        return 2. * step * cos_max / float(n)
    
    cos_min = math.cos(math.radians(theta_min))
    cos_max = math.cos(math.radians(theta_max))

    n = 0
    order_found = False
    while n < 200 and not order_found:
        n += 1
        step = get_step(nm_min_filter, n, cos_min)
        nm_max = get_nm_max(step, n, cos_max)
        if nm_max <= nm_max_filter:
            order_found = True
            order = n - 1
       
    step = get_step(nm_min_filter, order, cos_min)
    nm_max = get_nm_max(step, order, cos_max)
    
    return order, step, nm_max


def correct_bad_frames_vector(bad_frames_vector, dimz):
    """Remove bad indexes of the bad frame vector.

    :param bad_frames_vector: The vector of indexes to correct
    :param dimz: Dimension of the cube along the 3rd axis.
    """
    if (bad_frames_vector is None
        or np.size(bad_frames_vector) == 0):
        return bad_frames_vector
    
    bad_frames_vector= np.array(np.copy(bad_frames_vector))
    bad_frames_vector = [bad_frames_vector[badindex]
                         for badindex in range(bad_frames_vector.shape[0])
                         if (bad_frames_vector[badindex] >= 0
                             and bad_frames_vector[badindex] < dimz)]
    return bad_frames_vector

def restore_error_settings(old_settings):
    """Restore old floating point error settings of numpy.
    """
    np.seterr(divide = old_settings["divide"])
    np.seterr(over = old_settings["over"])
    np.seterr(under = old_settings["under"])
    np.seterr(invalid = old_settings["invalid"])
