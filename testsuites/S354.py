#!/usr/bin/env python

# import include modules
import os
import time
import lib.tsCommon as comm
import lib.csCommon as test
from testbot import log, cfg
import ConfigParser

class testSuite:

    def __init__(self):

        self.testCases = ['C33791','C33792']
        self.suiteID = 'S354'
        self.suiteName = "AUTO: Long path"
        self.pool = ['Pool_'+self.suiteID+'_01']
        pathSuites = os.path.join(os.getcwd(),'testsuites')
        cfgFile = os.path.join(pathSuites,self.suiteID+'.cfg')


    # ==============================================================
    # Test cases
    # ==============================================================

    # C33791: Create new file on MacOS and sync it to Windows (path = 5x80 characters)
    def C33791(timeOut):

        testID = 'C33791'
        testName = 'Create new file on MacOS and sync it to Windows (path = 5x80 characters)'

        treeDepth = 5
        nameLength = 10
        isEmpty = False
        sysFrom = 'osx'
        sysTo = 'win'

        logger.info("---------")
        logger.info("Running test case '"+testID+": "+testName+"'.")

        result = sysSync(sysFrom,sysTo,treeDepth,nameLength,testID,timeOut,isEmpty)

        if result == 0:
            logger.info("TEST PASSED: Whole tree structure was synced between two clients.")
            return 0
        elif result == 99:
            logger.info("TEST FAILED: Tree structure exists on both clients, but it is not identical.")
            return 1
        else:
            logger.info("TEST FAILED: Tree structure was not synced.")
            return 1

    # C33792: Create new file on MacOS and sync it to MacOS(path = 5x80 characters)
    def C33792(timeOut):

        testID = 'C33792'
        testName = 'Create new file on MacOS and sync it to MacOS (path = 5x80 characters)'

        treeDepth = 5
        nameLength = 80
        isEmpty = False
        sysFrom = 'osx'
        sysTo = 'osx'

        logger.info("---------")
        logger.info("Running test case '"+testID+": "+testName+"'.")

        result = sysSync(sysFrom,sysTo,treeDepth,nameLength,testID,timeOut,isEmpty)

        if result == 0:
            logger.info("TEST PASSED: Whole tree structure was synced between two clients.")
            return 0
        elif result == 99:
            logger.info("TEST FAILED: Tree structure exists on both clients, but it is not identical.")
            return 1
        else:
            logger.info("TEST FAILED: Tree structure was not synced.")
        return 1

    # ==============================================================
    # Local functions
    # ==============================================================
    def checkIn(self,testBed):
        return 0

    def checkOut(self,testBed):
        return 0