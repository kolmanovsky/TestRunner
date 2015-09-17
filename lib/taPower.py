#!/usr/bin/env python

import os
from autobot import cfg
import logging
import requests

logger = logging.getLogger(__name__)

class power():
    """
    allows for the control of the network controlled power strip that most of the lab is hooked into
    """

    def __init__(self):
        """
        :return:
        """

        self.baseurl = '%s/cmd.cgi?' % cfg.get('power','url')
        self.commands = {"off":"$A3 %s 0",
                         "on":"$A3 %s 1",
                         "reboot":"$A4 %s",
                         "status":"$A5 %s",
                         "allon":"$A7 1",
                         "alloff":"$A7 0"}
        self.user = 'admin'
        self.password = 'admin'

    def sendCommand(self, command, port=None):
        """
        sends the given command, do the provided port as applicable.

        :param command: command to send. see self.commands for list.  <br>
        :param port: port to send command do. only valid for commands that effect only 1 device. <br>
        :return: True on success
        """
        if command not in self.commands.keys():
            logger.error("Unknown command for power control.")
            return 'Error'

        logger.debug("Issuing %s command to power-strip", command)
        if port is None:
            baseurl = self.baseurl+self.commands[command]
        else:
            baseurl = self.baseurl+(self.commands[command] % str(port))

        try:
            issue = requests.get(baseurl, auth=(self.user, self.password))
        except Exception:
            logger.error("Exception in taPower.")
            return 'Error'
        else:
            if issue.status_code == requests.codes.ok:
                if command != "status":
                    return 'Success'
                else:
                    for i, p in enumerate(reversed(str(issue.text.split(',')[1]))):
                        if p == "1":
                            logger.debug("Port number %s is on" % str(i+1))
                            return str(issue.text.split(',')[1])