#!/usr/bin/env python

# import include modules
from autobot import cfg
import ConfigParser
import os
import taBackend as css
import logging

logger = logging.getLogger('user-lib')

# ==============================================================
# General function for use with CS
# ==============================================================

class autoUser:

    def __init__(self,name):

       path = os.path.join(os.getcwd(),'users')
       if not os.path.isdir(path):
           logger.error("Cannot access directory with known clients.")

       fileName = name+'.cfg'
       list = os.path.join(path,fileName)

       logger.debug("Will read information from config file '"+fileName+"'.")

       conf = ConfigParser.RawConfigParser()
       conf.read(list)

       self.name = name

       try:
           self.sysname = conf.get('system','user')
           self.syspass = conf.get('system','pass')
           self.fstname = conf.get('personal','first')
           self.lstname = conf.get('personal','last')
           self.cdnname = conf.get('connecteddata','user')
           self.cdemail = conf.get('connecteddata','mail')
           self.cdpassw = conf.get('connecteddata','pass')
       except:
           logger.error("Cannot read information from '"+fileName+"'.")

    def createAccount(self):
        return 'Success'

    def getCustomerID(self):

        """
        Returns the customer ID out of the CS based on their accountname.

        :param user: name of the user (account name) <br>
        :return: customer id, or False if unable to retrieve.
        """

        cs = css.autoCS()
        customerid = cs.csGetCustomerID(self.cdnname)

        return customerid

    def userReset(self):
        """

        :return:
        """

        logger.info("Will reset customer "+self.cdnname+".")

        userid = self.getCustomerID()

        cs = css.autoCS()

        pools = cs.csGetCustomerPools(userid)
        for poolid in pools:
            pname, powner, _ = cs.csGetPoolInfo(poolid)
            result = cs.csDeletePool(poolid,powner)
            if result  != 'Error':
                logger.debug("Successfully delete pool  '"+pname+"' assotiated with user '"+self.cdnname+"'.")
            else:
                logger.warning("Unable to delete pool '"+pname+"' (pool id="+poolid+") assotiated with user '"+self.cdnname+"'.")

        return 'Success'



