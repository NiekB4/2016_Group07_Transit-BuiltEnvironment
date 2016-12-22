# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PTStopCalc
                                 A QGIS plugin
 test
                             -------------------
        begin                : 2016-12-20
        copyright            : (C) 2016 by neeraj
        email                : sirneeraj@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load PTStopCalc class from file PTStopCalc.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .pt_stop_calc import PTStopCalc
    return PTStopCalc(iface)
