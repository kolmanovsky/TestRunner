#!/usr/bin/env python

# import include modules
import time
import csCommon as css
import usCommon as usr
import tbCommon as tfb
import clCommon as clt
from testbot import cfg

class testSuite:

    def __init__(self):

        #self.testcases = ['C34126']
        self.testcases = ['C34126','C34127','C34128','C34129','C34130','C34131','C34132','C34133']
        self.suiteid = 'S358'
        self.suitename = "AUTO: Initial play"
        self.pool = 'AUTO_'+self.suiteid
        self.timeout = int(cfg.get('general','timeout'))

    # ==============================================================
    # Test cases
    # ==============================================================

    # Claim primary device, reset primary device
    def C34126(self,testbed):

        switch_1 = 'nothing'
        switch_2 = 'nothing'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Claim primary device, add secondary device
    def C34127(self,testbed):

        switch_1 = 'nothing'
        switch_2 = 'nothing'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Crash replicator on secondary device
    def C34128(self,testbed):

        switch_1 = 'nothing'
        switch_2 = 'crash'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Reset power on secondary device
    def C34129(self,testbed):

        switch_1 = 'nothing'
        switch_2 = 're-power'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Reboot secondary device
    def C34130(self,testbed):

        switch_1 = 'nothing'
        switch_2 = 'reboot'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Crash replicator on primary device
    def C34131(self,testbed):

        switch_1 = 'crash'
        switch_2 = 'nothing'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Reset power on primary device
    def C34132(self,testbed):

        switch_1 = 're-power'
        switch_2 = 'nothing'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # Reboot primary device
    def C34133(self,testbed):

        switch_1 = 'reboot'
        switch_2 = 'nothing'

        result = self.testCase(testbed,switch_1,switch_2)
        return result

    # ==============================================================
    # Local functions
    # ==============================================================
    def poolSetup(self,auto_cs,pool,admin_id,client_id):

            log.debug("Will create pool '"+pool+"'.")
            pool_id = auto_cs.csAddPool(pool,admin_id,'MW','','',None)
            if pool_id == 13:
                log.error("Failed to create pool '"+pool+"'.")
                return 'Error'
            else:
                log.debug("Pool '"+pool+"' successfully created. Pool ID is '"+pool_id+"'.")

            # Send invitation to the pool
            invitation = auto_cs.csSendPoolInvitation(pool_id,admin_id,client_id)
            if invitation == 'Error':
                log.error("No invitation was send for pool '"+pool+"'.")
                return 'Error'
            else:
                log.debug("Invitation '"+invitation+"' for pool '"+pool+"' was send to the used with ID '"+client_id+"'.")

            # Accept invitation to the pool
            acceptance = auto_cs.csAckPoolInvitation(invitation,client_id,True)
            if acceptance == 'Error':
                log.error("Failed to accept invitation to the pool '"+pool+"'.")
                return 'Error'
            else:
                log.debug("Invitation was successfully accepted.")

            return pool_id

    def testCase(self,testbed,switch_1,switch_2):

        log.debug("Primary transporter will perform "+switch_1+", secondary transporter will perform "+switch_2+" during synchronization.")

        log.debug("Getting list of devices and users.")
        devices = testbed.getSystemList('target')
        users = testbed.getSystemList('user')
        clients = testbed.getSystemList('client')
        if len(users) < 2:
            log.error("This test requires at least 2 users. "+str(len(users))+" defined.")
            return 99

        auto_cs = css.autoCS()
        cs_url = auto_cs.csurl
        log.debug("Got URL to send requests to CS - "+cs_url+".")

        orgadmin = usr.autoUser(users[0])
        admin_id = orgadmin.getCustomerID()
        log.debug("Got customer ID ("+admin_id+") for org admin ("+users[0]+").")

        customer = usr.autoUser(users[1])
        customer_id = customer.getCustomerID()
        log.debug("Got customer ID ("+customer_id+") for regular user ("+users[1]+").")

        # Claim primary transporter (first from the list of devices)
        primo = tfb.autoTarget(devices[0])
        status = primo.deviceClaim(auto_cs,admin_id)
        if status == 99:
            log.error("Cannot execute test case: environment is not ready.")
            return 99
        elif status == 13:
            log.error("Cannot claim "+primo.type+" '"+primo.name+"'.")
            return 13
        else:
            log.debug(primo.type+" '"+primo.name+"' was successfully claimed.")

        # Verify clients (check path to the TL, check pools are present)
        for client in clients:
            currclient = clt.autoClient(client)
            log.debug("Client computer '"+currclient.name+"' running OS "+currclient.platform+".")
            log.debug("Local path to the Transporter Library is '"+currclient.tlpath+"'.")

        # Will use client to plant directory tree in the pool
        seller = clt.autoClient(clients[0])

        # Using CS calls: create pool as org admin, send invitation to the user and accept invitation as user
        pool_id = self.poolSetup(auto_cs,self.pool,admin_id,customer_id)
        if pool_id == 'Error':
            log.error("Unable to setup pool '"+self.pool+"'.")
            return 13
        else:
            log.debug("Pool '"+self.pool+"' was successfully setup.")

        # Waiting for transporter to create pool and verify/update pool name
        log.debug("Checking for pool '"+self.pool+"' on claimed device.")
        pool_name = 'Error'
        for x in range(1,11):
            time.sleep(self.timeout)
            pool_name = primo.getPoolName(pool_id)
            if pool_name == 'Error':
                log.error("Pool was not created on device in "+str(x*self.timeout)+" seconds.")
            else:
                log.debug("Pool '"+pool_name+"' was created on device in "+str(x*self.timeout)+" seconds.")
                break

        if pool_name == 'Error':
            log.error("Will not wait any more.")
            return 13

        # Waiting for client to get pool from transporter
        log.debug("Waiting for pool '"+pool_name+"' to get populated on client '"+seller.name+"'.")
        pool_exists = False
        for x in range (1,10):
            pool_exists = seller.directoryExists(pool_name)
            if pool_exists:
                log.debug("Pool '"+pool_name+"' directory was populated on the client '"+seller.name+"'.")
                break
            else:
                log.warning("Pool '"+pool_name+"' doesn't exist on client '"+seller.name+"' after "+str(x*self.timeout)+" seconds.")
                time.sleep(self.timeout)

        if not pool_exists:
            log.error("For some reason pool '"+pool_name+"' was not populated on client '"+seller.name+"'. Will not wait anymore.")
            return 13

        # Mount network storage on client and copy pre-generated directory structure to the pool
        gard = seller.plantTree(pool_name)
        if gard == 'Error':
            log.error("Failed to plant tree - copy directory structure from network storage to the pool directory.")
            return 13

        # Waiting for pool syncronization
        log.debug("Waiting up to "+str(30*self.timeout)+" seconds for pool synchronisation on "+primo.type+" '"+primo.name+"'.")
        last = 0
        diff = []
        for x in range(1,31):
            time.sleep(self.timeout)
            clienside = seller.cleanTree(pool_name)
            transporter = primo.getPoolTree(pool_id)
            diff = list(set(clienside) - set(transporter))
            last = len(diff)
            if last == 0:
                log.debug("Source and destination are the same.")
                status = 'InSync'
                break
            else:
                log.debug("After "+str(x*self.timeout)+" seconds source and distination are different.")

        if last != 0:
            x = 1
            for element in diff:
                log.warning(str(x).zfill(len(str(last)))+". '"+element+"'.")
                x = x + 1
            return 13

        # Get directory tree from primary transporter
        source = primo.getPoolTree(pool_id)

        # Claim secondary device (first from the list of devices)
        secundo = tfb.autoTarget(devices[1])
        status = secundo.deviceClaim(auto_cs,admin_id)
        if status == 99:
            log.error("Cannot execute test case: environment is not clean.")
            return 99
        elif status == 1:
            log.error("Cannot claim "+secundo.type+" '"+secundo.name+"'.")
            return 13
        else:
            log.debug(secundo.type+" '"+secundo.name+"' was claimed.")

        log.debug("Will wait "+str(3*self.timeout)+" seconds to start pool syncronization.")
        for x in range (1,4):
            time.sleep(self.timeout)
            log.debug("Passed "+str(x*self.timeout)+" of "+str(3*self.timeout)+" seconds.")

        if switch_1 != 'nothing':
            log.debug("Will "+switch_1+" "+primo.type+" '"+primo.name+"'.")
            reply = primo.doAction(switch_1)
            if reply == 'Error':
                log.error("Failed to "+switch_1+" "+primo.type+" '"+primo.name+"'.")
                return 13

            status = primo.waitDevice(30)
            if status == 13:
                log.error(primo.type+" '"+primo.name+"' didn't restart replicator after "+switch_1+".")
                return 13

        if switch_2 != 'nothing':
            log.debug("Will "+switch_2+" "+secundo.type+" '"+primo.name+"'.")
            reply = secundo.doAction(switch_2)
            if reply == 'Error':
                log.error("Failed to "+switch_2+" "+secundo.type+" '"+secundo.name+"'.")
                return 13

            status = secundo.waitDevice(30)
            if status == 13:
                log.error(secundo.type+" '"+secundo.name+"' didn't restart replicator after "+switch_2+".")
                return 13

        # Waiting for syncronization between two transporters
        log.debug("Will sleep up to 50 cycles for synchronization.")
        last = 1
        diff = []
        for x in range (1,51):
            destination = secundo.getPoolTree(pool_id)
            diff = list(set(source) - set(destination))
            last = len(diff)
            if last == 0:
                log.info("Pool got synced on both devices.")
                break
            else:
                log.debug("This is cycle No."+str(x)+". Source and distination are different.")
                time.sleep(self.timeout)

        if last == 0:
            return 0
        else:
            log.info("Pool didn't sync-up in "+str(50*self.timeout)+" seconds.")
            x = 1
            for element in diff:
                log.debug(str(x).zfill(len(str(last)))+". '"+element+"'.")
                x = x + 1
            return 1

