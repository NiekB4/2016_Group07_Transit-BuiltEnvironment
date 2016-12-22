# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PTStopCalcDockWidget
                                 A QGIS plugin
 test
                             -------------------
        begin                : 2016-12-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by neeraj
        email                : sirneeraj@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.networkanalysis import *
from qgis.gui import *
import processing

# matplotlib for the charts
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Initialize Qt resources from file resources.py
import resources

import os
import os.path
import sys
import random
import csv
import time
import qgis

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'pt_stop_calc_dockwidget_base.ui'))


class PTStopCalcDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(PTStopCalcDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # set up GUI operation signals

        # IMPORT TAB

        self.openTemplateFolder.clicked.connect(self.openBrowse)
        self.importData.clicked.connect(self.loadLayers)


        # ANALYSIS TAB

        self.resetWeightsAndLayers.clicked.connect(self.resetCheckBoxes)

        self.saveScenario.clicked.connect(self.saveAsScenario)


    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def openBrowse(self):
        filename1 = QFileDialog.getExistingDirectory()
        self.templateFolderDirectory.setText(filename1)

    def loadLayers(self):

        source_dir = self.templateFolderDirectory.text()

        # create Qt widget
        canvas = QgsMapCanvas()
        canvas.setCanvasColor(Qt.white)

        # enable this for smooth rendering
        canvas.enableAntiAliasing(True)

        # total list of layers actually displayed on map canvas
        canvas_layers = []

        extent = QgsRectangle()

        # load vector layers
        for files in os.listdir(source_dir):

            # load only the shapefiles
            if files.endswith(".shp"):
                vlayer = QgsVectorLayer(source_dir + "/" + files, files, "ogr")

                # add layer to the registry
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)

                extent.combineExtentWith(vlayer.extent())
                canvas_layers.append(QgsMapCanvasLayer(vlayer))

                # set the map canvas layer set
        canvas.setExtent(extent)
        canvas.setLayerSet(canvas_layers)

        # refresh canvas and show it
        canvas.refresh()
        canvas.show()

    def resetCheckBoxes(self):

        self.landUseCheckBox.setCheckState(0)
        self.trainStationCheckBox.setCheckState(0)
        self.retStopCheckBox.setCheckState(0)
        self.modalShareCheckBox.setCheckState(0)

    def saveAsScenario(self):
        project = QgsProject.instance()
        project.write(QFileInfo())



