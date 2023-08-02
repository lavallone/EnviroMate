import sys
sys.path.append('../action')

import os
import time, datetime
import socket
import random

from actionReader import *
from actionWriter import ActionWriter
from profileMatcher import ProfileMatcher

import threading
from thread2 import Thread
from threading import Lock

languages = {"en" : "English", "it": "Italian"}

def printError(message):
    RED   = "\033[1;31m"  
    RESET = "\033[0;0m"
    print("%s%s%s" %(RED,message,RESET))
    
# OUR IMPORTS
sys.path.append(os.getenv("MODIM_APP")+"/vision/garbage_detection")
from GarbageDet_detect import detect

class InteractionManager:
    def __init__(self, display, robot):
        self.profile =  ['*', '*', '*', '*']
        self.path = '.'           # path with demo files
        self.config = []
        self.display = display
        self.robot = robot
        self.saytime = {}
        self.vocabulary = None
        self.asr_meaning = None
        self.demoIP = '127.0.0.1' # web server containing the demo
        self.demoPort = 8000      
        self.logfile = None       # log file (log disabled by default)


    def setProfile(self, profile):
        self.profile = profile
        if (self.robot!=None):
            print "Setting language to: ", languages[self.profile[2]]
            self.robot.setLanguage(languages[self.profile[2]])

    def setDemoPath(self, path):
        self.path = path
        print('Demo path: %s' %self.path)
        sys.path.append(os.path.join(self.path,'scripts'))

    def setRelativeDemoPath(self, dirname):
        s = os.path.join(os.getenv("PEPPER_DEMOS"),dirname)
        self.setDemoPath(s)

    def setDemoServer(self, demoIP, demoPort):
        self.demoIP = demoIP
        self.demoPort = demoPort

    def gitpull(self): # executes a git pull command in the demo folder
        os.system('cd %s; git pull' %(self.path))
        #os.system('git pull')

    def getActionFilename(self, actionname):
        actionFullPath = os.path.join(self.path, "actions/"+actionname)
        return actionFullPath

    def getGrammarFilename(self, grammarname):
        grammarFullPath = os.path.join(self.path, "grammars/"+grammarname)
        return grammarFullPath
    
    def getGrammarURL(self, grammarname):
        url = 'http://%s:%d/grammars/%s' %(self.demoIP,self.demoPort,grammarname)
        return url

    def init(self):
        # path from env var
        app_path = os.getenv('MODIM_APP')
        if self.path == '.' and app_path!=None:
            self.path = app_path
        self.setDemoPath(self.path)

        initFilename = os.path.join(self.path, "init")

        self.config = ActionReader(initFilename, self.demoIP, self.demoPort) # we fill self.config with the 'init' file

        if "PROFILE" in self.config:
            self.setProfile(parseProfile(self.config["PROFILE"]))
        if "URL" in self.config:
            self.display.loadUrl(self.config["URL"])
        for key in self.config:
            if key != "PROFILE" and key != "URL":
                self.executeModality(key, self.config[key])
        print self.config

    # returns the list of conditions in an action
    def listConditions(self, actionname):
        actionFilename = self.getActionFilename(actionname)
        action = ActionReader(actionFilename, self.demoIP, self.demoPort)
        pm = ProfileMatcher(action, self.profile)
        r = pm.listConditions()
        self.display.setReturnValue(r)
        return r         
        
    def execute(self, actionname, audio=True):
        self.logdata('Exec-action-begin-%s' %actionname)
        self.vocabulary = None  # reinitialize ASR
        self.asr_meaning = None

        actionFilename = self.getActionFilename(actionname)
        action = ActionReader(actionFilename, self.demoIP, self.demoPort)
        pm = ProfileMatcher(action, self.profile)

        threads = [] #for parallel execution of the modalities
        for key in action: # all modalities except BUTTONS and ASR
            if key == 'NAME' or key == 'BUTTONS' or key == 'IMAGEBUTTONS' or key == 'ASR':
                continue
            actual_interaction = pm.evalSection(key)
            print('key interaction %s' %key)
            if (len(actual_interaction) == 0):
                continue
            if (not audio and key.upper()=='TTS'):
                continue
            #self.executeModality(key, actual_interaction)

            t = threading.Thread(target=self.executeModality, args=(key, actual_interaction))
            threads.append(t)
            t.start()

        # wait for threads to finish
        for t in threads:
            t.join()

        # show buttons        
        for key in action: # only BUTTONS
            if key == 'BUTTONS' or key == 'IMAGEBUTTONS':
                actual_interaction = pm.evalSection(key)
                for elem in actual_interaction:
                    if elem[1] == '': actual_interaction.remove(elem)
                print('key interaction %s' %key)
                if (len(actual_interaction) == 0):
                    continue
                self.executeModality(key, actual_interaction)

        # activate ASR
        for key in action: # only ASR
            if key == 'ASR':
                actual_interaction = pm.evalSection(key)
                print('key interaction %s' %key)
                if (len(actual_interaction) == 0):
                    continue
                self.executeModality(key, actual_interaction)

        self.logdata('Exec-action-end-%s' %actionname)

    def asr_run(self,timeout=30):
        print(self.vocabulary)
        if self.robot !=None and self.vocabulary != None:
            print(self.vocabulary)
            t0 = time.time()
            tnow = time.time()
            while tnow-t0<timeout:
                r = self.robot.asr(self.vocabulary,timeout=timeout-(tnow-t0))
                if r!=None and r!='':
                    if self.asr_meaning == None:
                        for v in self.vocabulary:
                            print("-- DEBUG ASR: %s == %s --" %(r,v))
                            if r==v:
                                self.answer_asr = v
                                return
                    else:
                        for key in self.asr_meaning.keys():
                            for v in self.asr_meaning[key]:
                                print("-- DEBUG ASR: %s == %s --" %(r,v))
                                if r==v:
                                    self.answer_asr = key
                                    return
                tnow = time.time()

    def buttons_run(self,timeout=30):
        if self.display != None:
            self.answer_buttons = self.display.answer(timeout)

    def ask_cancel(self):
        if self.robot !=None:
            self.robot.asr_cancel()
        if self.display != None:
            self.display.reset_answer = True

    def ask(self, actionname, timeout=10, audio=True):
        if actionname!=None:
            self.execute(actionname, audio=audio)
        self.answer_asr = None
        self.answer_buttons = None
        # start ASR and BUTTONS threads
        ta = Thread(target=self.asr_run, args=(timeout,))
        ta.start()
        tb = Thread(target=self.buttons_run, args=(timeout,))
        tb.start()

        t = 0
        dt = 0.25
        time.sleep(dt)
        a = None # first answer
        while timeout<0 or t<timeout:
            if self.answer_asr != None and self.answer_asr != '':
                a = self.answer_asr
                #print('MODIM debug:: ask from asr [%s]' %a)
                break
            elif self.answer_buttons != None:
                a = self.answer_buttons
                #print('MODIM debug:: ask from buttons [%s]' %a)
                break
            time.sleep(dt)
            t += dt

        self.ask_cancel()

        #print('MODIM debug:: ask return value here [%s]' %a)
        self.display.remove_buttons()
        if (a == None):
            a = 'timeout'
        else:
            a = a.rstrip()
        return a

    def askUntilCorrect(self, actionname, timeout=10):
        a = self.ask(actionname, timeout=timeout)
        #print("before while "+a)
        self.execute(a)
        time.sleep(3)
        while a[0:7]!='correct' and a!='timeout' and a!='cancel':
            # do not repeat the question with TTS
            a = self.ask(actionname, timeout=timeout, audio=False)
            self.execute(a) 
            time.sleep(3)
        return a

    def encode(self, interaction):
        l = min(10,len(interaction))
        return interaction[0:l]

    def executeModality(self, modality, interaction):

        self.logdata('Exec-modality-begin-%s-%s' %(modality,str(interaction)))

        if modality.upper().startswith('TEXT'):
            vmod = modality.split('_')
            place = 'default'
            if (len(vmod)>1):
                place = vmod[1]
            print 'display_text('+str(interaction)+','+place+')'
            if self.display != None:
                self.display.display_text(interaction, place)

        elif modality.upper() == 'IMAGE':
            vmod = modality.split('_')
            place = 'default'
            if (len(vmod)>1):
                place = vmod[1]

            # interaction =  os.path.join(self.path, interaction)
            print 'display_image('+str(interaction)+','+place+')'
            if self.display != None:
                self.display.display_image(interaction, place)

        elif modality.upper() == 'BUTTONS':
            print 'display_buttons('+str(interaction)+')'
            if self.display != None:
                self.display.display_buttons(interaction)
                
        elif modality.upper() == 'IMAGEBUTTONS':
            print 'display_buttons('+str(interaction)+')'
            if self.display != None:
                self.display.display_imagebuttons(interaction)

        elif modality.upper() == 'ASRCMD':
            grammarFile = None
            # try reading from file
            try:
                grammarFilename = self.getGrammarFilename(interaction)
                print 'Reading grammar file', grammarFilename
                grammarFile = open(grammarFilename, 'rU')
            except IOError:
                print "Cannot open grammar file", grammarFile

            if grammarFile==None:
                # try reading from URL
                try:
                    grammarURL = self.getGrammarURL(interaction)
                    print 'Reading grammar URL ', grammarURL
                    grammarFile = urllib2.urlopen(grammarURL)
                except:
                    print "Cannot open grammar URL", grammarURL

            if grammarFile==None:
                return

            inv_grammar = dict()
            grammar = dict()
            vocabulary = []
            for line in grammarFile.readlines():
                print 'grammar file: ',line
                try:
                    s = line.split('->')
                    words = s[0].strip().split(',')
                    words = map(str.strip, words) #removes spaces on all elements
                    key = s[1].strip()
                    grammar[key] = words
                    vocabulary.extend(words)
                    for w in words:
                        inv_grammar[w] = key
                except:
                    printError("Error in reading grammar file")

            #if (self.robot!=None):
            #    self.robot.asr(vocabulary) # TODO check

        elif modality.upper() == 'ASR':
            print("ASR %s" %interaction)
            if type(interaction)==type([]): # list of values
                self.vocabulary = interaction
                self.asr_meaning = None
            elif type(interaction)==type({}): # dict  { meaning: [values...] ... }
                self.asr_meaning = interaction
            elif type(interaction)==type(''): # string  "{ meaning: [values...] ... }"
                self.asr_meaning = eval(interaction)
            if self.asr_meaning != None:
                v = [item for sublist in self.asr_meaning.values() for item in sublist]
                print("ASR enabled with vocabulary: %r" %v)
                self.vocabulary = v
            #try:
            #    if (self.robot != None):
            #        print('#### start robot ASR... ####')
            #        #self.robot.asr(self.vocabulary, timeout=30) # blocking !!!
            #        print('#### end robot ASR... ####')
            #    else:
            #        print("No robot for ASR")
            #except Exception as e:
            #    print("ERROR in robot ASR")
            #    print(e)

        elif modality.upper() == 'GESTURE':
            print 'run_animation('+interaction+')'
            if (self.robot != None):
                self.robot.animation(interaction)

        elif modality.upper() == "TTS":
            cod = self.encode(interaction)
            if (not cod in self.saytime):
                #self.saytime[cod]=1
                print 'say('+interaction+')'            
                if (self.robot != None):
                    self.robot.say(interaction)

        print "Finished executeModality("+modality+","+str(interaction)+")\n"
        self.logdata('Exec-modality-end-%s-%s' %(modality,str(interaction)))

    # Logging functions
    def logenable(self,enable=True):
        if enable:
            if (self.logfile is None):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                logfilename = '/tmp/modim_%s.log' %timestamp
                self.logfile = open(logfilename,'a')
                print('Log enabled.')
        else:
            if (self.logfile is not None):
                self.logclose()
                print('Log disabled.')
                

    def logdata(self, data):
        if (self.logfile is not None):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            self.logfile.write("%s;%r\n" %(timestamp, data))
            self.logfile.flush()


    def logclose(self):
        if (self.logfile != None):
            self.logfile.close()
            self.logfile = None
      
    ## OUR FUNCTIONS

    def super_recycling_game(self):
        dir_path = 'imgs/super_recycling_imgs/'
        dict_trash = {}

        for elem in os.listdir('/home/robot/playground/'+dir_path):
            waste_class = elem.split('_')[0]
            dict_trash[elem] = waste_class

        img_waste = random.choice(list(dict_trash.keys()))
        class_wast = dict_trash[img_waste] 
        path_waste = dir_path+img_waste
        print('CLASS', class_wast)
        print('CLASS', path_waste)
        c = 0
        while c < 3: 
            self.executeModality('IMAGE', path_waste)
            ans = self.ask('play', timeout = 15)
            if ans == class_wast: 
                c += 1
                self.execute('correct')
                img_waste = random.choice(list(dict_trash.keys()))
                class_wast = dict_trash[img_waste] 
                path_waste = dir_path+img_waste
            else: 
                self.execute('wrong')
        return True

    def detect_garbage(self, img_path):
        # create a TCP/IP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # connect the socket to the server's address and port
        server_address = ('127.0.0.1', 3030)
        client_socket.connect(server_address)
        try:
            # send data to the server
            client_socket.sendall(img_path)
            # receive the response from the server
            ris = client_socket.recv(1024).decode('utf-8')
            print("Server's response:", ris)
            obj_class, ris_img_path = str(ris).split(",")
            ris_img_path = ris_img_path.replace("\n", "")
        finally:
            # Clean up the connection
            client_socket.close()
        return obj_class, ris_img_path
    
    def shortest_path(self, obj_class):
        # create a TCP/IP socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # connect the socket to the server's address and port
        server_address = ('127.0.0.1', 3031)
        client_socket.connect(server_address)
        try:
            # send data to the server
            client_socket.sendall(obj_class)
            # receive the response from the server
            ris = client_socket.recv(1024).decode('utf-8')
            print("Server's response:", ris)
            map_goals_path, map_bestpath_path = str(ris).split(",")
            
        finally:
            # Clean up the connection
            client_socket.close()
        return map_goals_path, map_bestpath_path

if __name__ == "__main__":
    pass


