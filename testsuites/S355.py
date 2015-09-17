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

        self.testCases = []
        self.suiteID = 'S355'
        self.suiteName = 'AUTO: AUTO: Interpool operations'
        self.pool = ['Pool_'+self.suiteID+'_01']
        pathSuites = os.path.join(os.getcwd(),'testsuites')
        cfgFile = os.path.join(pathSuites,self.suiteID+'.cfg')

    # ==============================================================
    # Test cases
    # ==============================================================

    # ==============================================================
    # Local functions
    # ==============================================================
    def checkIn(self,testBed):
        return 0

    def checkOut(self,testBed):
        return 0