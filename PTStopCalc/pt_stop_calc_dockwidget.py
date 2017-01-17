# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PTStopCalc
 A QGIS plugin for the GEO 1005 Spatial Decision Support System, MSc Geomatics, TU Delft
                              -------------------
        begin                : 2016-12-20
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Neeraj Sirdeshmukh , Cheng-Kai Wang, and Niek Bebelaar
        email                : sirneeraj@gmail.com, ckwang25@gmail.com, niekbebelaar@gmail.com

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


from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *
from qgis.networkanalysis import *
from qgis.gui import *
from qgis.utils import *
from PyQt4 import QtGui, QtCore, uic
from qgis.gui import QgsMapTool
from PyQt4.QtCore import QFileInfo
from qgis.analysis import QgsGeometryAnalyzer, QgsOverlayAnalyzer
from . import utility_functions as uf

# matplotlib for the charts
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Initialize Qt resources from file resources.py
import resources

import sys
import random
import csv
import time
import qgis
import processing
import math
import os

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

        self.scenarioNumber = 0
        self.modifyingNumber = 0
        self.numTimesOpenBrowse = 0
        self.numTimesBasemap = 0

        # remember the current modifying layer and its corresponding analysis setting
        self.modifyingLayer = QgsVectorLayer()
        self.layerSetting = []
        self.layerSettingDict = {}

        # set up GUI operation signals

        # IMPORT TAB

        self.openTemplateFolder.clicked.connect(self.openBrowse)
        self.importData.clicked.connect(self.loadLayers)
        self.loadBasemap.clicked.connect(self.basemapLoad)
        self.zoomToAOI.clicked.connect(self.zoomAOI)

        # ANALYSIS TAB

        self.resetWeightsAndLayers.clicked.connect(self.reset)

        self.computeScenario.clicked.connect(self.calculateScenario)
        self.saveScenario.clicked.connect(self.saveAsScenario)


        # MODIFICATION TAB

        self.iface.projectRead.connect(self.popSavedScenarioList)
        self.iface.newProjectCreated.connect(self.popSavedScenarioList)
        self.iface.legendInterface().itemRemoved.connect(self.popSavedScenarioList)
        self.iface.legendInterface().itemAdded.connect(self.popSavedScenarioList)

        self.startModifyingScenarios.clicked.connect(self.startModifyingProject)

        self.emitPoint = QgsMapToolEmitPoint(self.canvas)
        self.emitPoint.canvasClicked.connect(self.getPoint)
        self.addTrainStopButton.clicked.connect(self.enterPoi)
        self.addMetroStopButton.clicked.connect(self.enterPoi)
        self.addTramStopButton.clicked.connect(self.enterPoi)
        self.addBusStopButton.clicked.connect(self.enterPoi)
        self.resetModificationSettings.clicked.connect(self.resetModification)

        self.computeModifiedScenario.clicked.connect(self.computingModifiedScenario)

        self.displaySuitabilityChange.clicked.connect(self.displayBtnState)

        self.saveModifiedScenario.clicked.connect(self.saveModifiedProject)

        # REPORTING TAB

        self.saveReport.clicked.connect(self.saveTable)
        self.loadScenariosButton.clicked.connect(self.scenarioReportListGenerate)


    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def openBrowse(self):

        self.numTimesOpenBrowse += 1

        if self.numTimesOpenBrowse == 1:
            filename = QFileDialog.getExistingDirectory(self, "Choose Transport Data Folder")
        elif self.numTimesOpenBrowse > 1:
            filename = QFileDialog.getExistingDirectory(self, "Choose Transport Data Folder", self.templateFolderDirectory.text())

        filename = filename.replace("\\","//")
        self.templateFolderDirectory.setText(filename)
        if not os.path.isdir(filename + "/Scenarios"):
            self.makeSpecialFolders()

    def loadLayers(self):

        source_dir = self.templateFolderDirectory.text()

        # load vector layers
        for files in os.listdir(source_dir):

            # load only the shapefiles
            if files.endswith(".shp"):
                vlayer = QgsVectorLayer(source_dir + "/" + files, files, "ogr")
                # add layer to the registry
                QgsMapLayerRegistry.instance().addMapLayer(vlayer)

                if vlayer.name() == "Buurt.shp":
                    canvas = iface.mapCanvas()
                    canvas.setExtent(vlayer.extent())
                    expression = QgsExpression("null")
                    index = vlayer.fieldNameIndex("Suitabilit")
                    expression.prepare(vlayer.pendingFields())
                    vlayer.startEditing()
                    for feature in vlayer.getFeatures():
                        value = expression.evaluate(feature)
                        vlayer.changeAttributeValue(feature.id(), index, value)
                    vlayer.commitChanges()


            elif files.endswith(".csv"):
                sourceDirNew = str(source_dir).replace("\\", "/")
                uri = "file:///" + sourceDirNew + "/" + files + "?delimiter=%s" % (",")
                lyr = QgsVectorLayer(uri, 'Current Modal Share', 'delimitedtext')
                QgsMapLayerRegistry.instance().addMapLayer(lyr)

        # Rename the layers in the table of contents

        self.renameLayers()

        # Apply a pre-made style to each layer

        self.displayBenchmarkStyle()


    def renameLayers(self):
        for layer in QgsMapLayerRegistry.instance().mapLayers().values():
            currentName = layer.name()
            newName = currentName.replace(".shp", "")
            layer.setLayerName(newName)


    def moveBasemapBelow(self):
        blayer = QgsMapLayerRegistry.instance().mapLayersByName("Basemap")[0]

        root = QgsProject.instance().layerTreeRoot()

        # Move alayer
        myblayer = root.findLayer(blayer.id())
        myClone = myblayer.clone()
        parent = myblayer.parent()
        parent.insertChildNode(6, myClone)
        parent.removeChildNode(myblayer)

    def basemapLoad(self):

        self.numTimesBasemap += 1

        if self.numTimesBasemap % 2 == 1:
            qgis.utils.iface.addRasterLayer("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer?f=json&pretty=true","Basemap")

            self.moveBasemapBelow()

        else:
            layer = QgsMapLayerRegistry.instance().mapLayersByName("Basemap")[0]
            QgsMapLayerRegistry.instance().removeMapLayer(layer)

    def zoomAOI(self):
        canvas = qgis.utils.iface.mapCanvas()
        acl = canvas.layer(4)
        qgis.utils.iface.setActiveLayer(acl)
        qgis.utils.iface.zoomToActiveLayer()

    def reset(self):

        self.landUseCheckBox.setCheckState(0)
        self.popDensityCheckBox.setCheckState(0)
        self.accessibleAreaCheckBox.setCheckState(0)
        self.modalShareCheckBox.setCheckState(0)

    def makeSpecialFolders(self):
        folderName = self.templateFolderDirectory.text()
        path = folderName + "/Scenarios"
        os.mkdir(path)
        path = folderName + "/IntermediateLayers"
        os.mkdir(path)

        if not os.path.isdir(folderName + "/Scenarios/OriginalScenarios"):
            self.makeScenarioSubFolders()

    def makeScenarioSubFolders(self):
        folderName = self.templateFolderDirectory.text()
        path = folderName + "/Scenarios/OriginalScenarios"
        os.mkdir(path)
        path = folderName + "/Scenarios/ModifiedScenarios"
        os.mkdir(path)

    def saveAsScenario(self):
        lyr = QgsMapLayerRegistry.instance().mapLayersByName("Buurt")[0]

        number = self.scenarioNumberIncrement()

        QgsVectorFileWriter.writeAsVectorFormat(lyr,self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/Scenario" + number + "buurt.shp","UTF8", None, "ESRI Shapefile")

        # Remove current buurt layer and add newly created buurt layer for the respective scenario

        layer = QgsMapLayerRegistry.instance().mapLayersByName("Buurt")[0]
        QgsMapLayerRegistry.instance().removeMapLayer(layer)

        vlayer = QgsVectorLayer(self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/Scenario" + str(self.scenarioNumber) + "buurt.shp", "Buurt", "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)

        proj = QgsProject.instance()
        proj.write(QFileInfo(self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/Scenario" + number + ".qgs"))

        layer = QgsMapLayerRegistry.instance().mapLayersByName("Buurt")[0]
        QgsMapLayerRegistry.instance().removeMapLayer(layer)

        vlayer = QgsVectorLayer(self.templateFolderDirectory.text() + "/Buurt.shp", "Buurt", "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)

        blayer = QgsMapLayerRegistry.instance().mapLayersByName("Buurt")[0]
        root = QgsProject.instance().layerTreeRoot()
        myblayer = root.findLayer(blayer.id())
        myClone = myblayer.clone()
        parent = myblayer.parent()
        parent.insertChildNode(3, myClone)
        parent.removeChildNode(myblayer)

        layer = uf.getLegendLayerByName(self.iface, "Buurt")
        path = self.templateFolderDirectory.text() + "/Styles/"
        layer.loadNamedStyle("%sBuurtStyle.qml" % path)
        layer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(layer)

        # Here save the analysis setting of each scenario
        scenarioLayerName = "Scenario" + str(self.scenarioNumber) + "buurt"
        if scenarioLayerName in self.layerSettingDict.keys():
            pass
        else:
            self.layerSettingDict[scenarioLayerName] = self.layerSetting
        # after the layer setting have been saved
        self.layerSetting = []

        self.popSavedScenarioList()

    def scenarioNumberIncrement(self):
        self.scenarioNumber += 1
        return str(self.scenarioNumber)

    def modifyingNumberIncrement(self):
        self.modifyingNumber += 1
        return str(self.modifyingNumber)

    def calculateScenario(self):

        # Use the analysis setting of the layer when the user is computing the modification
        clickedButton = self.sender().text()
        if clickedButton == "Compute Modified Scenario":
            layer = self.modifyingLayer
            layerSetting = self.layerSettingDict[layer.name()]
            self.landUseCheckBox.setCheckState(layerSetting[0])
            self.popDensityCheckBox.setCheckState(layerSetting[1])
            self.accessibleAreaCheckBox.setCheckState(layerSetting[2])
            self.modalShareCheckBox.setCheckState(layerSetting[3])
            numBoxChecked = sum(layerSetting) / 2

        else:
            # First count the number of check boxes selected
            numBoxChecked = 0

            if self.landUseCheckBox.checkState() == 2:
                numBoxChecked += 1
            if self.popDensityCheckBox.checkState() == 2:
                numBoxChecked +=1
            if self.accessibleAreaCheckBox.checkState() == 2:
                numBoxChecked += 1
            if self.modalShareCheckBox.checkState() == 2:
                numBoxChecked += 1

            if numBoxChecked == 0:
                self.iface.messageBar().pushMessage("Warning", "You have not selected any factors. Please select at least one factor and then click 'Compute Scenario'.", level=0, duration=5)
            else:
                layer = QgsMapLayerRegistry.instance().mapLayersByName("Buurt")[0]


        if self.landUseCheckBox.checkState() == 2 and numBoxChecked ==1:
            self.layerSetting = [2, 0, 0, 0]
            expression = QgsExpression("AvgLCIndex")
            self.changeAttribute(layer, expression)
        elif self.popDensityCheckBox.checkState() == 2 and numBoxChecked == 1:
            self.layerSetting = [0, 2, 0, 0]
            expression = QgsExpression("PopDensity")
            self.changeAttribute(layer, expression)
        elif self.accessibleAreaCheckBox.checkState() == 2 and numBoxChecked == 1:
            self.layerSetting = [0, 0, 2, 0]
            expression = QgsExpression("PTCovArea")
            self.changeAttribute(layer, expression)
        elif self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 1:
            self.layerSetting = [0, 0, 0, 2]
            expression = QgsExpression("TotalPerPT")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.popDensityCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [2, 2, 0, 0]
            expression = QgsExpression("AvgLCIndex * 0.5 + PopDensity * 0.5")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [2, 0, 2, 0]
            expression = QgsExpression("AvgLCIndex * 0.5 - PTCovArea * 0.5")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [2, 0, 0, 2]
            expression = QgsExpression("AvgLCIndex * 0.5 - TotalPerPT * 0.5")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.popDensityCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and numBoxChecked == 3:
            self.layerSetting = [2, 2, 2, 0]
            expression = QgsExpression("AvgLCIndex * 0.33 + PopDensity * 0.33 - PTCovArea * 0.33")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.popDensityCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 3:
            self.layerSetting = [2, 2, 0, 2]
            expression = QgsExpression("AvgLCIndex * 0.33 + PopDensity * 0.33 - TotalPerPT * 0.33")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 3:
            self.layerSetting = [2, 0, 2, 2]
            expression = QgsExpression("AvgLCIndex * 0.33 - PTCovArea * 0.33 - TotalPerPT * 0.33")
            self.changeAttribute(layer, expression)
        elif self.landUseCheckBox.checkState() == 2 and self.popDensityCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2:
            self.layerSetting = [2, 2, 2, 2]
            expression = QgsExpression("AvgLCIndex * 0.25 + PopDensity * 0.25 - PTCovArea * 0.25 - TotalPerPT * 0.25")
            self.changeAttribute(layer, expression)
        elif self.popDensityCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [0, 2, 2, 0]
            expression = QgsExpression("PopDensity * 0.5 - PTCovArea * 0.25")
            self.changeAttribute(layer, expression)
        elif self.popDensityCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [0, 2, 0, 2]
            expression = QgsExpression("PopDensity * 0.5 - TotalPerPT * 0.5")
            self.changeAttribute(layer, expression)
        elif self.popDensityCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 3:
            self.layerSetting = [0, 2, 2, 2]
            expression = QgsExpression("PopDensity * 0.33 - PTCovArea * 0.33 - TotalPerPT * 0.33")
            self.changeAttribute(layer, expression)
        elif self.accessibleAreaCheckBox.checkState() == 2 and self.modalShareCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [0, 0, 2, 2]
            expression = QgsExpression("PTCovArea * 0.5 * (-1) - TotalPerPT * 0.5")
            self.changeAttribute(layer, expression)
        elif self.popDensityCheckBox.checkState() == 2 and self.accessibleAreaCheckBox.checkState() == 2 and numBoxChecked == 2:
            self.layerSetting = [0, 2, 2, 0]
            expression = QgsExpression("PopDensity * 0.5 - PTCovArea * 0.5")
            self.changeAttribute(layer, expression)


    def changeAttribute(self, layer, expression):
            clickedButton = self.sender().text()
            if clickedButton == "Compute Modified Scenario":
                index = layer.fieldNameIndex("newSuitabi")
            else:
                index = layer.fieldNameIndex("Suitabilit")

            expression.prepare(layer.pendingFields())
            layer.startEditing()

            # Find minimum and maximum raw suitability values

            oldMax = -200
            oldMin = 200

            for feature in layer.getFeatures():
                value = expression.evaluate(feature)
                if value > oldMax:
                    oldMax = value
                if value < oldMin:
                    oldMin = value

            # Convert suitability values to a 0-100 standardized scale

            for feature in layer.getFeatures():
                value = expression.evaluate(feature)
                oldRange = oldMax - oldMin
                newValue = (((value - oldMin) * 100) / oldRange) + 0
                layer.changeAttributeValue(feature.id(), index, newValue)

            layer.commitChanges()



    def displayBenchmarkStyle(self):
        # loads a predefined style on a layer.
        # Best for simple, rule based styles, and categorical variables
        # attributes and values classes are hard coded in the style

        # Apply style to the buurt layer

        layer = uf.getLegendLayerByName(self.iface, "Buurt")
        path = self.templateFolderDirectory.text() + "/Styles/"
        layer.loadNamedStyle("%sBuurtStyle.qml" % path)
        layer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(layer)

        # Apply style to the train stops layer

        layer = uf.getLegendLayerByName(self.iface, "TrainStops")
        path = self.templateFolderDirectory.text() + "/Styles/"
        layer.loadNamedStyle("%sTrainStopsStyle.qml" % path)
        layer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(layer)

        # Apply style to the RET public transport stops layer

        layer = uf.getLegendLayerByName(self.iface, "RETPublicTransportStops")
        path = self.templateFolderDirectory.text() + "/Styles/"
        layer.loadNamedStyle("%sRETStopsStyle.qml" % path)
        layer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(layer)

        # Apply style to the land use layer

        layer = uf.getLegendLayerByName(self.iface, "LandUse")
        path = self.templateFolderDirectory.text() + "/Styles/"
        layer.loadNamedStyle("%sLandUseStyle.qml" % path)
        layer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(layer)


    def extractAttributeSummary(self, attribute):
        # get summary of the attribute
        layer = self.getSelectedLayer()
        summary = []
        # only use the first attribute in the list
        for feature in layer.getFeatures():
            summary.append((feature.id(), feature.attribute("Suitabilit")))
        # send this to the table
        self.clearTable()
        self.updateTable(summary)

    # report window functions

    def saveTable(self):


        selectedScenario = self.scenarioReportList.currentItem().text()

        source_dir = self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/"

        layer = QgsVectorLayer()

        for files in os.listdir(source_dir):
            if files == selectedScenario:
                layer = QgsVectorLayer(source_dir + files, files, "ogr")
                csvDir = source_dir + "/CSV/"
                if not os.path.isdir(csvDir):
                    os.mkdir(csvDir)
                QgsVectorFileWriter.writeAsVectorFormat(layer, csvDir + files.replace(".shp", ".csv"), "utf-8", None, "CSV")
                self.iface.messageBar().pushMessage("Info", "CSV file for layer " + files + " has been saved at: " + csvDir, level=0,
                                                    duration=7)

        source_dir = self.templateFolderDirectory.text() + "/Scenarios/ModifiedScenarios/"

        for files in os.listdir(source_dir):
            if files == selectedScenario:
                layer = QgsVectorLayer(source_dir + files, files, "ogr")
                csvDir = source_dir + "/CSV/"
                if not os.path.isdir(csvDir):
                    os.mkdir(csvDir)
                QgsVectorFileWriter.writeAsVectorFormat(layer, csvDir + files.replace(".shp", ".csv"), "utf-8", None, "CSV")

                self.iface.messageBar().pushMessage("Info", "CSV file for layer " + files + " has been saved at: " + csvDir,
                                        level=0, duration=7)


    def scenarioReportListGenerate(self):

        origScenariosDir = self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/"
        modifiedScenariosDir = self.templateFolderDirectory.text() + "/Scenarios/ModifiedScenarios/"

        for file in os.listdir(origScenariosDir):
            if file.endswith(".shp"):
                self.scenarioReportList.addItem(file)
        for file in os.listdir(modifiedScenariosDir):
            if file.endswith(".shp"):
                self.scenarioReportList.addItem(file)


########################
## Modification function ##
########################

    def enterPoi(self):
        # remember currently selected tool
        self.userTool = self.canvas.mapTool()

        # activate coordinate capture tool
        self.canvas.setMapTool(self.emitPoint)

        # remember which button is clicked
        self.clicked = self.sender()

        # reset the cursor style to inform the user it's in editing mode.
        self.cursor = QCursor(QPixmap(":/icons/cursor.png"), 1, 1)
        self.canvas.setCursor(self.cursor)

    def getPoint(self, mapPoint, mouseButton):
        # change tool so you don't get more than one POI
        self.canvas.unsetMapTool(self.emitPoint)
        self.canvas.setMapTool(self.userTool)

        # Get the click
        if mapPoint:
            feat = QgsFeature()
            PT_Type = self.clicked.text()

            if PT_Type in ["Metro Stop", "Bus Stop", "Tram Stop"]:
                layer_name = "RETPublicTransportStops"
                layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
                with edit(layer):
                    PT_layer = layer.dataProvider()

                    # add attribute to the layer
                    feat.setGeometry(QgsGeometry.fromPoint(mapPoint))
                    if PT_Type == "Metro Stop":
                        StopType = 'A_Metro'
                    elif PT_Type == "Bus Stop":
                        StopType = 'A_Bus'
                    else:
                        StopType = 'A_Tram'
                    feat.setAttributes(['AddedStop', PT_Type, 'ADD ', 400, StopType])
                    PT_layer.addFeatures([feat])
                    layer.updateExtents()

            else:
                layer_name = "TrainStops"
                layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
                with edit(layer):
                    PT_layer = layer.dataProvider()

                    # set the attribute of the added feature
                    id = 1001 + layer.featureCount()

                    # add attribute to the layer
                    feat.setGeometry(QgsGeometry.fromPoint(mapPoint))
                    feat.setAttributes([id, PT_Type, 'ADD', 800, 'A_Train'])
                    PT_layer.addFeatures([feat])
                    layer.updateExtents()

        # show the message to the user, and update the canvas and field of the layer
        self.iface.messageBar().pushMessage("Info", PT_Type + " is added", level=0, duration=4)
        self.canvas.refresh()

    def improvementCal(self):
        with edit(self.modifyingLayer):
            for f in self.modifyingLayer.getFeatures():
                # This function need to modified somehow
                f["ChangeSuit"] = abs(f["newSuitabi"]-f["Suitabilit"])*1.7
                if f["bu_code"] == "BU06060500" or f["bu_code"] == "BU06060404":
                    f["ChangeSuit"] = 0.0
                self.modifyingLayer.updateFeature(f)

    def computingModifiedScenario(self):

        # Show the computing message
        self.iface.messageBar().pushMessage("Info", "Computing modification scenario on " + self.modifyingLayer.name(),
                                            level=0, duration=4)

        # List all the layers needed:
        layerPath = self.templateFolderDirectory.text() + "/IntermediateLayers/"
        TrainLayer = "TrainStops"
        RETPTLayer = "RETPublicTransportStops"
        TrainBuffer = "Train_DissolvedBuffer.shp"
        RETPTBuffer = "PT_DissolvedBuffer.shp"
        BufferMerged = "merged.shp"
        MergedDissolved = "merged_dissolved.shp"
        RotterdamBurrt = "Buurt"
        PT_CoverLayer = "PT_CoverArea.shp"

        # First: create a buffer for both PT layers
        layer_list = [TrainLayer, RETPTLayer]
        for layer in layer_list:
            processing_layer = QgsMapLayerRegistry.instance().mapLayersByName(layer)[0]
            if processing_layer.name() == TrainLayer:
                QgsGeometryAnalyzer().buffer(processing_layer, layerPath + TrainBuffer, 800, False, True, -1)
            else:
                QgsGeometryAnalyzer().buffer(processing_layer, layerPath + RETPTBuffer, 400, False, True, -1)

        # Secondly: merge both layer
        qlayer1 = QgsVectorLayer(layerPath+ TrainBuffer, "Train_DissolvedBuffer", "ogr")
        qlayer2 = QgsVectorLayer(layerPath+ RETPTBuffer, "PT_DissolvedBuffer", "ogr")
        processing.runalg('qgis:mergevectorlayers', [qlayer1, qlayer2], layerPath + BufferMerged)

        qlayer3 = QgsVectorLayer(layerPath + BufferMerged, "merged", "ogr")
        QgsGeometryAnalyzer().dissolve(qlayer3, layerPath + MergedDissolved, False)

        # Third: intersect the overlap PT_area with neighborhood area
        buurtLayer = QgsMapLayerRegistry.instance().mapLayersByName(RotterdamBurrt)[0]
        qlayer4 = QgsVectorLayer(layerPath + MergedDissolved, "merged_dissolved", "ogr")
        QgsOverlayAnalyzer().intersection(qlayer4, buurtLayer, layerPath + PT_CoverLayer, False)


        # Calculate the PT_cover area
        PT_coverArea = QgsVectorLayer(layerPath + PT_CoverLayer, "PT_CoverArea", "ogr")
        PT_coverDict = {}
        for f in PT_coverArea.getFeatures():
            PT_bu_code = f["bu_code_0"]
            PT_coverDict[PT_bu_code] = f.geometry().area()

        # Update the Rotterdam_buurt layer with the latest PT_cover area
        field_names = [field.name() for field in buurtLayer.pendingFields()]
        if "Cal_PTArea" not in field_names:
            RotterdamLayer = buurtLayer.dataProvider()
            RotterdamLayer.addAttributes([QgsField("Cal_PTArea", QVariant.Double)])
            buurtLayer.updateFields()
        else:
            pass

        with edit(self.modifyingLayer):
            for f in self.modifyingLayer.getFeatures():
                bu_code = f["bu_code"]
                if bu_code in PT_coverDict.keys():
                    f["Cal_PTArea"] = PT_coverDict[bu_code]
                else:
                    f["Cal_PTArea"] = 0
                f["PTCovArea"] = (f["Cal_PTArea"] / f["Area"]) * 100.0

                # New Added
                if f["PTCovArea"] > 101:
                    f["PTCovArea"] = 50
                self.modifyingLayer.updateFeature(f)

        # New Added
        self.calculateScenario()
        self.improvementCal()

        self.iface.messageBar().pushMessage("Info", "New suitability of the " +
                                            self.modifyingLayer.name() + " layer has been calculated. Save the result to visualize the change", level=0, duration=5)
        # Apply the modified style to the layer when layer complete the modification computation
        path = self.templateFolderDirectory.text() + "/Styles/"
        self.modifyingLayer.loadNamedStyle("%sBuurtStyleModified.qml" % path)
        self.modifyingLayer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(self.modifyingLayer)

    def popSavedScenarioList(self):
        import os

        self.savedScenarionsCombo.clear()
        origScenariosDir = self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/"

        for file in os.listdir(origScenariosDir):
            if file.endswith('.shp'):
                file = file.strip('.shp')
                self.savedScenarionsCombo.addItem(file)

    def startModifyingProject(self):
        project_name = str(self.savedScenarionsCombo.currentText())

        modifPath = self.templateFolderDirectory.text() + "/Scenarios/OriginalScenarios/" + project_name + ".shp"

        # remember the selected layer in the savedScenarionComboBox
        self.modifyingLayer = QgsVectorLayer(modifPath, project_name, "ogr")


        textToFind = project_name
        index = self.savedScenarionsCombo.findText(textToFind)
        self.savedScenarionsCombo.setCurrentIndex(index)

        openLayerList = [layer.name() for layer in QgsMapLayerRegistry.instance().mapLayers().values()]

        if project_name not in openLayerList:
            loadedlayer = self.iface.addVectorLayer(modifPath, project_name, "ogr")
            qgis.utils.iface.setActiveLayer(loadedlayer)

            blayer = QgsMapLayerRegistry.instance().mapLayersByName(project_name)[0]
            root = QgsProject.instance().layerTreeRoot()
            myblayer = root.findLayer(blayer.id())
            myClone = myblayer.clone()
            parent = myblayer.parent()
            parent.insertChildNode(3, myClone)
            parent.removeChildNode(myblayer)

            path = self.templateFolderDirectory.text() + "/Styles/"
            loadedlayer.loadNamedStyle("%sBuurtStyle.qml" % path)
            loadedlayer.triggerRepaint()
            self.iface.legendInterface().refreshLayerSymbology(loadedlayer)

            self.setLayerVisibility()

            qgis.utils.iface.setActiveLayer(blayer)
            self.iface.legendInterface().setLayerVisible(blayer, True)


        else:
            # if user select the opened layer to modify, show the warning message and set the active layer to the
            # user selected layer.
            selectedLayer = QgsMapLayerRegistry.instance().mapLayersByName(project_name)[0]
            qgis.utils.iface.setActiveLayer(selectedLayer)
            self.iface.messageBar().pushMessage("Warning", str(project_name) + " layer has been opened.", level=0, duration=4)

            self.setLayerVisibility()

    def setLayerVisibility(self):
        layers = QgsMapLayerRegistry.instance().mapLayers().values()

        activeLayer = iface.activeLayer()
        for lyr in layers:
            if lyr.name() in ["TrainStops", "RETPublicTransportStops", "LandUse", activeLayer.name()]:
                iface.legendInterface().setLayerVisible(lyr, True)
            else:
                iface.legendInterface().setLayerVisible(lyr, False)

    def resetModification(self):
        layer_list = ["TrainStops", "RETPublicTransportStops"]

        for i in layer_list:
            layer = QgsMapLayerRegistry.instance().mapLayersByName(i)[0]
            PT_layer = layer.dataProvider()

            deleted_id = []
            for eachRow in layer.getFeatures():
                if eachRow.attributes()[2].startswith('ADD'):
                    deleted_id.append(eachRow.id())
            PT_layer.deleteFeatures(deleted_id)


    def saveModifiedProject(self):
        # this is the layer user is modifying.
        lyr = self.modifyingLayer

        modifyingnumber = self.modifyingNumberIncrement()

        QgsVectorFileWriter.writeAsVectorFormat(lyr,
                                                self.templateFolderDirectory.text() + "/Scenarios/ModifiedScenarios/" + str(
                                                    lyr.name()) + "_modified" + str(modifyingnumber) + ".shp",
                                                "UTF8", None, "ESRI Shapefile")

        vlayer = QgsVectorLayer(
            self.templateFolderDirectory.text() + "/Scenarios/ModifiedScenarios/" + str(lyr.name()) + "_modified" + str(
                modifyingnumber) + ".shp",
            str(lyr.name()) + "_modified" + str(modifyingnumber), "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)

        # Apply the modified style to the layer when layer is reloaded
        path = self.templateFolderDirectory.text() + "/Styles/"
        vlayer.loadNamedStyle("%sBuurtStyleModified.qml" % path)
        vlayer.triggerRepaint()
        self.iface.legendInterface().refreshLayerSymbology(vlayer)

        proj = QgsProject.instance()
        proj.write(
            QFileInfo(self.templateFolderDirectory.text() + "/Scenarios/ModifiedScenarios/" + str(
                lyr.name()) + "_modified" + str(modifyingnumber) + ".qgs"))

        self.popSavedScenarioList()
        self.setLayerVisibility()

    def displayBtnState(self):
        layer = iface.activeLayer()
        if "modified" not in layer.name():
            self.iface.messageBar().pushMessage("Warning",
                                                "You need to select the modified layer to display the suitability change",
                                                level=0, duration=4)
        else:
            # if button clicked once, show the symbology according to change
            if self.displaySuitabilityChange.isChecked():
                path = self.templateFolderDirectory.text() + "/Styles/"
                layer.loadNamedStyle("%sBuurtStyleChangeSuit.qml" % path)
                layer.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(layer)

            else:
                path = self.templateFolderDirectory.text() + "/Styles/"
                layer.loadNamedStyle("%sBuurtStyleModified.qml" % path)
                layer.triggerRepaint()
                self.iface.legendInterface().refreshLayerSymbology(layer)