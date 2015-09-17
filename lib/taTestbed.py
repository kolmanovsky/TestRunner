#!/usr/bin/env python

# import include modules

import os
import ConfigParser
import logging
from autobot import cfg
import taUser as usr
import taTransporter as tfb
import taClient as clt

logger = logging.getLogger('taTestbed')


class taTestbed:
    """

    """
    def __init__(self,suite):

        self.suite = suite
        self.timeout = int(cfg.get('general', 'timeout'))

        path = os.path.join(os.getcwd(), 'testsuites')

        filename = self.suite+'.cfg'
        fullname = os.path.join(path,filename)

        logger.debug("Will read information from config file '"+filename+"'.")

        conf = ConfigParser.RawConfigParser()
        conf.read(fullname)

        try:
            self.targets = conf.get('testbed', 'target')
            self.clients = conf.get('testbed', 'client')
            self.trrun = conf.get('testrail', 'run')
            self.users = conf.get('testbed', 'user')
        except:
            logger.error("Cannot read information from '"+filename+"'.")

    def getlist(self,system):

        logger.debug("Will read list of "+system+"s.")

        systems = []

        if system == 'target':
            syslist = self.targets
        elif system == 'client':
            syslist = self.clients
        elif system == 'user':
            syslist = self.users
        else:
            logger.error("Cannot read list of "+system+"s.")
            return 'Error'

        devices = syslist.split(',')
        for eachDev in devices:
            systems.append(eachDev.strip())

        counter = len(devices)
        if counter == 0:
            logger.warning("Found 0 "+system+"s.")
            return 'Error'
        else:
            if counter == 1:
                logger.debug("Found 1 "+system+".")
            else:
                logger.debug("Found "+str(counter)+" "+system+"s.")
            logger.debug(system.capitalize()+"'s list: "+str(systems))

        return systems

    def getsetup(self):

        logger.debug("Getting testbed configuration.")

        for system in ['target', 'client', 'user']:
            devices = self.getlist(system)
            if devices == 'Error':
                logger.error("Cannot get information about "+system+"s, to use in test suite.")
                return 'Error', 'Error', 'Error'
            else:
                logger.debug("Successfully got information about "+system+"s, to use in test suite.")
                if system == 'target':
                    targets = devices
                elif system == 'client':
                    clients = devices
                elif system == 'user':
                    users = devices
                else:
                    logger.warning("I don't know what the strange part of set is '"+system+"'. Whatever. Will ignore.")

        return clients, targets, users

    def checksetup(self):

        logger.info("Check availability of all testbed components.")

        # Get setup
        clients, targets, users = self.getsetup()
        if clients.lower() == 'error':
            logger.error("Failed to read setup for test suite. Cannot proceed.")
            return 'Error'

        # Validate setup
        for client in clients:
            system = clt.autoClient(client)
            status = system.checkClient()
            if status.lower() == 'error':
                logger.error("Client '"+client+"' is not available for test execution.")
                return 'Error'
            else:
                logger.debug("Client '"+client+"' is available for test execution. It runs "+status+".")

        for target in targets:
            system = tfb.taTransporter(target)
            status = system.isClaimed()
            if status.lower() == 'unclaimed':
                logger.debug("Target '"+target+"' passed pre-fly check. It is "+status.lower()+".")
            else:
                logger.error("Target '"+target+"' is not ready for test execution.")
                return 'Error'

        for user in users:
            system = usr.autoUser(user)
            status = system.getCustomerID()
            if status.lower() == 'error':
                logger.error("User '"+user+"' is not ready for test execution.")
                return 'Error'
            else:
                logger.debug("User '"+user+"' passed pre-fly check. Has CID "+status+".")
        return 'Success'

    def cleanup(self):

        logger.info("Attempt to bring testbed into default state.")

        # Get setup
        clients, targets, users = self.getsetup()
        if clients.lower() == 'error':
            logger.error("Failed to read setup for test suite. Cannot proceed.")
            return 'Error'

        # Reset clients
        for client in clients:
            system = clt.autoClient(client)
            status = system.reset()
            if status.lower() == 'error':
                logger.error("Unable to reset client '"+client+"'.")
                return 'Error'
            else:
                logger.info("Client '"+client+"' was successfully reset.")

        # Reset targets
        for target in targets:
            system = tfb.taTransporter(target)
            status = system.reset()
            if status.lower() == 'error':
                logger.error("Unable to reset '"+target+"'.")
                return 'Error'
            else:
                logger.info("Target '"+target+"' was successfully reset.")
