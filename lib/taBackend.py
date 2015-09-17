#!/usr/bin/env python

# import include modules
from autobot import cfg
import requests
import json
import taClient as clt
import logging

logger = logging.getLogger(__name__)

# ==============================================================
# General function for use with CS
# ==============================================================

class autoCS:

    def __init__(self):

        self.csurl = cfg.get('general','cs')

    def csClaimDeviceID(self,deviceid,customerid):
        """
        Send request to CS to claim device by ID

        :param urlBase: URL for CS to work with<br>
        :param deviceid: UUID of device to claim<br>
        :param customerid: User who will claim this device<br>
        :return: 0 - success, 13 - fail to claim
        """


        url = self.csurl+"/polcentral/v1_0/customers/"+customerid+"/devices/claimbyid"
        payload = {"deviceid": deviceid}

        logger.debug("Attempting to claim device '"+deviceid+"' by user '"+customerid+"'.")

        try:
            claim = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to claim device.")
            return 'Error'

        if claim.status_code == 200:
            logger.debug("Device with ID '"+deviceid+"' was successfully claimed.")
            return 'Success'
        else:
            logger.error("Device with ID '"+deviceid+"' was not claimed. Error code is "+str(claim.status_code)+".")
            return 'Error'

    def csUnclaimDeviceID(self,deviceid,customerid):
        """
        Send request to CS to reset(unclaim) device by ID

        :param urlBase: URL for CS to work with<br>
        :param deviceid: UUID of device to claim<br>
        :param customerid: User who will unclaim this device<br>
        :return: 0 - success, 13 - fail to claim
        """
        logger.debug("Attempting to reset device")

        url = self.csurl+"/polcentral/v1_0/devices/reset/"+deviceid
        payload = {"requestorid": customerid}

        try:
            claim = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to reset device.")
            return 'Error'

        if claim.status_code == 200:
            logger.debug("Device with ID '"+deviceid+"' was successfully reset.")
            return 'Success'
        else:
            logger.error("Device with ID '"+deviceid+"' was not reset. Error code is "+str(claim.status_code)+".")
            return 'Error'

    def csAddPool(self,poolname,creatorid,pooltype,deviceid,localpath,nas):
        """
        Send request to CS to add new pool
        :return: poolid - success, 13 - fail to add pool
        """
        logger.debug("Attempting to create pool.")

        if localpath == '':
            localpath = '/.'+poolname

        url = self.csurl + "/polcentral/v1_0/pools/"

        if pooltype not in ["MW","PS"]:
            logger.error("Fail to create pool of unknown type: '"+pooltype+"'.")
            return 'Error'
        else:
            logger.debug("Configuration required '"+pooltype+"' type of "+poolname+" pool.")

        if nas == None:
            logger.warning("NAS info is missing. Pool will be created as 'MW' type.")
            pooltype = "MW"
            nasname = ''
            nasshare = ''
            naspath = ''
            nascred = ''
        else:
            logger.error("Not ready yet.")
            return 'Error'

        payload = {
                  "name": poolname,
                  "description":"Pool added by testbot",
                        "creatorid": {
                            "$id": creatorid
                        },
                        "type":pooltype,
                        "allowpiggybacks":True,
                        "localpoolpath": localpath,
                        "subscribedevices":True,
                        "deviceid": deviceid,
                        "pathinpool": "/",
                        "servername": nasname,
                        "sharename": nasshare,
                        "sharepath": naspath,
                        "credsetname": nascred,
                        "overridewarnings":True
                    }

        try:
            r = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to add pool.")
            return 'Error'

        if r.status_code == 200:
            logger.debug("Pool '"+poolname+"' was successfully created.")
            poolid = r.json()['_id']
            return poolid['$id']
        else:
            logger.error("Pool '"+poolname+"' was not created. Error code is "+str(r.status_code)+".")
            return 'Error'

    def csDeletePool(self,poolid,usedid):
        """
        Send request to CS to delete existing pool
        :return: 0 - success, 13 - failed
        """

        logger.debug("Attempting to delete pool.")

        url = self.csurl + "/polcentral/v1_0/pools/delete/"+poolid
        payload = {"requestorid":usedid,"disallowlostfound":False}

        try:
            r = requests.delete(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to add pool.")
            return 'Error'

        if r.status_code == 200:
            logger.debug("Pool with ID '"+poolid+"' was successfully deleted.")
            return 'Success'
        else:
            logger.error("Pool with ID '"+poolid+"' was not deleted. Error code is "+str(r.status_code)+".")
            return 'Error'

    def csAddSubscription(self,poolid,deviceid,customerid):
        """
        :param urlBase:
        :param poolid:
        :param deviceid:
        :param customerid:
        :return:
        """
        logger.debug("Attempt to create subsription")

        url = self.csurl + "/polcentral/v1_0/subscriptions/"

        name,owner,type = self.csGetPoolInfo(poolid)

        if owner == 'Error':
            logger.error("Failed to retrive information for pool with ID '"+poolid+"'.")
            return 13

        payload = {
                   "customerid":customerid,
                   "deviceid":deviceid,
                   "poolid":poolid,
                   "requestorid":owner
                   }

        try:
            r = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to add subscription.")
            return 'Error'

        if r.status_code == 200:
            subscribe = r.json()['_id']['$id']
            logger.debug("Subscription for pool '"+name+"' was successfully added. Subscription ID is '"+subscribe+"'.")
            return subscribe
        else:
            logger.error("Subscription for pool '"+name+"' was not added. Error code is "+str(r.status_code)+".")
            return 'Error'

    def csGetPoolInfo(self,poolid):
        """
        :param urlBase:
        :param poolid:
        :return:
        """
        logger.debug("Retrive information for the pool.")

        url = self.csurl + "/polcentral/v1_0/pools/"+poolid

        try:
            r = requests.get(url)
        except:
            logger.error("Exception during api call to get pool's owner ID.")
            return 'Error','Error','Error'

        if r.status_code == 200:
            logger.debug("Sucessfully retrive ID of the pool owner.")
            poolname = r.json()['name']
            poolowner = r.json()['ownerid']['$id']
            pooltype = r.json()['type']
            return poolname,poolowner,pooltype
        else:
            logger.error("Didn't get pool information. Error code is "+str(r.status_code)+".")
            return 'Error','Error','Error'

    def csGetCustomerVerify(self,customerid):
        """
        :param urlBase:
        :param customerid:
        :return:
        """
        logger.debug("Retrive information for the customer.")

        url = self.csurl + "/polcentral/v1_0/customers/"+customerid

        try:
            r = requests.get(url)
        except:
            logger.error("Exception during api call to get pool's owner ID.")
            return 'Error','Error','Error'

        if r.status_code == 200:
            logger.debug("Sucessfully retrive ID of the pool owner.")
            name = r.json()['accountname']
            firstname = r.json()['firstname']
            lastname = r.json()['lastname']
            return name,firstname,lastname
        else:
            logger.error("Didn't get pool information. Error code is "+str(r.status_code)+".")
            return 'Error','Error','Error'

    def csSendPoolInvitation(self,poolid,inviterid,customerid):
        """
        :param urlBase:
        :param poolID:
        :param inviterID:
        :param customerID:
        :return:
        """

        logger.debug("Attempt to send invitation to the pool.")

        url = self.csurl + "/polcentral/v1_0/customers/"+inviterid+"/pools/"+poolid+"/memberships"

        payload = {
                  "customerid":{
                               "$id": customerid
                               },
                  "membershiprights": "full"
                  }

        try:
            r = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to send invitation.")
            return 'Error'

        if r.status_code == 200:
            logger.debug("Invitation was successfully send.")
            inviteid = r.json()['_id']
            return inviteid['$id']
        else:
            logger.error("Invitation was not send. Error code is "+str(r.status_code)+".")
            return 'Error'

    def csAckPoolInvitation(self,invitationid,customerid,reply):
         """
         :param urlBase:
         :param invitationid:
         :param customerid:
         :param reply:
         :return:
         """

         logger.debug("Attempt to reply to the pool invitation.")
         url = self.csurl + "/polcentral/v1_0/customers/"+customerid+"/invitations/"+invitationid

         if reply:
             logger.debug("Will accept invitation.")
         else:
             logger.debug("Will decline invitation.")

         payload = {"accept":reply}

         try:
             r = requests.post(url, data=json.dumps(payload))
         except Exception:
             logger.error("Exception during api call to send invitation.")
             return 'Error'

         if r.status_code == 200:
             logger.debug("Successfully replyed to the invitation.")
             status = r.json()['membershipstatus']
             return status
         else:
             logger.error("Could not reply to invitation. Error code is "+str(r.status_code)+".")
             return 'Error'

    def csGetCustomerID(self,name):
        """
        :param name:
        :return:
        """
        logger.debug("Attempt to get customer ID by account name.")

        url = self.csurl+"/polcentral/v1_0/customers/"+name+"/accountname"

        try:
            r = requests.get(url)
            cust_id = str(r.json()['customerid'])
        except Exception, e:
            logger.error("Unable to get customer ID for account: "+name)
            return 'Error'
        #test result for validity before turning
        return cust_id

    def csGetCustomerPools(self,customerid):
        """
        :param customerid:
        :return:
        """
        logger.debug("Get list of pools (pool ids) for user with id '"+customerid+"'.")

        poolids = []

        url = self.csurl+"/polcentral/v1_0/customers/"+customerid+"/pools"

        try:
            r = requests.get(url)
        except Exception, e:
            logger.error("Unable to get pools for customer: "+customerid)
            return 'Error'

        if r.status_code == 200:
            poolids = []
            number = len(r.json())
            for eachid in range(0,number):
                poolids.append(r.json()[eachid]['poolid'])
            return poolids
        else:
            logger.error("Request returned error. Error code is "+str(r.status_code)+".")
            return 'Error'

    def csRenameDevice(self,device_id,name):
        """
        :param name:
        :return:
        """

        logger.debug("Rename device to '"+name+"'.")

        url = self.csurl+"/polcentral/v1_0/devices/"+device_id

        if len(name) > 14:
            cifsname = name[0:15]
        else:
            cifsname = name

        payload = {"name": name,"cifsprotocolname": cifsname,"cifsenabled": True}

        try:
            r = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to rename device.")
            return 'Error'

        if r.status_code == 200:
            return 'Success'
        else:
            logger.error("Failed to rename device.")
            return 'Error'

    def scAddPoolNas(self,poolname,creatorid,deviceid,desktop):

        logger.debug("Attempting to create NAS pool.")

        url = self.csurl + "/polcentral/v1_0/pools/"

        client = clt.autoClient(desktop)

        payload = {
                    "name":poolname,
                    "description":"AUTO test map",
                    "creatorid": {
                        "$id": creatorid
                        },
                    "type":"PS",
                    "allowpiggybacks":True,
                    "localpoolpath": "/.RootOfNetworkAttached",
                    "subscribedevices":True,
                    "deviceid": deviceid,
                    "pathinpool": "/",
                    "servername": client.smbserv,
                    "sharename": self.smbnas,
                    "sharepath": "/path/in/engineering/share",
                    "credsetname": "CredSetName2",
                    "overridewarnings":True
                    }

        try:
            r = requests.post(url, data=json.dumps(payload))
        except Exception:
            logger.error("Exception during api call to add pool.")
            return 'Error'

        if r.status_code == 200:
            logger.debug("Pool '"+poolname+"' was successfully created.")
            poolid = r.json()['_id']
            return poolid['$id']
        else:
            logger.error("Pool '"+poolname+"' was not created. Error code is "+str(r.status_code)+".")
            return 'Error'

    def poolSetup(self,poolname,adminid,clientid,pooltype,deviceid='',localpath='',nas=None):

        logger.debug("Will create pool '"+poolname+"'.")
        pool_id = self.csAddPool(poolname,adminid,pooltype,deviceid,localpath,nas)
        if pool_id == 13:
            logger.error("Failed to create pool '"+poolname+"'.")
            return 'Error'
        else:
            logger.debug("Pool '"+poolname+"' successfully created. Pool ID is '"+pool_id+"'.")

        # Send invitation to the pool
        invitation = self.csSendPoolInvitation(pool_id,adminid,clientid)
        if invitation == 'Error':
            logger.error("No invitation was send for pool '"+poolname+"'.")
            return 'Error'
        else:
            logger.debug("Invitation '"+invitation+"' for pool '"+poolname+"' was send to the used with ID '"+clientid+"'.")

        # Accept invitation to the pool
        acceptance = self.csAckPoolInvitation(invitation,clientid,True)
        if acceptance == 'Error':
            logger.error("Failed to accept invitation to the pool '"+poolname+"'.")
            return 'Error'
        else:
            logger.debug("Invitation was successfully accepted.")

        return pool_id