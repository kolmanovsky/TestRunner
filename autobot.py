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
parser.add_argument('-c', '--config',help="Override default config file",default='autobot.cfg')
parser.add_argument('-v', '--verbose', help="Level of console messages",default='INFO')
args = parser.parse_args()

# ==============================================================
# Reading configuration
# ==============================================================
cfg = ConfigParser.RawConfigParser()
cfgFile = args.config
try:
    cfg.read(cfgFile)
except Exception, e:
    print "CRITICAL ERROR: Fail to read configuration from file",cfgFile
    print e
    exit(1)


def timer(starttime):
    total_time = time.time()-starttime
    hours, rest = divmod(total_time,3600)
    minutes, seconds = divmod(rest, 60)

    return str(int(hours)).zfill(2)+':'+str(int(minutes)).zfill(2)+':'+str(int(seconds)).zfill(2)


def main():

    # ==============================================================
    # Prepare logging
    # ==============================================================
    import logging
    loglocation = os.getcwd()
    try:
        loglocation = cfg.get('general', 'loglocation')
    except:
        print "ERROR: Cannot read log directory from config file."

    if not os.path.isdir(loglocation):
        try:
            os.mkdir(loglocation)
            print "Directory for logs was created."
        except:
            loglocation = os.getcwd()
            print "ERROR: Cannot create directory for logs. Will use current directory: %s.", loglocation
    else:
        print "Directory for logs exists. It is: ", os.path.join(os.getcwd(),loglocation)

    logfile = time.strftime("%Y%m%d-%H%M%S_")+'autobot.log'
    logfullname = os.path.join(loglocation,logfile)

    cfglevel = cfg.get('general', 'loglevel')
    if cfglevel.lower() == 'debug':
        loglevel = logging.DEBUG
    elif cfglevel.lower() == 'error':
        loglevel = logging.ERROR
    elif cfglevel.lower() == 'warning':
        loglevel = logging.WARNING
    else:
        loglevel = logging.INFO

    # set up logging to file - see previous section for more details
    logging.basicConfig(level=loglevel,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d-%Y %H:%M:%S',
                        filename=logfullname,
                        filemode='w')

    # define a Handler which writes messages to the sys.stdout
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)

    level = args.verbose
    if level.lower() == 'error':
        console.setLevel(logging.ERROR)
    elif level.lower() == 'warning':
        console.setLevel(logging.WARNING)
    elif level.lower() == 'debug':
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)

    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    # Now, define a couple of other loggers which might represent areas in your
    # application:

    logger = logging.getLogger('autobot')

    # ======================================================
    # MAIN
    # ======================================================
    start_time = time.time()

    logger.info("============================================================================================")
    logger.info("Test execution starts "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(start_time)))
    logger.info("Test execution based on "+cfgFile+" file.")
    logger.info("============================================================================================")

    # Get TestRail configuration
    logger.info("Getting TestRail configuration.")
    tr_address = cfg.get('testrail', 'url')
    tr_user = cfg.get('testrail', 'user')
    tr_password = cfg.get('testrail', 'pass')

    timeout = int(cfg.get('general','timeout'))

    logger.debug("Will use TestRail at '"+tr_address+"' using '"+tr_user+"/"+tr_password+"'.")

    logger.info("Creating connection to the TestRail.")
    import testrail as trail
    tr = trail.APIClient(tr_address)
    tr.user = tr_user
    tr.password = tr_password

    #Get test suites to execute
    tsuites = cfg.get('execution', 'suites').split(',')

    import taTestbed as ta
    import taTransporter as tfb
    import taBackend as css
    import taClient as clt
    import taUser as usr

    for ts in tsuites:
        try:
            run = __import__(ts)
        except:
            logger.error("Cannot execute test suite '"+ts+"'.")
            continue

        suite = run.testSuite()
        ts_start = time.time()

        logger.info("===> Test suite '"+suite.suiteid+": "+suite.suitename+"'.")
        logger.info("Starts at "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(ts_start)))

        # List of test cases to execute.
        tcases = suite.testcases
        tc_count = len(tcases)
        if tc_count == 0:
            logging.warning("Test suite '"+suite.suiteid+": "+suite.suitename+" has no test cases.")
            msg = "doesn't have any test cases."
        elif tc_count == 1:
            msg = "has 1 test case."
        else:
            msg = "has "+str(tc_count)+" test cases."

        logger.info("Test suite '"+suite.suiteid+" - "+suite.suitename+"' "+msg)

        testbed = ta.taTestbed(suite.suiteid)

        for x in range (1,4):
            status = testbed.checksetup()
            if status.lower() == 'error':
                logger.error("Testbed is not ready for execution tests from '"+suite.suiteid+": "+suite.suitename+"'.")
                chck = testbed.cleanup()
                time.sleep(timeout)
            else:
                logger.info("Testbed is ready for execution tests from '"+suite.suiteid+": "+suite.suitename+"'.")

        logger.info("---> Summary for '"+suite.suiteid+": "+suite.suitename+"'.")
        logger.info("Executed "+str(tc_count)+" test cases.")
        logger.info("Execution time is "+timer(ts_start))

    logger.info("============================================================================================")
    logger.info("Total test execution time is "+timer(start_time))


if __name__ == '__main__':
    main()