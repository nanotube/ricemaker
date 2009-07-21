#!/usr/bin/python
#################################################
##
## RiceMaker: Automate the gameplay on freerice.com
## Copyright (C) 2008  Daniel Folkinshteyn <dfolkins@temple.edu>
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
# Author:       Daniel Folkinshteyn <nanotube@users.sourceforge.net>
#
# Project home (where to get the freshest version): 
#               http://wiki.df.dreamhosters.com/wiki/RiceMaker
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
import threading
import Queue

class VersionInfo:
    '''Version information storage
    '''
    def __init__(self):
        self.name = "RiceMaker"
        self.version = "0.5.3"
        self.description = "Script to automatically generate rice on freerice.com"
        self.url = "http://wiki.df.dreamhosters.com/wiki/RiceMaker"
        self.license = "GPL"
        self.author = "Daniel Folkinshteyn"
        self.author_email = "nanotube@users.sourceforge.net"
        self.platform = "Any"

class RiceMakerController:
    '''This class spawns a number of RiceMaker threads.'''
    def __init__(self):
        
        self.version = VersionInfo()
        self.options=None
        self.ParseOptions()
        self.session_filename="ricemakersession.txt"
        self.readDictFile()
        
        self.running_rice_total = 0
        self.read_session_info()
        
        self.ricecounter = 0
        self.answer_value = self.get_answer_value(url='http://www.freerice.com/index.php')
        
        self.queue = Queue.Queue(0)
        self.queueitem = {}
        
        self.threadlist = []
        for i in range(self.options.threads):
            self.threadlist.append(RiceMaker(url='http://www.freerice.com/index.php', options = self.options, wordlist = self.ricewordlist, queue=self.queue, threadnumber = i))
    
    def get_answer_value(self, url):
        response = urllib2.urlopen(urllib2.Request(url, headers={'User-Agent':self.options.useragent})) # spoof useragent
        result = response.read()
        soup = BeautifulSoup(result)
        try:
            text = soup.find(text=re.compile(r'1 right ='))
            answer_value = re.search(r'=\s*(\d+)\s*grains', text).group(1)
            return int(answer_value)
        except:
            print 'Failed to get answer value, using 10 as default...'
            return 10 # if we can't find the grain value, just assume it's 10. 
        
    
    def start(self):
        '''This is where we start the threads, and process the data queue'''
        
        print "Starting threads..."
        i = 0
        for t in self.threadlist:
            t.start()
            print "started thread", i
            i += 1
        
        print "Started all threads!"
        print "******************************************"
        
        self.starttime = time.time() #our start time - will use this to figure out rice per second stats
        
        try:
            self.iterator = 0
            while 1:
                self.iterator += 1
                try:
                    self.queueitem = self.queue.get(block=True, timeout=10)
                    self.ricecounter += int(self.queueitem['rice'])
                    print "iteration:", self.iterator
                    print "thread number:", self.queueitem['print']['threadnumber']
                    print "targetword:", self.queueitem['print']['targetword']
                    print "answer:", self.queueitem['print']['answer']
                    print "correct?", self.queueitem['print']['correct']
                    print "vocab level:", self.queueitem['print']['vocablevel']
                    print "total rice this session:", self.ricecounter
                    print "total rice all recorded sessions:", self.running_rice_total + self.ricecounter
                    print "percent correct this session:", str(round(self.ricecounter/self.answer_value/self.iterator*100.0, 2))+"%"
                    print "iterations per second", str(self.iterator/(time.time()-self.starttime)), ";", "rice per second", str(self.ricecounter/(time.time() - self.starttime))
                    print "******************************************"
                    for key in self.queueitem['dict'].keys():
                        self.ricewordlist[key] = self.queueitem['dict'][key]
                    if self.iterator % self.options.iterationsbetweendumps == 0:
                        self.dbDump()
                        self.write_session_info()
                except Queue.Empty:
                    self.iterator -= 1
                    pass #empty queue, we will try again.
                
        except: #catch everything
            traceback.print_exc()
            for t in self.threadlist:
                t.cancel()
    
    def __del__(self):
        if self.options != None: #when running with -h option, optparse exits before doing anything, including initializing options...
            f = open(self.options.freericedictfilename, 'wb')
            pickle.dump(self.ricewordlist, f, -1)
            f.close()
            print 'Successfully wrote internal dictionary to file.', len(self.ricewordlist), "elements in dictionary."
            
            f = open(self.session_filename, 'wb')
            pickle.dump(self.running_rice_total + self.ricecounter, f, -1)
            f.close()
            print 'Successfully wrote session info file.'
            print 'Rice this session:', self.ricecounter
            print 'Rice all stored sessions:', self.running_rice_total + self.ricecounter
            
            for t in self.threadlist:
                t.cancel()
    
    def readDictFile(self):
        if os.path.lexists(self.options.freericedictfilename) and os.path.getsize(self.options.freericedictfilename) > 0:
            try:
                f = open(self.options.freericedictfilename, 'rb')
                self.ricewordlist = pickle.load(f)
                f.close()
                print "dict read successful,", len(self.ricewordlist), "elements in dictionary"
            except:
                print "bad dict"
                traceback.print_exc()
                self.ricewordlist = {}
        else:
            self.ricewordlist = {}
    
    def dbDump(self):
        try:
            f = open(self.options.freericedictfilename, 'wb')
            pickle.dump(self.ricewordlist, f, -1)
            f.close()
            self.printDebug('dump successful')
        except:
            print 'bad dump'
            traceback.print_exc()
            pass # keep going, what else can we do?

    def read_session_info(self):
        if os.path.exists(self.session_filename) and os.path.getsize(self.session_filename) > 0:
            try:
                f = open(self.session_filename, 'rb')
                self.running_rice_total = pickle.load(f)
                f.close()
                print "session read successful. current running rice total:", self.running_rice_total
            except:
                print "bad session info file"
                traceback.print_exc()
                self.running_rice_total = 0
        else:
            self.running_rice_total = 0
    
    def write_session_info(self):
        try:
            f = open(self.session_filename, 'wb')
            pickle.dump(self.running_rice_total + self.ricecounter, f, -1)
            f.close()
            print 'Session dump successful, total rice:', self.running_rice_total + self.ricecounter
        except:
            print 'bad session dump'
            traceback.print_exc()
            pass # keep going, what else can we do?
    
    def ParseOptions(self):
        '''Read command line options
        '''
        parser = optparse.OptionParser(
                        version=self.version.name.capitalize() + " version " +self.version.version + "\nProject homepage: " + self.version.url, 
                        description="RiceMaker will automatically play the vocabulary game on freerice.com to generate rice donations. For a more detailed usage manual, see the project homepage: " + self.version.url, 
                        formatter=optparse.TitledHelpFormatter(),
                        usage="python %prog [options]")
        parser.add_option("-d", "--debug", action="store_true", dest="debug", help="Debug mode (print some extra debug output). [default: %default]")
        parser.add_option("-s", "--savesession", action="store_true", dest="savesession", help="Save session in a file. This will store a running total of the rice generated by you, across multiple runs of ricemaker. [default: %default]")
        parser.add_option("-w", "--wordnetpath", action="store", dest="wordnetpath", help="Full path to the WordNet commandline executable, if installed. On Linux, something like '/usr/bin/wn'; on Windows, something like 'C:\Program Files\WordNet\wn.exe'. [default: %default]")
        parser.add_option("-u", "--useragent", action="store", dest="useragent", help="The User-Agent string to use for the HTTP requests. The default is the User-Agent from IE7 on WinXP SP2. [default: %default]")
        parser.add_option("-l", "--sleeplowsec", action="store", type="float", dest="sleeplowsec", help="Lower bound on the random number of seconds to sleep between iterations. [default: %default]")
        parser.add_option("-m", "--sleephighsec", action="store", type="float", dest="sleephighsec", help="Upper bound on the random number of seconds to sleep between iterations. [default: %default]")
        parser.add_option("-f", "--freericedictfilename", action="store", dest="freericedictfilename", help="Filename for internally generated dictionary. You may specify a full path here, otherwise it will just get written to the same directory where this script resides (default behavior). No need to change this unless you really feel like it. [default: %default]")
        parser.add_option("-i", "--iterationsbetweendumps", action="store", type="int", dest="iterationsbetweendumps", help="Number of iterations between dictionary dumps to file. More often than 5 minutes is really unnecessary (Time between dumps is iterationsbetweendumps * avgsleeptime = time between dumps.) [default: %default]")
        parser.add_option("-t", "--threads", action="store", type="int", dest="threads", help="Number of simultaneous threads of RiceMaker to start. Stick with 1 to reduce probability of being filtered out as a bot. [default: %default]")
        parser.add_option("-b", "--benchmark", type="choice", action="append", dest="benchmark", choices=['dict.org','wordnet', 'idict'], help="For benchmarking or dictionary building purposes: do you want to skip dict.org lookups and/or wordnet and/or internal dictionary lookups ('dict.org' to skip dict.org, 'wordnet' to skip wordnet, 'idict' to skip internal dictionary). [default: %default]")

        
        parser.set_defaults(debug=False, 
                            savesession=True,
                            wordnetpath="/usr/bin/wn",
                            useragent="Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)",
                            sleeplowsec=3,
                            sleephighsec=6,
                            freericedictfilename="freericewordlist.txt",
                            iterationsbetweendumps=1000,
                            threads=1,
                            benchmark=[])
        
        (self.options, args) = parser.parse_args()
        self.printDebug("Your commandline options:\n", self.options)

    def printDebug(self, *args):
        if self.options.debug:
            for arg in args:
                print arg,
            print

class RiceMaker(threading.Thread):

    def __init__(self, url, options, wordlist, queue, threadnumber):
        threading.Thread.__init__(self)
        self.options=options
        self.url = url
        self.finished = threading.Event()
        self.ricecounter = [0,0,0] #[total, previous iteration value, current iteration value]
        self.ricewordlist = wordlist
        self.queue = queue
        self.queueitem = {'print':{}, 'dict':{}, 'rice':0}
        self.threadnumber = threadnumber

        response = urllib2.urlopen(urllib2.Request(self.url, headers={'User-Agent':self.options.useragent})) # spoof useragent
        result = response.read()
        self.soup = BeautifulSoup(result)
        
    def cancel(self):
        """Stop the thread"""
        self.finished.set()
            
    def run(self):
        self.iterator = 0
        while not self.finished.isSet():
            self.iterator = self.iterator+1
            
            time.sleep(random.uniform(self.options.sleeplowsec,self.options.sleephighsec)) # let's wait - to not hammer the server, and to not appear too much like a bot
            
            self.queueitem = {'print':{'threadnumber':self.threadnumber}, 'dict':{}, 'rice':0}
            
            try: #to catch all exceptions and ignore them
                mydiv = self.soup.findAll(attrs={'class':'questionDisplayChoices'})
                myol = mydiv[0].ol
                targetword = re.sub("&#8217;", "'", str(myol.li.strong.string)).strip()
                
                self.queueitem['print']['targetword'] = targetword
                
                itemlist = myol.findAll('li')
                self.wordlist={}
                for li in itemlist[1:5]:
                    ## format: 'word' = ' 1 '
                    word = re.sub("&#8217;", "'", str(li.a.string))
                    word = re.sub("&nbsp;", "", str(li.a.string)).strip()
                    self.wordlist[word] = str(li.noscript.input['value']).strip()
                    
                self.match = self.lookupWord(targetword,self.wordlist)
                #self.postdict = {'PAST':'','INFO':'','INFO2':''}
                self.postdict = {'PAST':'','INFO':'','INFO2':'', 'INFO3':''}
                for key in self.postdict.keys():
                    self.postdict[key] = self.soup.find("input",{'name':key})['value']
                
                try:
                    self.postdict['SELECTED'] = self.wordlist[re.sub("&#8217;", "'", self.match)].strip()
                except KeyError:
                    print "Match found but not present in possible answers. Using random."
                    answer = wordlist.keys()[random.randint(0,3)]
                    self.queueitem['print']['answer'] = answer+" (source: random)"
                    self.postdict['SELECTED'] = self.wordlist[answer].strip()
                
                response = urllib2.urlopen(urllib2.Request(self.url, data=urllib.urlencode(self.postdict), headers={'User-Agent':self.options.useragent}))
                result = response.read()
                self.soup = BeautifulSoup(result)
                
                # get rice donation amount (take care of possible loopback at 100k grains
                divstr = str(self.soup.findAll(id='donatedAmount')[0])
                if self.options.threads == 1:
                    print divstr
                divmatch = re.search('([0-9]+)',divstr)
                if divmatch != None:
                    self.ricecounter[1] = self.ricecounter[2]
                    self.ricecounter[2] = int(divmatch.group(1))
                    if self.ricecounter[2] - self.ricecounter[1] >= 0:
                        self.queueitem['rice'] = self.ricecounter[2] - self.ricecounter[1]
                    else:
                        self.queueitem['rice'] = self.ricecounter[2]
                
                # get vocab level
                #divstr =  str(self.soup.findAll(attrs={'class':'vocabLevel'})[0])
                try:
                    leveldiv = self.soup.findAll(id='questionDisplayBottomMenuBar')[0]
                    self.printDebug("level div found")
                    levelpara = leveldiv.findAll(text=re.compile(r'Level[^0-9]*[0-9]+\s*of\s*[0-9]+'))[0]
                    self.printDebug("level para found")
                    leveltext = unicode(levelpara.string)
                    self.printDebug('level text:', leveltext)
                    levelmatch = re.search(r'([0-9]+)\s*of',leveltext)
                    #if int(divmatch.group(1)) > 50:
                        #vocablevel = 0
                    vocablevel = int(levelmatch.group(1))
                    print 'vocab level', vocablevel
                except IndexError: 
                    self.printDebug('no level info found, setting vocab level to 0')
                    vocablevel = 0
                self.queueitem['print']['vocablevel'] = vocablevel
                self.createDict(targetword,self.wordlist)
                
                self.queue.put(self.queueitem)
            
            except KeyboardInterrupt:
                raise
            except:
                print "Exception in main loop!"
                traceback.print_exc()
                print "##########################"
                print self.soup
                print "##########################"
                response = urllib2.urlopen(urllib2.Request(self.url, data=urllib.urlencode(self.postdict), headers={'User-Agent':self.options.useragent}))
                result = response.read()
                self.soup = BeautifulSoup(result)
                # just keep going, don't care...
                pass
        self.finished.set()
    
    def createDict(self, targetword, wordlist):
        '''find if our new soup says our previous match was correct
        if so, add to dict, if not, parse their answer and add that to dict
        dict format: target: match'''
        
        answer = self.soup.findAll(id='correct')
        if len(answer) != 0:
            target, match = targetword, self.match
            self.queueitem['print']['correct'] = "True"
        else:
            answer = self.soup.findAll(id='incorrect')[0].string
            target, match = answer.split(' = ')
            self.queueitem['print']['correct'] = "False"
            print "Correct answer is:", match
        self.queueitem['dict'][str(target).strip()] = str(match).strip()
    
    def lookupWord(self, targetword, wordlist):
        self.printDebug('answer choices:', wordlist)
        
        try:
            return self.lookupInMyDict(targetword,wordlist)
        except KeyboardInterrupt:
            raise
        except:
            print "Exception in lookupWord"
            traceback.print_exc()
            return wordlist.keys()[random.randint(0,3)]
    
    def lookupInMyDict(self, targetword, wordlist):
        if 'idict' not in self.options.benchmark:
            try:
                word = self.ricewordlist[targetword]
                self.printDebug("internal dict match found!!!")
                self.queueitem['print']['answer'] = word+" (source: internal dictionary)"
                return word
            except KeyError: #not in our dict
                self.printDebug("no internal dict match found, trying wordnet")
                return self.lookupInWordnet(targetword, wordlist)
        else:
            return self.lookupInWordnet(targetword, wordlist)
    
    def lookupInWordnet(self, targetword, wordlist):
        if os.path.lexists(self.options.wordnetpath) and ('wordnet' not in self.options.benchmark):
            executionstring = "wn '" + targetword + "' -synsn -synsv -synsa -synsr -hypen -hypev -hypon -hypov"
            p = subprocess.Popen(executionstring, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
            returncode = p.wait()
            result = p.stdout.read()
            
            for word in wordlist.keys():
                if re.search(word, result):
                    self.printDebug("wn match found!")
                    self.queueitem['print']['answer'] = word+" (source: wordnet)"
                    return word
            else:
                self.printDebug("no wn match found, looking in dict.org")
                return self.lookupInDictorg(targetword, wordlist)
        else:
            return self.lookupInDictorg(targetword, wordlist)
    
    def lookupInDictorg(self, targetword, wordlist):
        if 'dict.org' not in self.options.benchmark:
            response = urllib2.urlopen('http://www.dict.org/bin/Dict', data=urllib.urlencode({'Query':targetword, 'Form':'Dict1', 'Strategy':'*', 'Database':'*'}))
            result = response.read()
            for word in wordlist.keys():
                if re.search(word, result):
                    self.printDebug("dict.org match found!")
                    self.queueitem['print']['answer'] = word+" (source: dict.org)"
                    return word
            else:
                self.printDebug("no dict.org match found, returning random.")
                answer = wordlist.keys()[random.randint(0,3)]
                self.queueitem['print']['answer'] = answer+" (source: random)"
                return answer
        else:
            answer = wordlist.keys()[random.randint(0,3)]
            self.queueitem['print']['answer'] = answer+" (source: random)"
            return answer
            
    def printDebug(self, *args):
        if self.options.debug:
            for arg in args:
                print arg,
            print
        
if __name__ == '__main__':
    rmc = RiceMakerController()
    rmc.start()
