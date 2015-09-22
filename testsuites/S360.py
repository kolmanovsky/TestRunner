#!/usr/bin/env python

# import include modules
import time
import taBackend as css
import taUser as usr
import taTransporter as tfb
import taClient as clt
from testbot import cfg
import logging

logger = logging.getLogger('S360')

class testSuite:

    def __init__(self):

        self.testcases = ['C34209']
        #self.testcases = ['C34209','C34210','C34211','C34212','C34213','C34214','C34215','C34216','C34217','C34218']
        self.suiteid = 'S360'
        self.suitename = "AUTO: Graceful shutdown"
        self.pool = 'AUTO_'+self.suiteid
        self.timeout = int(cfg.get('general','timeout'))
        self.wide = 5

    # ==============================================================
    # Test cases
    # ==============================================================

    # Replicator crash, scan on start-up
    def C34209(self,testbed):

        logger.debug("Start replicator after crash.")

        action1 = 'crash'
        action2 = 'nothing'

        result = self.testCase(testbed,action1,action2)
        if result != 0:
            logger.error("Test case C34209 didn't pass. Returned code is '"+str(result)+"'.")
            return result
        else:
            return result

    # Graceful shutdown, no scan on start-up
    def C34210(self,testbed):
        return 0

    # System reboot, no scan on start-up
    def C34211(self,testbed):
        return 0

    # FW upgrade, no scan on start-up
    def C34212(self):
        return 0

    # Crash during graceful shutdown, scan on start-up
    def C34213(self):
        return 0

    # Damaged graceful shutdown (no marker), scan on start-up
    def C34214(self):
        return 0

    # Damaged graceful shutdown (unreadable file 1), scan on start-up
    def C34215(self):
        return 0

    # Damaged graceful shutdown (unreadable file 2), scan on start-up
    def C34216(self):
        return 0

    # Replicator stop during graceful shutdown, no scan on start-up
    def C34217(self):
        return 0

    # Graceful shutdown during start-up scan
    def C34218(self):
        return 0

    # ==============================================================
    # Local functions
    # ==============================================================
    def testCase(self,testbed,action1,action2):

        logger.info("Transporter will perform "+action1+", then "+action2+" and then check start-up scan.")

        logger.debug("Getting list of devices and users.")
        devices = testbed.getlist('target')
        users = testbed.getlist('user')
        clients = testbed.getlist('client')
        if len(users) < 2:
            logger.error("This test requires at least 2 users. "+str(len(users))+" defined.")
            return 99

        cs = css.autoCS()
        cs_url = cs.csurl
        logger.debug("Got URL to send requests to CS - "+cs_url+".")

        orgadmin = usr.autoUser(users[0])
        admin_id = orgadmin.getCustomerID()
        logger.debug("Got customer ID ("+admin_id+") for org admin ("+users[0]+").")

        customer = usr.autoUser(users[1])
        customer_id = customer.getCustomerID()
        logger.debug("Got customer ID ("+customer_id+") for regular user ("+users[1]+").")

        # Claim primary transporter (first from the list of devices)
        primo = tfb.taTransporter(devices[0])
        status = primo.deviceClaim(cs,admin_id)
        if status == 99:
            logger.error("Cannot execute test case: environment is not ready.")
            return 99
        elif status == 13:
            logger.error("Cannot claim "+primo.type+" '"+primo.name+"'.")
            return 13
        else:
            logger.debug(primo.type+" '"+primo.name+"' was successfully claimed.")

        # Claim secondary transporter (second from the list of devices)
        secundo = tfb.taTransporter(devices[1])
        status = secundo.deviceClaim(cs,admin_id)
        if status == 99:
            logger.error("Cannot execute test case: environment is not clean.")
            return 99
        elif status == 1:
            logger.error("Cannot claim "+secundo.type+" '"+secundo.name+"'.")
            return 13
        else:
            logger.debug(secundo.type+" '"+secundo.name+"' was claimed.")

        # Will use client to plant directory tree in the pool
        seller = clt.autoClient(clients[0])

        # Will need multiple pools during the test
        pools = []
        for x in range (1,self.wide+1):
            lengh = len(str(x))+1
            poolname = self.pool+"-"+str(x).zfill(lengh)

            # Create pool as org admin, send invitation to the user and accept invitation as user
            pool_id = cs.poolSetup(poolname,admin_id,customer_id)
            if pool_id == 'Error':
                logger.error("Unable to setup pool '"+poolname+"'.")
                break

            logger.debug("Pool '"+poolname+"' was successfully setup. It has ID '"+pool_id+"'.")

            # Check transporters for new pool and verify/update pool name
            for device in devices:
                target = tfb.taTransporter(device)
                poolname = target.getPoolName(pool_id)
                if poolname == 'Error':
                    logger.error("Pool "+poolname+"'was not created on "+target.type+" '"+target.name+"'.")
                else:
                    logger.debug("Pool "+poolname+"'was created on "+target.type+" '"+target.name+"'.")

            # Waiting for client to get pool from transporter
            logger.debug("Waiting for pool '"+poolname+"' to get populated on client '"+seller.name+"'.")
            pool_exists = False
            for x in range (1,11):
                pool_exists = seller.directoryExists(poolname)
                if pool_exists:
                    logger.debug("Pool '"+poolname+"' directory was populated on the client '"+seller.name+"'.")
                    break
                else:
                    logger.warning("Pool '"+poolname+"' doesn't exist on client '"+seller.name+"' after "+str(x*self.timeout)+" seconds.")
                    time.sleep(self.timeout)

            if not pool_exists:
                logger.error("For some reason pool '"+poolname+"' was not populated on client '"+seller.name+"'. Will not use it.")
            else:
                pools.append(poolname)

        poolscount = len(pools)
        if poolscount < 3:
            logger.error("There are not enough shared pools on client '"+seller.name+"'.")
            return 13
        else:
            logger.debug("Test case will use "+str(poolscount)+" pools.")


        # Mount network storage on client and copy pre-generated directory structure to the pool
        gard = seller.plantTree(pools[0])
        if gard == 'Error':
            logger.error("Failed to plant tree - copy directory structure from network storage to the pool directory.")
            return 13

        # Waiting for pool synchronization
        logger.debug("Waiting up to "+str(30*self.timeout)+" seconds for pool synchronisation on "+primo.type+" '"+primo.name+"'.")
        last = 0
        diff = []
        for x in range(1,31):
            time.sleep(self.timeout)
            clienside = seller.cleanTree(pools[pools.keys()[0]])
            transporter = primo.getPoolTree(pools.keys()[0])
            diff = list(set(clienside) - set(transporter))
            last = len(diff)
            if last == 0:
                logger.debug("Source and destination are the same.")
                status = 'InSync'
                break
            else:
                logger.debug("After "+str(x*self.timeout)+" seconds source and distination are different.")

        if last != 0:
            x = 1
            for element in diff:
                logger.warning(str(x).zfill(len(str(last)))+". '"+element+"'.")
                x = x + 1
            return 13

        # Play in pools - copy content from orgpool to another pool
        src = seller.tpath+pools[pools.keys()[0]]+"/vault"
        dst = seller.tpath+pools[pools.keys()[1]]+"/vault"
        response = seller.copyTree(src,dst)
        if response == 'Error':
            logger.error("Fail to play in pool. Step 1 - copy")
            return 13

        # Play in pool - move content from orgpool to another pool
        dst = seller.tpath+pools[pools.keys()[2]]+"/vault"
        response = seller.copyTree(src,dst)
        if response == 'Error':
            logger.error("Fail to play in pool. Step 2.1 - copy")
            return 13

        response = seller.delTree(src)
        if response == 'Error':
            logger.error("Fail to play in pool. Step 2.2 - delete")
            return 13

        logger.debug("Will wait "+str(3*self.timeout)+" seconds to start pool syncronization.")
        for x in range (1,4):
            time.sleep(self.timeout)
            logger.debug("Passed "+str(x*self.timeout)+" of "+str(3*self.timeout)+" seconds.")

        if action1 != 'nothing':
            logger.debug("Will "+action1+" "+secundo.type+" '"+secundo.name+"'.")
            reply = secundo.doAction(action1)
            if reply == 'Error':
                logger.error("Failed to "+action1+" "+secundo.type+" '"+secundo.name+"'.")
                return 13

            #log.debug("Will wait "+str(3*self.timeout)+" seconds before second action.")
            #for x in range (1,4):
            #    time.sleep(self.timeout)
            #    log.debug("Passed "+str(x*self.timeout)+" of "+str(3*self.timeout)+" seconds.")

        result1 = secundo.checkShutdown()
        if result1 == 'Error':
            logger.error(action1.capitalize()+" on "+secundo.type+" '"+secundo.name+"' didn't cause shutdown.")
            return 13
        else:
            logger.debug(action1.capitalize()+" on "+secundo.type+" '"+secundo.name+"' cause "+result1+" shutdown.")

        if action2 != 'nothing':
            delay = 2
            logger.debug("Will wait "+str(delay)+" seconds before "+action2+" on "+secundo.type+" '"+secundo.name+"'.")
            time.sleep(delay)
            logger.debug("Will "+action2+" "+secundo.type+" '"+secundo.name+"'.")
            reply = secundo.doAction(action2)
            if reply == 'Error':
                logger.error("Failed to "+action2+" "+secundo.type+" '"+secundo.name+"'.")
                return 13

            status = secundo.waitDevice(30)
            if status == 13:
                logger.error(secundo.type+" '"+secundo.name+"' didn't restart replicator after "+action2+".")
                return 13

        status = secundo.sshCmd("cat /replicator/logs/replicator_0.log |grep Startup")
        pending = []

        for line in status:
            _,response = line.split('Startup')
            print response


        return 0