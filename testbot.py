#!/usr/bin/env python

# import include modules
import os
import sys
import argparse
import ConfigParser
import time
from inspect import ismethod

sys.path.append(os.path.join(os.getcwd(),'lib'))
sys.path.append(os.path.join(os.getcwd(),'testsuites'))



# ==============================================================
# Parsing arguments
# ==============================================================

parser = argparse.ArgumentParser(description="TestRunner")
parser.add_argument('-c', '--config',help="Override default config file",default=None)
parser.add_argument('-v', '--verbose', help="Level of console messages",default=None)
args = parser.parse_args()

# ==============================================================
# Reading configuration
# ==============================================================
if args.config is not None:
    cfgFile = args.config
else:
    cfgFile = 'testbot.cfg'

cfg = ConfigParser.RawConfigParser()

try:
    cfg.read(cfgFile)
except:
    print "CRITICAL ERROR: Fail to read configuration from file",cfgFile
    exit(1)

# ==============================================================
# Prepare logging
# ==============================================================
def myLog():

    import logging

    logLocation = os.getcwd()
    try:
        logLocation = cfg.get('general', 'loglocation')
    except:
        print "ERROR: Cannot read log directory from config file."

    if not os.path.isdir(logLocation):
        try:
            os.mkdir(logLocation)
        except:
            print "ERROR: Cannot create directory for logs. Will use current directory."
            logLocation = os.getcwd()

    logFile = time.strftime("%Y%m%d-%H%M%S_")+'testbot.log'

    logFullName = os.path.join(logLocation,logFile)

    # create logger with 'fwtest'
    logger = logging.getLogger(__name__)

    # Logging level
    logLevels = {'INFO':logging.INFO,'DEBUG':logging.DEBUG,'WARNING':logging.WARNING,'ERROR':logging.ERROR}

    try:
        fLevel = cfg.get('general', 'loglevel')
    except:
        print "ERROR: Cannot read logging level from config file. Will use DEBUG mode."
        fLevel = 'DEBUG'

    if fLevel in logLevels:
        logger.setLevel(logLevels[fLevel])
    else:
        logger.setLevel(logging.DEBUG)

    # create log handler
    fh = logging.FileHandler(logFullName)

    # create formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s: %(levelname)-8s: %(message)s')
    fh.setFormatter(formatter)

    # add the handler to the logger
    logger.addHandler(fh)

    # Create, format and add handler for VERBOSE mode
    if args.verbose != None:
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger

log = myLog()

def timer(starttime):
    total_time = time.time()-starttime
    hours, rest = divmod(total_time,3600)
    minutes, seconds = divmod(rest, 60)

    return str(int(hours)).zfill(2)+':'+str(int(minutes)).zfill(2)+':'+str(int(seconds)).zfill(2)

def checkin(testbed,css,usr,clt,tfb):

    log.debug("Perform check-in procedure.")

    auto_cs = css.autoCS()

    log.debug("Getting list of devices and users.")
    devices = testbed.getSystemList('target')
    users = testbed.getSystemList('user')
    clients = testbed.getSystemList('client')

    orgadmin = usr.autoUser(users[0])
    admin_id = orgadmin.getCustomerID()
    log.debug("Got customer ID ("+admin_id+") for org admin ("+users[0]+").")

    log.debug("Clients check.")
    for client in clients:
        currclient = clt.autoClient(client)
        log.debug("Client computer '"+currclient.name+"' running OS "+currclient.platform+".")
        log.debug("Local path to the Transporter Library is '"+currclient.tlpath+"'.")

    log.debug("Transporters check.")
    version = []
    for device in devices:
        target = tfb.autoTarget(device)

        log.debug("Perform check on FW version on "+target.type+" '"+target.name+"'.")
        result = target.installBuild()
        if result != 0:
            log.warning("Was not able to update build. Running with old build.")

        response = target.readFWversion()
        version.append(response)
            
        status = target.deviceClaim(auto_cs,admin_id)
        if status == 99:
            log.error("Environment error: "+target.type+" '"+target.name+"' was claimed before.")
            return 99
        elif status == 13:
            log.error("Cannot claim "+target.type+" '"+target.name+"'.")
            return 13
        else:
            log.debug(target.type+" '"+target.name+"' was successfully claimed.")

    fwnum = len(set(version))
    if fwnum == 1:
        log.debug("All transporters are running version '"+version[0]+"'.")
        result = version[0]
    elif fwnum == 0:
        log.warning("Something went wrong. FW version was not detected.")
        result = 'Unknown'
    else:
        log.warning("There are different FW versions. One of them is '"+version[0]+"'.")
        result = version[0]+"+/-"

    return result

def checkout(testbed,css,usr,clt,tfb):

    log.debug("Perform clean-up procedure.")

    auto_cs = css.autoCS()
    devices = testbed.getSystemList('target')
    users = testbed.getSystemList('user')
    clients = testbed.getSystemList('client')

    for user in users:
        customer = usr.autoUser(user)
        log.debug("Delete all pools belongs to user "+customer.cdnname+", if any.")
        customer_id = customer.getCustomerID()
        pools = auto_cs.csGetCustomerPools(customer_id)
        count = len(pools)
        if count == 0:
            log.debug("User "+customer.cdnname+" has no pools to delete.")
        else:
            log.debug("Found "+str(count)+" pools for user "+customer.cdnname+" (user ID '"+customer_id+"').")
            for pool in pools:
                result = auto_cs.csDeletePool(pool,customer_id)
                if result == 'Error':
                    log.warning("Unable delete pool with ID '"+pool+"' ("+customer.cdnname+").")
                else:
                    log.debug("Pool with ID '"+pool+"' successfully deleted.")

    log.debug("Reset all transporters, if they are claimed.")
    for device in devices:
        target = tfb.autoTarget(device)
        status = target.isClaimed()
        if status != 'Unclaimed':
            admin_id = target.readOwnerID()
            result = target.deviceUnclaim(auto_cs,admin_id)
            if result == 13:
                log.warning("Unable reset "+target.type+" '"+target.name+"'.")
            else:
                log.debug(target.type+" '"+target.name+"' was reset successfully.")
        else:
            log.debug(target.type+" '"+target.name+"' is not claimed.")

    log.debug("Delete all possible test leftovers on all clients.")
    for client in clients:
        desktop = clt.autoClient(client)

        log.debug("Will try to clean Transporter directory on client '"+desktop.name+"'.")
        status = desktop.deleteAll()
        if status == 'Error':
            log.warning("Failed to delete directories on client '"+desktop.name+"'.")

        log.debug("Will try to remove all network mounts on client '"+desktop.name+"'.")
        status = desktop.smbUmount()
        if status == 'Error':
            log.warning("Failed to unmount network storage from client '"+desktop.name+"'.")

    return 0

# ======================================================
# MAIN
# ======================================================
def main():

    import tsCommon as comm
    import testrail as trail
    import tbCommon as tfb
    import csCommon as css
    import clCommon as clt
    import usCommon as usr

    start_time = time.time()

    log.info("============================================================================================")
    log.info("Test execution starts "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(start_time)))
    log.info("Test execution based on "+cfgFile+" file.")
    log.info("============================================================================================")

    #Get test suites to execute

    tsuites = cfg.get('execution','suites').split(',')

    # Get TestRail configuration
    tr_address = cfg.get('testrail','url')
    tr_user = cfg.get('testrail','user')
    tr_password = cfg.get('testrail','pass')

    testrail = trail.APIClient(tr_address)
    testrail.user = tr_user
    testrail.password = tr_password

    for ts in tsuites:
        try:
            run = __import__(ts)
        except:
            log.error("Cannot execute test suite '"+ts+"'.")
            continue

        suite = run.testSuite()
        ts_start = time.time()

        log.info("------- Test suite -------")
        log.info("'"+suite.suiteid+": "+suite.suitename+"' starts "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(ts_start)))

        # List of test cases to execute.
        testcases = suite.testcases

        log.info("Test suite '"+suite.suiteid+" - "+suite.suitename+"' has "+str(len(testcases))+" test cases.")

        testbed = comm.autoSetup(suite.suiteid)

        log.debug("Checking TestBed for the test suite.")
        flag = 1
        for x in range (1,4):
            status = testbed.checkSetup()
            if status == 99:
                log.warning("Testbed is not ready for test suite: '"+suite.suiteid+" - "+suite.suitename+"'. Will try to reset it.")
                sofar = checkout(testbed,css,usr,clt,tfb)
                if sofar == 0:
                    log.debug("Attempt "+str(x)+". Successfully performed clean-up on test bed.")
            else:
                log.debug("Testbed is good. Let's do some testing.")
                flag = 0
                break

        if flag != 0:
            log.error("Several reset didn't brought testbed to testable state. Cannot execute suite '"+suite.suitename+"'.")
            return 99

        trrun = testbed.trun
        version = checkin(testbed,css,usr,clt,tfb)

        for testcase in testcases:
            log.info("------>>")
            log.info("Going to execute test case '"+testcase+"'.")

            tc_start = time.time()

            tc = getattr(suite,testcase)
            if not ismethod(tc):
                log.warning("Test case '"+testcase+"' does not exist in code.")
                continue

            result = tc(testbed)
            if result == 99:
                message = "Test case '"+testcase+"' was blocked by evironment error."
                log.warning(message)
                tc_status = 2
            elif result == 0:
                message = "Test case '"+testcase+"' passed."
                log.debug(message)
                tc_status = 1
            elif result == 13:
                message = "Test case '"+testcase+"' cannot run because of error not related to the case."
                log.warning(message)
                tc_status = 2
            else:
                message = "Test case '"+testcase+"' failed."
                log.warning(message)
                tc_status = 5

            if result in (1,13,99):
                log.info("Will retry to execute test case on clean setup.")
                sofar = checkout(testbed,css,usr,clt,tfb)
                sofar = checkin(testbed,css,usr,clt,tfb)
                result = tc(testbed)
                if result == 0:
                    message = "Test case '"+testcase+"' conditionly passed."
                    tc_status = 7
                else:
                    message = "Test case '"+testcase+"' didn't pass."
                log.debug("Re-execution on freshly cleaned setup: "+message)

            log.info(message)

            tc_time = timer(tc_start)
            tc_id = testcase[1:]
            run_id = trrun[1:]

            tr_command = 'add_result_for_case/'+run_id+'/'+tc_id
            payload = {'status_id':tc_status,'comment':message,'elapsed':tc_time,'version':version}

            try:
                rCode = testrail.send_post(tr_command,payload)
                log.debug("Execution result of test case '"+testcase+"' was successfully submitted to the TestRail.")
            except:
                log.error("Result submition for test case '"+testcase+"' caused an error.")

            # Last step in test case: clean-up
            sofar = checkout(testbed,css,usr,clt,tfb)
            if sofar == 0:
                log.info("Successfully performed clean-up on test bed.")

        log.info("--- Summary for test suite "+suite.suiteid+": "+suite.suitename+" ---")
        log.info("Execution time is "+timer(ts_start))

    log.info("============================================================================================")
    log.info("Total test execution time is "+timer(start_time))
    print "That was easy"

if __name__ == '__main__':
    main()