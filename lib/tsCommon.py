#!/usr/bin/env python

# import include modules

import os
import ConfigParser
from testbot import log, cfg
import usCommon as usr
import tbCommon as tfb
import clCommon as clt

class autoSetup:
    """
    this class wraps a bunch of funtions that are all involved in setting up and tearing down a test environment

    """
    def __init__(self,suite):

        self.suite = suite
        self.timeout = cfg.get('general','timeout')

        path = os.path.join(os.getcwd(),'testsuites')

        fileName = self.suite+'.cfg'
        list = os.path.join(path,fileName)

        log.debug("Will read information from config file '"+fileName+"'.")

        conf = ConfigParser.RawConfigParser()
        conf.read(list)

        try:
            self.targets = conf.get('testbed','target')
            self.clients = conf.get('testbed','client')
            self.trun = conf.get('testrail','run')
            self.users = conf.get('testbed','user')
        except:
            log.error("Cannot read all information from '"+fileName+"'.")

    def getSystemList(self,system):

        log.debug("Will read list of "+system+"s.")

        allSystems = []

        if system == 'target':
            list = self.targets
        elif system == 'client':
            list = self.clients
        elif system == 'user':
            list = self.users
        else:
            log.error("Cannot read list of "+system+"s.")
            return 'Error'

        devices = list.split(',')
        for eachDev in devices:
            allSystems.append(eachDev.strip())

        counter = len(devices)
        if counter == 0:
            log.warning("Found 0 "+system+"s.")
            return 'Error'
        else:
            if counter == 1:
                log.debug("Found 1 "+system+".")
            else:
                log.debug("Found "+str(counter)+" "+system+"s.")
            log.debug(system.capitalize()+"'s list: "+str(allSystems))

        return allSystems

    def getSetup(self):

        log.debug("Getting testbed configuration.")

        for system in ['target','client','user']:
            devices = self.getSystemList(system)
            if devices == 'Error':
                log.error("Cannot get information about "+system+"s, to use in test suite.")
                return 'Error','Error','Error','Error'
            else:
                log.debug("Successfuly got information about "+system+"s, to use in test suite.")
                if system == 'target':
                    targets = devices
                elif system == 'client':
                    clients = devices
                elif system == 'user':
                    users = devices
                else:
                    log.warning("I don't know what the strange part of set is '"+system+"'. Whatever. Will ignore.")

        return clients, targets, users

    def checkSetup(self):

        log.debug("Check availability of all testbed components.")

        # Get setup

        clients, targets, users = self.getSetup()
        if clients == 'Error':
            log.error("Failed to read setup for test suite. Cannot proceed.")
            return 99

        # Validate setup

        for client in clients:
            system = clt.autoClient(client)
            status = system.checkClient()
            if status == 'Error':
                log.error("Client '"+client+"' is not available for test execution.")
                return 99
            else:
                log.debug("Client '"+client+"' is available for test execution. It runs "+status+".")

        for target in targets:
            system = tfb.autoTarget(target)
            status = system.isClaimed()
            if status == 'Unclaimed':
                log.debug("Target '"+target+"' passed pre-fly check. It is "+status.lower()+".")
            else:
                log.error("Target '"+target+"' is not ready for test execution.")
                return 99

        for user in users:
            system = usr.autoUser(user)
            status = system.getCustomerID()
            if status == 'Error':
                log.error("User '"+user+"' is not ready for test execution.")
                return 99
            else:
                log.debug("User '"+user+"' passed pre-fly check. Has CID "+status+".")
        return 0

    def checkIn(self):
        return 0

    def cleanUp(self):
        return 0





