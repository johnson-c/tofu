# -*- coding: utf-8 -*-
#! /usr/bin/python
"""
The geometry module of tofu

Provides classes to model the 3D geometry of:
* the vacuum vessel and structural elements
* LOS
* apertures and detectors
"""

from tofu.geom._core import PlasmaDomain, Ves, PFC, CoilPF, CoilCS, Config
from tofu.geom._core import Rays, CamLOS1D, CamLOS2D
from tofu.geom._core_optics import *
import tofu.geom._comp_solidangles
from . import utils

__all__ = ['_GG', '_comp', '_plot', '_def', 'utils']
