#!/usr/bin/python
#######
# requires python (http://www.python.org)
# requires BeautifulSoup module (http://www.crummy.com/software/BeautifulSoup/)
# run with command:
#               python ricemaker.py
#######
# ricemaker.py
#               Script to automatically generate rice on freerice.com
#
# Author:       Daniel Folkinshteyn <dfolkins@temple.edu>
# 
# Version:      ricemaker.py  0.1.2  13-Nov-2007  dfolkins@temple.edu
#
# Project home (where to get the freshest version): 
#               http://smokyflavor.wikispaces.com/RiceMaker
#
#######

import urllib, urllib2
from BeautifulSoup import BeautifulSoup
import subprocess
import re
import os.path
import random
import time
import traceback
import pickle
	
class RiceMaker:

	def __init__(self, url):
		
		self.url = url
		response = urllib2.urlopen(self.url)
		result = response.read()
		self.soup = BeautifulSoup(result)
		
		if os.path.lexists('freericewordlist.txt') and os.path.getsize('freericewordlist.txt') > 0:
			try:
				f = open('freericewordlist.txt', 'rb')
				self.ricewordlist = pickle.load(f)
				f.close()
				print "dict read successful"
			except:
				print "bad dict"
				traceback.print_exc()
				self.ricewordlist = {}
		else:
			self.ricewordlist = {}
		
	def __del__(self):
		f = open('freericewordlist.txt', 'wb')
		pickle.dump(self.ricewordlist, f, -1)
		f.close()
		print 'dump successful'
		
	def dbDump(self):
		try:
			f = open('freericewordlist.txt', 'wb')
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
			if i % 10 == 0:
				self.dbDump()
			
			time.sleep(random.randint(1,5)) # let's wait - to not hammer the server, and to not appear too much like a bot
			
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
		if os.path.lexists('/usr/bin/wn'):
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