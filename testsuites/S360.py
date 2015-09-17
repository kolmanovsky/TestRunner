#!/usr/bin/env python

# import include modules
import time
import csCommon as css
import usCommon as usr
import tbCommon as tfb
import clCommon as clt
from testbot import log, cfg

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

        log.debug("Start replicator after crash.")

        action1 = 'crash'
        action2 = 'nothing'

        result = self.testCase(testbed,action1,action2)
        if result != 0:
            log.error("Test case C34209 didn't pass. Returned code is '"+str(result)+"'.")
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

        log.debug("Transporter will perform "+action1+", then "+action2+" and then check start-up scan.")

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

        # Will use client to plant directory tree in the pool
        seller = clt.autoClient(clients[0])

        # Will need multiple pools during the test
        pools = []
        for x in range (1,self.wide+1):
            lengh = len(str(x))+1
            poolname = self.pool+"-"+str(x).zfill(lengh)
            pooltype = "MW"

            # Create pool as org admin, send invitation to the user and accept invitation as user
            pool_id = auto_cs.poolSetup(poolname,admin_id,customer_id,pooltype)
            if pool_id == 'Error':
                log.error("Unable to setup pool '"+poolname+"'.")
                break

            log.debug("Pool '"+poolname+"' was successfully setup. It has ID '"+pool_id+"'.")

            # Check transporters for new pool and verify/update pool name
            for device in devices:
                target = tfb.autoTarget(device)
                poolname = target.getPoolName(pool_id)
                if poolname == 'Error':
                    log.error("Pool "+poolname+"'was not created on "+target.type+" '"+target.name+"'.")
                else:
                    log.debug("Pool "+poolname+"'was created on "+target.type+" '"+target.name+"'.")

            # Waiting for client to get pool from transporter
            log.debug("Waiting for pool '"+poolname+"' to get populated on client '"+seller.name+"'.")
            pool_exists = False
            for x in range (1,11):
                pool_exists = seller.directoryExists(poolname)
                if pool_exists:
                    log.debug("Pool '"+poolname+"' directory was populated on the client '"+seller.name+"'.")
                    break
                else:
                    log.warning("Pool '"+poolname+"' doesn't exist on client '"+seller.name+"' after "+str(x*self.timeout)+" seconds.")
                    time.sleep(self.timeout)

            if not pool_exists:
                log.error("For some reason pool '"+poolname+"' was not populated on client '"+seller.name+"'. Will not use it.")
            else:
                pools.append(poolname)

        poolscount = len(pools)
        if poolscount < 3:
            log.error("There are not enough shared pools on client '"+seller.name+"'.")
            return 13
        else:
            log.debug("Test case will use "+str(poolscount)+" pools.")


        # Mount network storage on client and copy pre-generated directory structure to the pool
        gard = seller.plantTree(pools[0])
        if gard == 'Error':
            log.error("Failed to plant tree - copy directory structure from network storage to the pool directory.")
            return 13

        # Waiting for pool synchronization
        log.debug("Waiting up to "+str(30*self.timeout)+" seconds for pool synchronisation on "+primo.type+" '"+primo.name+"'.")
        last = 0
        diff = []
        for x in range(1,31):
            time.sleep(self.timeout)
            clienside = seller.cleanTree(pools[pools.keys()[0]])
            transporter = primo.getPoolTree(pools.keys()[0])
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

        # Claim secondary device (second from the list of devices)
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

        # Play in pools - copy content from orgpool to another pool
        src = seller.tpath+pools[pools.keys()[0]]+"/vault"
        dst = seller.tpath+pools[pools.keys()[1]]+"/vault"
        response = seller.copyTree(src,dst)
        if response == 'Error':
            log.error("Fail to play in pool. Step 1 - copy")
            return 13

        # Play in pool - move content from orgpool to another pool
        dst = seller.tpath+pools[pools.keys()[2]]+"/vault"
        response = seller.copyTree(src,dst)
        if response == 'Error':
            log.error("Fail to play in pool. Step 2.1 - copy")
            return 13

        response = seller.delTree(src)
        if response == 'Error':
            log.error("Fail to play in pool. Step 2.2 - delete")
            return 13

        log.debug("Will wait "+str(3*self.timeout)+" seconds to start pool syncronization.")
        for x in range (1,4):
            time.sleep(self.timeout)
            log.debug("Passed "+str(x*self.timeout)+" of "+str(3*self.timeout)+" seconds.")

        if action1 != 'nothing':
            log.debug("Will "+action1+" "+secundo.type+" '"+secundo.name+"'.")
            reply = secundo.doAction(action1)
            if reply == 'Error':
                log.error("Failed to "+action1+" "+secundo.type+" '"+secundo.name+"'.")
                return 13

            #log.debug("Will wait "+str(3*self.timeout)+" seconds before second action.")
            #for x in range (1,4):
            #    time.sleep(self.timeout)
            #    log.debug("Passed "+str(x*self.timeout)+" of "+str(3*self.timeout)+" seconds.")



        result1 = secundo.checkShutdown()
        if result1 == 'Error':
            log.error(action1.capitalize()+" on "+secundo.type+" '"+secundo.name+"' didn't cause shutdown.")
            return 13
        else:
            log.debug(action1.capitalize()+" on "+secundo.type+" '"+secundo.name+"' cause "+result1+" shutdown.")

        if action2 != 'nothing':
            delay = 2
            log.debug("Will wait "+str(delay)+" seconds before "+action2+" on "+secundo.type+" '"+secundo.name+"'.")
            time.sleep(delay)
            log.debug("Will "+action2+" "+secundo.type+" '"+secundo.name+"'.")
            reply = secundo.doAction(action2)
            if reply == 'Error':
                log.error("Failed to "+action2+" "+secundo.type+" '"+secundo.name+"'.")
                return 13

            status = secundo.waitDevice(30)
            if status == 13:
                log.error(secundo.type+" '"+secundo.name+"' didn't restart replicator after "+action2+".")
                return 13

        status = secundo.sshCmd("cat /replicator/logs/replicator_0.log |grep Startup")
        pending = []

        for line in status:
            _,response = line.split('Startup')
            print response


        return 0