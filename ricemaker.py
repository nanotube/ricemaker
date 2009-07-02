#!/usr/bin/python
#################################################
##
## RiceMaker: Automate the gameplay on freerice.com
## Copyright (C) 2007  Daniel Folkinshteyn <dfolkins@temple.edu>
##
## http://smokyflavor.wikispaces.com/RiceMaker
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License
## as published by the Free Software Foundation; either version 3
## of the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
#################################################

#################################################
# requires python (http://www.python.org)
# requires BeautifulSoup module (http://www.crummy.com/software/BeautifulSoup/)
# run with command:
#               python ricemaker.py
#################################################
# ricemaker.py
#               Script to automatically generate rice on freerice.com
#
# Author:       Daniel Folkinshteyn <dfolkins@temple.edu>
# 
# Version:      ricemaker.py  0.2.1  18-Nov-2007  dfolkins@temple.edu
#
# Project home (where to get the freshest version): 
#               http://smokyflavor.wikispaces.com/RiceMaker
#
#################################################

import urllib, urllib2
from BeautifulSoup import BeautifulSoup
import optparse
import subprocess
import re
import os.path
import random
import time
import traceback
import pickle

class VersionInfo:
	'''Version information storage
	'''
	def __init__(self):
		self.name = "RiceMaker"
		self.version = "0.2.1"
		self.description = "Script to automatically generate rice on freerice.com"
		self.url = "http://smokyflavor.wikispaces.com/RiceMaker"
		self.license = "GPL"
		self.author = "Daniel Folkinshteyn"
		self.author_email = "dfolkins@temple.edu"
		self.platform = "Any"

class RiceMaker:

	def __init__(self, url):
		self.version = VersionInfo()
		self.options=None
		self.ParseOptions()
		
		self.url = url
		response = urllib2.urlopen(self.url)
		result = response.read()
		self.soup = BeautifulSoup(result)
		
		if os.path.lexists(self.options.freericedictfilename) and os.path.getsize(self.options.freericedictfilename) > 0:
			try:
				f = open(self.options.freericedictfilename, 'rb')
				self.ricewordlist = pickle.load(f)
				f.close()
				print "dict read successful"
			except:
				print "bad dict"
				traceback.print_exc()
				self.ricewordlist = {}
		else:
			self.ricewordlist = {}

	def ParseOptions(self):
		'''Read command line options
		'''
		parser = optparse.OptionParser(
						version=self.version.name.capitalize() + " version " +self.version.version + "\nProject homepage: " + self.version.url, 
						description="RiceMaker will automatically play the vocabulary game on freerice.com to generate rice donations. For a more detailed usage manual, see the project homepage: " + self.version.url, 
						formatter=optparse.TitledHelpFormatter(),
						usage="python %prog [options]")
		parser.add_option("-d", "--debug", action="store_true", dest="debug", help="Debug mode (print some extra debug output). [default: %default]")
		parser.add_option("-w", "--wordnetpath", action="store", dest="wordnetpath", help="Full path to the WordNet commandline executable, if installed. On Linux, something like '/usr/bin/wn'; on Windows, something like 'C:\Program Files\WordNet\wn.exe'. [default: %default]")
		parser.add_option("-l", "--sleeplowsec", action="store", type="float", dest="sleeplowsec", help="Lower bound on the random number of seconds to sleep between iterations. [default: %default]")
		parser.add_option("-m", "--sleephighsec", action="store", type="float", dest="sleephighsec", help="Upper bound on the random number of seconds to sleep between iterations. [default: %default]")
		parser.add_option("-f", "--freericedictfilename", action="store", dest="freericedictfilename", help="Filename for internally generated dictionary. You may specify a full path here, otherwise it will just get written to the same directory where this script resides (default behavior). No need to change this unless you really feel like it. [default: %default]")
		parser.add_option("-i", "--iterationsbetweendumps", action="store", type="int", dest="iterationsbetweendumps", help="Number of iterations between dictionary dumps to file. More often than 5 minutes is really unnecessary (Time between dumps is iterationsbetweendumps * avgsleeptime = time between dumps.) [default: %default]")
		
		parser.set_defaults(debug=False, 
							wordnetpath="/usr/bin/wn", 
							sleeplowsec=1,
							sleephighsec=5,
							freericedictfilename="freericewordlist.txt",
							iterationsbetweendumps=100)
		
		(self.options, args) = parser.parse_args()
		if self.options.debug:
			print "Your commandline options:\n", self.options

	def __del__(self):
		if self.options != None: #when running with -h option, optparse exits before doing anything, including initializing options...
			f = open(self.options.freericedictfilename, 'wb')
			pickle.dump(self.ricewordlist, f, -1)
			f.close()
			print 'dump successful'
		
	def dbDump(self):
		try:
			f = open(self.options.freericedictfilename, 'wb')
			pickle.dump(self.ricewordlist, f, -1)
			f.close()
			print 'dump successful'
		except:
			print 'bad dump'
			traceback.print_exc()
			pass # keep going, what else can we do?
			
	def start(self):
		i = 0
		while 1:
			i = i+1
			print "*************************"
			if i % self.options.iterationsbetweendumps == 0:
				self.dbDump()
			
			time.sleep(random.uniform(self.options.sleeplowsec,self.options.sleephighsec)) # let's wait - to not hammer the server, and to not appear too much like a bot
			
			try: #to catch all exceptions and ignore them
				mydiv = self.soup.findAll(attrs={'class':'wordSelection'})
				myol = mydiv[0].ol
				targetword = str(myol.li.strong.string)
				print 'iteration', i
				print "targetword:",targetword
				
				itemlist = myol.findAll('li')
				self.wordlist={}
				for li in itemlist[1:5]:
					## format: 'word' = ' 1 '
					self.wordlist[str(li.a.string)] = str(li.noscript.input['value'])
					#wordlist.append(li.a.string)
					
				self.match = self.lookupWord(targetword,self.wordlist)
				self.postdict = {'PAST':'','INFO':'','INFO2':''}
				for key in self.postdict.keys():
					self.postdict[key] = self.soup.form.find("input",{'name':key})['value']
				self.postdict['SELECTED'] = self.wordlist[self.match]
				
				#print self.postdict

				response = urllib2.urlopen(self.url, data=urllib.urlencode(self.postdict))
				result = response.read()
				self.soup = BeautifulSoup(result)
				print self.soup.findAll(id='donatedAmount')[0]
				print self.soup.findAll(attrs={'class':'vocabLevel'})[0]
				
				#if targetword not in self.ricewordlist.keys():
				self.createDict(targetword,self.wordlist)
			
			except KeyboardInterrupt:
				raise
			except:
				print "Exception in main loop!"
				traceback.print_exc()
				print "##########################"
				print self.soup
				print "##########################"
				response = urllib2.urlopen(self.url, data=urllib.urlencode(self.postdict))
				result = response.read()
				self.soup = BeautifulSoup(result)
				# just keep going, don't care...
				pass
	
	def createDict(self, targetword, wordlist):
		'''find if our new soup says our previous match was correct
		if so, add to dict, if not, parse their answer and add that to dict
		dict format: target: match'''
		
		answer = self.soup.findAll(id='correct')
		if len(answer) != 0:
			target, match = targetword, self.match
		else:
			answer = self.soup.findAll(id='incorrect')[0].string
			target, match = answer.split(' = ')
		
		self.ricewordlist[str(target)] = str(match)
		#print self.ricewordlist
	
	def lookupWord(self, targetword, wordlist):
		print wordlist
		
		try:
			return self.lookupInMyDict(targetword,wordlist)
		except KeyboardInterrupt:
			raise
		except:
			print "Exception in lookupWord"
			traceback.print_exc()
			return wordlist.keys()[random.randint(0,3)]
	
	def lookupInMyDict(self, targetword, wordlist):
		try:
			answer = self.ricewordlist[targetword]
			print "internal dict match found!!!", answer
			return answer
		except KeyError: #not in our dict
			print "no internal dict match found, trying wordnet"
			return self.lookupInWordnet(targetword, wordlist)
	
	def lookupInWordnet(self, targetword, wordlist):
		if os.path.lexists(self.options.wordnetpath):
			executionstring = "wn '" + targetword + "' -synsn -synsv -synsa -synsr -hypen -hypev -hypon -hypov"
			p = subprocess.Popen(executionstring, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
			returncode = p.wait()
			result = p.stdout.read()
			#print "wnresult:", result
			
			for word in wordlist.keys():
				if re.search(word, result):
					print "wn match found!", word
					return word
			else:
				print "no wn match found, looking in dict.org"
				return self.lookupInDictorg(targetword, wordlist)
		else:
			return self.lookupInDictorg(targetword, wordlist)
	
	def lookupInDictorg(self, targetword, wordlist):
		response = urllib2.urlopen('http://www.dict.org/bin/Dict', data=urllib.urlencode({'Query':targetword, 'Form':'Dict1', 'Strategy':'*', 'Database':'*'}))
		result = response.read()
		for word in wordlist.keys():
			if re.search(word, result):
				print "dict.org match found!", word
				return word
		else:
			print "no dict.org match found, returning random."
			return wordlist.keys()[random.randint(0,3)]

		
if __name__ == '__main__':
	rm = RiceMaker(url='http://www.freerice.com/index.php')
	rm.start()