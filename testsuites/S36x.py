#!/usr/bin/env python

# import include modules
import time
import taBackend as css
import taUser as usr
import taTransporter as tfb
import taClient as clt
from testbot import cfg
import logging

logger = logging.getLogger('S36x')

class testSuite:

    def __init__(self):

        self.testcases = ['Cxxxxx']
        self.suiteid = 'S36x'
        self.suitename = "AUTO: Three way conflict"
        self.pool = 'AUTO_'+self.suiteid
        self.timeout = int(cfg.get('general','timeout'))
        self.wide = 5

    # ==============================================================
    # Test cases
    # ==============================================================

    # Basic test
    def Cxxxxx(self,testbed):

        logger.debug("Three way synchronization with pause.")

        result = self.testCase(testbed)
        if result != 0:
            logger.error("Test case "+__name__+" didn't pass. Returned code is '"+str(result)+"'.")
            return result
        else:
            return result


    # ==============================================================
    # Local functions
    # ==============================================================
    def testCase(self,testbed):

        logger.debug("Getting list of devices and users.")
        devices = testbed.getlist('target')
        users = testbed.getlist('user')
        clients = testbed.getlist('client')

        cs = css.autoCS()
        cs_url = cs.csurl
        logger.debug("Got URL to send requests to CS - "+cs_url+".")

        # Get admins ID
        admin_id = testbed.getAdminID()

        # Claim three transporters
        for device in devices:
            transporter = tfb.taTransporter(device)
            status = transporter.deviceClaim(cs,admin_id)
            if status != 0:
                logger.error("Cannot claim "+transporter.type+" '"+transporter.name+"'.")
                return 13
            else:
                logger.debug(transporter.type+" '"+transporter.name+"' was successfully claimed.")

        # Will wait to let transporters find each other
        logger.debug("Will wait "+str(self.timeout)+" seconds to let transporters find each other.")
        time.sleep(self.timeout)

        poolname = self.pool+"-01"

        print poolname

        # Create pool as org admin
        pool_id = cs.csAddPool(self,poolname,admin_id)
        if pool_id == 'Error':
            logger.error("Failed to create pool '"+poolname+"'.")
            return 13

        return 0