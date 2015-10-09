#!/usr/bin/env python

# import include modules
import time
import taBackend as css
import taUser as usr
import taTransporter as tfb
import taClient as clt
from testbot import cfg
import logging

logger = logging.getLogger('S369')

class testSuite:

    def __init__(self):

        self.testcases = ['C35645']
        self.suiteid = 'S369'
        self.suitename = "AUTO: Multy transporter sync"
        self.pool = 'AUTO_'+self.suiteid
        self.timeout = int(cfg.get('general','timeout'))
        self.wide = 5

    # ==============================================================
    # Test cases
    # ==============================================================

    # Basic test
    def C35645(self,testbed):

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
        admin_id = testbed.userAdminId()

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

        # Create pool as org admin
        pool_id = cs.csAddPool(poolname,admin_id)
        if pool_id == 'Error':
            logger.error("Failed to create pool '"+poolname+"'.")
            return 13

        # Invite to all users to the pool
        for user in users:
            customer = usr.autoUser(user)
            user_id = customer.getCustomerID()

            # Send invitation
            invitation = cs.csSendPoolInvitation(pool_id,admin_id,user_id)
            if invitation == 'Error':
                logger.error("No invitation was send for pool '"+poolname+"'.")
                return 'Error'
            else:
                logger.debug("Invitation '"+invitation+"' for pool '"+poolname+"' was send to the user with ID '"+user_id+"'.")

            # Accept invitation
            acceptance = cs.csAckPoolInvitation(invitation,user_id,True)
            if acceptance == 'Error':
                logger.error("Failed to accept invitation to the pool '"+poolname+"'.")
                return 'Error'
            else:
                logger.debug("Invitation was successfully accepted.")

        # Checking clients have pool from transporter
        for client in clients:
            desktop = clt.autoClient(client)
            logger.debug("Waiting for pool '"+poolname+"' to get populated on client '"+desktop.name+"'.")
            pool_exists = False
            for x in range (1,6):
                pool_exists = desktop.directoryExists(poolname)
                if pool_exists:
                    logger.debug("Pool '"+poolname+"' directory was populated on the client '"+desktop.name+"'.")
                    break
                else:
                    logger.warning("Pool '"+poolname+"' doesn't exist on client '"+desktop.name+"' after "+str(x*self.timeout)+" seconds.")
                    time.sleep(self.timeout)

            if not pool_exists:
                logger.error("For some reason pool '"+poolname+"' was not populated on client '"+desktop.name+"'. Will not wait anymore.")
                return 'Error'

        # Delete users from devices except only one per device
        for x in range (0,3):
            transporter = tfb.taTransporter(devices[x])
            device_id = transporter.readUUID()
            if device_id == 'Error':
                logger.error("Failed read device UUID for "+transporter.type+" '"+transporter.name+"'.")
                return 'Error'
            for user in users:
                customer = usr.autoUser(user)
                user_id = customer.getCustomerID()
                if users.index(user) == x:
                    logger.debug("User '"+customer.name+"' will stay on "+transporter.type+" '"+transporter.name+"'.")
                else:
                    logger.debug("User '"+customer.name+"' will be deleted from "+transporter.type+" '"+transporter.name+"'.")
                    status = cs.csDeleteUser(admin_id,device_id,user_id)
                    if status == 'Error':
                        logger.error("Unable to remove user '"+customer.name+"' from "+transporter.type+" '"+transporter.name+"'.")
                        return 'Error'
                    else:
                        logger.debug("User '"+customer.name+"' was successfully deleted from "+transporter.type+" '"+transporter.name+"'.")

        # Pause replication
        for device in devices:
            transporter = tfb.taTransporter(device)
            status = transporter.cmdReplicator('stop')
            if status == 'Error':
                logger.error("Unable to stop replicator on "+transporter.type+" '"+transporter.name+"'.")
                return 'Error'
            else:
                logger.debug("Replicator was stopped on "+transporter.type+" '"+transporter.name+"'.")

        # Will use client to plant directory tree in the pool
        for client in clients:
            desktop = clt.autoClient(client)

            # Mount network storage on client and copy pre-generated directory structure to the pool
            gard = desktop.plantTree(poolname)
            if gard == 'Error':
                logger.error("Failed to plant tree - copy directory structure from network storage to the pool directory.")
                return 'Error'
            else:
                logger.debug("Tree was successfully planted on client '"+desktop.name+"'.")


        return 0