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


# ======================================================
# MAIN
# ======================================================
def main():

    import tbCommon as tfb
    import clCommon as clt

    timeout = int(cfg.get('general','timeout'))

    start_time = time.time()

    log.info("============================================================================================")
    log.info("Test execution starts "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(start_time)))
    log.info("Test execution based on "+cfgFile+" file.")



    #client =clt.autoClient('mac_108')
    pool_name = 'AUTO_S358_01'

    tporter = tfb.autoTarget('auto-tfb150-01')
    pool_id = tporter.getPoolId(pool_name)

    print pool_id

    pool_tree = tporter.getPoolTree(pool_id)

    print "\n\n\nPool",pool_name,"has ID ("+pool_id+").\n\n"

    print "<<<--->>>"
    print pool_tree

    client = clt.autoClient('win7x64-02')
    client_pool = client.cleanTree(pool_name)
    print "<<<--->>>"
    print client_pool

    diff = list(set(pool_tree) - set(client_pool))
    #diff = list(set(client_pool) - set(pool_tree))
    last = len(diff)

    if last != 0:
        x = 1
        print "<<<--->>>"
        for element in diff:
            print str(x).zfill(len(str(last)))+". '"+element+"'."
            x = x + 1

    print "<<<--->>>"
    print len(pool_tree)
    print len(client_pool)
    print last
    print "<<<--->>>"

    print "That was easy"

if __name__ == '__main__':
    main()

print "Done"
