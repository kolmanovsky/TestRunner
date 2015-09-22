#!/usr/bin/env python

# import include modules
from autobot import cfg
import time
import os
import paramiko
import logging
import socket
import ConfigParser
import urllib2
import taPower as power
import requests
from StringIO import StringIO

logger = logging.getLogger('tfb-lib')

# ==============================================================
# General function for Test Runner
# ==============================================================

class taTransporter:

    def __init__(self,name):

        path = os.path.join(os.getcwd(),'targets')
        if not os.path.isdir(path):
            logger.error("Cannot access directory with known clients.")

        fileName = name+'.target'
        list = os.path.join(path,fileName)

        logger.debug("Will read information from config file '"+fileName+"'.")

        conf = ConfigParser.RawConfigParser()
        conf.read(list)

        self.name = name
        self.timeout = int(cfg.get('general','timeout'))

        self.maxwait = 10

        try:
            self.address = conf.get('access','address')
            self.port = int(conf.get('access','port'))
            self.user = conf.get('credentials','user')
            self.pswd = conf.get('credentials','password')
            self.type = conf.get('hardware','type')
            self.power = int(conf.get('hardware','power'))
            self.firmware = conf.get('build','firmware')
            self.last = conf.get('build','build')
            self.qa_dev = conf.get('build','type')
        except:
            logger.error("Cannot read all information from '"+name+"'.")


    def readDiagConfig(self):
        """
        Reads configuration from command 'cmd diag config'

        :return List of lines from STDOUT or 'Error'
        """

        # Check is replicator running by getting process ID for replicator
        logger.debug("First of all check is replicator running.")
        for x in range (1,self.maxwait):
            repcheck = self.pidofReplicator()
            if repcheck == '':
                logger.warning("Replicator is down. Will try to start it.")
                replica = self.cmdReplicator('start')
                time.sleep(self.timeout)
            else:
                logger.debug("Got process ID for replicator: "+repcheck+".")
                break

        # If process ID for replicator is empty string at this point - script was not able to start replicator
        if repcheck == '':
            logger.error("Was not able to start replicator. Fatal error.")
            return 'Error'

        # Send command to get configuration. Check for key fraze to recognize response.
        cmd = "cmd diag config"
        for x in range(1,self.maxwait):
            reply = self.sshCmd(cmd)
            if reply == 'Error':
                logger.error("Failed to execute remote command '"+cmd+"Will wait and then retry "+str(self.maxwait-x)+" times.")
                time.sleep(self.timeout)
            else:
                for line in reply:
                    if line.startswith("Dumping Diagnostics"):
                        logger.debug("Got expected result from command '"+cmd+"'.")
                        return reply
                logger.warning("Command didn't return expected result. Will wait and then re-run "+str(self.maxwait-x)+" times.")
                time.sleep(self.timeout)

        logger.error("It takes too long to get reply. Something is wrong!")
        return 'Error'

    def readMacID(self):
        """
        Reads MacID from 'cmd diag config'

        :return String with MacID or 'Error'
        """

        # Parse response from 'cmd diag config' for 'MAC Addr'
        response = self.readDiagConfig()
        if response == 'Error':
            logger.error("Cannot read MacID from 'diag config'. It didn't reply.")
            return 'Error'
        else:
            for line in response:
                if line.startswith('MAC Addr'):
                    macid = line[24:41]
            logger.debug("MacID from 'diag config' retrived as '"+macid+"'.")

        return macid

    def readFWversion(self):
        """
        Reads firmware version from 'cmd diag config'

        :return String with FW version or 'Error'
        """

        # Parse response from 'cmd diag config' for 'Firmware version'
        response = self.readDiagConfig()
        if response == 'Error':
            logger.error("Cannot read FW version from 'diag config'. It didn't reply.")
            return 'Error'
        else:
            for line in response:
                if line.startswith('Firmware version'):
                    version = line[25:39]
            logger.debug("FW version from 'diag config' retrived as '"+version+"'.")

        return version

    def readUUID(self):
        """
        Reads device ID from 'cmd diag config'

        :return String with device ID or 'Error'
        """

        # Parse response from 'cmd diag config' for 'UUID'
        response = self.readDiagConfig()
        if response == 'Error':
            logger.error("Cannot read device ID from 'diag config'. It didn't reply.")
            return 'Error'
        else:
            for line in response:
                if line.startswith('UUID'):
                    uuid = line[24:48]
            logger.debug("Device ID from 'diag config' retrived as '"+uuid+"'.")

        return uuid

    def readOwnerID(self):
        """
        Reads owner ID from 'cmd diag config'

        :return String with owner ID or 'Error'
        """

        # Parse response from 'cmd diag config' for 'Owner UUID'
        response = self.readDiagConfig()
        if response == 'Error':
            logger.error("Cannot read owner ID from 'diag config'. It didn't reply.")
            return 'Error'
        else:
            for line in response:
                if line.startswith('Owner UUID'):
                    ownerid = line[24:48]
                    break
            logger.debug("Owner ID from 'diag config' retrived as '"+ownerid+"'.")

        return ownerid

    def getPoolList(self):
        """
        Reads list of pools with command 'cmd diag config'

        :return List of pool names or 'Error'
        """
        logger.debug("List of pools from command 'cmd diag all|grep Pools'.")

        cmd = "cmd diag all|grep 'Pool:'"

        pools = self.sshCmd(cmd)
        if pools == 'Error':
            logger.error("Failed to retrive pools from replicator")
            return 'Error'
        else:
            return pools

    def isClaimed(self):

        logger.debug("Validate availability of "+self.type+" '"+self.name+"'.")

        ownerid = self.readOwnerID()

        if ownerid == 'Error':
            return 'Error'
        elif ownerid == '000000000000000000000000':
            return 'Unclaimed'
        else:
            return 'Claimed'

    def buildInstall(self, build):
        """

        :param build:
        :return:
        """

        for x in range(1,self.maxwait):
            try:
                ret = urllib2.urlopen(build)
                break
            except:
                logger.warning("Something went wrong when try to access the build. Will re-try in "+str(self.timeout)+" seconds.")
                time.sleep(self.timeout)

        if ret.code == 200:
            logger.debug("Build exists at "+build)
        else:
            logger.error("Build is not available. Will skip installation.")
            return 99


        cmd = "upgrade-manager full none none "+build

        install = self.sshSudo(cmd)
        if install == 'Error':
            logger.error("Was not able to install new build on "+self.type+" '"+self.name+"'.")
            return 13
        else:
            logger.debug("Successfully run installation of new build on "+self.type+" '"+self.name+"'. Waiting up to "+str(10*self.timeout)+" seconds.")

        flag = 1
        for x in range (1,2*self.maxwait):
            time.sleep(self.timeout)
            version = self.readFWversion()
            if version == 'Error':
                 logger.debug(self.type +" '"+self.name+"' didn't come on-line after FW upgrate in "+str(x*self.timeout)+" seconds.")
                 flag = 1
            else:
                 logger.debug("After "+str(x*self.timeout)+" seconds "+self.type+" '"+self.name+"' reported FW version: '"+version+"'.")
                 flag = 0
                 break

        if flag == 1:
            logger.error(self.type +" '"+self.name+"' didn't come on-line after FW upgrate.")
            return 13
        else:
            return 0

    def buildFinder(self):

        import re, cgi

        logger.debug("Will search for latest build for '"+self.firmware+".x' version.")
        if self.qa_dev == 'dev':
            logger.debug("Working with build from BuildBot.")
            url = cfg.get('build','dev')
            path = '/Product/Device/installation/tfb/'
        else:
            logger.debug("Working with build from QA server.")
            url = cfg.get('build','qa')
            path = '/'

        builds = []

        if os.path.exists('build.tmp'):
            logger.debug("Delete old version of temporary file.")
            os.remove('build.tmp')
            time.sleep(5)

        try:
            wFile = urllib2.urlopen(url)
        except:
            logger.error("Unable to access BuildBot server at "+url+".")
            return 'Error'

        lFile = open("build.tmp",'w')

        tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')

        for i, line in enumerate(wFile):
            if line.startswith('<tr>'):
                no_tags = tag_re.sub('', line)
                build_name = cgi.escape(no_tags)
                name = build_name.split('/')
                if not name[0].startswith('Parent'):
                    new_line = url+name[0]+path+'\n'
                    lFile.writelines(new_line)

        wFile.close()
        lFile.close()

        for line in reversed(open("build.tmp").readlines()):
            wFile = urllib2.urlopen(line)
            for i, place in enumerate(wFile):
                if place.startswith('<tr>'):
                    no_tags = tag_re.sub('', place)
                    build_name = cgi.escape(no_tags)
                    if self.firmware != 'x.x':
                        key = 'tfb64-'+self.firmware
                    else:
                        key = 'tfb64-'
                    if build_name.startswith(key):
                        tarfile = build_name.split('tar.gz')
                        builds.append(line[:-1]+tarfile[0]+'tar.gz')

        if len(builds) < 1:
            logger.warning("Build with required prefix was not found.")
            return 'Error'

        return builds[0]

    def buildCheck(self):
        """

        :return:
        """

        if self.last == 'current':
            logger.debug("Configuration requires to run on previously installed build.")
            return 'Success'
        elif self.last == 'last':
            logger.debug("Configuration requires to install latest build.")
            build = self.buildFinder()
            if build == 'Error':
                logger.warning("Something went wrong when was finding the build. Will skipp installation.")
                return 'Error'
            else:
                logger.debug("Build path is: "+build)
            build_file = build[:44] + '/Product/Device/replicator/version/version.txt'
            r = requests.get(build_file)
            f = StringIO(r.content)
            build_ver = f.readline()[8:21]
        else:
            logger.debug("Configuration requires build from "+self.last)
            build_ver = 'forgetit'

        # Compare installed version with build version
        if build_ver == 'forgetit':
            logger.debug("Configuration requires specific build. It will be installed no matter what.")
        else:
            logger.debug("Will compare FW version on device versus build version.")
            tfb_ver = self.readFWversion()
            if tfb_ver.replace(' ','') == build_ver.replace(' ',''):
                logger.info("Build has same version as FW installed on "+self.type+" '"+self.name+"'. Will skip installation.")
                return 'Success'

        result = self.buildInstall(build)
        if result == 'Error':
            logger.error("Failed to install FW from "+build+".")
            return 'Error'

        return 'Success'


    def cmdSyncer(self,switch):

            syncer = 'cmd syncer '+switch

            result = self.sshCmd(syncer)

            if result == 'Error':
                logger.error("Was not able to "+switch+" syncer on "+self.type+" '"+self.name+"'.")
                return 13
            else:
                logger.debug("Syncer was "+switch+" on "+self.type+" '"+self.name+"'. Waiting "+str(self.timeout)+" seconds.")
                time.sleep(self.timeout)
            return 0

    def cmdReplicator(self,switch):
            """
            Disable syncer service on the Transporter.

            :param targetAddress: name or IP of the Transporter to work on <br>
            :param targetUser: user name to login on target <br>
            :return: True or False based on success <br>
            """

            replicator = '/etc/init.d/replicator '+switch

            result = self.sshSudo(replicator)

            if result == 'Error':
                logger.error("Was not able to "+switch+" replicator process on "+self.type+" '"+self.name+"'.")
                return 'Error'
            else:
                logger.debug("Replicator process is going to "+switch+" on "+self.type+" '"+self.name+"'. Waiting "+str(self.timeout)+" seconds.")
                time.sleep(self.timeout)
            return 'Success'

    def getPoolId(self,poolname):

        logger.debug("Retrive pool ID by pool name, which is "+poolname+" on "+self.type+" '"+self.name+"'.")
        reply = self.sshCmd('cmd pools|grep "Pool:"')
        pool_line = ''

        length = len(poolname)
        result = ""

        for line in reply:
            if poolname in line:
                    result = line[length+9:length+33]

        if result == "":
            logger.error("Pool '"+poolname+"' was not found on the "+self.type+" '"+self.name+"'.")
            return 13
        else:
            logger.debug("Pool '"+poolname+"' has id '"+result+".")
            return result

    def sshSudo(self,command):
        """
        Execute 'sudo' command over SSH

        :param command: *NIX command to be executed as sudo<br>
        :return: stdout
        """
        command = "echo "+self.pswd+"|sudo -S -p '' "+command
        reply = self.sshCmd(command)
        return reply

    def sshCmd(self,command):
        """
        Connects to the remote host over SSH and executes "command". If remote host is not available trys to reset power on it.

        :param command: Command to be executed on remote host.
        :return: STDOUT or 'Error'
        """

        logger.debug("Connecting with SSH to the host: '"+self.address+"' over port "+str(self.port)+".")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(self.address,self.port,self.user,self.pswd)
        except (socket.error,paramiko.AuthenticationException) as message:
            logger.warning("SSH connection failed: "+str(message)+".")
            return 'Error'

        logger.debug("Executing command '"+command+"' on remote host.")
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)

        reply = stdout.readlines()

        client.close()

        return reply

    def powerOn(self):

        logger.debug("Power on "+self.type+" '"+self.name+"'.")

        if (self.power < 1) or (self.power > 8):
            logger.error("Power port "+str(self.power)+"' is not manageble.")
            return 'Error'

        pdu = power.power()

        result = pdu.sendCommand('on',self.power)
        if result == 'Error':
            logger.error("Failed to power on "+self.type+" '"+self.name+"'.")
            return 'Error'
        else:
            return 'Success'

    def powerOff(self):

        logger.debug("Power off "+self.type+" '"+self.name+"'.")

        if (self.power < 1) or (self.power > 8):
            logger.error("Power port "+str(self.power)+"' is not manageble.")
            return 'Error'

        pdu = power.power()

        result = pdu.sendCommand('off',self.power)
        if result == 'Error':
            logger.error("Failed to power off "+self.type+" '"+self.name+"'.")
            return 'Error'
        else:
            return 'Success'

    def powerCycle(self):

        logger.debug("Power cycle "+self.type+" '"+self.name+"'.")

        if (self.power < 1) or (self.power > 8):
            logger.error("Power port "+str(self.power)+"' is not manageble.")
            return 'Error'

        pdu = power.power()

        result = pdu.sendCommand('reboot',self.power)
        if result == 'Error':
            logger.error("Failed to power cycle "+self.type+" '"+self.name+"'.")
            return 'Error'
        else:
            return 'Success'

    def powerRepower(self):

        logger.debug("Will power-off "+self.type+" '"+self.name+" and restore power after "+str(self.timeout)+" seconds.")

        logger.debug("Power-off.")
        reply = self.powerOff()
        if reply == 'Error':
            logger.error("Not able to power-off "+self.type+" '"+self.name)
            return 'Error'

        time.sleep(self.timeout)

        reply = self.powerOn()
        if reply == 'Error':
            logger.error("Not able to power-on "+self.type+" '"+self.name)
            return 'Error'

        return 'Success'

    def getPoolName(self,pool_id):

        import re

        logger.debug("Checking for actual pool name on device by pool ID, which is "+pool_id)
        pool_line = ''
        pool_name = 'Error'

        for x in range (1,self.maxwait+1):
            reply = self.sshCmd('cmd pools|grep "Pool:"')
            for line in reply:
                if pool_id not in line:
                    pool_line = ''
                else:
                    logger.debug("Found pool with ID '"+pool_id+"' on "+self.type+" '"+self.name+"'.")
                    pool_line = line
                    break

            if pool_line == '':
                logger.warning("Cannot find pool with ID '"+pool_id+"' on "+self.type+" '"+self.name+"'. Will wait "+str(self.timeout)+" seconds.")
                time.sleep(self.timeout)
            else:
                logger.debug("It took less than "+str(x*self.timeout)+" to create pool '"+pool_id+" on "+self.type+" '"+self.name+"'.")
                break

        if pool_line == '':
            logger.error("After "+str(x*self.timeout)+" seconds pool with ID '"+pool_id+"' still doesn't exist on "+self.type+" '"+self.name+"'.")
            return 'Error'

        quoted = re.compile("'[^']*'")
        for value in quoted.findall(pool_line):
            pool_name = value[1:-1]

        logger.debug("Pool with ID '"+pool_id+"' created with actual name '"+pool_name+"'.")
        return pool_name

    def getPoolTree(self,pool_id):

        logger.debug("Will return pool tree for pool with ID "+pool_id)

        ls_command = "find /replicator/storagePools/"+pool_id+" -type f -follow -print"

        reply = self.sshCmd(ls_command)

        tree = []

        for line in reply:
            line = line.replace('\r\n','')
            line = line.replace('/replicator/storagePools/'+pool_id,'')
            tree.append(line)

        return tree

    def checkPoolSync(self, pool_id):

        logger.debug("Will check synchronization status of pool '"+pool_id+"'.")

        sync = "cmd checkPoolSync "+pool_id
        status = ''

        reply = self.sshCmd(sync)

        for line in reply:
            line = line.strip('\n')
            if (line.startswith('Pool:')) and (pool_id in line):
                status = line[-7:-1]
                break

        if status =='hanges':
            status = 'PendingChanges'
        elif status == 'InSync':
            status = 'InSync'
        else:
            status = 'Error'

        return status

    def systemReboot(self):

        logger.debug("Will reboot "+self.type+" '"+self.name+"'.")

        command = "reboot -now"

        reply = self.sshSudo(command)

        return reply

    def doAction(self, switch):

        switches = ['nothing','reboot','re-power','power-on','power-off','crash','replicator stop','replicator start','upgrade','delete marker','destroy femq','destroy pending']

        if switch in switches:
            logger.debug("Atempt to "+switch+".")
        else:
            logger.error("Unable to perform unknown action: '"+switch+"'.")
            return 'Error'

        if switch == 'reboot':
            reply = self.systemReboot()
        elif switch == 're-power':
            reply = self.powerRepower()
        elif switch == 'power-off':
            reply = self.powerOff()
        elif switch == 'power-on':
            reply = self.powerOn()
        elif switch == 'crash':
            reply = self.killReplicator()
        elif switch == 'replicator stop':
            reply = self.cmdReplicator('stop')
        elif switch == 'replicator start':
            reply = self.cmdReplicator('start')
        elif switch == 'upgrade':
            reply = self.installBuild()
        elif switch == 'delete marker':
            reply = self.sshCmd('rm -f /replicator/configuration/clean_shutdown')
        elif switch == 'destroy femq':
            reply = self.sshCmd('echo "Try to read this file" > /replicator/configuration/clean_shutdown_femq')
        elif switch == 'destroy pending':
            reply = self.sshCmd('echo "Try to read this file" > /replicator/configuration/clean_shutdown_pending')
        else:
            logger.debug("Nothing to do.")
            reply = 'Success'

        if reply == 'Error':
            logger.error("Unable to reboot")
            return 'Error'
        else:
            return 'Success'

    def pidofReplicator(self):

        logger.debug("Will check process id for 'replicator' process on "+self.type+" '"+self.name+"'.")

        reply = self.sshCmd('pidof replicator')

        pid = ''
        if len(reply) == 0:
            logger.warning("Process ID for replicator returns empty string.")
        else:
            pid = reply[0]
            pid = pid.replace('\r\n','')

        return pid

    def killReplicator(self):

        logger.debug("Will kill replicator process on "+self.type+" '"+self.name+"'.")

        pid = self.pidofReplicator()
        if pid == '':
            logger.warning("Looks like replicator process is not running.")
            return 'Success'

        command = 'kill -9 '+pid
        result = self.sshCmd(command)
        if result == 'Error':
            logger.error("Something went wrong.")
            return 'Error'

        return 'Success'

    def deviceUnclaim(self):

        import taBackend as tab

        cs = tab.autoCS()

        device_id = self.readUUID()
        if device_id.lower() == 'error':
            logger.error("Cannot retrieve UUID of "+self.type+" '"+self.name+"'.")
            return 'Error'

        admin_id = self.readOwnerID()
        if admin_id.lower() == 'error':
            logger.error("Cannot retrive Owner ID of "+self.type+" '"+self.name+"'.")
            return "Error"

        result = cs.csUnclaimDeviceID(device_id,admin_id)
        if result == 'Error':
            logger.error("Failed to reset device.")
            return 'Error'

        logsave = self.saveLogs()
        if logsave == 'Error':
            logger.error("Failed to archive logs. Will miss them.")

        # Three extra restart of replicator should not hurt the system :)
        for x in range (1,3):
            restart = self.cmdReplicator('restart')
            if restart.lower() == 'error':
                logger.error("Failed to restart "+self.type+" '"+self.name+"'.")
                return 'Error'
            time.sleep(self.timeout)

        # Validate device was reset
        tStart = time.time()
        for x in range (1,6):
            time.sleep(self.timeout)
            newStat = self.isClaimed()
            if newStat.lower() != 'unclaimed':
                logger.warning(self.type+" '"+self.name+"' is not reset in "+str(time.time()-tStart)+" seconds after CS call.")
            else:
                logger.debug(self.type+" '"+self.name+"' was successfully reset with CS call.")
                break

        if newStat.lower() != 'unclaimed':
            logger.error("CS call failed to reset "+self.type+" '"+self.name+"' in "+str(time.time()-tStart)+" seconds.")
            return 'Error'
        else:
            return 'Success'

    def deviceClaim(self,auto_cs,admin_id):

        status = self.isClaimed()
        if status == 'Unclaimed':
            device_id = self.readUUID()
            result = auto_cs.csClaimDeviceID(device_id,admin_id)
            if result == 'Error':
                logger.error("Failed to claim device.")
                return 13
        else:
            logger.error("Cannot claim "+self.type+" '"+self.name+"'. It is already claimed.")
            return 99

        # Extra restart of replicator should not hurt the system :)
        restart = self.cmdReplicator('restart')
        if restart == 13:
            logger.error("Failed to restart "+self.type+" '"+self.name+"'.")
            return 99

        # Validate device is claimed
        newStat = ''
        tStart = time.time()
        for x in range (1,2*self.maxwait):
            time.sleep(self.timeout)
            newStat = self.isClaimed()
            if newStat != 'Claimed':
                logger.warning(self.type+" '"+self.name+"' is not claimed in "+str(time.time()-tStart)+" seconds after CS call.")
            else:
                logger.debug(self.type+" '"+self.name+"' was successfully claimed with CS call.")
                break

        if newStat != 'Claimed':
            logger.error("CS call failed to claim "+self.type+" '"+self.name+"'  in "+str(time.time()-tStart)+" seconds.")
            return 13

        logger.debug("Rename "+self.type+".")
        rename = auto_cs.csRenameDevice(device_id,self.name)
        if rename == 'Error':
            logger.warning("For some reason was not able to rename "+self.type+" '"+self.name+"'.")

        return 0

    def saveLogs(self):

        logger.debug("Archiving and storing replicator logs.")

        arj_name = time.strftime("%Y%b%d-%H%M%S",time.localtime(time.time()))+"_replicator_logs_from_"+self.type+"_"+self.name+".tar.gz"
        logs_dir = "/replicator/logs"

        command = "tar -zcvf "+arj_name+" "+logs_dir

        result = self.sshCmd(command)
        if result == 'Error':
            logger.error("Something went wrong, when try tar logs.")
            return 'Error'

        return 'Success'

    def waitSSH(self):


        logger.debug("Will wait for "+self.type+" '"+self.name+"' to start SSH deamon.")

        for x in range (1,2*self.maxwait):
            response = self.sshCmd('hostname')
            if response != 'Error':
                logger.debug("Device accessable over SSH. Response was "+response[0])
                return 'Success'
            else:
                time.sleep(self.timeout)

        return 'Error'

    def waitReplicator(self):

        logger.debug("Will wait for "+self.type+" '"+self.name+"' to start replicator.")

        for x in range (1,2*self.maxwait):
            response = self.pidofReplicator()
            if response != '':
                logger.debug("Replicator process is running. Process ID is "+response)
                return 'Success'
            else:
                time.sleep(self.timeout)

        return 'Error'

    def checkFile(self,filename):

        logger.debug("Will confirm file "+filename+" exists and it is file.")

        reply = self.sshCmd('[ -f /etc/hosts ] && echo "YES" || echo "NO"')
        if reply == 'YES':
            return 'Success'
        else:
            return 'Error'

    def checkShutdown(self):

        logger.debug("Validate, how graceful was last shutdown.")

        for x in range (1,11):
            replicator = self.pidofReplicator()
            if replicator != '':
                logger.debug("Replicator still running on "+self.type+" '"+self.name+"'. PID is "+replicator+". Will wait "+str(self.timeout)+" seconds.")
                time.sleep(self.timeout)
            else:
                break

        if replicator != '':
            logger.warning("Cannot determine shutdown, when replicator keeps running.")
            return 'Error'

        marker = self.checkFile('/replicator/configuration/clean_shutdown')
        if marker == 'Error':
            logger.warning("Graceful shutdown marker is missing on "+self.type+" '"+self.name+"'.")
            return 'ungraceful'

        femq = self.checkFile('/replicator/configuration/clean_shutdown_femq')
        if femq == 'Error':
            logger.warning("Graceful FEMQ file is missing on "+self.type+" '"+self.name+"'.")
            return 'ungraceful'

        pending = self.checkFile('/replicator/configuration/clean_shutdown_pending')
        if pending == 'Error':
            logger.warning("Graceful shutdown PENDING file is missing on "+self.type+" '"+self.name+"'.")
            return 'ungraceful'

        logger.debug("Last shutdown was graceful on "+self.type+" '"+self.name+"'.")
        return 'graceful'

    def reset(self):

        logger.info("Attempt to bring "+self.type+" '"+self.name+"' to default state.")

        # Check access to transporter
        for x in range (1, 6):
            response = self.waitSSH()
            if response.lower() == 'error':
                logger.warning("Device '"+self.name+"' cannot be reached over SSH.")
                chck = self.powerRepower()
                time.sleep(self.timeout)
            else:
                break

        if response.lower() == 'error':
            logger.error("Unable to SSH to "+self.type+" '"+self.name+"' after several power cycles.")
            return 'Error'

        # Check replicator is running
        for x in range (1, 6):
            response = self.waitReplicator()
            if response.lower() == 'error':
                logger.warning("Cannot get process ID for Replicator on '"+self.name+"'.")
                chck = self.cmdReplicator('restart')
                time.sleep(self.timeout)
            else:
                break

        if response.lower() == 'error':
            logger.error("Unable to start replicator on "+self.type+" '"+self.name+"' after several attempts.")
            return 'Error'

        # Check device is not claimed
        for x in range (1, 6):
            status = self.isClaimed()
            if status.lower() == 'unclaimed':
                logger.debug("Device '"+self.name+"' is in default state.")
                return 'Success'
            else:
                chck = self.deviceUnclaim()
                time.sleep(self.timeout)

        return 'Error'
