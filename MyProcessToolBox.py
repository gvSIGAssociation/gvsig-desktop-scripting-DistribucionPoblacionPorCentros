# encoding: utf-8


from gvsig import *
from gvsig.commonsdialog import *

import sys
import os

from java.io import File
from org.gvsig.tools import ToolsLocator

from gvsig.libs.toolbox import *
from es.unex.sextante.gui import core
from es.unex.sextante.gui.core import NameAndIcon

from process import Process

from org.gvsig.andami import PluginsLocator

class DistribucionDePoblacionPorCentro(ToolboxProcess):

  def defineCharacteristics(self):
    i18n = ToolsLocator.getI18nManager()

    # Fijamos el nombre con el que se va a mostrar nuestro proceso
    self.setName(i18n.getTranslation("_Distribucion_de_poblacion_por_centro"))

    # Indicamos el grupo en el que aparecera
    self.setGroup("Vectorial")

    self.setUserCanDefineAnalysisExtent(False)
    
    params = self.getParameters()
    params.addInputVectorLayer("POBLACION",i18n.getTranslation("_Capa_poblacion"), SHAPE_TYPE_POINT,True)
    params.addTableField("POB_ID", i18n.getTranslation("_Identificador_en_la_tabla_de_poblacion"),"POBLACION", True)
    params.addTableField("POB_EDAD", i18n.getTranslation("_Campo_edad_en_la_tabla_de_poblacion"),"POBLACION", True)

    params.addInputVectorLayer("CENTROS",i18n.getTranslation("_Capa_de_centros"), SHAPE_TYPE_POINT,True)
    params.addTableField("CENTRO_ID", i18n.getTranslation("_Identificador_en_la_tabla_de_centros"),"CENTROS", True)
    params.addTableField("CENTRO_NOMBRE", i18n.getTranslation("_Campo_nombre_en_la_tabla_de_centros"),"CENTROS", True)

    # Indicamos que precisamos un par de valores numericos, X e Y
    params.addNumericalValue("MAX_PERSONAS", i18n.getTranslation("_Poblacion_por_centro"),0, NUMERICAL_VALUE_INTEGER)
    params.addNumericalValue("MAX_DISTANCIA_VECINOS", i18n.getTranslation("_Maxima_distancia_para_alcanzar_un_centro_vecino"), 100, NUMERICAL_VALUE_INTEGER)
    params.addNumericalValue("EDAD_MIN", i18n.getTranslation("_Edad_minima_para_tener_en_cuenta_a_una_persona"),18, NUMERICAL_VALUE_INTEGER)
    params.addNumericalValue("EDAD_MAX", i18n.getTranslation("_Edad_maxima_para_tener_en_cuenta_a_una_persona"),0, NUMERICAL_VALUE_INTEGER)

    # Y por ultimo indicamos que precisaremos una capa de salida de puntos.
    self.addOutputVectorLayer("RESULT", i18n.getTranslation("_Resultado"), SHAPE_TYPE_POINT)

  def processAlgorithm(self):
        features=None

        try:
          i18n = ToolsLocator.getI18nManager()
          params = self.getParameters()
          
          process = Process(
            params.getParameterValueAsVectorLayer("CENTROS").getFeatureStore(),
            params.getParameterValueAsVectorLayer("POBLACION").getFeatureStore(),
            params.getParameterValueAsInt("POB_ID"),
            params.getParameterValueAsInt("POB_EDAD"),
            params.getParameterValueAsInt("CENTRO_ID"),
            params.getParameterValueAsInt("CENTRO_NOMBRE"),
            params.getParameterValueAsInt("MAX_PERSONAS"),
            params.getParameterValueAsInt("MAX_DISTANCIA_VECINOS"),
            params.getParameterValueAsInt("EDAD_MIN"),
            params.getParameterValueAsInt("EDAD_MAX"),
            self
          )
          output_store = self.buildOutPutStore(
                process.getPointsFeatureType(),
                SHAPE_TYPE_POINT,
                i18n.getTranslation("_Distribucion_poblacion"),
                "RESULT"
          )
          process.estimarProceso()

          process.cargarCentros()
          
          process.calcularPoblacionPorCentro()
          process.calcularDistribucionPorDistancia()
          
          process.redistribuirEntreLosCentrosVecinos()
          
          process.populateOutput(output_store)

        except:
          ex = sys.exc_info()[1]
          print str(ex)
          
        finally:
          print "Proceso terminado %s" % self.getCommandLineName()
          return True

  def getHelpFile(self):
      name = "distribucionPoblacionPorCentros"
      extension = ".xml"
      locale = PluginsLocator.getLocaleManager().getCurrentLocale()
      tag = locale.getLanguage()
  
      helpPath = getResource(__file__, "help", name + "_" + tag + extension)
      if os.path.exists(helpPath):
          return File(helpPath)
      #Alternatives
      alternatives = PluginsLocator.getLocaleManager().getLocaleAlternatives(locale)
      for alt in alternatives:
          helpPath = getResource(__file__, "help", name + "_" + alt.toLanguageTag() + extension )
          if os.path.exists(helpPath):
              return File(helpPath)
      # More Alternatives
      helpPath = getResource(__file__, "help", name + extension)
      if os.path.exists(helpPath):
          return File(helpPath)
      return None
      
def selfRegister():
  i18n = ToolsLocator.getI18nManager()
  i18n.addResourceFamily("text",File(getResource(__file__,"i18n")))
  
  process = DistribucionDePoblacionPorCentro()
  process.selfregister("Scripting")
  process.updateToolbox()
  #msgbox(i18n.getTranslation("_Se_ha_incorporado_el_script_Scripting_Group_Name_a_la_paleta_de_geoprocesos") % (
  #        "Scripting",
  #        process.getGroup(),
  #        process.getName()
  #  )
  #)

def main(*args):
  selfRegister()
