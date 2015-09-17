#!/usr/bin/env python

# import include modules
import os
import sys
import argparse
import ConfigParser
import time
import logging

testStart = time.time()

sys.path.append(os.path.join(os.getcwd(),'lib'))
sys.path.append(os.path.join(os.getcwd(),'testsuites'))

import tasTransporterLib as tfb
import tasCommon as comm

# ==============================================================
# Parsing arguments
# ==============================================================

parser = argparse.ArgumentParser(description="TestRunner")
parser.add_argument('-l', '--logfile',help="Override default path for log file",default=None)
parser.add_argument('-v', '--verbose', help="Level of console messages",default='ERROR')
parser.add_argument('-b', '--build', help="Build to run against",default=None)
parser.add_argument('-m', '--mode', help="Manual - will not install new build, or Auto - will install new build",default='auto')
args = parser.parse_args()

# ==============================================================
# CONFIG
# ==============================================================

# Setup the logging.

cfgFile = 'testrunner.cfg'

cfgl = ConfigParser.RawConfigParser()
cfgl.read(cfgFile)

# ==============================================================
# Prepare logging
# ==============================================================

# Log file name
logLocation = os.getcwd()

if args.logfile is not None:
    logLocation = args.logfile
else:
    try:
        logLocation = cfgl.get('log', 'loglocation')
    except:
        print "Cannot read log directory from",cfgFile

if os.path.isdir(logLocation):
    print "Log directory exists."
else:
    print "Log directory does not exist. Will use current directory."
    logLocation = os.getcwd()

logfileName = os.path.join(logLocation,time.strftime("%Y%m%d-%H%M%S_")+'testrunner.log')

# create logger with 'spam_application'
logger = logging.getLogger('testrunner')
logger.setLevel(logging.DEBUG)
# create log handlers
fh = logging.FileHandler(logfileName)
ch = logging.StreamHandler()

# Logging level
logLevels = {'INFO':logging.INFO,'DEBUG':logging.DEBUG,'WARNING':logging.WARNING,'ERROR':logging.ERROR}

try:
    fLevel = cfgl.get('log', 'loglevel')
except:
    print "Cannot read logging level from config file. Will use DEBUG mode."
    fLevel = 'DEBUG'

if fLevel in logLevels:
    fh.setLevel(logLevels[fLevel])
else:
    fh.setLevel(logging.DEBUG)

if args.verbose in logLevels:
    ch.setLevel(logLevels[args.verbose])
else:
    ch.setLevel(logging.ERROR)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

logger.info("============================================================================================")
logger.info("Script starts "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(testStart)))

# ==============================================================
# Constants
# ==============================================================

try:
    timeOut = int(cfgl.get('testrunner','timeout'))
except:
    logger.warning("Cannot read timeout settings from the file "+cfgFile+". Will use default 120 seconds.")
    timeOut = 120

try:
    devServ = cfgl.get('build','server')
    devTFB = cfgl.get('build','file')
except:
    logger.warning("Cannot read configuration for build server. Will use default.")
    devServ = 'http://172.24.12.10/builds/data/buildbot/'
    devTFB = '/Product/Device/installation/tfb/tfb64-4.0.X.XXXXX.tar.gz'

# ======================================================
# Build installation
# ======================================================

# Determine which build to install

flag = 0

if args.mode != 'auto':
    logger.info("Running against currently installed build.")
    fullPath = ''
else:
    if args.build != None:
        logger.info("Will install build from "+args.build)
        fullPath = args.build
    else:
        logger.info("Build ID is not specified. Will install latest.")
        build = comm.buildFinder(devServ)

        if build == 13:
            logger.warning("Was not able to identify latest build. Will skip installation.")
            fullPath = ''
        else:
            logger.info("Build to install is "+str(build)+".")
            fullPath = devServ+str(build)+devTFB

# Determine TFBs to install build

tfbs = comm.listTargets(cfgFile,'testrunner','tfbs')

if tfbs == 'Error':
    logger.error("Failed to get list of available Transporters. Nothing to do.")
    exit(1)

tfbCount = len(tfbs)
if tfbCount == 1:
    logger.info("Test execution will use 1 transporter.")
elif tfbCount == 0:
    logger.info("Test execution will not use transporters today. Nothing to do.")
    exit(1)
else:
    logger.info("Test execution will use "+str(tfbCount)+" transporters.")

for tfbName in tfbs:
    tfbAddr, tfbPort, tfbUser, tfbPass = comm.getTransporter(tfbName)

    if tfbAddr == 'Error':
        logging.warning("Cannot get info for transporter '"+tfbName+"'.")
        continue

    if fullPath != '':
        logger.debug("Going to install build.")

        result = comm.installBuild(tfbAddr,tfbPort,tfbUser,tfbPass,fullPath,timeOut)

        if result == 0:
            logger.info("New build was successfully installed on '"+tfbName+"'.")
        elif result == 99:
            logger.warning("Build installation was skipped on '"+tfbName+"'.")
        else:
            logger.warning("Lost connection to the transporter '"+tfbName+"' during installation.")


    version = tfb.vTFB(tfbAddr,tfbPort,tfbUser,tfbPass)
    if version != 13:
        logger.info("Transporter '"+tfbName+"' running FW version "+version)
    else:
        logger.warning("Cannot check FW version on transporter '"+tfbName+"'.")


# ======================================================
# MAIN
# ======================================================

logger.info("Test execution based on "+cfgFile+" file.")

# List of acceptable test suites
tSuites = ['S329']

for ts in tSuites:
    try:
        test = __import__(ts)
    except:
        logger.error("Cannot find test suite "+ts+".")
        continue
    logger.debug("Starting execution of test suite "+ts)
    test.suite(timeOut)