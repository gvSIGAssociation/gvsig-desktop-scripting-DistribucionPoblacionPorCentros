# encoding: utf-8

import gvsig
from gvsig import currentView

from gvsig.geom import D2
from gvsig.geom import POLYGON, MULTIPOINT, POINT
from gvsig.geom import createMultiPoint

from org.gvsig.tools import ToolsLocator

from gvsig import createFeatureType
from gvsig import createShape

from java.lang import IllegalArgumentException

class Centro(object):
  def __init__(self, id, nombre, pos):
    self.id = id
    self.nombre = nombre
    self.pos = pos
    self.poblacion = list()
    self.area = None

  def add(self, personaid, pos):
    self.poblacion.append((personaid, pos))
    self.area = None

  def remove(self, personaid):
    for n in xrange(len(self.poblacion)):
      persona = self.poblacion[n]
      if personaid == persona[0]:
        del self.poblacion[n]
        self.area = None
        return
    pass

  def getTotalCount(self):
    return len(self.poblacion)

  def getPolygon(self):
    if self.area == None:
      points = createMultiPoint()
      for persona in self.poblacion:
        points.addPoint(persona[1])
      self.area = points.convexHull()
    return self.area

  def getMultiPoint(self):
    points = createMultiPoint()
    for persona in self.poblacion:
      points.addPoint(persona[1])
    return points
      
class Process(object):
  def __init__(self, centros, poblacion, pob_id, pob_edad, centro_id, centro_nombre, max_poblacion, max_distancia, edad_min, edad_max, progress):
    print "pob_id=", repr(pob_id)
    print "pob_edad=", repr(pob_edad)
    print "centro_id=", repr(centro_id)
    print "centro_nombre=", repr(centro_nombre)
    print "max_poblacion=", repr(max_poblacion)
    print "max_distancia=", repr(max_distancia)
    print "edad_min=", repr(edad_min)
    print "edad_max=", repr(edad_max)
    self.max_distancia = max_distancia # Buffer para calcular los centros vecinos
    self.max_poblacion = max_poblacion # por centro
    self.total_poblacion = 0
    self.pob_id = pob_id
    self.pob_edad = pob_edad
    self.centro_id = centro_id
    self.centro_nombre = centro_nombre
    self.progress = progress
    self.store_centros = centros
    self.store_poblacion = poblacion
    self.edad_min = edad_min
    self.edad_max = edad_max
    if self.edad_min <0:
      self.edad_min = 0
    if self.edad_max<1:
      self.edad_max = 2000000000
    if self.edad_min >= self.edad_max:
      raise IllegalArgumentException("Rango de edad incorrecto (min=%s, max=%s)" % (self.edad_min, self.edad_max))
    self.centros = list()

  def estimarProceso(self):
    ncentros = self.store_centros.getFeatureCount()
    npoblacion = self.store_poblacion.getFeatureCount()

    n = ncentros*2 + npoblacion*2 +1
    self.progress.setRangeOfValues(0,n)
    
  def cargarCentros(self):
    i18n = ToolsLocator.getI18nManager()
    
    self.progress.setProgressText(i18n.getTranslation("_Cargando_centros"))
    self.centros = list()
    for feature in self.store_centros:
      centro = Centro(
        feature.get(self.centro_id),
        feature.get(self.centro_nombre),
        feature.getDefaultGeometry()
      )
      self.progress.next()
      for unCentro in self.centros:
        if unCentro.nombre == centro.nombre:
          centro = None
          break
      if centro!=None:
        self.centros.append(centro)

  def calcularPoblacionPorCentro(self):
    i18n = ToolsLocator.getI18nManager()
    self.progress.setProgressText(i18n.getTranslation("_Calculando_poblacion_en_la_edad_indicada"))
    self.total_poblacion = 0
    for persona in self.store_poblacion:
      self.progress.next()
      edad = persona.get(self.pob_edad)
      if edad < self.edad_min and edad>self.edad_max:
        continue
      self.total_poblacion += 1
    if self.max_poblacion<1:
      self.max_poblacion = self.total_poblacion/len(self.centros)
    print "Poblacion por centro:", self.max_poblacion

  def calcularDistribucionPorDistancia(self):
    i18n = ToolsLocator.getI18nManager()
    self.progress.setProgressText(i18n.getTranslation("_Distribuyendo_en_funcion_de_la_distancia"))
    for persona in self.store_poblacion:
      self.progress.next()
      edad = persona.get(self.pob_edad)
      if edad < self.edad_min and edad>self.edad_max:
        continue
      elCentro = None
      distancia = -1
      for centro in self.centros:
        d2 = centro.pos.distance(persona.getDefaultGeometry())
        if elCentro==None or d2<distancia:
          elCentro = centro
          distancia = d2
      elCentro.add(persona.get(self.pob_id), persona.getDefaultGeometry())
      self.progress.next()

  def calcularLosCentrosVecinosALosQuePuedeCederExcedente(self, centro):
    area = centro.getPolygon()
    area = area.buffer(self.max_distancia)
    receptores = list()
    for unCentro in self.centros:
      if unCentro == centro:
        continue
      if area.intersects(unCentro.getPolygon()) and unCentro.getTotalCount()<self.max_poblacion:
        receptores.append(unCentro)
    if len(receptores)<1:
      return None
    return receptores

  def cederExcedenteAlCentro(self, origen, destino):    
    destipo_pos = destino.pos
    poblacion = list()
    for persona in origen.poblacion:
      persona_pos = persona[1]
      distancia = persona_pos.distance(destipo_pos)
      poblacion.append((persona[0], persona_pos, distancia))
    poblacion.sort(reverse=False, key=lambda x: x[2])
    count = 0
    for persona in poblacion:
      destino.add(persona[0], persona[1])
      origen.remove(persona[0])
      if origen.getTotalCount()<self.max_poblacion:
        break
      if destino.getTotalCount()>=self.max_poblacion:
        break
      count +=1
      if count == 10:
        break
    
  def cederExcedenteALosCentrosVecinos(self, origen, vecinos):
    vecinos.sort(reverse=True, key=lambda x: self.max_poblacion-x.getTotalCount())
    for vecino in vecinos:
      self.cederExcedenteAlCentro(origen, vecino)
      if origen.getTotalCount()<self.max_poblacion:
        break
    
  def redistribuirEntreLosCentrosVecinos(self):
    i18n = ToolsLocator.getI18nManager()
    self.progress.setProgressText(i18n.getTranslation("_Redistribuyendo_poblacion"))
    self.centros.sort(reverse=True, key=lambda x: x.getTotalCount())
    for x in xrange(1000):
      terminado = True
      for unCentro in self.centros:
        unCentro_count = unCentro.getTotalCount()
        if unCentro_count > self.max_poblacion:
          vecinos = self.calcularLosCentrosVecinosALosQuePuedeCederExcedente(unCentro)
          if vecinos!=None:
            self.cederExcedenteALosCentrosVecinos(unCentro, vecinos)
            if unCentro_count != unCentro.getTotalCount():
              terminado = False
      if terminado:
        break
    self.progress.next()
        
  def process(self):
    self.calcularPersonasPorCentro()
    self.calcularDistribucionPorDistancia()
    self.redistribuirEntreLosCentrosVecinos()

  def getPointsFeatureType(self):
    schema = createFeatureType()
    
    schema.append("POB_ID", "INTEGER", 10)
    schema.append("CENTRO_ID", "INTEGER", 10)
    schema.append("GEOMETRY", "GEOMETRY")
    schema.get("GEOMETRY").setGeometryType(POINT, D2)
    return schema

    
  def getPolygonFeatureType(self):
    schema = createFeatureType()
    
    schema.append("ID", "INTEGER", 10)
    schema.append("COUNT", "INTEGER", 10)
    schema.append("NAME", "STRING", 50)
    schema.append("GEOMETRY", "GEOMETRY")
    schema.get("GEOMETRY").setGeometryType(POLYGON, D2)
    return schema

  def populateOutput(self, store):
    i18n = ToolsLocator.getI18nManager()
    self.progress.setProgressText(i18n.getTranslation("_Generando_resultados"))
    for unCentro in self.centros:
      for persona in unCentro.poblacion:
        f = store.createNewFeature()
        f.set("CENTRO_ID",unCentro.id)
        f.set("POB_ID",persona[0])
        f.set("GEOMETRY",persona[1])
        store.insert(f)
    store.commit()  


class Progress(object):

  def setProgressText(self, msg):
    print msg

  def setRangeOfValues(self, min, max):
    self.min = min 
    self.max = max
    self.current = min

  def next(self):
    self.current += 1
      
def crearCapaDePoligonos(process, layerName):
  capa = createShape(process.getPolygonFeatureType())
  capa.setName(layerName)
  store = capa.getFeatureStore()
  store.edit()
  for unCentro in process.centros:
    unCentro.area = None
    f = store.createNewFeature()
    f.set("ID",unCentro.id)
    f.set("NAME",unCentro.nombre)
    f.set("COUNT",unCentro.getTotalCount())
    f.set("GEOMETRY",unCentro.getPolygon())
    store.insert(f)
  capa.commit()  
  currentView().addLayer(capa)


def main(*args):
  vista = currentView()
  centros = vista.getLayer("colegios_electorales-puntos_def")
  poblacion = vista.getLayer("Padron_direccion_buena_-unido-1")

  process = Process(
    centros.getFeatureStore(),
    poblacion.getFeatureStore(),
    "contador", 
    "Edad", 
    "ID", 
    "Nombre", 
    0, 
    100,
    18, -1,
    Progress()
  )
  process.estimarProceso()
  process.cargarCentros()
  process.calcularPoblacionPorCentro()
  process.calcularDistribucionPorDistancia()

  # Crear capa de poligonos con la distribucion por distancia
  crearCapaDePoligonos(process, "centros_por_distancia")

  process.redistribuirEntreLosCentrosVecinos()

  # Crear capa de poligonos con la redistribucion realizada
  crearCapaDePoligonos(process, "centros_redistribuidos")

  # Crear capa de puntos con poblacion por centro
  capa = createShape(process.getPointsFeatureType())
  capa.setName("Poblacion por centro")
  store = capa.getFeatureStore()
  store.edit()
  process.populateOutput(store)
  currentView().addLayer(capa)

  