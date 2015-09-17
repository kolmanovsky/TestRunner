#!/usr/bin/env python

# import include modules
import os
import sys
sys.path.append(os.path.join(os.getcwd(),'lib'))

import time
import rpyc
import logging

testStart = time.time()
conn = rpyc.classic.connect("172.18.34.124")

# ==============================================================
# Logging
# ==============================================================

logLocation = os.path.join(os.getcwd(),'logs')

if not os.path.exists(logLocation):
    try:
        os.mkdir(logLocation)
    except:
        print "Cannot create",logLocation
        logLocation = os.getcwd()

logfileName = os.path.join(logLocation,time.strftime("%Y%m%d-%H%M%S_")+'longname.log')

# create logger
logger = logging.getLogger('longname')
logger.setLevel(logging.DEBUG)

# create log handlers
fh = logging.FileHandler(logfileName)
ch = logging.StreamHandler()

fh.setLevel(logging.INFO)
ch.setLevel(logging.INFO)

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
# Functions to read directory structure
# ==============================================================

def get_winpaths(directory):
    logger.info("Getting directory structure for '"+directory+"' on Windows.")

    file_paths = []  # List which will store all of the full filepaths.

    # Walk the tree.
    for root, directories, files in conn.modules.os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            filepath = filepath[31:].replace('\\','/')
            if filepath[10:] == 'desktop.ini':
                continue
            else:
                file_paths.append(filepath)  # Add it to the list.

    return file_paths  # Self-explanatory.

def get_macpaths(directory):
    logger.info("Getting directory structure for '"+directory+"' on MacOS.")

    file_paths = []  # List which will store all of the full filepaths.

    # Walk the tree.
    for root, directories, files in os.walk(directory):
        for filename in files:
            # Join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            filepath = filepath[27:]
            file_paths.append(filepath)  # Add it to the list.

    return file_paths  # Self-explanatory.

def syncCheck(name,wTime,mWait):
    flag = 0
    for i in range(0,maxWait):
        logger.debug("Checking transportation of "+name+".")
        if os.path.exists(name):
            cTime = wTime+(i*wTime)
            logger.debug(name+" was delivered to Windows in "+str(cTime)+" seconds.")
            flag = 1
            return cTime
        else:
            cTime = wTime+(i*wTime)
            logger.debug(name+". Not yet delivered to Windows in "+str(cTime)+" seconds.")
            time.sleep(wTime)
            flag = 0

    if flag == 0:
        cTime = wTime+(mWait*wTime)
        logger.error(name+" was not delivered to the Windows in "+str(cTime)+" seconds.")
        return 0

def saveDir(fileName,list):
    logger.debug("Saving directory structure in file '"+fileName+"'.")
    try:
        f = open(fileName, "w")
        for line in list:
            f.write(line+'\n')
        f.close()
        return True
    except:
        logger.error("Cannot create file "+fileName+".")
        return False

# ==============================================================
#
# ==============================================================

# Constants - later will move to config file
winPath = 'C:\Users\\automation\Transporter\Longname'
macPath = '/Users/autotest/Transporter/Longname'
sharePath = '/Volumes/Users/automation/Transporter/Longname'

poolName = 'Longname'

waitTime = 1
level = 20
length = 20

maxWait = 600

logger.info("Will try to create path "+str(level)+" levels deep, using names "+str(length)+" characters long.")

# Don't want to mess with initial paths
workPath = macPath
checkPath = sharePath

# Main loop
for x in range(1,level+1):
    logger.info("------------------------")
    logger.info("Current level - "+str(x)+".")
    dirName = str(x).zfill(length)
    workPath = os.path.join(workPath,dirName)
    sharePath = os.path.join(sharePath,dirName)
    try:
        os.makedirs(workPath)
        logger.info("Directory "+dirName+" was created on MacOS.")
    except:
        logger.error("Step "+str(x)+". Cannot create directory "+dirName+" on Mac.")

    time.sleep(waitTime)

    result = syncCheck(sharePath,waitTime,maxWait)
    if result == 0:
        logger.error(dirName+" was not delivered to the Windows system.")
    else:
        logger.info(dirName+" was delivered to the Windows system in "+str(result)+" seconds.")

    logger.info("Length of path on MacOS side is "+str(len(workPath))+" characters.")

    fileName = os.path.join(workPath,'TestFile')
    checkName = os.path.join(sharePath,'TestFile')
    extentions = ['.doc','.docx','.txt','.csv','.xls','.xlsx','.htm']

    for ext in extentions:
        workFile = fileName+ext
        checkFile = checkName+ext
        logger.info("Creating file "+workFile+".")
        try:
            newFile = open(workFile, "w")
            newFile.write("Long path test.")
            newFile.close()
        except:
            logger.error("Cannot create file "+workFile+".")
            continue

        time.sleep(waitTime)

        result = syncCheck(checkFile,waitTime,maxWait)

        if result == 0:
            logger.error("TestFile"+ext+" was not delivered to the Windows system.")
        else:
            logger.info("TestFile"+ext+" was delivered to the Windows system in "+str(result)+" seconds.")


    winList = get_winpaths(winPath)
    winFileName = os.path.join('logs','Win-'+str(x).zfill(4)+'.log')
    saveDir(winFileName,winList)

    macList = get_macpaths(macPath)
    macFileName = os.path.join('logs','Mac-'+str(x).zfill(4)+'.log')
    saveDir(macFileName,macList)

    if winList == macList:
        logger.info("SUCCESS: Mac and Win are equal on step "+str(x)+".")
    else:
        logger.info("TO BAD: Mac and Win are not equal on step"+str(x)+".")

timeDif = time.time()-testStart
hours, rest = divmod(timeDif,3600)
minutes, seconds = divmod(rest, 60)

totalTime = str(int(hours)).zfill(2)+':'+str(int(minutes)).zfill(2)+':'+str(int(seconds)).zfill(2)

logger.info("Test execution time: "+totalTime+".")

print "That was easy"
