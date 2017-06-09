#!/usr/bin/python
#   Frizzbar Besturing
#	Versie: 5.0.0
#

import ConfigParser							# required to handle all configurations
import logging								# logging functions
import sqlite3								# required to handle database functions
import time                 				# for all time functions
from time import strftime,gmtime
import serial              					# for communication with RFID reader
import schedule								# Scheduler to run tasks (turn on, turn off etc)
from grove_rgb_lcd import * 				# For LCD
import grovepi              				# For button and switch
from grovepi import *

# Configuration
config = ConfigParser.SafeConfigParser()
config.read('config.ini')
# Logging
logfile = config.get('main', 'logfile')
FORMAT = "%(asctime)s - %(message)s"  
logging.basicConfig(filename=logfile,level=logging.WARNING,format=FORMAT)
logging.warning("Started Frizzbar Control")
# Database
database_file = config.get('main', 'database')
conn = sqlite3.connect(database_file)
# Define Globals
global status
status = 0							# Status defines Frizzbar status (0 = OFF; 1 = ON)
global mode
mode = 0							# Mode defines user mode (0 = OFF; 1 = IDLE)
global message	
message = "empty"	
global temperature
temperature = 0 		
# Setup RFID
rfid = serial.Serial('/dev/ttyAMA0',9600,timeout=0.010)
time.sleep(0.001)
rfid.flushInput()
# Pins
pinpushbutton = int(config.get('pins', 'pushbutton'))
pinkeyswitch = int(config.get('pins', 'keyswitch'))
pinbuzzer = int(config.get('pins', 'buzzer'))
pinpower = int(config.get('pins', 'power'))
pinpay = int(config.get('pins', 'pay'))
pintemp = int(config.get('pins', 'temp'))
# GrovePi Pins
grovepi.pinMode(pinpushbutton,"INPUT")
grovepi.pinMode(pinkeyswitch,"INPUT")
grovepi.pinMode(pinbuzzer,"OUTPUT")
grovepi.pinMode(pinpower,"OUTPUT")
grovepi.pinMode(pinpay,"OUTPUT")
# LCD Scherm
setRGB(255,255,255)
bericht = '{:^16}'.format("Frizzbar Starten")
setText(bericht)

def frizzbar():
    if (status == 0): 	# Power off, Frizzbar offline
        try:
            offline()
        except BaseException as e:
            message = "Error;" + str(e)
            logging.error(message)
            print message
    if (status == 1):	# Power on, Frizzbar online
        try:
            online()
        except BaseException as e:
            message = "Error;" + str(e)
            logging.error(message)   
            print message

def offline():
	try:
		if (pushcallback() == 1):
			changemode("on")
		schedule.run_pending()
	except BaseException as e:
		logging.warning(str(e))
		print(str(e))

def online():
	try:
		if (mode == 1): # Normale mode
			modenormal()
			schedule.run_pending()
		if (mode == 2): # Info mode
			modeinfo()
		if (mode == 3): # Upgrade mode
			modeupgrade()
	except BaseException as e:
		logging.warning(str(e))
		print(str(e))
		
def changemode(setmode):
	global status
	global mode
	if (setmode == "on"):
		digitalWrite(pinpower, 1)
		setRGB(255,255,255)
		bericht = '{:^16}'.format("Frizzbar")
		setText(bericht)
		bericht = '{:^16}'.format("Opstarten")
		setText_norefresh("\n" + bericht)
		status = 1
		mode = 1
		time.sleep(1)
		cur = conn.cursor()
		sql = "UPDATE status SET status = '1'"
		cur.execute(sql)
		sql = "UPDATE status SET remote = '1'"
		cur.execute(sql)
		conn.commit()
		changemode("normal")
	if (setmode == "normal"):
		status = 1
		mode = 1
		bericht = '{:^16}'.format("Frizzbar")
		setText(bericht)
		printtime()
	if (setmode == "credit"):
		bericht = '{:*^16}'.format("Informatie")
		setText(bericht)
		bericht = '{:^16}'.format("Geef uw tag..")
		setText_norefresh("\n" + bericht)
		status = 1
		mode = 2
	if (setmode == "admin"):
		bericht = '{:*^16}'.format("Opwaarderen")
		setText(bericht)
		bericht = '{:^16}'.format("Geef een tag..")
		setText_norefresh("\n" + bericht)
		status = 1
		mode = 3;
	if (setmode == "off"):
		digitalWrite(pinpower, 0)
		bericht = '{:^16}'.format("Frizzbar")
		setText(bericht)
		bericht = '{:^16}'.format("Afsluiten..")
		setText_norefresh("\n" + bericht)
		time.sleep(1)
		bericht = '{:#^16}'.format(" Offline ")
		setText(bericht)
		status = 0
		mode = 1
		cur = conn.cursor()
		sql = "UPDATE status SET status = '0'"
		cur.execute(sql)
		sql = "UPDATE status SET remote = '0'"
		cur.execute(sql)
		conn.commit()
		printtime()

def modenormal():
	card = readrfid()
	if card != None:
		digitalWrite(pinbuzzer, 1)
		tag = card.encode('hex')
		print tag
		time.sleep(0.1)
		digitalWrite(pinbuzzer, 0)
		vend(tag)
		time.sleep(0.001)
		rfid.flushInput()
	try:
		if (pushcallback() == 1):
			changemode("credit")
		if (keycallback() == 1):
			changemode("admin")
	except BaseException as e:
		logging.warning(str(e))
		print(str(e))
	#normal

def vend(input):
	card = str(input)
	cur = conn.cursor()
	sql = "SELECT * FROM gebruikers WHERE `tag` = '" + card + "'"
	cur.execute(sql)
	row = cur.fetchone()
	if row is not None:
		bericht = '{:^16}'.format(str(row[1]))
		naam = str(row[1])
		setText(bericht)
		bericht = '{:^16}'.format("Credits: " + str(row[3]) + " (" + str(row[4]) +")")
		setText_norefresh("\n" + bericht)
		if (row[3] < 1):
			setRGB(255,0,0)
			bericht = '{:^16}'.format("Geen saldo")
			setText_norefresh("\n" + bericht)
			time.sleep(2)
			setRGB(255,255,255)
		else:
			setRGB(0,255,0)
			saldo = row[3]-1
			consumpties = row[4]+1
			cur = conn.cursor()
			sql = "UPDATE gebruikers SET credits = '"+str(saldo)+"' , consumpties = '"+str(consumpties)+"' WHERE tag = '"+card+"'"
			cur.execute(sql)
			conn.commit()
			digitalWrite(pinpay, 1)
			bericht = '{:^16}'.format("Credits: " + str(saldo) + " (" + str(consumpties) +")")
			setText_norefresh("\n" + bericht)
			time.sleep(0.5)
			digitalWrite(pinpay, 0)
			cur = conn.cursor()
			sql = "INSERT INTO `gebruikslog` (datumtijd, naam, credits) VALUES ('"+strftime("%Y-%m-%d %H:%M")+"','"+naam+"','"+str(saldo)+"','frizzbar')"
			cur.execute(sql)
			conn.commit()
			time.sleep(1.5)
			setRGB(255,255,255)
		changemode("normal")
	else:
		onbekendetag(card)
		changemode("normal")
	
	
def modeinfo():
	card = readrfid()
	if card != None:
		digitalWrite(pinbuzzer, 1)
		tag = card.encode('hex')
		print tag
		time.sleep(0.1)
		digitalWrite(pinbuzzer, 0)
		taginfo(tag)
		time.sleep(0.001)
		rfid.flushInput()
	try:
		if (pushcallback() == 1):
			changemode("normal")
	except BaseException as e:
		logging.warning(str(e))
		print(str(e))
	#normal

def taginfo(input):
	card = str(input)
	cur = conn.cursor()
	sql = "SELECT * FROM gebruikers WHERE `tag` = '" + card + "'"
	cur.execute(sql)
	row = cur.fetchone()
	if row is not None:
		bericht = '{:^16}'.format(str(row[1]))
		setText(bericht)
		bericht = '{:^16}'.format("Credits: " + str(row[3]) + " (" + str(row[4]) +")")
		setText_norefresh("\n" + bericht)
		time.sleep(2)
	else:
		onbekendetag(card)
	changemode("normal")
		
# info mode
		
def modeupgrade():
	card = readrfid()
	if card != None:
		digitalWrite(pinbuzzer, 1)
		tag = card.encode('hex')
		print tag
		time.sleep(0.1)
		digitalWrite(pinbuzzer, 0)
		upgrade(tag)
		time.sleep(0.001)
		rfid.flushInput()
	try:
		if (pushcallback() == 1):
			changemode("off")
		if (keycallback() == 0):
			changemode("normal")
	except BaseException as e:
		logging.warning(str(e))
		print(str(e))

def upgrade(input):
	card = str(input)
	cur = conn.cursor()
	sql = "SELECT * FROM gebruikers WHERE `tag` = '" + card + "'"
	cur.execute(sql)
	row = cur.fetchone()
	if row is not None:
		naam = str(row[1])
		bericht = '{:^16}'.format("Upgrade: "+naam)
		setText(bericht)
		credits = str(row[3])
		bericht = '{:^16}'.format("Credits: " + credits)
		setText_norefresh("\n" + bericht)
		time.sleep(1)
		saldo = row[3]+1
		cur = conn.cursor()
		sql = "UPDATE gebruikers SET credits = '"+str(saldo)+"' WHERE tag = '"+card+"'"
		cur.execute(sql)
		conn.commit()
		setRGB(0,255,0)
		bericht = '{:^16}'.format("Credits: " + str(saldo))
		setText_norefresh("\n" + bericht)
		cur = conn.cursor()
		sql = "INSERT INTO `upgradelog` (datumtijd, naam, credits, source) VALUES ('"+strftime("%Y-%m-%d %H:%M")+"','"+naam+"','"+str(saldo)+"','frizzbar')"
		cur.execute(sql)
		conn.commit()
		time.sleep(2)
		setRGB(255,255,255)
		changemode("admin")
	else:
		onbekendetag(card)
		changemode("admin")
		
	#upgrade
		
def readrfid():
  if rfid.inWaiting() == 0:
    return None
  card=rfid.read(6)
  #delay a little in case of bad end transmission
  time.sleep(0.001)
  rfid.flushInput()
  if len(card)!= 5:
   return None
  return card	

def onbekendetag(card):
	setRGB(0,0,255)
	bericht = '{:^16}'.format('Onbekende Tag')
	setText(bericht)
	bericht = '{:^16}'.format(card)
	setText_norefresh("\n" + bericht)
	logging.debug("Onbekende tag: " + card)

def gettemp():
    try:
        [temp,humidity] = grovepi.dht(pintemp,0)
        temperature = str(temp)
		cur = conn.cursor()
		sql = "UPDATE status SET temperatuur = '"+temperature+"'"
		cur.execute(sql)
		conn.commit()
    except IOError:
        temperature = str(0)	

def printtime():
	current_datetime = strftime("%d-%m  %H:%M")
	bericht = '{:^16}'.format(current_datetime + temperature + chr(233) + "C")
	setText_norefresh("\n" + bericht)
	
## TIMED TASKS
def timedon():
	changemode("on")

def timedoff():
	changemode("off")
  
## BUTTON
def pushcallback():
	readingpush = grovepi.digitalRead(pinpushbutton)
	time.sleep(0.2)
	if (readingpush == grovepi.digitalRead(pinpushbutton)):
		return readingpush
	
def keycallback():
	readingkey = grovepi.digitalRead(pinkeyswitch)
	time.sleep(0.1)
	if (readingkey == grovepi.digitalRead(pinkeyswitch)):
		return readingkey

##############################################################################		
# Jobs
schedule.every(1).minutes.do(printtime)
schedule.every(5).minutes.do(gettemp)
schedule.every().friday.at("18:30").do(timedon)
schedule.every().friday.at("23:30").do(timedoff)
schedule.every().saturday.at("07:00").do(timedon)
schedule.every().saturday.at("18:00").do(timedoff)
schedule.every().day.at("00:01").do(timedoff)
# Starting mode
changemode("off")		# Always start offline
gettemp() # Get temp now..
digitalWrite(pinpay, 0)
digitalWrite(pinpower, 0)
##############################################################################
# Running
##############################################################################
while(True):
	try:
		frizzbar()
	except BaseException as e:
		logging.warning(str(e))
	except KeyboardInterrupt, e:
		logging.info("Stopping...")
