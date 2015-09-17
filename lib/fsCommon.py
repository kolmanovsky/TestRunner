#!/usr/bin/env python

# import include modules
import logging
import os
import shutil
import general as gen
import rpyc

# ==============================================================
# Functions to manipulate with files and folders
# ==============================================================

logger = logging.getLogger('testrunner')

# Create file on remote system
def remoteFileCreate(address,path,fileName,fileText):
    """
    Creates a file on remote client.

    :param address: IP address of client.<br>
    :param path: Local path on client.<br>
    :param fileName: Name of the file to create.<br>
    :param fileText: Text to save in file.<br>
    :return: 0 - success, 1 - fail to create file, 13 - cannot access remote system
    """

    logger.info("Creating file '"+fileName+"' on remote computer (IP="+address+").")

    try:
        conn = rpyc.classic.connect(address)
    except:
        logger.error("Cannot connect to RPYC on remote computer (IP="+address+").")
        return 13

    fullName = conn.modules.os.path.join(path,fileName)

    if not conn.modules.os.path.isdir(path):
        logger.debug("Path does not exist on remote system. Will create.")
        try:
            conn.modules.os.path.mkdir(path)
            logger.debug("Path '"+path+"' was created on remote computer.")
        except:
            logger.error("Cannot create path '"+path+"' on remote computer.")
            return 1

    if conn.modules.os.path.isfile(fullName):
        logger.warning("File '"+fileName+"' already exists on remote computer. Will overwrite.")

    try:
        conn.execute("f = open("+fullName+", 'w')")
        conn.execute("f.write("+fileText+")")
        conn.execute("f.close()")
        logger.debug("File "+fileName+" was created.")
    except:
        logger.error("Cannot create file "+fileName+".")
        return 1

    if conn.modules.os.path.isfile(fullName):
        logger.debug("File "+fileName+" checked. File exists.")
        return 0
    else:
        logger.error("File "+fileName+" checked. File does not exist.")
        return 1

# Create directory on remote computer
def remoteDirCreate(address,path):
    """
    Creates a directory on remote client.

    :param address: IP address of client.<br>
    :param path: Local path on client.<br>
    :return: 0 - success, 1 - fail to create directory, 13 - cannot access remote system
    """

    logger.info("Creating directory '"+path+"' on remote computer (IP="+address+").")

    try:
        conn = rpyc.classic.connect(address)
    except:
        logger.error("Cannot connect to RPYC on remote computer (IP="+address+").")
        return 13

    if not conn.modules.os.path.isdir(path):
        logger.debug("Path does not exist on remote system. Will create.")
        try:
            conn.modules.os.path.mkdir(path)
            logger.debug("Path '"+path+"' was created on remote computer.")
        except:
            logger.error("Cannot create path '"+path+"' on remote computer.")
            return 1

    if conn.modules.os.path.isdir(path):
        logger.debug("Directory '"+path+"' checked. Path exists.")
        return 0
    else:
        logger.error("Directory '"+path+"' checked. Path does not exist.")
        return 1




