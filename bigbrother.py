#!/usr/bin/env python

# import include modules
import os
import sys
import argparse
import ConfigParser
import time
import subprocess
import select


sys.path.append(os.path.join(os.getcwd(),'lib'))
sys.path.append(os.path.join(os.getcwd(),'testsuites'))

# ==============================================================
# Parsing arguments
# ==============================================================

parser = argparse.ArgumentParser(description="BigBrother")
parser.add_argument('-c', '--config',help="Override default config file",default=None)
parser.add_argument('-v', '--verbose', help="Level of console messages",default=None)
args = parser.parse_args()

# ==============================================================
# Reading configuration
# ==============================================================

cfg = ConfigParser.RawConfigParser()
try:
    cfg.read('bigbrother.cfg')
except:
    print "CRITICAL ERROR: Fail to read configuration from file."
    exit(1)

# ==============================================================
# Prepare logging
# ==============================================================
def myLog():

    import logging

    logLocation = os.path.join(os.getcwd(),'logs')
    if not os.path.isdir(logLocation):
        try:
            os.mkdir(logLocation)
        except:
            print "ERROR: Cannot create directory for logs. Will use current directory."
            logLocation = os.getcwd()

    logName = os.path.join(logLocation,time.strftime("%Y%m%d-%H%M%S_")+'bigbrother.log')

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
    fh = logging.FileHandler(logName)

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

    start_time = time.time()

    log.info("============================================================================================")
    log.info("Start time is "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(start_time)))
    log.info("============================================================================================")

    targetpath = os.path.join(os.getcwd(),cfg.get('general','dir'))

    _, _, filenames = next(os.walk(targetpath), (None, None, []))

    devices =[]
    for name in filenames:
        devices.append(name.replace('.target',''))

    log.debug("Known devices are: "+', '.join(devices))

    if args.config is not None:
        device = args.config
    else:
        log.error("Device is not specified.")
        return 1

    if device not in devices:
        log.error("Unknown device '"+device+"'")
        return 1
    else:
        target = device+".target"
        log.debug("Device described in file "+target)

    confile = os.path.join(targetpath,target)
    conf = ConfigParser.RawConfigParser()

    log.debug("Reading configuration for "+device)
    try:
        conf.read(confile)
    except:
        log.error("Fail to read configuration from file "+confile)
        return 1

    log.debug("Setting connection info")
    try:
        addr = conf.get('access', 'address')
        port = conf.get('access', 'port')
        user = conf.get('credentials', 'user')
        pswd = conf.get('credentials', 'password')
    except:
        log.error("Fail to read device information for "+device)
        return 1

    log.debug("Checking directory for logs")
    if not os.path.isdir("BB-logs"):
        log.debug("Directory for logs does not exist. Will create.")
        try:
            os.mkdir("BB-logs")
        except:
            log.warning("System error when try to create directory")

    filename = os.path.join(os.path.join(os.getcwd(),"BB-logs"),"BB-"+device+".log")

    log.debug("Creating file "+filename)
    f = open(filename,"a")

    f.write("================================================================================================="+"\n")
    f.write("Start watching '"+device+"' "+time.strftime("%d-%b-%Y at %H:%M:%S %Z",time.localtime(time.time()))+"\n")
    f.write("================================================================================================="+"\n")

    command = "tail -f /replicator/logs/replicator_0.log"
    #command = "hostname"

    log.debug("Running command is "+command)

    x = 1
    cmd = "sshpass -p "+pswd+" ssh "+user+"@"+addr+" -p "+port+" '"+command+" 2>&1' >> "+ filename

    alive = None
    while x <= 120:
        log.debug ("Starting subprocess")
        p = subprocess.Popen(cmd, shell=True)
        x = x+1
        while True:
            sys.stdout.flush()
            alive = p.poll()

            if alive != None:
                log.warning("Watched process is not running. Will try to restart.")
                f.write("================================================================================================="+"\n")
                f.write("Watched process is not running")
                time.sleep(10)
                break

        if alive == None:
            log.debug("User's attampt to interrupt process.")
            try:
                p.kill()
            except:
                log.error("Was not able to kill process.")
            break

    f.close()

    log.info("============================================================================================")
    log.info("Total execution time is "+timer(start_time))
    print "That was easy"

if __name__ == '__main__':
    main()