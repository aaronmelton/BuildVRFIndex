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


import base64		# Required to decode password
import ConfigParser # Required for configuration file
import Exscript		# Required for SSH, queue & logging functionality
import os			# Required to determine OS of host
import re			# Required for REGEX operations

from Exscript                   import Account, Queue, Host
from Exscript.protocols 		import SSH2
from Exscript.util.file			import get_hosts_from_file
from Exscript.util.log          import log_to
from Exscript.util.decorator    import autologin
from Exscript.util.interact     import read_login
from Exscript.util.report		import status,summarize

def fileExist(fileName):
# This function checks the parent directory for the presence of a file
# Returns true if found, false if not

	try:
		# If file can be opened, it must exist
		with open(fileName, 'r') as openedFile:
			return 1	# File found

	# Exception: file cannot be opened, must not exist
	except IOError:
		return 0		# File NOT found

@autologin()		# Exscript login decorator; Must precede buildIndex!
def buildIndex(job, host, socket):
# This function builds the index file by connecting to the router and extracting all
# matching sections.  I chose to search for 'crypto keyring' because it is the only
# portion of a VPN config that contains the VRF name AND Peer IP.  Caveat is that
# the program temporarily captures the pre-shared key.  'crypto isakmp profile' was not
# a suitable query due to the possibility of multiple 'match identity address' statements

	print("Building index...")		# Let the user know the program is working dot dot dot
	socket.execute("terminal length 0")	# Disable user-prompt to page through config
										# Exscript doesn't always recognize Cisco IOS
										# for socket.autoinit() to work correctly

	# Send command to router to capture results
	socket.execute("show running-config | section crypto keyring")

	outputFile = open(indexFileTmp, 'a')	# Open output file (will overwrite contents)

	outputFile.write(socket.response)	# Write contents of running config to output file
	outputFile.close()					# Close output file
	socket.send("exit\r")				# Send the "exit" command to log out of router gracefully
	socket.close()						# Close SSH connection

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
					b = re.sub(r'show running-config \| section crypto keyring.*', '', a)
					c = re.sub(r'crypto keyring ', '' ,b)
					d = re.sub(r'.(\r?\n)..pre-shared-key.address.', ',' ,c)
					e = re.sub(r'.key.*\r', ','+host.get_name() ,d)
					f = re.sub(r'.*#', '', e)
					dstIndex.write(f)

			# Exception: actual index file was not able to be opened
			except IOError:
				print "\nAn error occurred opening the index file.\n"

	# Exception: temporary index file was not able to be opened
	except IOError:
		print "\nAn error occurred opening the temporary index file.\n"
	
	# Always remove the temporary index file
	finally:
		os.remove(indexFileTmp)	# Critical to remove temporary file as it contains passwords!
			
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
			account = read_login()		# Prompt the user for login credentials
		elif password == '':			# If password is blank
			account = read_login()		# Prompt the user for login credentials
		else:							# Else use username/password from configFile
			account = Account(name=username, password=base64.b64decode(password))
			
		queue = Queue(verbose=0, max_threads=1)	# Minimal message from queue, 1 threads
		queue.add_account(account)				# Use supplied user credentials
		queue.run(hosts, buildIndex)			# Create queue using provided hosts
		queue.shutdown()						# End all running threads and close queue
		
		#print status(Logger())	# Print current % status of operation to screen
								# Status not useful unless # threads > 1

	# Exception: router file was not able to be opened
	except IOError:
		print "\nAn error occurred opening the router file.\n"


# Change the filenames of these variables to suit your needs
configFile='settings.cfg'

# Determine OS in use and clear screen of previous output
os.system('cls' if os.name=='nt' else 'clear')

print "Build VRF Index v0.0.1-alpha"
print "----------------------------"

try:
# Try to open configFile
	file = open(configFile, 'r')
	
except IOError:
# Except if configFile does not exist, create an example configFile to work from
	try:
		with open (configFile, 'w') as exampleFile:
			exampleFile.write("[files]\n#variable='C:\path\\to\\filename.ext'\nrouterFile='routers.txt'\nindexFile='index.txt'\nindexFileTmp='index.txt.tmp'")
			exampleFile.write("\n\n[account]\n#password is base64 encoded! Plain text passwords WILL NOT WORK!\n#Use website such as http://www.base64encode.org/ to encode your password\nusername=''\npassword=''\n")
	except IOError:
		print "\nAn error occurred creating the example "+configFile+".\n"

finally:
# Finally, using the provided configFile (or example created), pull values
# from the config and login to the router(s)
	config = ConfigParser.ConfigParser(allow_no_value=True)
	config.read(configFile)
	routerFile = config.get('files', 'routerFile')
	indexFile = config.get('files', 'indexFile')
	indexFileTmp = config.get('files', 'indexFileTmp')
	username = config.get('account', 'username')
	password = config.get('account', 'password')
	
	if fileExist(routerFile):
	# If the routerFile exists, proceed to login to routers
		if fileExist(indexFile):	# If indexFile exists
			os.remove(indexFile)	# Remove existing indexFile
		routerLogin()
		print "Done."
	else: # if fileExist(routerFile):
	# Else if routerFile does not exist, create an example file and exit
		try:
			with open (routerFile, 'w') as exampleFile:
				exampleFile.write("192.168.1.1\n192.168.1.2\nRouterA\nRouterB\nRouterC\netc...")
				print
				print "Required file "+routerFile+" not found; One has been created for you."
				print "This file must contain a list, one per line, of Hostnames or IP addresses the"
				print "application will then connect to download the running-config."
				print
		except IOError:
			print
			print "Required file "+routerFile+" not found."
			print "This file must contain a list, one per line, of Hostnames or IP addresses the"
			print "application will then connect to download the running-config."
			print
