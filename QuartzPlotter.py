#%% -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 06:58:24 2025

@author: rdavis, modified by skomatsu

This script pulls and plots data from your google drive.
"""

import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from matplotlib.offsetbox import AnchoredText
import os
import json
from scipy.optimize import curve_fit
from pathlib import Path
from cycler import cycler
import matplotlib as mpl
from datetime import datetime, timezone, timedelta

mpl.rcParams['axes.prop_cycle'] = cycler(color=['r', 'b', 'k', 'y','g','m','c','tab:pink'])
dateStamp = datetime.now().strftime("%Y-%m-%d")

"Step 1: Input the WP name, Cryostat, and Run ID from Quartz."

#coilName = "WP02_Aries"
#coilName = "WP03_Capricornus"
coilName = "WP04_Cassiopeia"

#whichCryostat = "CT1"
whichCryostat = "CT2"

#experimentID =  '0a57b157-36fc-4d52-aaff-eefb52ab493a' #WP02
#experimentID =  "4ab35d0e-51e6-48cf-8fe9-609be232e9ce" #WP01
#experimentID = "0e90fb47-2b00-4b6e-bb9e-bc5ebc438ee9" #WP03, high temp
#experimentID = "5f883fd1-4180-4158-883a-4d233ca85d53" #WP03, low temp
#experimentID = "101f78fb-96ba-4bb6-aa55-f0266d1c70ad" #WP03, post WCC failure high current
#experimentID = "4241a8c7-d28a-44f7-b8a7-bd0fd4c26d44" #WP02.1
experimentID = "bdb112b9-3b9b-42f4-9f6d-ef3abf4a8941" #WP4Restart

"""Step 2: Set the time range of data you want to plot.

To plot a specific time range, set 'starttime' and 'stoptime' in the format 
(year, month, day, hour, minute, second), and set 'plotLim' as 
[starttime,stoptime]."""

starttime = datetime(2025, 8, 11, 16, 0, 0,tzinfo=timezone.utc)
stoptime = datetime(2025, 8, 12, 0, 0, 0,tzinfo=timezone.utc)

"""To plot the full time range of data you have downloaded, set 'plotLim'
to None. """

#plotLim = [starttime,stoptime] #Plots speific time range
plotLim = None #Plots the full time range of the data you have downloaded

"Adjust additional settings if desired."

author = "Insert your name"
channel_whitelist = "channel_whitelist_"+whichCryostat+".csv" #Shouldn't change - list of channels
saveFigs = True
postprocess = False #flag to denote the code at the end for post-test data processing
tAgg = 10 #Seconds of aggregation of data. Default is 10s
aveTime = 5*60//tAgg #number of seconds to average flattop data over. Default 5*60
xAxis = "s" #flag to set 
testConfigFilename = "testConfig"+whichCryostat+".json" #Shouldn't change - offset info


# %% Define channels to plot

"""Step 3: Input channel refdes' here to be plotted on the 1st y-axis. 
Input channels in quotation marks separated by commas."""

channels1 = ["ct2_plc.Scaled_C2_GT_32"]

"""Step 4: Input channel refdes' here to be plotted on the 2nd y-axis. 
Input channels in quotation marks separated by commas."""

channels2 = ["ct2_plc.Scaled_C2_GE_17_A", 
             "ct2_plc.Scaled_C2_GE_17_B", 
             "ct2_plc.Scaled_C2_GE_17_C", 
             "ct2_plc.Scaled_C2_GE_17_D"]
#To plot nothing on the 2nd y-axis, leave brackets empty []

"""Give the plot a title if you'd like. To make the plots smooth, set 
'overallsmooth' as True. """

plotTitle = "Multi-Plot"
overallsmooth = False

"Step 5: Click 'run' to make the plot."


#Here are all of the pancake overall voltage channels for conventient access (CT2)
# "ct2_plc.Scaled_C2_GE_1_OA", 
# "ct2_plc.Scaled_C2_GE_2_OA", 
# "ct2_plc.Scaled_C2_GE_3_OA", 
# "ct2_plc.Scaled_C2_GE_4_OA", 
# "ct2_plc.Scaled_C2_GE_5_OA", 
# "ct2_plc.Scaled_C2_GE_6_OA", 
# "ct2_plc.Scaled_C2_GE_7_OA", 
# "ct2_plc.Scaled_C2_GE_8_OA", 
# "ct2_plc.Scaled_C2_GE_9_OA", 
# "ct2_plc.Scaled_C2_GE_10_OA", 
# "ct2_plc.Scaled_C2_GE_11_OA", 
# "ct2_plc.Scaled_C2_GE_12_OA", 
# "ct2_plc.Scaled_C2_GE_13_OA", 
# "ct2_plc.Scaled_C2_GE_14_OA", 
# "ct2_plc.Scaled_C2_GE_15_OA", 
# "ct2_plc.Scaled_C2_GE_16_OA"


#%%
#make x axis scaling functions
if(xAxis == "s"):
    tDiv = 1
elif(xAxis == "hr"):
    tDiv = 3600
#make y axis scaling functions
yDiv = {"": 1,
          "m": 1e3,
          "$\mu$": 1e6,
          "n": 1e9}

outputVars = np.array([coilName,dateStamp,experimentID,aveTime],dtype=str)
outputVarLabels = np.array(['Pancake Name','Processing Date','Quartz ID',
                            'Flattop Averaging Time (s)',],dtype=str)

#modelPath = glob.glob("G:\\My Drive\\Electrostatic Pancake Models\\*\\"+coilName+"\\")[0]
modelPath = Path(f"G:\My Drive\Quartz")

expDataPath = modelPath
dataFilename = "data.npy" 
timeFilename = "timestamps.npy"


#%% Make directory to store images
savePathPlots = expDataPath/experimentID/"plots"
if not os.path.exists(savePathPlots):
    os.makedirs(savePathPlots) #make a directory to store the run, if it doesn't exist yet
savePathFlattopPlots = savePathPlots/"flattopPlots"
if not os.path.exists(savePathFlattopPlots):
    os.makedirs(savePathFlattopPlots) #make a directory to store the run, if it doesn't exist yet
    
savePathProcessedData = expDataPath/experimentID/"processed_data"
if not os.path.exists(savePathProcessedData):
    os.makedirs(savePathProcessedData) #make a directory to store the run, if it doesn't exist yet
    
    
#%% read in channel metadata
print("Loading in channel whitelist .csv")
channelListData = np.genfromtxt(modelPath/channel_whitelist,delimiter=",",skip_header=1,dtype=str)
ch_quartzName = channelListData[:,1]
channels_units = channelListData[:,2]
channels_titles = channelListData[:,0]
#keys = ["channel","name","unit"]

#ch_meta = {"mt_fac_plc.MpCurrentFdbkSumOfAllNodes": {"channel": "mt_fac_plc.MpCurrentFdbkSumOfAllNodes", "unit": "Current (A)"}}
#dictionary with key = channel name
#keys to second dictionary, with all needed meta data
#each channel reads in the top level key-pair, then accesses the subdict
ch_meta = {}
idx = 0
# for ch in channels:
#     ch_meta[ch] = {"channel": ch, "name": channels_titles[idx], "unit": channels_units[idx]}
#     idx+=1

for ch in ch_quartzName:
    ch_meta[ch] = {"channel": ch_quartzName[idx], "name": channels_titles[idx], "unit": channels_units[idx]}
    idx+=1


#%% read offset data
try:
    f = open(expDataPath/testConfigFilename)
    config = json.load(f)
    print("Loaded in offset configuration data")
except:
    print("Unable to load offset data; assuming zero offset")
    f = open(expDataPath/"testConfig_default"+whichCryostat+".json")
    config = json.load(f)


#%% make single plotter
def plotSignal(sig,meta,scale,times=None,tAgg = 10,zeroLine=False,smooth=False,smoothTime=10):
    
    plt.figure(figsize=(16,6),dpi=200)
    #option 1: no time information; assume fixed divisions
    if(times is None):
        times = np.arange(0,sig.shape[0]*tAgg,tAgg)/tDiv
        plt.xlabel("Time ({})".format(xAxis),fontsize=18)
    #option 2: an array of timestamps are provided
    else:
        plt.xlabel("Timestamp",fontsize=18)
        
    if(smooth):
        sig = np.transpose(np.squeeze(np.lib.stride_tricks.sliding_window_view(sig,smoothTime).mean(axis=-1)))
        times = times[int(smoothTime/2):-int(smoothTime/2)+1]
        
    plt.plot(times,sig*yDiv[scale],markersize=3,label = meta["channel"])
    plt.ylabel("{}".format(meta["unit"].split("(")[0]+"("+scale+meta["unit"].split("(")[-1]),fontsize=18)
    
    plt.title(coilName+": {}\n{}".format(meta["name"],meta["channel"]),fontsize=18)
    text_box = AnchoredText(f"{author}\n"+dateStamp, frameon=False, loc=4, pad=0.1,prop=dict(size=6))
    plt.gca().add_artist(text_box)
    text_box = AnchoredText("Quartz ID: "+experimentID, frameon=False, loc=9, pad=0.1,prop=dict(size=6))
    plt.gca().add_artist(text_box)
    plt.legend()
    if(zeroLine):
        plt.axhline(y=0.0, color='k', linestyle=':',linewidth=1)
    if(plotLim is not None):
        plt.xlim(plotLim)


def plotSignalGroup(title, sig, meta, scale, times=None, tAgg=10, zeroLine=False,
                    add=False, smooth=False, smoothTime=100, legendOutside=True,
                    xLim=None, dashed=False, second_signal=False):
    if times is None:
        times = np.arange(0, sig.shape[0] * tAgg, tAgg) / tDiv
        xlabel = "Time ({})".format(xAxis)
    else:
        xlabel = "Timestamp"

    if smooth:
        sig = np.transpose(np.squeeze(np.lib.stride_tricks.sliding_window_view(sig, smoothTime).mean(axis=-1)))
        times = times[int(smoothTime/2):-int(smoothTime/2)+1]
    if not second_signal:
        if not add:
            fig, ax1 = plt.subplots(figsize=(16, 6), dpi=200, )
            ax1.set_title(coilName + ": {}".format(title), fontsize=18)
            ax1.set_xlabel(xlabel, fontsize=18)
    
            ax1.set_ylabel("{}".format(meta["unit"].split("(")[0] + "(" + scale + meta["unit"].split("(")[-1]), fontsize=18)
    
            text_box = AnchoredText(f"{author}\n" + dateStamp, frameon=False, loc=4, pad=0.1, prop=dict(size=6))
            ax1.add_artist(text_box)
            text_box = AnchoredText("Quartz ID: " + experimentID, frameon=False, loc=9, pad=0.1, prop=dict(size=6))
            ax1.add_artist(text_box)
    
            if zeroLine:
                ax1.axhline(y=0.0, color='k', linestyle=':', linewidth=1)
    
            if plotLim is not None:
                ax1.set_xlim(plotLim)
    
        else:
            ax1 = plt.gca()
    
        lineType = "--" if dashed else ""
        ax1.plot(times, sig * yDiv[scale], lineType, label=meta["name"])
        if legendOutside:
            ax1.legend(loc='center left', bbox_to_anchor=(0, 0.1))
        else:
            ax1.legend()
        return ax1
    
    else:
        #  Plot the second signal on a twin y-axis
        if not add:
            ax1 = plt.gca()
            ax2 = ax1.twinx()
            ax2.set_ylabel("{}".format(meta["unit"].split("(")[0] + "(" + scale + meta["unit"].split("(")[-1]), fontsize=18)
        else:
            ax2 = plt.gca()
        lineType = "--" if dashed else ""
        ax2.plot(times, sig * yDiv[scale], lineType, label=meta["name"])
        
        if legendOutside:
            ax2.legend(loc='center right', bbox_to_anchor=(1, 0.1))
        else:
            ax2.legend()


#%% Make channel loader

#global start/stop config
start = 0
stop = -1

def loadChannel(ch,removeOffset=True):
    #loads in a channel, using the default path and the loaded-in metadata
    qName = ch["channel"] #quartz channel name
    sig = np.load(expDataPath/experimentID/qName/dataFilename)
    
    sig = sig[start:stop]
    if(removeOffset):
        sig = sig-config.get(qName, 0)
    sig_meta = ch
    t = np.load(expDataPath/experimentID/qName/timeFilename)
    
    t = t[start:stop]
    return sig, ch, t


# %% Read in and plot several channels in one plot with double y-axis

for i in range(len(channels1)):
    if i == 0:
        channel_name, channel_name_meta, channel_name_t = loadChannel(ch_meta[channels1[i]])
        plotSignalGroup(plotTitle, channel_name, channel_name_meta, r"", zeroLine=True, times=channel_name_t, smooth=overallsmooth)
    else:
        channel_name, channel_name_meta, channel_name_t = loadChannel(ch_meta[channels1[i]])
        plotSignalGroup(plotTitle, channel_name, channel_name_meta, r"", add=True, times=channel_name_t, smooth=overallsmooth)

for i in range(len(channels2)):
    if i == 0:
        channel_name, channel_name_meta, channel_name_t = loadChannel(ch_meta[channels2[i]])
        plotSignalGroup(plotTitle, channel_name, channel_name_meta, r"", zeroLine=True, times=channel_name_t, second_signal=True, dashed=True, smooth=overallsmooth)
    else:
        channel_name, channel_name_meta, channel_name_t = loadChannel(ch_meta[channels2[i]])
        plotSignalGroup(plotTitle, channel_name, channel_name_meta, r"", add=True, times=channel_name_t, second_signal=True, dashed=True, smooth=overallsmooth)


