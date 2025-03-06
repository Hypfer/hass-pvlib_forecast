"""
This file contains an assortment of things taken from multiple older versions of the pvlib library

The library can be found here: https://github.com/pvlib/pvlib-python

LICENSE

BSD 3-Clause License

Copyright (c) 2023 pvlib python Contributors
Copyright (c) 2014 PVLIB python Development Team
Copyright (c) 2013 Sandia National Laboratories

All rights reserved.
"""


import numpy as np
import pandas as pd
from collections import OrderedDict

from pvlib import tools, irradiance

def adjust_clearsky(location, clearsky, cloud_cover, method='clearsky_scaling'):
    """Adjust clear sky values based on cloud cover."""
    if method == 'clearsky_scaling':
        return clearsky_scaling(location, clearsky, cloud_cover)
    elif method == 'campbell_norman':
        return campbell_norman_adjustment(location, cloud_cover)
    else:
        raise ValueError('Invalid adjustment method')


def clearsky_scaling(location, clearsky, cloud_cover):
    """Use clearsky scaling method to adjust irradiance."""
    ghi = cloud_cover_to_ghi_linear(cloud_cover, clearsky['ghi'])
    solpos = location.get_solarposition(cloud_cover.index)

    # Calculate DNI using disc model
    kt = irradiance.clearness_index(ghi, solpos['zenith'],
                        irradiance.get_extra_radiation(cloud_cover.index))
    airmass = get_relative_airmass(solpos['zenith'])
    dni = _disc_dni(kt, airmass, irradiance.get_extra_radiation(cloud_cover.index))

    dhi = ghi - dni * np.cos(np.radians(solpos['zenith']))

    return pd.DataFrame({
        'ghi': ghi,
        'dni': dni,
        'dhi': dhi
    }).fillna(0)


def campbell_norman_adjustment(location, cloud_cover, pressure=101325.0, dni_extra=1367.0):
    """
    Use Campbell-Norman method to calculate irradiance.

    Parameters
    ----------
    location : Location
        Location for calculation
    cloud_cover : Series
        Cloud cover values in %
    pressure : float, default 101325.0
        Air pressure in Pascal
    dni_extra : float, default 1367.0
        Extraterrestrial irradiance in W/m^2

    References
    ----------
    [1] Campbell, G. S., J. M. Norman (1998) An Introduction to
        Environmental Biophysics. 2nd Ed. New York: Springer.
    """
    solar_position = location.get_solarposition(cloud_cover.index)

    # Get absolute airmass
    airmass = get_relative_airmass(solar_position['apparent_zenith'])
    airmass = get_absolute_airmass(airmass, pressure)

    transmittance = cloud_cover_to_transmittance_linear(cloud_cover)

    # Calculate components exactly as in Campbell-Norman model
    dni = dni_extra * transmittance ** airmass
    cos_zen = np.cos(np.radians(solar_position['apparent_zenith']))
    dhi = 0.3 * (1.0 - transmittance ** airmass) * dni_extra * cos_zen
    ghi = dhi + dni * cos_zen

    return pd.DataFrame({
        'ghi': ghi,
        'dni': dni,
        'dhi': dhi
    }).fillna(0)

def get_relative_airmass(zenith):
    """
    Calculate relative airmass using Kasten and Young's 1989 model.

    Parameters
    ----------
    zenith : numeric
        Solar zenith angle in degrees

    Returns
    -------
    airmass : numeric
        Relative airmass
    """
    zenith_rad = np.radians(zenith)
    return 1 / (np.cos(zenith_rad) + 0.50572 * (96.07995 - zenith)**-1.6364)


def get_absolute_airmass(airmass_relative, pressure=101325.0):
    """
    Convert relative airmass to absolute airmass using pressure.

    Parameters
    ----------
    airmass_relative : numeric
        Relative airmass
    pressure : numeric, default 101325.0
        Site pressure in Pascal

    Returns
    -------
    numeric
        Absolute airmass
    """
    return airmass_relative * (pressure / 101325.0)

def _disc_dni(kt, airmass, dni_extra, max_zenith=87, min_cos_zenith=0.065, max_airmass=12):
    """
    Determine DNI using the DISC model.

    The DISC algorithm converts global horizontal irradiance to direct
    normal irradiance through empirical relationships between the global
    and direct clearness indices.

    Parameters
    ----------
    kt : numeric
        Clearness index
    airmass : numeric
        Relative airmass
    dni_extra : numeric
        Extraterrestrial direct normal irradiance
    max_zenith : numeric, default 87
        Maximum solar zenith angle for valid DNI
    min_cos_zenith : numeric, default 0.065
        Minimum cosine of zenith angle for kt calculation
    max_airmass : numeric, default 12
        Maximum airmass value allowed

    Returns
    -------
    dni : numeric
        Direct normal irradiance in W/m^2

    References
    ----------
    [1] Maxwell, E. L., "A Quasi-Physical Model for Converting Hourly
        Global Horizontal to Direct Normal Insolation", Technical
        Report No. SERI/TR-215-3087, Golden, CO: Solar Energy Research
        Institute, 1987.
    """
    # Limit airmass to max value
    am = np.minimum(airmass, max_airmass)

    # Calculate Kn using empirical relationships
    is_cloudy = (kt <= 0.6)

    # Use Horner's method to compute polynomials efficiently
    a = np.where(
        is_cloudy,
        0.512 + kt * (-1.56 + kt * (2.286 - 2.222 * kt)),
        -5.743 + kt * (21.77 + kt * (-27.49 + 11.56 * kt)))
    b = np.where(
        is_cloudy,
        0.37 + 0.962 * kt,
        41.4 + kt * (-118.5 + kt * (66.05 + 31.9 * kt)))
    c = np.where(
        is_cloudy,
        -0.28 + kt * (0.932 - 2.048 * kt),
        -47.01 + kt * (184.2 + kt * (-222.0 + 73.81 * kt)))

    delta_kn = a + b * np.exp(c * am)

    # Knc is the clear sky direct beam transmission
    Knc = 0.866 + am * (-0.122 + am * (0.0121 + am * (-0.000653 + 1.4e-05 * am)))
    Kn = Knc - delta_kn

    # Calculate DNI
    dni = Kn * dni_extra

    # Filter out bad values
    zenith = np.degrees(np.arccos(np.maximum(min_cos_zenith,
                                             np.cos(np.radians(airmass)))))
    bad_values = (zenith > max_zenith) | (kt < 0) | (dni < 0)
    dni = np.where(bad_values, 0, dni)

    return dni


def cloud_cover_to_ghi_linear(cloud_cover, ghi_clear, offset=35):
    """
    Convert cloud cover to GHI using linear relationship.

    Uses a linear relationship between cloud cover and clearness,
    with an offset to account for minimum GHI even with full cloud cover.

    Parameters
    ----------
    cloud_cover : numeric
        Cloud cover in %
    ghi_clear : numeric
        GHI under clear sky conditions in W/m^2
    offset : numeric, default 35
        Determines the minimum GHI as percentage of clear sky GHI

    Returns
    -------
    ghi : numeric
        Estimated GHI in W/m^2

    References
    ----------
    [1] Larson et. al. "Day-ahead forecasting of solar power output from
        photovoltaic plants in the American Southwest" Renewable Energy
        91, 11-20 (2016).
    """
    offset = offset / 100.
    cloud_cover = cloud_cover / 100.
    return (offset + (1 - offset) * (1 - cloud_cover)) * ghi_clear


def cloud_cover_to_transmittance_linear(cloud_cover, offset=0.75):
    """
    Convert cloud cover to transmittance using linear relationship.

    Parameters
    ----------
    cloud_cover : numeric
        Cloud cover in %
    offset : numeric, default 0.75
        Determines the maximum transmittance [unitless]

    Returns
    -------
    transmittance : numeric
        The fraction of extraterrestrial irradiance that reaches
        the ground [unitless]
    """
    return ((100.0 - cloud_cover) / 100.0) * offset
