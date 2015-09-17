#!/usr/bin/env python

# import include modules
from testbot import log, cfg
import ConfigParser
import os
import csCommon as css

# ==============================================================
# General function for use with CS
# ==============================================================

class autoUser:

    def __init__(self,name):

       path = os.path.join(os.getcwd(),'users')
       if not os.path.isdir(path):
           log.error("Cannot access directory with known clients.")

       fileName = name+'.cfg'
       list = os.path.join(path,fileName)

       log.debug("Will read information from config file '"+fileName+"'.")

       conf = ConfigParser.RawConfigParser()
       conf.read(list)

       try:
           self.sysname = conf.get('system','user')
           self.syspass = conf.get('system','pass')
           self.fstname = conf.get('personal','first')
           self.lstname = conf.get('personal','last')
           self.cdnname = conf.get('connecteddata','user')
           self.cdemail = conf.get('connecteddata','mail')
           self.cdpassw = conf.get('connecteddata','pass')
       except:
           log.error("Cannot read information from '"+fileName+"'.")

    def createAccount(self):
        return 'Success'

    def getCustomerID(self):

        """
        Returns the customer ID out of the CS based on their accountname.

        :param user: name of the user (account name) <br>
        :return: customer id, or False if unable to retrieve.
        """

        testcs = css.autoCS()
        customerid = testcs.csGetCustomerID(self.cdnname)

        return customerid

