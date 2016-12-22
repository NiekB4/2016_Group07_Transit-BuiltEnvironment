# coding=utf-8
"""DockWidget test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'sirneeraj@gmail.com'
__date__ = '2016-12-20'
__copyright__ = 'Copyright 2016, neeraj'

import unittest

from PyQt4.QtGui import QDockWidget

from pt_stop_calc_dockwidget import PTStopCalcDockWidget

from utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class PTStopCalcDockWidgetTest(unittest.TestCase):
    """Test dockwidget works."""

    def setUp(self):
        """Runs before each test."""
        self.dockwidget = PTStopCalcDockWidget(None)

    def tearDown(self):
        """Runs after each test."""
        self.dockwidget = None

    def test_dockwidget_ok(self):
        """Test we can click OK."""
        pass

if __name__ == "__main__":
    suite = unittest.makeSuite(PTStopCalcDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

