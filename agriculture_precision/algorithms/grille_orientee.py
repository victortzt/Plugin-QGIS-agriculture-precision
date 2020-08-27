# -*- coding: utf-8 -*-

"""
/***************************************************************************
 AgriculturePrecision
                                 A QGIS plugin
 Chaines de traitement
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-07-21
        copyright            : (C) 2020 by ASPEXIT
        email                : cleroux@aspexit.com
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

__author__ = 'ASPEXIT'
__date__ = '2020-07-21'
__copyright__ = '(C) 2020 by ASPEXIT'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

#import QColor

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsApplication,
                       QgsVectorLayer,
                       QgsDataProvider,
                       QgsVectorDataProvider,
                       QgsField,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterNumber)

from qgis import processing 

import numpy as np
import pandas as pd
from scipy.spatial import distance
from math import sqrt,pi,atan2
import statistics as st

class GrilleOrientee(QgsProcessingAlgorithm):
    """
    
    """

    OUTPUT= 'OUTPUT'
    INPUT = 'INPUT'
    FIELD = 'FIELD'
    INPUT_ROTATION = 'INPUT_ROTATION'
    INPUT_SIZE = 'INPUT_SIZE'
    BOOLEAN = 'BOOLEAN'


    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr('Point layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.BOOLEAN,
                self.tr("Enter rotation angle manually")
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_ROTATION, 
                self.tr('Rotation angle (if manual entry), in degrees'),
                QgsProcessingParameterNumber.Double
            )
        ) 
        
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_SIZE, 
                self.tr('Grid resolution (in meters)'),
                QgsProcessingParameterNumber.Double,
                5
            )
        ) 
               
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Oriented grid')
            )
        )
        
        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        
        layer=self.parameterAsVectorLayer(parameters,self.INPUT,context) 
        output_path = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        
        
        ex = layer.extent()
        xlength = (ex.xMaximum() - ex.xMinimum())
        ylength = (ex.yMaximum() - ex.yMinimum())
        x = ex.xMinimum() + xlength/2
        y = ex.yMinimum() + ylength/2
        cote_min = min(xlength,ylength)
        buffer = (1/2)*(sqrt((xlength**2)+(ylength**2))-cote_min)
            
         # Tampon
        # Pour avoir un extent plus grand
        alg_params = {
            'DISSOLVE': False,
            'DISTANCE': buffer,
            'END_CAP_STYLE': 0,
            'INPUT': parameters['INPUT'],
            'JOIN_STYLE': 0,
            'MITER_LIMIT': 2,
            'SEGMENTS': 5,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        tampon = processing.run('native:buffer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['OUTPUT']
        
        # Créer une grille
        alg_params = {
            'CRS': 'ProjectCrs',
            'EXTENT': tampon,
            'HOVERLAY': 0,
            'HSPACING': parameters['INPUT_SIZE'],
            'TYPE': 2,
            'VOVERLAY': 0,
            'VSPACING': parameters['INPUT_SIZE'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        creer_grille = processing.run('native:creategrid', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        if parameters['BOOLEAN']:
            angle = parameters['INPUT_ROTATION']
        else :
            features = layer.getFeatures()
            head_dir = []
            
            for feat in features :
                coordinates_arr = np.array([[feat.geometry().asPoint()[k] for k in range(2)] for feat in features])
                  
            for k in range(len(coordinates_arr)-1):
                delta_X = coordinates_arr[k+1][0]-coordinates_arr[k][0]
                delta_Y = coordinates_arr[k+1][1]-coordinates_arr[k][1]
                angle_degree = atan2(-delta_Y,-delta_X)*180/pi
                if angle_degree <0:
                    angle_degree+=180
                head_dir.append(angle_degree)

            principal_headir = st.median(head_dir)
            angle = -principal_headir
            

        # Rotation
        alg_params = {
            'ANCHOR': str(x)+','+str(y),
            'ANGLE': angle,
            'INPUT': creer_grille['OUTPUT'],
            'OUTPUT': parameters['OUTPUT']
        }
        processing.run('native:rotatefeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        return{self.OUTPUT : output_path} 

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'V - Grid oriented in the direction of rows'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Data Manipulation')

    def shortHelpString(self):
        short_help = self.tr(
            'For a given point layer oriented in a particular direction'
            '(following rows or a machine passage for example), the function '
            'builds a grid oriented in the majority direction of the points. '
            'The size of the grid is defined by the user.  Prerequisite: The order'
            'of the points in the layer must follow the data acquisition.'
        ) 
        return short_help


    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'data_manipulation'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return GrilleOrientee()
