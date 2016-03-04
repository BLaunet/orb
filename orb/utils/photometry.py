#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca>
# File: photometry.py

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

import math
import numpy as np
import warnings
import orb.constants
import scipy.interpolate
import scipy.optimize
import orb.utils.spectrum
from orb.utils.astrometry import Gaussian
 
def flambda2ABmag(flambda, lam):
    """Return AB magnitude from flux in erg/cm2/s/A

    :param flambda: Flux in erg/cm2/s/A. Can be an array.

    :param lambda: Wavelength in A of the Flux. If flambda is an array
      lambda must have the same shape.
    """
    c = 2.99792458e18 # Ang/s
    fnu = lam**2./c*flambda
    ABmag = -2.5 * np.log10(fnu) - 48.60
    return ABmag

def ABmag2fnu(ABmag):
    """Return flux in erg/cm2/s/Hz from AB magnitude (Oke, ApJS, 27,
    21, 1974)

    ABmag = -2.5 * log10(f_nu) - 48.60
    f_nu = 10^(-0.4 * (ABmag + 48.60))

    :param ABmag: A magnitude in the AB magnitude system

    .. note:: Definition of the zero-point can change and be
      e.g. 48.59 for Oke standard stars (Hamuy et al., PASP, 104, 533,
      1992). This is the case for Spectrophotometric Standards given
      on the ESO website (https://www.eso.org/sci/observing/tools/standards/spectra/okestandards.html). Here the HST definition is used.
    """
    return 10**(-0.4*(ABmag + 48.60))

def fnu2flambda(fnu, nu):
    """Convert a flux in erg/cm2/s/Hz to a flux in erg/cm2/s/A

    :param fnu: Flux in erg/cm2/s/Hz
    :param nu: frequency in Hz
    """
    c = 2.99792458e18 # Ang/s
    return fnu * nu**2. / c

def lambda2nu(lam):
    """Convert lambda in Ang to nu in Hz

    :param lam: Wavelength in angstrom
    """
    c = 2.99792458e18 # Ang/s
    return c / lam

def ABmag2flambda(ABmag, lam):
    """Convert AB magnitude to flux in erg/cm2/s/A

    :param ABmag: A magnitude in the AB magnitude system

    :param lam: Wavelength in angstrom
    """
    return fnu2flambda(ABmag2fnu(ABmag), lambda2nu(lam))


def read_atmospheric_extinction_file(file_path):
    with open(file_path, 'r') as f:
        wav = list()
        ext = list()
        for line in f:
            if ('#' not in line) and (len(line) > 2):
                line = np.array(line.strip().split(), dtype=float)
                wav.append(line[0] / 10.) # ang -> nm
                ext.append(line[1])
        
    return np.array(wav), np.array(ext)

def get_atmospheric_extinction(file_path, step, order, step_nb):
    axis, atm_ext = read_atmospheric_extinction_file(file_path)
    atm_extf = scipy.interpolate.UnivariateSpline(axis, atm_ext, s=0, k=3)
    nm_axis = orb.utils.spectrum.create_nm_axis(step_nb, step, order).astype(float)
    return atm_extf(nm_axis)

def get_atmospheric_transmission(file_path, step, order, step_nb, airmass=1):
    atm_ext = get_atmospheric_extinction(file_path, step, order, step_nb)
    return 10**(-atm_ext*airmass/2.5)

def read_quantum_efficiency_file(file_path):
    with open(file_path, 'r') as f:
        wav = list()
        qe = list()
        for line in f:
            if ('#' not in line) and (len(line) > 2):
                line = np.array(line.strip().split(), dtype=float)
                wav.append(line[0])
                qe.append(line[1]/100.) # percent to coeff
        
    return np.array(wav), np.array(qe)

def get_quantum_efficiency(file_path, step, order, step_nb):
    axis, qe = read_quantum_efficiency_file(file_path)
    qef = scipy.interpolate.UnivariateSpline(axis, qe, s=0, k=3)
    nm_axis = orb.utils.spectrum.create_nm_axis(step_nb, step, order).astype(float)
    return qef(nm_axis)


def read_mirror_transmission_file(file_path):
    with open(file_path, 'r') as f:
        wav = list()
        mir_trans = list()
        for line in f:
            if ('#' not in line) and (len(line) > 2):
                line = np.array(line.strip().split(), dtype=float)
                wav.append(line[0])
                mir_trans.append(line[1]/100.) # percent to coeff
        
    return np.array(wav), np.array(mir_trans)

def get_mirror_transmission(file_path, step, order, step_nb):
    axis, mir_trans = read_mirror_transmission_file(file_path)
    mir_transf = scipy.interpolate.UnivariateSpline(axis, mir_trans, s=0, k=3)
    nm_axis = orb.utils.spectrum.create_nm_axis(step_nb, step, order).astype(float)
    return mir_transf(nm_axis)


def read_optics_file(optics_file_path):
    """
    Read a file containing the optics transmission function.

    :param optics_file_path: Path to the optics file.

    :returns: (wavelength, transmission coefficients)
      
    .. note:: The optics file used must have two colums separated by a
      space character. The first column contains the wavelength axis
      in nm. The second column contains the transmission
      coefficients. Comments are preceded with a #.  

        ## ORBS optics file 
        # Author: Thomas Martin <thomas.martin.1@ulaval.ca>
        # Filter name : SpIOMM_R
        # Wavelength in nm | Transmission percentage
        1000 0.001201585284
        999.7999878 0.009733387269
        999.5999756 -0.0004460749624
        999.4000244 0.01378122438
        999.2000122 0.002538740868

    """
    optics_file = open(optics_file_path, 'r')
    optics_trans_list = list()
    optics_nm_list = list()
    for line in optics_file:
        if len(line) > 2:
            line = line.split()
            if '#' not in line[0]: # avoid comment lines
                optics_nm_list.append(float(line[0]))
                optics_trans_list.append(float(line[1]))
    optics_nm = np.array(optics_nm_list)
    optics_trans = np.array(optics_trans_list)
    # sort coefficients the correct way
    if optics_nm[0] > optics_nm[1]:
        optics_nm = optics_nm[::-1]
        optics_trans = optics_trans[::-1]
        
    return optics_nm, optics_trans

def get_optics_transmission(file_path, step, order, step_nb):
    axis, optics_trans = read_optics_file(file_path)
    optics_transf = scipy.interpolate.UnivariateSpline(axis, optics_trans, s=0, k=1)
    nm_axis = orb.utils.spectrum.create_nm_axis(step_nb, step, order).astype(float)
    return optics_transf(nm_axis)

def compute_mean_star_flux(star_spectrum, filter_transmission):

    return (np.sum(star_spectrum * filter_transmission)
            / np.sum(filter_transmission))


def compute_mean_photon_energy(nm_axis, filter_transmission):
    
    ph_energy_spectrum = compute_photon_energy(nm_axis)
    return (np.sum(ph_energy_spectrum * filter_transmission)
            / np.sum(filter_transmission))

def compute_photon_energy(nm_axis):
    return (orb.constants.HEISEN
            * orb.constants.LIGHT_VEL_KMS * 1e12
            / nm_axis)

def compute_equivalent_bandwidth(nm_axis, filter_transmission):
    return np.nansum(np.diff(nm_axis) * filter_transmission[:-1]
                     / np.nanmax(filter_transmission))


def compute_star_flux_in_frame(nm_axis, star_flux, filter_trans,
                               optics_trans, atm_trans,
                               mirror_trans, qe, mirror_surface, ccd_gain):
    """Return the estimation of the flux of a star in counts/s in one image.
    """
    flux = star_flux # erg/cm2/s/A
    flux /= compute_photon_energy(nm_axis) # photons/s/A
    flux *= atm_trans
    flux *= mirror_surface # photons/s/A
    flux *= mirror_trans**2 # **2 because we have two mirrors 
    flux *= optics_trans
    flux *= filter_trans
    flux *= qe # electrons/s/A
    flux *= ccd_gain # counts/s/A
    # sum all counts by wavelength bins
    flux = np.diff(nm_axis) * 10. * flux[:-1] 
    flux = np.nansum(flux) # counts/s
    flux /= 2 # photon flux divided by two at the beam splitter
    return flux

def compute_star_central_pixel_value(seeing, plate_scale):
    
    N = 100
    fwhm_pix = seeing / plate_scale
    star = Gaussian([0,1,N/2,N/2,fwhm_pix]).array2d(N,N)
    star /= np.nansum(star)
    return np.nanmax(star)

def compute_optimal_texp(star_flux, seeing, plate_scale,
                         saturation=30000):

    print 'Optimal exposure time is computed for a saturation value of: {} counts'.format(saturation)
    max_flux = compute_star_central_pixel_value(
        seeing, plate_scale) * star_flux

    return saturation/max_flux
    
def fit_std_spectrum(real_spectrum, std_spectrum, polydeg=2):


    def model(p, x, real_spectrum):
        return (real_spectrum
                * np.polynomial.polynomial.polyval(x, p))


    def diff(p, x, std_spectrum, real_spectrum):
        res = model(p, x, real_spectrum) - std_spectrum
        return res[~np.isnan(res)]

    p = np.zeros((polydeg+1), dtype=float)
    x = np.arange(real_spectrum.shape[0], dtype=float)
    p[0] = np.nanmedian(std_spectrum / real_spectrum)
    
    p = scipy.optimize.leastsq(
        diff, p, args=(
            x, std_spectrum,
            real_spectrum))[0]
    
    return np.polynomial.polynomial.polyval(x, p)