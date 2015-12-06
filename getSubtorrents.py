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
import transmissionrpc
import re
import os
import smtplib
import datetime
#
## Init
db = sqlite3.connect("~/projects/getTorrent/getTorrent.db")
cursor = db.cursor()
p = re.compile('\d+[x]\d+', re.IGNORECASE)
hconn = http.client.HTTPConnection('www.subtorrents.com')
tc = transmissionrpc.Client('localhost', port=9091, user='transmission', password='password')
months = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
sourceId = '1'

def getSrc(idSource):
  cursor.execute('SELECT url, rss, download FROM source WHERE sourceId = ?', (idSource,))
  return cursor.fetchone()

def getTitles(idSource):
  cursor.execute('SELECT titleId, title, downloadDir, pubDate FROM title WHERE sourceId = ?', (idSource,))
  return cursor.fetchall()

def getRss():
  hconn.request('GET', '/rss.php')
  resp = hconn.getresponse()
  return resp.read()
  
def getXml(data):
  bData = data.replace(b'&', b'')
  return minidom.parseString(bData)
  
def getRssTitles(xmlDoc):
  return xmlDoc.getElementsByTagName('item')

def getGuidId(text):
  sguid = text.rsplit('/')
  return sguid[len(sguid) - 2]

def getTorrents(nodeList, myTitles, downUrl):
  torrents = []
  for node in nodeList:
    title = node.getElementsByTagName('title')[0].firstChild.data
    guid = node.getElementsByTagName('guid')[0].firstChild.data
    pubDate = node.getElementsByTagName('pubDate')[0].firstChild.data
    idt = getGuidId(guid) 
    cTitle = cleanTitle(title)
    dPubDate = getRssDate(pubDate)
    for myTitle in myTitles:
      if myTitle[1].upper() == cTitle.upper() and myTitle[3] < dPubDate:
        url = downUrl + idt
        season = getSeason(title)
        downloadDir = '{0}/S{1}'.format(myTitle[2], season)
        torrents.append((myTitle[0], url, downloadDir, dPubDate))
  return torrents

def cleanTitle(title):
  title = title.replace('\\n', '').strip()
  season = p.search(title)
  if season:
    return title[0:season.start() - 1]
  else:
    return title
  
def getSeason(title):
  season = p.findall(title)[0]
  sn = season[0:season.upper().find('X')]
  if season:
    return '{0:0>2}'.format(sn)
  else:
    return '01'

def getRssDate(txtD):
  txtDate = txtD.split()
  year = txtDate[3]
  i = 0
  for m in months:
    i = i + 1
    if m.upper() == txtDate[2].upper():
      month = i
      break
  day = txtDate[1]
  time = txtDate[4]
  return '{0}-{1}-{2} {3}'.format(year, month, day, time)

def valDownDir(downDir):
  if not os.path.isdir(downDir):
    os.makedirs(downDir)
  
def addTorrents(torrents):
  for t in torrents:
    valDownDir(t[2])
    tc.add_torrent(t[1], paused = 'false', download_dir = t[2])
    title = cursor.execute('SELECT pubDate FROM title WHERE sourceId = ? AND titleId = ?', (sourceId, t[0]))
    if title.fetchone()[0] < t[3]:
      cursor.execute('UPDATE title SET pubDate = ? WHERE sourceId = ? AND titleId = ?', (t[3], sourceId, t[0]))        
      db.commit()
    print('{0} - {1}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), t))

def manageTorrents():
  torrents = tc.get_torrents()
  for t in torrents:
    cursor.execute('SELECT mailSent, doneDate FROM torrents WHERE hashString = ?', (t.hashString,))
    dbt = cursor.fetchone()
    if not dbt:
      cursor.execute('INSERT INTO torrents(hashString, name, status, addedDate, mailSent) VALUES(?, ?, ?, datetime(), 0)', (t.hashString, t.name, t.status))
      db.commit()
    else:
      if t.status == 'seeding' and not dbt[0]:
          sendMsg(t)
      else:
        cursor.execute('UPDATE torrents SET status = ? WHERE hashString = ?', (t.status, t.hashString))
        db.commit()
      if t.status == 'seeding' and (t.uploadRatio >= 1 or (datetime.datetime.now() - datetime.datetime.strptime(dbt[1], '%Y-%m-%d %H:%M:%S')).days >= 1):
        tc.remove_torrent(t.hashString)
        print('{0} - Removed torrent: {1} UploadRatio: {2} DoneDate: {3}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), t.name, t.uploadRatio, dbt[1]))

def sendMsg(t):
  ems = smtplib.SMTP('smtp.gmail.com:587')
  ems.starttls()
  ems.login('user@gmail.com', 'password')
  subject = t.name + ' completed'
  message = 'HashString: {0} Name {1} Added date: {2} Done date: {3}'.format(t.hashString, t.name, t.addedDate, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
  ems.sendmail('maldonadoga.raspberrypi@gmail.com', 'maldonadoga@hotmail.com', 'Subject: {0}\r\n{1}'.format(subject, message))
  ems.quit()
  cursor.execute('UPDATE torrents SET mailSent = 1, doneDate = datetime() WHERE hashString = ?', (t.hashString,))
  db.commit()

srcTorrent = getSrc(sourceId)
myTitles = getTitles(sourceId)
Rss = getRss()
xmlDoc = getXml(Rss)
rssTitles = getRssTitles(xmlDoc)
torrents = getTorrents(rssTitles, myTitles, srcTorrent[2])
if torrents:
  addTorrents(torrents)
manageTorrents()

#
## End
db.close()
hconn.close()
