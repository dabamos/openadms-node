#!/usr/bin/env python3.6

"""Static utility routines."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import math


def gon_to_rad(angle: float) -> float:
    """Converts from gon (grad) to radiant.

    Args:
        angle: Angle in gon.

    Returns:
        Converted angle in rad.
    """
    return angle * math.pi / 200


def rad_to_gon(angle: float) -> float:
    """Converts from radiant to gon (grad).

    Args:
        angle: Angle in rad.

    Returns:
        Converted angle in gon.
    """
    return angle * 200 / math.pi
