#!/usr/bin/python
#
#	Frizzbar
#	Programma om de Frizzbar draaiend te houden
#	Versie: 0.0.2
#	
#
print("Start Frizzbar Script")

from time import strftime,sleep

from grove_rgb_lcd import *
try:
	setRGB(255,255,255)
	bericht = '{:^16}'.format("Frizzbar Starten")
	setText(bericht)
except BaseException as e:
	print(str(e))


import socket 
  
# Function to display hostname and 
# IP address 
def get_Host_name_IP(): 
	try: 
		host_name = socket.gethostname() 
		host_ip = socket.gethostbyname(host_name) 
		setRGB(255,255,255)
		bericht = '{:^16}'.format(host_name)
		setText(bericht)
		bericht = '{:^16}'.format(host_ip)
		setText_norefresh("\n" + bericht)
		time.sleep(3)
	except: 
		print("Unable to get Hostname and IP") 
	changemode(4)


import configparser	# required to handle all configurations
config = configparser.ConfigParser()
config.read('/home/pi/config.ini')

import logging	# logging functions
import logging.handlers
logfile = config.get('main', 'logfile')
FORMAT = "%(asctime)s - %(message)s"  
logging.basicConfig(filename="/home/pi/frizzbar.log",level=logging.WARNING,format=FORMAT)
logging.warning("Frizzbar Script Gestart")

import sqlite3	# open database connection
database_file = config.get('main', 'database')
conn = sqlite3.connect('/home/pi/frizzbar.db')

# Frizzbar Schedule System
import schedule


# Serial rfidreader Subsystem
import serial  # open serial rfid reader
rfid = serial.Serial('/dev/ttyAMA0',9600,timeout=0.010)
sleep(0.001)
rfid.reset_input_buffer()

def readrfid():
	try:
		if rfid.inWaiting() == 0:
			return None
		card=rfid.read(6)
		#delay a little in case of bad end transmission
		sleep(0.001)
		rfid.flushInput()
		if len(card)!= 5:
			return None
		tag = card.encode('hex')
		print(str(tag))
		if (tag != "0000000000" and tag != "c00c000000" and tag != "c0000000c0" and tag != "f00000000f" and tag != "cc00000000" and tag != "f000f0f0ff" and tag != "ffc0000c00" and tag != "c000c00000" and tag != "300028b578"):
			digitalWrite(pinbuzzer, 1)
			time.sleep(0.1)
			digitalWrite(pinbuzzer, 0)
			rfid.flushInput()
			return card
		return None
	except BaseException as e:
		logging.warning(str(e))
		return None     

# GrovePi Subsystem
import grovepi  # open grovepi pins
from grovepi import digitalWrite, analogWrite
pinpushbutton = int(config.get('pins', 'pushbutton'))
grovepi.pinMode(pinpushbutton,"INPUT")
pinkeyswitch = int(config.get('pins', 'keyswitch'))
grovepi.pinMode(pinkeyswitch,"INPUT")
pinbuzzer = int(config.get('pins', 'buzzer'))
grovepi.pinMode(pinbuzzer,"OUTPUT")
pinpower = int(config.get('pins', 'power'))
grovepi.pinMode(pinpower,"OUTPUT")
pinpay = int(config.get('pins', 'pay'))
grovepi.pinMode(pinpay,"OUTPUT")
pintemp = int(config.get('pins', 'temp'))

def tone(freq,timer):
	analogWrite(pinbuzzer, freq)
	time.sleep(timer)
	analogWrite(pinbuzzer, 0)

digitalWrite(pinpay, 0) # we don't want free cans
digitalWrite(pinpower, 0) # we don't want to turn on the fridge yet

tone(150, 0.1)
time.sleep(0.1)
tone(125, 0.1)
time.sleep(0.1)
tone(150, 0.1)
time.sleep(0.1)
tone(125, 0.1)
time.sleep(0.1)
tone(150, 0.1)

# Temperature Subsystem
global temperature
temperature = 0 # DHT temp sensor
def gettemp():
	temperature = str(0)
	try:
		[temp,humidity] = grovepi.dht(pintemp,0)
		temperature = str(temp)
		cur = conn.cursor()
		sql = "UPDATE status SET temperatuur = '"+temperature+"'"
		cur.execute(sql)
		conn.commit()
		print("Temperatuur")
		print temperature
	except IOError:
		temperature = str(0)
		print("Temperatuur faalt")
schedule.every(5).minutes.do(gettemp)
# Frizzbar Status System
global status
status = 0 # Frizzbar On or OFF:  0 = OFF; 1 = ON
global mode
mode = 1 # Frizzbar Running Mode: 1 = Normal; 2 = Info; 3 = Upgrade

    

# Print time functions
def printtime():
	current_datetime = strftime("%d-%m-%y  %H:%M")
	bericht = '{:^16}'.format(current_datetime)
	setText_norefresh("\n" + bericht)
	print(bericht)
	
schedule.every(1).minutes.do(printtime)

##############################################################################
# Inputs (pushbutton and key)
##############################################################################
def pushcallback():
	readingpush = grovepi.digitalRead(pinpushbutton)
	timepush = time.time()
	time.sleep(0.1)
	if (readingpush != grovepi.digitalRead(pinpushbutton)):
		return None
	else:
		if (readingpush == 0):
			return 0
		while (readingpush == grovepi.digitalRead(pinpushbutton)):
			time.sleep(0.05)
			endtime = time.time() - timepush
			if (endtime > 1):
				tone(150, 0.1)
				print("langdurige druk")
				print endtime
				time.sleep(0.2)
				return endtime
			if (grovepi.digitalRead(pinpushbutton) == 0):
				newtime = time.time() - timepush
				print("korte druk")
				print newtime
				return newtime
def keycallback():
	readingkey = grovepi.digitalRead(pinkeyswitch)
	sleep(0.05)
	if (readingkey == grovepi.digitalRead(pinkeyswitch)):
		return readingkey
##############################################################################
##############################################################################   
# Turn our Frizzbar on or off
##############################################################################
def turnon():
	logging.warning("Frizzbar gaat online.")
	rfid.flushInput()
	tone(150, 0.2)
	print("Frizzbar online")
	setRGB(255,255,255)
	bericht = '{:^16}'.format("Frizzbar")
	setText(bericht)
	bericht = '{:^16}'.format("Opstarten")
	setText_norefresh("\n" + bericht)
	digitalWrite(pinpower, 1)
	global status
	status = 1
	global mode
	mode = 1
	sleep(1)
	bericht = '{:^16}'.format("Frizzbar")
	setText(bericht)
	cur = conn.cursor()
	sql = "UPDATE status SET status = '1'"
	cur.execute(sql)
	sql = "UPDATE status SET remote = '1'"
	cur.execute(sql)
	conn.commit()
	tone(150, 0.2)
	time.sleep(0.1)
	tone(150, 0.2)
	printtime()
def turnoff():
	print("Frizzbar offline")
	logging.warning("Frizzbar gaat offline")
	setRGB(255,255,255)
	bericht = '{:^16}'.format("Frizzbar")
	setText(bericht)
	bericht = '{:^16}'.format("Afsluiten")
	setText_norefresh("\n" + bericht)
	digitalWrite(pinpower, 1)
	global status
	status = 0
	global mode
	mode = 1
	sleep(1)
	bericht = '{:#^16}'.format(" Offline ")
	setText(bericht)
	cur = conn.cursor()
	sql = "UPDATE status SET status = '0'"
	cur.execute(sql)
	sql = "UPDATE status SET remote = '0'"
	cur.execute(sql)
	conn.commit()
	tone(25, 0.5)
	printtime()
	bericht = '{:#^16}'.format(" Offline ")
	setText_norefresh(bericht)
##############################################################################
# Running mode and how to change mode
##############################################################################
def runmode(rm):
	card = readrfid()
	if (rm == 1): # normal mode
		if (pushcallback() > 1):
			changemode(2)
		if (keycallback() == 1):
			changemode(3)
		if card != None:
			vend(card)
	if (rm == 2): # info mode
		if (pushcallback() > 0):
			changemode(1)
		if (keycallback() == 1):
			changemode(3)
		if card != None:
			info(card)
	if (rm == 3): # admin mode
		pushed = pushcallback()
		if (pushed > 0.01 and pushed < 1):
			changemode(4)
			time.sleep(0.5)			
		if (pushed > 1):
			turnoff()
		if (keycallback() == 0):
			changemode(1)
		if card != None:
			upgrade(card)
	if (rm == 4): # show ip
		pushed = pushcallback()
		if (keycallback() == 0):
			changemode(1)
		if (pushed > 0.01 and pushed < 1):
			changemode(5)
			time.sleep(0.5)
		if (pushed > 1):
			print("Show magic")
			get_Host_name_IP()
	if (rm == 5): # Reboot
		pushed = pushcallback()
		if (keycallback() == 0):
			changemode(1)
		if (pushed > 0.01 and pushed < 1):
			changemode(6)
			time.sleep(0.5)
		if (pushed > 1):
			print("reboot")
			logging.warning("Reboot the Raspberry Pi")
			bericht = '{:^16}'.format("Hold on..")
			setText(bericht)
			bericht = '{:^16}'.format("Reboot now!")
			setText_norefresh("\n" + bericht)
			time.sleep(1)
			setRGB(0,0,0)
			setText("")
			print("Reboot the Raspberry Pi")
			command = "/usr/bin/sudo /sbin/shutdown -r now"
			import subprocess
			process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
			output = process.communicate()[0]
			print output
	if (rm == 6): # GoTo Free
		pushed = pushcallback()
		if (keycallback() == 0):
			changemode(1)
		if (pushed > 0.01 and pushed < 1):
			changemode(3)
			time.sleep(0.5)  
		if (pushed > 1):
			changemode(7)
	if (rm == 7): # FREE MODE
		pushed = pushcallback()
		if (keycallback() == 0):
			digitalWrite(pinpay, 0)
			changemode(1)
		if (pushed > 0.01 and pushed < 1):
			digitalWrite(pinpay, 0)
			changemode(1)
		if (pushed > 1):
			digitalWrite(pinpay, 0)
			changemode(1)
			time.sleep(0.5)			   
def changemode(setmode):
	setRGB(255,255,255)
	global mode
	logging.warning("Mode: "+str(setmode))
	if (setmode == 1): # normal mode
		mode = 1
		bericht = '{:*^16}'.format("Frizzbar")
		setText(bericht)
		printtime()
	if (setmode == 2):  # info mode
		mode = 2
		bericht = '{:*^16}'.format("Informatie")
		setText(bericht)
		bericht = '{:^16}'.format("Geef uw tag..")
		setText_norefresh("\n" + bericht)
	if (setmode == 3):  # admin mode
		mode = 3
		bericht = '{:*^16}'.format("Opwaarderen")
		setText(bericht)
		bericht = '{:^16}'.format("Geef uw tag..")
		setText_norefresh("\n" + bericht)
	if (setmode == 4):  # admin secret mode
		mode = 4
		bericht = '{:*^16}'.format("ADMIN")
		setText(bericht)
		bericht = '{:<16}'.format("1. Show IP")
		setText_norefresh("\n" + bericht)
	if (setmode == 5):  # admin secret mode
		mode = 5
		bericht = '{:*^16}'.format("ADMIN")
		setText(bericht)
		bericht = '{:<16}'.format("2. Reboot Pi")
		setText_norefresh("\n" + bericht) 
	if (setmode == 6):  # admin secret mode
		mode = 6
		bericht = '{:*^16}'.format("ADMIN")
		setText(bericht)
		bericht = '{:<16}'.format("3. Pay Free")
		setText_norefresh("\n" + bericht)		
	if (setmode == 7):  # admin secret mode
		mode = 7
		bericht = '{:*^16}'.format("FREE DRINKS!")
		setText(bericht)
		digitalWrite(pinpay, 1)
##############################################################################
#   Remote Control
##############################################################################
def checkremote():
	cur = conn.cursor()
	sql = "SELECT * FROM status"
	cur.execute(sql)
	row = cur.fetchone()
	if (row[1] != row[0]):
		if (row[1] == 0):
			logging.warning("Programma uit remote")
			turnoff()
			time.sleep(0.5)
		if (row[1] == 1):
			logging.warning("Programma aan remote")
			turnon()
			time.sleep(0.5)
##############################################################################
# Frizzbar Functions: vend, info, upgrade
##############################################################################
def vend(input):
	print("Vend")
	tag = input.encode('hex')
	code = str(tag)
	cur = conn.cursor()
	sql = "SELECT * FROM gebruikers WHERE `tag` = '" + code + "'"
	cur.execute(sql)
	row = cur.fetchone()
	if row is not None:
		naam = str(row[1])
		bericht = '{:^16}'.format(str(row[1]))
		setText(bericht)
		bericht = '{:^16}'.format("Saldo: " + str(row[3]) + " (" + str(row[4]) +")")
		setText_norefresh("\n" + bericht)
		if (row[3] < 1):
			setRGB(255,0,0)
			bericht = '{:^16}'.format("Geen saldo")
			setText_norefresh("\n" + bericht)
			tone(50, 0.3)
			time.sleep(0.1)
			tone(50, 0.3)
			sleep(1.4)
		else:
			setRGB(0,255,0)
			saldo = row[3]-1
			consumpties = row[4]+1
			tone(150, 0.1)
			time.sleep(0.1)
			tone(150, 0.1)
			cur = conn.cursor()
			sql = "UPDATE gebruikers SET credits = '"+str(saldo)+"' , consumpties = '"+str(consumpties)+"' WHERE tag = '"+code+"'"
			cur.execute(sql)
			conn.commit()
			digitalWrite(pinpay, 1)
			bericht = '{:^16}'.format("Saldo: " + str(saldo) + " (" + str(consumpties) +")")
			setText_norefresh("\n" + bericht)
			sleep(0.5)
			digitalWrite(pinpay, 0)
			cur = conn.cursor()
			sql = "INSERT INTO `gebruikslog` (datumtijd, naam, credits) VALUES ('"+strftime("%Y-%m-%d %H:%M")+"','"+naam+"','"+str(saldo)+"')"
			cur.execute(sql)
			conn.commit()
			sleep(1)
			logging.warning("Succes: "+naam+" - "+str(saldo))
	else:
		setRGB(0,0,255)
		bericht = '{:^16}'.format('Onbekende Tag')
		setText(bericht)
		bericht = '{:^16}'.format(code)
		setText_norefresh("\n" + bericht)
		tone(50, 0.1)
		time.sleep(0.1)
		tone(50, 0.3)
		sleep(0.5)
	rfid.flushInput()
	changemode(1)
def info(input):
	print("Info")
	tag = input.encode('hex')
	code = str(tag)
	cur = conn.cursor()
	sql = "SELECT * FROM gebruikers WHERE `tag` = '" + code + "'"
	cur.execute(sql)
	row = cur.fetchone()
	if row is not None:
		naam = str(row[1])
		bericht = '{:^16}'.format(str(row[1]))
		setText(bericht)
		bericht = '{:^16}'.format("Saldo: " + str(row[3]) + " (" + str(row[4]) +")")
		setText_norefresh("\n" + bericht)
		sleep(2)
	else:
		setRGB(0,0,255)
		bericht = '{:^16}'.format('Onbekende Tag')
		setText(bericht)
		bericht = '{:^16}'.format(code)
		setText_norefresh("\n" + bericht)
		tone(50, 0.1)
		time.sleep(0.1)
		tone(50, 0.3)
		sleep(0.5)
	rfid.flushInput()
	changemode(1)
def upgrade(input):
	print("Upgrade")
	tag = input.encode('hex')
	code = str(tag)
	cur = conn.cursor()
	sql = "SELECT * FROM gebruikers WHERE `tag` = '" + code + "'"
	cur.execute(sql)
	row = cur.fetchone()
	if row is not None:
		naam = str(row[1])
		credits = str(row[3])
		bericht = '{:^16}'.format("Upgrade: "+naam)
		setText(bericht)
		bericht = '{:^16}'.format("Saldo: " + credits)
		setText_norefresh("\n" + bericht)
		sleep(0.5)
		setRGB(0,255,0)
		saldo = row[3]+11
		cur = conn.cursor()
		sql = "UPDATE gebruikers SET credits = '"+str(saldo)+"' WHERE tag = '"+code+"'"
		cur.execute(sql)
		conn.commit()
		bericht = '{:^16}'.format("Saldo: " + str(saldo))
		setText_norefresh("\n" + bericht)
		cur = conn.cursor()
		sql = "INSERT INTO `upgradelog` (datumtijd, naam, credits, source) VALUES ('"+strftime("%Y-%m-%d %H:%M")+"','"+naam+"','"+str(saldo)+"','frizzbar')"
		cur.execute(sql)
		conn.commit()
		logging.warning("Succes: "+naam+" - "+str(saldo))
		sleep(1.5)
	else:
		setRGB(0,0,255)
		bericht = '{:^16}'.format('Admin:')
		setText(bericht)
		bericht = '{:^16}'.format(code)
		setText_norefresh("\n" + bericht)
		tone(50, 0.1)
		time.sleep(0.1)
		tone(50, 0.3)
		cur = conn.cursor()
		sql = "INSERT INTO `nieuwetags` (tag) VALUES ('"+code+"')"
		cur.execute(sql)
		conn.commit()
		sleep(1)
	rfid.flushInput()
	changemode(1)
##############################################################################
# Running
##############################################################################
def offline():
	schedule.run_pending()
	if (pushcallback() > 1):
		turnon()
##############################################################################	 
def online():
	if (mode == 1):
		schedule.run_pending()
		runmode(1) # normal vending mode
	if (mode == 2):
		runmode(2) # info mode
	if (mode == 3):
		runmode(3) # upgrade mode
	if (mode == 4):
		runmode(4) # admin mode show ip
	if (mode == 5):
		runmode(5) # admin reboot pi
	if (mode == 6):
		runmode(6) # admin extra
	if (mode == 7):
		runmode(7) # FREEEEEEEEEEE
		schedule.run_pending()
##############################################################################
def frizzbar():
	if (status == 0): #off
		offline()
	if (status == 1): #on
		online()
##############################################################################
schedule.every(10).seconds.do(checkremote)
schedule.every().friday.at("18:30").do(turnon)
schedule.every().saturday.at("07:00").do(turnon)
schedule.every().day.at("00:00").do(turnoff)
##############################################################################
print("Running Frizzbar Programme")
bericht = '{:#^16}'.format(" Offline ")
setText(bericht)
printtime()
cur = conn.cursor()
sql = "UPDATE status SET status = '0'"
cur.execute(sql)
sql = "UPDATE status SET remote = '0'"
cur.execute(sql)
conn.commit()
try:
	while(True):
		try:
			frizzbar()
		except BaseException as e:
			print(e)
			logging.warning(e)
except KeyboardInterrupt:
	exit()
##############################################################################
