#!/usr/bin/env python

# import include modules

import os
import ConfigParser
import rpyc
import time
from autobot import cfg
import logging

logger = logging.getLogger('client-lib')

class autoClient:
    'Common base class for all employees'

    def __init__(self,name):
        path = os.path.join(os.getcwd(),'clients')
        if not os.path.isdir(path):
            logger.error("Cannot access directory with known clients.")

        fileName = name+'.cfg'
        list = os.path.join(path,fileName)

        logger.debug("Will read information from config file '"+fileName+"'.")

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
            logger.error("Cannot read all information from '"+name+"'.")

        self.platform = self.getOS()

        if self.platform == 'WIN':
            self.tpath = "C:\\Users\\"+self.user+"\\Transporter\\"
            self.tlpath = self.tpath+"Transporter Library"
        else:
            self.tpath = "/Users/"+self.user+"/Transporter/"
            self.tlpath = self.tpath+".Transporter Library"

    def getOS(self):

        logger.debug("Getting OS on '"+self.name+"'.")

        try:
            conn = rpyc.classic.connect(self.publ)
        except:
            logger.error("Cannot connect to RPYC on '"+self.name+"'.")
            return 'Error'

        osName = conn.modules.platform.platform()

        if osName.startswith('Windows'):
            system = 'WIN'
            logger.debug("Computer '"+self.name+"' (IP address "+self.publ+") is running Windows.")
        elif osName.startswith('Darwin'):
            system = 'OSX'
            logger.debug("Computer '"+self.name+"' (IP address "+self.publ+") is  running MacOS.")
        else:
            logger.error("Computer '"+self.name+"' (IP address "+self.publ+") is running something called: "+osName)
            return 'Error'

        return system

    def getClientInfo(self):
        """
        Return account information for active user (e-mail and app version)

        :return: Connected data user e-mail and app version
        """

        logger.debug("Client '"+self.name+"' is running "+self.platform+".")


        username = self.userName()
        if username == 'Error':
            username = self.user
            logger.warning("Cannot get current user name. Will use one from config file: '"+username+"'.")
        else:
            logger.debug("Current user on '"+self.name+"' has login '"+username+"'.")

        try:
            conn = rpyc.classic.connect(self.publ)
            logger.debug("Successfully connected to RPYC running on '"+self.name+"' over IP '"+self.publ+"'.")
        except:
            logger.error("Cannot connect to RPYC on remote computer (IP="+self.publ+".")
            return 'Error'

        try:
            if self.platform == 'WIN':
                file_name = 'C:\\Users\\'+username+'\\AppData\\Roaming\\Connected Data\\configuration.ini'
                rmt_cfg = conn.modules.ConfigParser.RawConfigParser()
                rmt_cfg.read(file_name)
                cd_account = rmt_cfg.get('Credentials','UserName')
                cd_clientver = rmt_cfg.get('Options','LastRunVersion')
            else:
                file_name = '/Users/'+username+'/Library/Preferences/com.connecteddata.ConnectedDesktop.plist'
                rmt_cfg = conn.modules.biplist.readPlist(file_name)
                cd_account = rmt_cfg['Account']
                info_cfg = conn.modules.biplist.readPlist('/Applications/Transporter Desktop.app/Contents/Info.plist')
                cd_clientver = info_cfg['CFBundleShortVersionString']
        except:
            logger.error("Failed to get information from client's desktop application.")
            return 'Error'

        logger.debug("Client's desktop information was retrived from local file '"+file_name+"'.")

        return cd_account, cd_clientver

    def checkClient(self):

        logger.debug("Check availability of client '"+self.name+"'.")

        # Check platphorm
        platform = self.getOS()
        if platform == 'Error':
            logger.error("Something went wrong when checked platform on '"+self.name+"'.")
            return 'Error'

        # Check data for currently logged user
        usermail, userver = self.getClientInfo()

        if usermail == 'Error':
            logger.warning("Unable to retrive information for current user on '"+self.name+"'.")
            return 'Error'

        if usermail != self.tusr:
            logger.error("Wrong user name ('"+usermail+"' instead of '"+self.tusr+"'.")
            return 'Error'

        logger.info("Client will use desk app version '"+userver+"'.")

        response = self.smbUmountAll()
        if response == 'Error':
            logger.warning("Probably there are still mounted network storages on '"+self.name+"'.")

        return platform

    def smbCheck(self):
        """
        Checks for mounted network file systems
        :return: list of attached network file systems
        """

        logger.info("Checking for network file systems attached to the client '"+self.name+"'.")

        if self.platform == 'WIN':
            cmd = 'net use'
        else:
            cmd = 'df'

        conn = rpyc.classic.connect(self.publ)
        try:
            response = conn.modules.os.popen(cmd).read()
        except:
            logger.error("Error when try to get list of mounted NFS on '"+self.name+"'.")
            return 'Error'

        mountpoints = []
        lines = response.split('\n')
        for line in lines:
            if line.startswith('OK') or line.startswith('//'):
                mountpoints.append(line.replace(' ',''))

        mounts = []
        for point in mountpoints:
            if self.platform == 'WIN':
                mounts.append(point[2:3])
            else:
                mounts.append(point.split('/Users/autotest/')[1])

        return mounts

    def smbMount(self):

        logger.debug("Mount shared folder.")

        if self.platform == 'WIN':
            mountpoint = self.mount+":"
            logger.debug("Will mount network share as "+mountpoint+"-drive.")
            cmd = "net use "+mountpoint+" \\\\"+self.smbserv+"\\"+self.smbshare+" "+self.smbpass+" /user:"+self.smbuser
        else:
            logger.debug("Will mount network share as "+self.mount+" in home directory.")
            mountpoint = "$HOME/"+self.mount
            cmd = "mkdir -p "+mountpoint+" && mount_smbfs //"+self.smbuser+":"+self.smbpass+"@"+self.smbserv+"/"+self.smbshare+" $HOME/"+self.mount

        logger.debug("Will mount network storage on '"+self.name+"' using command: '"+cmd+"'.")

        conn = rpyc.classic.connect(self.publ)
        try:
            response = conn.modules.os.system(cmd)
        except:
            logger.error("Cannot map network share on "+self.name+".")
            return 'Error'

        checkpoint = mountpoint+'/shared-disk.txt'
        checknorm = conn.modules.os.path.normcase(checkpoint)

        logger.debug("To check mounted network FS will search for the '"+checknorm+"'.")

        checker = conn.modules.os.path.isfile(checknorm)
        if checker:
            logger.debug("Successfully mounted network storage on '"+self.name+"'.")
        else:
            logger.error("Failed to mount network storage on '"+self.name+"'.")
            return 'Error'

        return mountpoint

    def smbUmount(self,mountpoint):

        logger.debug("Unmount shared folder.")

        if self.platform == 'WIN':
            logger.debug("Will disconnect network share from "+mountpoint+"-drive.")
            cmd = "net use "+mountpoint+": /delete"
        else:
            logger.debug("Will umount network share from "+mountpoint+" in home directory.")
            cmd = "umount "+mountpoint

        conn = rpyc.classic.connect(self.publ)
        try:
            response = conn.modules.os.system(cmd)
        except:
            logger.error("Cannot remove network share on "+self.name+".")
            return 'Error'

        return 'Success'

    def smbUmountAll(self):
        """
        Remove all attached network file systems
        :return: 'Success'
        """

        logger.info("Check and remove all network file systems attached to the client '"+self.name+"'.")

        mountpoints = self.smbCheck()
        count = len(mountpoints)

        if count == 0:
            logger.debug("Client '"+self.name+"' doesn't have any network file systems attached.")
            return 'Success'
        elif count == 1:
            logger.debug("Client '"+self.name+"' has 1 network file system attached.")
        else:
            logger.debug("Client '"+self.name+"' has "+str(count)+" network file systems attached.")

        status = 'Success'
        for mount in mountpoints:
            response = self.smbUmount(mount)
            if response == 'Error':
                logger.warning("Failed to remove network file system mounted as '"+mount+"' on '"+self.name+"'.")
                status = 'Error'

        return status

    def userName(self):
        """

        :return: Current user name
        """

        logger.info("Check user name currently logged on '"+self.name+"'.")

        conn = rpyc.classic.connect(self.publ)
        try:
            response = conn.modules.os.popen('whoami').read()
        except:
            logger.error("Error when try to get user name on '"+self.name+"'.")
            return 'Error'

        username = response.split('\\')
        username = username[len(username)-1].replace('\n','')

        return username

    def plantTree(self,poolname):

        logger.debug("Will copy files from network storage to the pool directory.")

        result = self.smbMount()
        if result == 'Error':
            logger.error("Failed to mount network storage on '"+self.name+"'.")
            return 'Error'
        else:
            logger.debug("Network storage mounted as '"+result+"'.")

        source = result+"/vault"
        destination = self.tpath+poolname+"/vault"

        conn = rpyc.classic.connect(self.publ)

        try:
            src = conn.modules.os.path.normcase(source)
            dst = conn.modules.os.path.normcase(destination)
        except:
            logger.error("Fail to normalize path to the "+self.platform+" standards.")
            return 'Error'

        logger.debug("Client platform is "+self.platform+". Will copy from "+src+" to "+dst+".")

        response = self.copyTree(src,dst)
        if response == 'Error':
            logger.error("Failed to plant tree from "+src+" in "+dst+".")
            return 'Error'

        last = 1
        for x in range (1,11):
            precheck = self.cleanTree(poolname)
            time.sleep(self.timeout)
            aftercheck = self.cleanTree(poolname)

            diff = list(set(precheck) - set(aftercheck))
            last = len(diff)
            if last == 0:
                logger.debug("Source and destination are the same.")
                break
            else:
                logger.debug("After "+str((11-x)*self.timeout)+" seconds source and distination are different.")

        if last != 0:
            x = 1
            for element in diff:
                logger.warning(str(x).zfill(len(str(last)))+". '"+element+"'.")
                x = x + 1
            return 'Error'

        result = self.smbUmountAll()
        if result == 'Error':
            logger.warning("Failed to unmount network storage from '"+self.name+"'.")

        return 'Success'

    def readTree(self,poolname):

        logger.debug("Will read directory tree in the pool '"+poolname+"'.")

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

        logger.debug("Will delete everything in Transporter folder")

        conn = rpyc.classic.connect(self.publ)

        dir_tree = conn.modules.os.listdir(self.tpath)

        if len(dir_tree) == 0:
            logger.error("Didn't get directory structure on client "+self.name+".")
            return 'Error'

        for directory in dir_tree:
            if 'Transporter Library' in directory:
                logger.debug("Will not delete "+directory+" because it is part of 'Transporter Library'.")
                dir_tree.remove(directory)
            else:
                logger.debug("Deleting "+directory+".")
                response = self.delTree(directory)
                if response == 'Error':
                    logger.error("Failed to clean Transporter directory on '"+self.name+"'.")
                    return 'Error'

        return 'Success'

    def directoryExists(self,dir_name):

        logger.debug("Check if '"+dir_name+"' exists and it is directory.")
        full_path = self.tpath+dir_name
        logger.debug("Pool's directory path will be '"+full_path+"'.")

        conn = rpyc.classic.connect(self.publ)

        try:
            status = conn.modules.os.path.isdir(full_path)
        except:
            logger.error("Cannot retrive information from '"+self.name+"'.")
            return False

        return status

    def cleanTree(self,poolname):

            #List of files to ignore
            ignored = ['desktop.ini','.DS_Store','Thumbs.db']

            list = self.readTree(poolname)
            clean_list = []

            logger.debug("Removing ignored files from the list.")

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

        if conn.modules.os.path.isdir(dst):
            logger.debug("'"+dst+" already exists. Will delete it.")
            result = self.delTree(dst)
            if result == 'Error':
                logger.warning("Fail to delete '"+dst+"'. Will try to copy anyway.")

        if conn.modules.os.path.isdir(src):
            logger.debug("Found source '"+src+"' at '"+self.name+"'.")
        else:
            logger.error("Cannot find source '"+src+"' at '"+self.name+"'.")
            return 'Error'

        try:
            treestat = conn.modules.shutil.copytree(src,dst,symlinks=False,ignore=None)
        except conn.modules.shutil.Error as e:
            logger.error('Directory not copied. Error: %s' % e)
            return 'Error'

        return 'Success'

    def delTree(self,dirname):
        """

        :param dirname:
        :return:
        """

        logger.debug("Will delete everything in "+dirname)

        conn = rpyc.classic.connect(self.publ)

        try:
            conn.modules.shutil.rmtree(dirname,True)
        except conn.modules.shutil.Error as e:
            logger.error("Directory "+dirname+" was not deleted. Error: %s" % e)
            return 'Error'

        return 'Success'

    def reset(self):

        logger.info("Attempt to set client according to config file.")

        logger.debug("Disconnect all attached storages if any.")
        for x in range (1,6):
            response = self.smbUmountAll()
            if response == 'Error':
                logger.warning("Unable to disconnect all storages on "+str(x)+" attempt.")
                time.sleep(self.timeout)
            else:
                logger.debug("All attacheg network storages should be already disconnected.")
                break

        status = response

        logger.debug("Delete everything from Transporter directory.")
        for x in range (1,6):
            response = self.deleteAll()
            if response == 'Error':
                logger.warning("Unable to delete files/folders from Transporter directory on "+str(x)+" attempt.")
                time.sleep(self.timeout)
            else:
                logger.debug("Everything should be already removed from Transporter directory.")
                break

        if status == 'Error':
            return status
        else:
            return response