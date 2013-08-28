#!/usr/bin/env python
#
# BuildVRFIndex.py
# Copyright (C) 2013 Aaron Melton <aaron(at)aaronmelton(dot)com>
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import argparse		# Required to read arguments from the command line
import base64		# Required to decode password
import ConfigParser # Required for configuration file
import datetime		# Required for date format
import Exscript		# Required for SSH & queue functionality
import re			# Required for REGEX operations
import sys			# Required for printing without newline
import os			# Required to determine OS of host

from argparse					import ArgumentParser, RawDescriptionHelpFormatter
from base64						import b64decode
from ConfigParser				import ConfigParser
from datetime                   import datetime
from Exscript                   import Account, Queue, Host
from Exscript.protocols 		import SSH2
from Exscript.util.file			import get_hosts_from_file
from Exscript.util.decorator    import autologin
from Exscript.util.interact     import read_login
from re							import sub
from sys						import stdout
from os							import name, remove, system


class Application:
# This class was created to provide me with an easy way to update application
# details across all my applications.  Also used to display information when
# application is executed with "--help" argument.
	author = "Aaron Melton <aaron@aaronmelton.com>"
	date = "(2013-08-28)"
	description = "Creates a CSV of VRF Names across multiple Cisco routers"
	name = "BuildVRFIndex.py"
	url = "https://github.com/aaronmelton/BuildVRFIndex"
	version = "v0.0.6-alpha"


@autologin()		# Exscript login decorator; Must precede buildIndex!
def buildIndex(job, host, socket):
# This function builds the index file by connecting to the router and extracting all
# matching sections.  I chose to search for 'crypto keyring' because it is the only
# portion of a VPN config that contains the VRF name AND Peer IP.  Caveat is that
# the program temporarily captures the pre-shared key.  'crypto isakmp profile' was not
# a suitable query due to the possibility of multiple 'match identity address' statements

	stdout.write('.')					# Write period without trailing newline
	socket.execute("terminal length 0")	# Disable user-prompt to page through config
										# Exscript doesn't always recognize Cisco IOS
										# for socket.autoinit() to work correctly

	# Send command to router to capture results
	socket.execute("show running-config | section crypto keyring")

	# Open indexFileTmp to temporarily hold router output
	with open(indexFileTmp, 'a') as outputFile:
		try:
			outputFile.write(socket.response)	# Write contents of running config to output file
		
		# Exception: indexFileTmp could not be opened
		except IOError:
			print
			print "--> An error occurred opening "+indexFileTmp+"."

	socket.send("exit\r")	# Send the "exit" command to log out of router gracefully
	socket.close()			# Close SSH connection
	cleanIndex(indexFileTmp, host)		# Execute function to clean-up the index file
	
def cleanIndex(indexFileTmp, host):
# This function strips all the unnecessary information collected from the router leaving
# only the VRF name, remote Peer IP and local hostname or IP

	try:
		# If the temporary index file can be opened, proceed with clean-up
		with open(indexFileTmp, 'r') as srcIndex:

			try:
				# If the actual index file can be opened, proceed with clean-up
				# Remove unnecessary details from the captured config
				with open(indexFile, 'a') as dstIndex:
					# Use REGEX to step through config and remove everything but
					# the VRF Name, Peer IP & append router hostname/IP to the end
					a = srcIndex.read()
					b = sub(r'show running-config \| section crypto keyring.*', '', a)
					c = sub(r'crypto keyring ', '' ,b)
					d = sub(r'.(\r?\n)..pre-shared-key.address.', ',' ,c)
					e = sub(r'.key.*\r', ','+host.get_name() ,d)
					f = sub(r'.*#', '', e)
					dstIndex.write(f)	# Write cleaned-up output to indexFile

			# Exception: actual index file could not be opened
			except IOError:
				print
				print "--> An error occurred opening "+indexFile+"."

	# Exception: temporary index file could not be opened
	except IOError:
		print
		print "--> An error occurred opening "+indexFileTmp+"."
	
	# Always remove the temporary index file
	finally:
		remove(indexFileTmp)	# Critical to remove temporary file as it contains passwords!

def fileExist(fileName):
# This function checks the parent directory for the presence of a file
# Returns true if found, false if not

	try:
		# If file can be opened, it must exist
		with open(fileName, 'r') as openedFile:
			return True	# File found

	# Exception: file cannot be opened, must not exist
	except IOError:
		return False	# File NOT found
		
def routerLogin():
# This function prompts the user to provide their login credentials and logs into each
# of the routers before calling the buildIndex function to extract relevant portions of
# the router config.  As designed, this function actually has the capability to login to
# multiple routers simultaneously.  I chose to not allow it to multi-thread given possibility
# of undesirable results from multiple threads writing to the same index file simultaneously

	try:# Check for existence of routerFile; If exists, continue with program
		with open(routerFile, 'r'): pass
		
		# Read hosts from specified file & remove duplicate entries, set protocol to SSH2
		hosts = get_hosts_from_file(routerFile,default_protocol='ssh2',remove_duplicates=True)

		if username == '':				# If username is blank
			print
			account = read_login()		# Prompt the user for login credentials

		elif password == '':			# If password is blank
			print
			account = read_login()		# Prompt the user for login credentials

		else:							# Else use username/password from configFile
			account = Account(name=username, password=b64decode(password))
		
		queue = Queue(verbose=0, max_threads=1)	# Minimal message from queue, 1 threads
		queue.add_account(account)				# Use supplied user credentials
		print
		stdout.write("--> Building index...") 	# Print without trailing newline
		queue.run(hosts, buildIndex)			# Create queue using provided hosts
		queue.shutdown()						# End all running threads and close queue
		
	# Exception: router file could not be opened
	except IOError:
		print
		print "--> An error occurred opening "+routerFile+"."


# Check to determine if any arguments may have been presented at the command
# line and generate help message for "--help" switch
parser = ArgumentParser(
    formatter_class=RawDescriptionHelpFormatter,description=(
		Application.name+" "+Application.version+" "+Application.date+"\n"+
		"--\n"+
		"Description: "+Application.description+"\n\n"+
		"Author: "+Application.author+"\n"+
		"URL:    "+Application.url
	))
# Add additional argument to handle any optional configFile passed to application
parser.add_argument("-c", "--config", dest="configFile", help="config file", default="settings.cfg", required=False)
args = parser.parse_args()		# Set 'args' = input from command line
configFile = args.configFile	# Set configFile = config file from command line OR 'settings.cfg'


# Determine OS in use and clear screen of previous output
if name == 'nt':	system("cls")
else:				system("clear")

# PRINT PROGRAM BANNER
print Application.name+" "+Application.version+" "+Application.date
print "-"*(len(Application.name+Application.version+Application.date)+2)

try:
# Try to open configFile
	with open(configFile, 'r'): pass
	
except IOError:
# Except if configFile does not exist, create an example configFile to work from
	try:
		with open (configFile, 'w') as exampleFile:
			print
			print "--> Config file not found; Creating "+configFile+"."
			exampleFile.write("## BuildVRFIndex.py CONFIGURATION FILE ##\n#\n")
			exampleFile.write("[account]\n#password is base64 encoded! Plain text passwords WILL NOT WORK!\n#Use website such as http://www.base64encode.org/ to encode your password\nusername=\npassword=\n#\n")
			exampleFile.write("[BuildVRFIndex]\n#Check your paths! Files will be created; Directories will not.\n#Bad directories may result in errors!\n#variable=C:\path\\to\\filename.ext\nrouterFile=routers.txt\nindexFile=index.txt\nindexFileTmp=index.txt.tmp\n")

	# Exception: file could not be created
	except IOError:
		print
		print "--> An error occurred creating the example "+configFile+"."

finally:
# Finally, using the provided configFile (or example created), pull values
# from the config and login to the router(s)
	config = ConfigParser(allow_no_value=True)
	config.read(configFile)
	username = config.get('account', 'username')
	password = config.get('account', 'password')
	routerFile = config.get('BuildVRFIndex', 'routerFile')
	indexFile = config.get('BuildVRFIndex', 'indexFile')
	indexFileTmp = config.get('BuildVRFIndex', 'indexFileTmp')
	
	if fileExist(routerFile):
	# If the routerFile exists, proceed to login to routers
		if fileExist(indexFile):	# If indexFile exists
			remove(indexFile)		# Remove existing indexFile
		routerLogin()				# Log into router(s)	

	else: # if fileExist(routerFile):
	# Else if routerFile does not exist, create an example file and exit
		try:
			with open (routerFile, 'w') as exampleFile:
				print
				print "--> Router file not found; Creating "+routerFile+"."
				print "    Edit this file and restart the application."
				exampleFile.write("## BuildVRFIndex.py ROUTER FILE ##\n#\n")
				exampleFile.write("#Enter a list of hostnames or IP Addresses, one per line.\n#For example:\n")
				exampleFile.write("192.168.1.1\n192.168.1.2\nRouterA\nRouterB\nRouterC\netc...")

		# Exception: file could not be created
		except IOError:
			print
			print "--> Required file "+routerFile+" not found; An error has occurred creating "+routerFile+"."
			print "This file must contain a list, one per line, of Hostnames or IP addresses the"
			print "application will then connect to download the running-config."
