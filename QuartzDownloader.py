# -*- coding: utf-8 -*-
"""
Created on Tue Sep 17 12:28:15 2024

@author: rdavis, modified by skomatsu

This script downloads quartz data to your google drive.
"""

from datetime import datetime, timezone, timedelta
import os
import urllib.parse
from urllib.request import urlretrieve
import sys
import glob
import numpy as np
import json
import time
import quartz
import pandas as pd

data_access_client = quartz.DataAccessClient(quartz.PRODUCTION_DATA_ACCESS_URL)
data_registry_client = quartz.DataRegistryClient(quartz.PRODUCTION_DATA_REGISTRY_URL)

"Step 1: Input the WP name, Cryostat, and Run ID from Quartz."

#coilName = "TF01_Andromeda"
#coilName = "WP02_Aries"
#coilName = "WP03_Capricornus"
coilName = "WP04_Cassiopeia"

#whichCryostat = "CT1"
whichCryostat = "CT2"

#experimentID = "a43ce227-d48e-412d-babd-b36ab850c114" #WP04, first test
#experimentID =  '0a57b157-36fc-4d52-aaff-eefb52ab493a' #WP02
#experimentID =  "4ab35d0e-51e6-48cf-8fe9-609be232e9ce" #WP01
#experimentID = "0e90fb47-2b00-4b6e-bb9e-bc5ebc438ee9" #WP03, high temp
#experimentID = "5f883fd1-4180-4158-883a-4d233ca85d53" #WP03, low temp
#experimentID = "101f78fb-96ba-4bb6-aa55-f0266d1c70ad" #WP03, post WCC failure high current
#experimentID = "a43ce227-d48e-412d-babd-b36ab850c114" #testrun for Vinny
#experimentID = "4241a8c7-d28a-44f7-b8a7-bd0fd4c26d44" #WP02.1
#experimentID = "c87f413f-74f5-485e-a575-76fd20d09b60"
experimentID = "bdb112b9-3b9b-42f4-9f6d-ef3abf4a8941" #WP4Restart

"""Step 2: Set the time range of data you want to download.

If you want a specific time range, set 'manualTimeRange' as True and set 
'start' and 'stop' in the format (year, month, day, hour, minute, second)."""

manualTimeRange = False #True/flase flag to pull a specific period of data
start = datetime(2025, 8, 10, 0, 0, 0,tzinfo=timezone.utc)
stop = datetime(2025, 8, 11, 0, 0, 0,tzinfo=timezone.utc)

"""If you just want the last x hours of data, set 'manualTimeRange' as False and
set 'timeToPull'. If you want data from the entire run, set 'manualTimeRange' 
as False and set 'timeToPull' as None."""

timeToPull = 12.0 #Requests last x hrs of data
#timeToPull= None #Gives all times

"""Step 3: Adjust additional settings if desired.
If you are downloading larger timeframes of data, a higher 'timeStep' will make
downloading faster."""

timeStep = 10.0 #Takes data every x seconds, aka Aggregation. Default is 10s
channel_whitelist = "channel_whitelist_"+whichCryostat+".csv" #Shouldn't change - list of channels
highDataRateRog = False #True/Flase flag to download the Rogowski signals at max data rate (200 Hz)
saveCSV = False #flag to send all the returned data into a single csv (can be huge)
updateCSV = False #flag to update the CSV for every channel (can be slow)
fullDataRateAll = False
singleChannelDL = False #flag to download a single channel at a time (slower, but can get longer times)
modelPath = glob.glob("G:\\My Drive\\Quartz\\")[0] #Data will be downloaded here
savePath = modelPath

print("Begining download for coil test: ",coilName)


#%% Define channels to download

tstart = time.perf_counter()  #initial start time
print("Loading in channel whitelist .csv")
channelListData = np.genfromtxt(modelPath+channel_whitelist,delimiter=",",skip_header=1,dtype=str)
channels = channelListData[:,1]

"Step 4: Input channels to download in quotation marks separated by commas."

selectChannels = np.array(["ct2_plc.Scaled_C2_GT_32", 
                           "ct2_plc.Scaled_C2_GE_17_A", 
                           "ct2_plc.Scaled_C2_GE_17_B", 
                           "ct2_plc.Scaled_C2_GE_17_C", 
                           "ct2_plc.Scaled_C2_GE_17_D"])

"If you want all channels, comment this line to skip it."
channels = np.array([i for i in channels if i in selectChannels]) #comment this to get all channels

"Step 5: Click 'run' to start download."


#%% Get quartz clients

data_access_client = quartz.DataAccessClient(quartz.PRODUCTION_DATA_ACCESS_URL)
data_registry_client = quartz.DataRegistryClient(quartz.PRODUCTION_DATA_REGISTRY_URL)

quartzRunInfo = data_registry_client.get_run(experimentID)
print("Quarz run name: ",quartzRunInfo["name"])

#%% Test start-stop automation based on creation/deactivation times

if(not manualTimeRange):
    print("Attempting to use activation and current times to pull full data")
    startPD = pd.Timestamp(quartzRunInfo["creation_time"]).round('s') + pd.Timedelta(seconds=10)
    start = startPD.to_pydatetime()
    # #check if still active. If yes, use current time. If not, use deactivation time
    if(quartzRunInfo["active"]):
        print("Run still active; using current time as stop time")
        stopPD = (pd.to_datetime(datetime.now(timezone.utc)).round('s')).to_pydatetime()- pd.Timedelta(seconds=5)
        stop = stopPD.replace(tzinfo=timezone.utc)
    else:
        print("Run deactivated. Using deactivation time as stop time")
        stopPD = pd.Timestamp(quartzRunInfo["deactivation_time"]).round('s') - pd.Timedelta(seconds=60)
        stop = stopPD.to_pydatetime()
    
    if(timeToPull is not None):
        print("Requested {} hrs of data".format(timeToPull))
        startPD = pd.Timestamp(stop) - pd.Timedelta(hours=timeToPull)
        start = startPD.to_pydatetime()
    if(stop-start > timedelta(hours=12)):
        print("switching to single channel download")
        singleChannelDL = True
        if (timeStep<60):
            timeStep = 60
else:
    print(f"Requested {stop-start} hrs of data")
    if(stop-start > timedelta(hours=12)):
        print("switching to single channel download")
        singleChannelDL = True
        if (timeStep<60):
            timeStep = 60


#%% fetch the data using the configured settings

tstart = time.perf_counter()  #initial start time
if(not singleChannelDL):
    
    #looking to download all channels in one go
    if(fullDataRateAll):
        response = data_access_client.read_channel_data(
                experimentID,
                channels=list(channels),
                start=start,
                end=stop
            )
    else:
        response = data_access_client.read_channel_data(
                experimentID,
                channels=list(channels),
                start=start,
                end=stop,
                aggregation_window=str(timeStep) + "s",
                aggregation="mean"
            )
    print("Done fetching. Total time: {} sec".format(time.perf_counter()-tstart))
    
    #% save channels to disk
    inx = 0
    for group in range(len(response)):
        for channel in range(len(response[group]["children"])):
            chName = response[group]["name"] + "."+ response[group]["children"][channel]["name"]
            print("Saving channel: {}".format(chName))
            
            os.makedirs(os.path.join(savePath, experimentID, chName), exist_ok=True) #make sub dirs
            
            #save data
            np.save(os.path.join(savePath, experimentID, chName, 'data.npy'),np.array(response[group]["children"][channel]["data"]["values"]))
            #save timestamps
            np.save(os.path.join(savePath, experimentID, chName, 'timestamps.npy'),np.array(response[group]["children"][channel]["data"]["times"],dtype='datetime64'))
            
    print("Done saving. Total time: {} sec".format(time.perf_counter()-tstart))
    
else:
    print("Beginning data download in a single channel level")
    chInx = 0 #channel count, for csv export 
    
    for channel in list(channels):
        print("Loading channel: {}".format(channel))
        #if you try to gather more than this much data, break it up into chunks
        start_chunk = start
        stop_chunk = start + pd.Timedelta("12 hours")
        outputData = []
        outputTimes = []
        lastChunk = False
        while True:
            if(stop_chunk > stop):
                stop_chunk = stop
                lastChunk = True
            print("fetching 12 hrs of data")
            response_chunk = data_access_client.read_channel_data(
                    experimentID,
                    channels=[channel],
                    start=start_chunk,
                    end=stop_chunk,
                    aggregation_window=str(timeStep) + "s",
                    aggregation="mean"
                )
            outputData.extend(response_chunk[0]["children"][0]["data"]["values"])
            outputTimes.extend(response_chunk[0]["children"][0]["data"]["times"])
            start_chunk = start_chunk + pd.Timedelta("12 hours")
            stop_chunk = stop_chunk + pd.Timedelta("12 hours")
            
            if(lastChunk):
                break
        
        if(saveCSV):
            if(chInx == 0):
                print("Building .csv variable")
                outputCSVData = np.empty([len(outputData),channels.shape[0]+1],dtype=object)
                outputCSVData[:,chInx] = outputTimes #add times to megaarray
            outputCSVData[:,chInx+1] = outputData #add to megaarray
            chInx = chInx +1
        
        os.makedirs(os.path.join(savePath, experimentID, channel), exist_ok=True) #make sub dirs
        #% save channels to disk
        #save data
        np.save(os.path.join(savePath, experimentID, channel, 'data.npy'),np.array(outputData))
        #save timestamps
        np.save(os.path.join(savePath, experimentID, channel, 'timestamps.npy'),np.array(outputTimes,dtype='datetime64'))
        
        if(updateCSV):
            print("Saving mid-download csv")
            np.savetxt(savePath + "outputData.csv", outputCSVData,delimiter=",",header=",".join(channels),fmt='%s')
        
        print("Done fetching. Total time: {} sec".format(time.perf_counter()-tstart))

    if(saveCSV):
        np.savetxt(savePath + "outputData.csv", outputCSVData,delimiter=",",header=",".join(channels),fmt='%s')
    print("Done saving. Total time: {} sec".format(time.perf_counter()-tstart))


#%% high data rate Rogowski sampling (off by default)

if(highDataRateRog):
    print("Fetching max data rate Rogowski signals")
    channelsRog = ["ct1_plc.Scaled_C1_GI_1",
                   "ct1_plc.Scaled_C1_GI_2",
                   "ct1_plc.Scaled_C1_GI_3",
                   "ct1_plc.Scaled_C1_GI_4"]
    tstart = time.perf_counter()  #initial start time
    responseRog = data_access_client.read_channel_data(
            experimentID,
            channels=channelsRog,
            start=start,
            end=stop,
        )
    print("Done fetching. Total time: {} sec".format(time.perf_counter()-tstart))
    for group in range(len(responseRog)):
        for channel in range(len(responseRog[group]["children"])):
            chName = responseRog[group]["name"] + "."+ responseRog[group]["children"][channel]["name"]
            print("Saving channel: {}".format(chName))
            
            os.makedirs(os.path.join(savePath, experimentID, chName), exist_ok=True) #make sub dirs
            
            #save data
            np.save(os.path.join(savePath, experimentID, chName, 'data.npy'),np.array(responseRog[group]["children"][channel]["data"]["values"]))
            #save timestamps
            np.save(os.path.join(savePath, experimentID, chName, 'timestamps.npy'),np.array(responseRog[group]["children"][channel]["data"]["times"],dtype='datetime64'))

    print("Done saving. Total time: {} sec".format(time.perf_counter()-tstart))


