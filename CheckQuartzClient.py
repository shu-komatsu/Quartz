# -*- coding: utf-8 -*-
"""
Created on Tue Jul 22 13:34:00 2025

@author: skomatsu

This script checks whether your access token for Quartz works
"""

import quartz
runID =  "101f78fb-96ba-4bb6-aa55-f0266d1c70ad" #WP3 in Briefcase test

from importlib.metadata import version
print(version("quartz")) #print out the version, to make sure it’s the one you think it is
data_access_client = quartz.DataAccessClient(quartz.PRODUCTION_DATA_ACCESS_URL)
data_registry_client = quartz.DataRegistryClient(quartz.PRODUCTION_DATA_REGISTRY_URL)
print("Successfully set up clients")

quartzRunInfo = data_registry_client.get_run(runID)

testing
