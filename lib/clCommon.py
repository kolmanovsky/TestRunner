#!/usr/bin/env python

# import include modules

import os
import ConfigParser
import rpyc
import time
from testbot import log, cfg

class autoClient:
    'Common base class for all employees'

    def __init__(self,name):
        path = os.path.join(os.getcwd(),'clients')
        if not os.path.isdir(path):
            log.error("Cannot access directory with known clients.")

        fileName = name+'.cfg'
        list = os.path.join(path,fileName)

        log.debug("Will read information from config file '"+fileName+"'.")

        conf = ConfigParser.RawConfigParser()
        conf.read(list)

        self.name = name
        self.timeout = int(cfg.get('general','timeout'))

        try:
            self.publ = conf.get('address','corp')
            self.locl = conf.get('address','local')
            self.user = conf.get('system','user')
            self.pswd = conf.get('system','pass')
            self.tver = conf.get('connecteddata','version')
            self.tlib = conf.get('connecteddata','directory')
            self.tusr = conf.get('connecteddata','user')
            self.tpwd = conf.get('connecteddata','pass')
            self.mount = conf.get('samba','drive')
            self.smbserv = conf.get('samba','server')
            self.smbshare = conf.get('samba','share')
            self.smbuser = conf.get('samba','user')
            self.smbpass = conf.get('samba','pass')
            self.smbnas = conf.get('samba','nas')
        except:
            log.error("Cannot read all information from '"+name+"'.")

        self.platform = self.getOS()

        if self.platform == 'WIN':
            self.tpath = "C:\\Users\\"+self.user+"\\Transporter\\"
            self.tlpath = self.tpath+"Transporter Library"
        else:
            self.tpath = "/Users/"+self.user+"/Transporter/"
            self.tlpath = self.tpath+".Transporter Library"

    def getOS(self):

        log.debug("Geting OS on '"+self.name+"'.")

        try:
            conn = rpyc.classic.connect(self.publ)
        except:
            log.error("Cannot connect to RPYC on '"+self.name+"'.")
            return 'Error'

        osName = conn.modules.platform.platform()

        if osName.startswith('Windows'):
            system = 'WIN'
            log.debug("Computer '"+self.name+"' (IP address "+self.publ+") is running Windows.")
        elif osName.startswith('Darwin'):
            system = 'OSX'
            log.debug("Computer '"+self.name+"' (IP address "+self.publ+") is  running MacOS.")
        else:
            log.error("Computer '"+self.name+"' (IP address "+self.publ+") is running something called: "+osName)
            return 'Error'

        return system

    def getClientInfo(self):

        try:
            conn = rpyc.classic.connect(self.publ)
            log.debug("Successfully connected to RPYC running on '"+self.name+"' over corporate IP '"+self.publ+"'.")
        except:
            log.error("Cannot connect to RPYC on remote computer (IP="+self.publ+".")
            return 'Error'

        platform = self.getOS()
        if platform == 'WIN':
            path = "C:\\Users\\"+"\\"+self.user+"\\AppData\\Roaming\\Connected Data\\configuration.ini"
        elif platform == 'OSX':
            path = "/Users/"+self.user+"/Library/Preferences/com.connecteddata.ConnectedDesktop.plist"
        else:
            log.error("Something went wrong when checked platform on '"+self.name+"'. Reported OS is '"+platform+"'.")
            return 'Error'

        return platform

        '''
            if conn.modules.os.path.isfile(path):
            log.debug("Configuration file found: '"+path+"'.")
            conn.execute('f = open("'+path+'", "r")')
            conn.execute("appInfo = f.readlines()")
            conn.execute("f.close()")
            appInfo = conn.namespace["appInfo"]
        else:
            log.error("Cannot fine file '"+path+"'.")
            return 'Error'

        if platform == 'WIN':
            cdUser = appInfo[1][11:-1]
            cdUUID = appInfo[3][7:-1]
            cdVerl = appInfo[29][17:-1]

            print cdUser
            print cdUUID
            print cdVerl
        else:
            print appInfo

        '''

    def checkClient(self):

        log.debug("Check availability of client '"+self.name+"'.")

        platform = self.getOS()
        if platform == 'Error':
            log.error("Something went wrong when checked platform on '"+self.name+"'.")
            return 'Error'

        return platform

    def smbMount(self):

        log.debug("Mount shared folder.")

        if self.platform == 'WIN':
            mountpoint = self.mount+":"
            log.debug("Will mount network share as "+mountpoint+"-drive.")
            cmd = "net use "+mountpoint+" \\\\"+self.smbserv+"\\"+self.smbshare+" "+self.smbpass+" /user:"+self.smbuser
        else:
            log.debug("Will mount network share as "+self.mount+" in home directory.")
            mountpoint = "$HOME/"+self.mount
            cmd = "mkdir -p "+mountpoint+" && mount_smbfs //"+self.smbuser+":"+self.smbpass+"@"+self.smbserv+"/"+self.smbshare+" $HOME/"+self.mount

        conn = rpyc.classic.connect(self.publ)
        try:
            response = conn.modules.os.system(cmd)
        except:
            log.error("Cannot map network share on "+self.name+".")
            return 'Error'

        return mountpoint

    def smbUmount(self):

        log.debug("Unmount shared folder.")

        if self.platform == 'WIN':
            log.debug("Will disconnect network share from "+self.mount+"-drive.")
            cmd = "net use "+self.mount+": /delete"
        else:
            log.debug("Will umount network share from "+self.mount+" in home directory.")
            cmd = "umount "+self.mount

        conn = rpyc.classic.connect(self.publ)
        try:
            response = conn.modules.os.system(cmd)
        except:
            log.error("Cannot remove network share on "+self.name+".")
            return 'Error'

        return 'Success'

    def plantTree(self,poolname):

        log.debug("Will copy files from network storage to the pool directory.")

        result = self.smbMount()
        if result == 'Error':
            log.error("Failed to mount network storage on '"+self.name+"'.")
            return 'Error'
        else:
            log.debug("Network storage mounted as '"+result+"'.")

        source = result+"/vault"
        destination = self.tpath+poolname+"/vault"

        response = self.copyTree(source,destination)
        if response == 'Error':
            log.error("Failed to plant tree from "+source+" in "+destination+".")
            return 'Error'

        last = 1
        for x in range (1,11):
            precheck = self.cleanTree(poolname)
            time.sleep(self.timeout)
            aftercheck = self.cleanTree(poolname)

            diff = list(set(precheck) - set(aftercheck))
            last = len(diff)
            if last == 0:
                log.debug("Source and destination are the same.")
                break
            else:
                log.debug("After "+str((11-x)*self.timeout)+" seconds source and distination are different.")

        if last != 0:
            x = 1
            for element in diff:
                log.warning(str(x).zfill(len(str(last)))+". '"+element+"'.")
                x = x + 1
            return 'Error'

        result = self.smbUmount()
        if result == 'Error':
            log.warning("Failed to unmount network storage from '"+self.name+"'.")

        return 'Success'

    def readTree(self,poolname):

        log.debug("Will read directory tree in the pool '"+poolname+"'.")

        file_paths = []
        conn = rpyc.classic.connect(self.publ)

        if self.platform == 'WIN':
            tree = self.tpath+"\\"+poolname
        else:
            tree = self.tpath+"/"+poolname

        long = len(tree)

        # Walk trough the directory structure
        for root, directories, files in conn.modules.os.walk(tree):
            for file in files:
                # Join the two strings in order to form the full filepath.
                filepath = os.path.join(root, file)
                file_paths.append(filepath[long:])

        return file_paths

    def deleteAll(self):

        log.debug("Will delete everything in Transporter folder")

        conn = rpyc.classic.connect(self.publ)

        dir_tree = conn.modules.os.listdir(self.tpath)

        if len(dir_tree) == 0:
            log.error("Didn't get directory structure on client "+self.name+".")
            return 'Error'

        for directory in dir_tree:
            if 'Transporter Library' in directory:
                log.debug("Will not delete "+directory+" because it is part of 'Transporter Library'.")
                dir_tree.remove(directory)
            else:
                log.debug("Deleting "+directory+".")
                response = self.delTree(directory)
                if response == 'Error':
                    log.error("Failed to clean Transporter directory on '"+self.name+"'.")
                    return 'Error'

        return 'Success'

    def directoryExists(self,dir_name):

        log.debug("Check if '"+dir_name+"' exists and it is directory.")
        full_path = self.tpath+dir_name
        log.debug("Pool's directory path will be '"+full_path+"'.")

        conn = rpyc.classic.connect(self.publ)

        try:
            status = conn.modules.os.path.isdir(full_path)
        except:
            log.error("Cannot retrive information from '"+self.name+"'.")
            return False

        return status

    def cleanTree(self,poolname):

            #List of files to ignore
            ignored = ['desktop.ini','.DS_Store','Thumbs.db']

            list = self.readTree(poolname)
            clean_list = []

            log.debug("Removing ignored files from the list.")

            for line in list:
                if not any(word in line for word in ignored):
                    line = line.replace('\\','/')
                    clean_list.append(line)

            return clean_list

    def copyTree(self,src,dst):
        """

        :param src:
        :param dst:
        :return:
        """

        conn = rpyc.classic.connect(self.publ)

        log.debug("Will copy '"+src+"' to '"+dst+"'.")

        try:
            normsrc = conn.modules.os.path.normcase(src)
            normdst = conn.modules.os.path.normcase(dst)
        except:
            log.error("Fail to normalize path to the "+self.platform+" standards.")
            return 'Error'

        log.debug("Client platform is "+self.platform+". Will copy from "+normsrc+" to "+normdst+".")

        log.debug("First of all: will delete destination folder if it already exists.")

        result = self.delTree(normdst)
        if result == 'Error':
            log.warning("Fail to delete destination. Will try to copy anyway.")

        if conn.modules.os.path.exists(normdst):
            try:
                if conn.modules.os.path.isdir(normdst):
                    log.warning(normdst.capitalize()+" already exists on '"+self.name+"'.")
                    conn.modules.shutil.rmtree(normdst)
                elif conn.modules.os.path.isfile(normdst):
                    log.warning(normdst.capitalize()+" already exists on '"+self.name+"' and it is a file.")
                    conn.modules.os.unlink(normdst)
            except:
                log.warning(normdst.capitalize()+" already exists on '"+self.name+"' and it is impossible to delete it.")
                return 'Error'

        try:
            treestat = conn.modules.shutil.copytree(normsrc,normdst,symlinks=False,ignore=None)
        except conn.modules.shutil.Error as e:
            log.error('Directory not copied. Error: %s' % e)
            return 'Error'

        return 'Success'

    def delTree(self,dirname):
        """

        :param dirname:
        :return:
        """

        log.debug("Will delete everything in "+dirname)

        conn = rpyc.classic.connect(self.publ)

        normdir = conn.modules.os.path.normcase(dirname)
        if conn.modules.os.path.isdir(normdir):
            log.debug(normdir+" exists. Deleting "+normdir)
            try:
                conn.modules.shutil.rmtree(normdir,True)
            except conn.modules.shutil.Error as e:
                log.error("Directory "+normdir+" was not deleted. Error: %s" % e)
                return 'Error'
        elif conn.modules.os.path.isfile(normdir):
            log.debug(normdir+" is file. Deleting "+normdir)
            try:
                conn.modules.os.unlink(normdir)
            except conn.modules.shutil.Error as e:
                log.error("Directory "+normdir+" was not deleted. Error: %s" % e)
                return 'Error'
        else:
            log.debug(normdir+" does not exist.")

        return 'Success'