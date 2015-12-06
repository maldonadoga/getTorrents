# getSubtorrents.py
# Obtiene rss de subtorrents, monitoriza los torrents y
# los lanza en transmission para su bajada
# Fecha: 30 de noviembre del 2015
# Autor: Guillermo Maldonado
# Python
# raspbian / wheezy

import http.client
import sqlite3
from xml.dom import minidom

def getRss():
  hconn = http.client.HTTPConnection('www.subtorrents.com')
  hconn.request('GET', '/rss.php')
  resp = hconn.getresponse()
  data = resp.read()
  xmlDoc = minidom.parseString(data)
  itemList = xmlDoc.getElementsByTagName('item')
  return itemList

def printItems(nodeList):
  for node in nodeList:
    title = node.getElementsByTagName('title')[0].firstChild.data
    guid = node.getElementsByTagName('guid')[0].firstChild.data
    sguid = guid.rsplit('/')
    idt = sguid[len(sguid) - 2]
    title = title.replace('\\n', '').strip()
    print(title, idt)
  return

printItems(getRss())
