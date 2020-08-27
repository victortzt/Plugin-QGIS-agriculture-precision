# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Precision Agriculture
                                 A QGIS plugin
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

__author__ = 'Lisa Rollier - ASPEXIT'
__date__ = '2020-07-21'
__copyright__ = '(C) 2020 by ASPEXIT'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

#import QColor

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsApplication,
                       QgsRasterLayer,
                       #QgsColorRampShader,
                       #QgsRasterShader,
                       #QgsSingleBandPseudoColorRenderer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterEnum)

from .functions.fonctions_repartition import *

from qgis import processing 

from osgeo import gdal
import numpy as np
#from PyQt5.QtGui import QColor

class ClassifyRaster(QgsProcessingAlgorithm):
    """
    
    """

    OUTPUT= 'OUTPUT'
    INPUT = 'INPUT'
    INPUT_METHOD = 'INPUT_METHOD'
    INPUT_N_CLASS='INPUT_N_CLASS'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Raster to classify')
            )
        )

       
        self.addParameter(
            QgsProcessingParameterEnum(
                self.INPUT_METHOD,
                self.tr('Classification method'),
                ['Quantiles', 'Equal-intervals', 'K-means']                
            )
        )
       
        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_N_CLASS, 
                self.tr('Number of classes'),
                QgsProcessingParameterNumber.Integer,
                4,
                False,
                2,
                10
            )
        )
        
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                self.tr('Classified raster')
            )
        )
        
        
        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        
        layer_temp=self.parameterAsRasterLayer(parameters,self.INPUT,context)
        fn = self.parameterAsOutputLayer(parameters,self.OUTPUT,context)
        method = self.parameterAsEnum(parameters,self.INPUT_METHOD,context)
        nombre_classes=self.parameterAsInt(parameters,self.INPUT_N_CLASS,context)
                        
        if feedback.isCanceled():
            return {}
                
        #k-means
        if method == 2 :
            # K-means clustering for grids
            alg_params = {
                'GRIDS': parameters[self.INPUT],
                'MAXITER': 0,
                'METHOD': 0,
                'NCLUSTER': nombre_classes,
                'NORMALISE': False,
                'OLDVERSION': False,
                'UPDATEVIEW': True,
                'CLUSTER': parameters[self.OUTPUT],
                'STATISTICS': parameters[self.OUTPUT]
            }
            #on place manuellement la couche CLUSTER dans fn, sinon l'algorithme classification n'a pas la couche en OUTPUT (problèmes
            #dans zonage ensuite)
            fn = processing.run('saga:kmeansclusteringforgrids', alg_params, context=context, feedback=feedback, is_child_algorithm=True)['CLUSTER']
            
        else :
            # récupération du path de la couche en entrée
            fn_temp = layer_temp.source()
            
            # ouverture de la couche avec la bibliothèque gdal
            ds_temp = gdal.Open(fn_temp)

            #permet de lire la bande du raster en tant que matrice de numpy. 
            band_temp = ds_temp.GetRasterBand(1)
            array = band_temp.ReadAsArray()

            #extraction de la valeur "artificielle" (-infini) des points sans valeur
            nodata_val = band_temp.GetNoDataValue()
            
            #on va masquer les valeurs de "sans valeur", ce qui va permettre le traitement ensuite
            if nodata_val is not None:
                array = np.ma.masked_equal(array, nodata_val)
                
                                
            if feedback.isCanceled():
                return {}
                    
            #on créé la couche raster en calque sur la couche source
            driver_tiff = gdal.GetDriverByName("GTiff")
            ds = driver_tiff.Create(fn, xsize=ds_temp.RasterXSize, \
            ysize = ds_temp.RasterYSize, bands = 1, eType = gdal.GDT_Float32)

            ds.SetGeoTransform(ds_temp.GetGeoTransform())
            ds.SetProjection(ds_temp.GetProjection())
            
            #on récupère la bande en matrice
            output = ds.GetRasterBand(1).ReadAsArray()
            
            # on rempli cette couche de NaN
            output[:].fill(np.nan)
                                         
            if feedback.isCanceled():
                return {}
                    

            #QUANTILES
            if method == 0:             
                output = rep_quantiles(nombre_classes,array,output)
            #INTERVALLES EGAUX
            elif method == 1 :
                output = intervalles_egaux(nombre_classes,array,output)
           
          
     
            #ajouter les modifications effectuées sur la matrice dans la couche raster
            ds.GetRasterBand(1).WriteArray(output)
                                    
        if feedback.isCanceled():
            return {}
                

        return{self.OUTPUT : fn} 
   
    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "R - Classification"

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
        return self.tr('Classification')
        
    def shortHelpString(self):
        short_help = self.tr(
            'Allows to reclassify a raster into a user-defined number of classes'
            'using several classification methods'
            '\nprovided by ASPEXIT\n'
            'author : Lisa Rollier'
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
        return 'classification'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ClassifyRaster()
