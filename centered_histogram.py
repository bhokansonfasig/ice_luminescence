#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT offline-software/trunk
#
# muon_luminescence.py
# Script for plotting hits after MinBias events from i3 files
#
#
# Ben Hokanson-Fasig
# Created   02/21/17
# Last edit 02/21/17

from __future__ import division, print_function
import argparse

parser_desc = """Script for plotting hits after MinBias events from i3 files,
                 recentered around main hit on DOM-by-DOM basis"""
parser_ep = """Note that this script depends on the standard python libraries
               sys, os, os.path, numpy, matplotlib.pyplot, cPickle;
               and the IceCube project's custom library icecube"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('datadir', nargs='+',
                    help="directory containing zipped i3 files")
parser.add_argument('-l', '--logfile',
                    nargs='?', const='muon_lum_processing.log',
                    help="""log file in which to write progress, instead of
                    printing to stdout. If flag present without file
                    name, uses 'muon_lum_processing.log'. Existing file will
                    be overwritten""")
parser.add_argument('-o', '--outputdir', default='.',
                    help="""directory to place output. Defaults to current
                    directory""")
parser.add_argument('-k', '--keyword', default='', type=str,
                    help="""keyword for grabbing specific files from data
                    directory/directories (any files containing the keyword)""")
parser.add_argument('--antikeyword', type=str,
                    default='thisISanANTIKEYWORDandHOPEFULLYitISlongENOUGHthatNOfileCOULDpossiblyHAVEit',
                    help="""keyword for grabbing specific files from data
                    directory/directories (any files NOT containing the
                    antikeyword)""")
parser.add_argument('--showplots', action='store_true')
parser.add_argument('-p','--pickle',
                    nargs='?', const='muon_plot_histograms.pickle',
                    help="""pickle file in which to save histograms.
                    If flag present without file name, uses
                    'muon_plot_histograms.pickle'. Existing file will
                    be overwritten""")
args = parser.parse_args()

# Store arguments to variables for rest of the script
datadirs = args.datadir
logfilename = args.logfile
outputdir = args.outputdir
filekeyword = args.keyword
fileantikeyword = args.antikeyword
showplots = args.showplots
picklefilename = args.pickle

# Standard libraries
import sys, os, os.path
import numpy as np
import matplotlib
if not(showplots):
    # Get saved plots on machines without an X server
    matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cPickle as pickle

# IceCube libraries
from icecube import dataio, dataclasses


# Function for writing log statements
def write_log(logline, logfilestr):
    """Writes a line to the log file, or stdout if logfilename is None.
    Done this way so the file updates each time a line is written"""
    if logfilestr==None:
        print(logline)
    else:
        with open(logfilestr, 'a') as logfile:
            logfile.write(logline+"\n")
            logfile.close()


def grab_filenames(datadir,keyword,antikeyword):
    """Returns a list of file names in datadir containing the keyword"""
    allfiles = os.listdir(datadir)
    matching = []
    for filename in allfiles:
        if ".i3" in filename and keyword in filename and \
        not(antikeyword in filename):
            matching.append(os.path.join(datadir,filename))
    return sorted(matching)



# Clear log file of old information
if logfilename!=None:
    with open(logfilename, 'w') as logfile:
        logfile.close()

# Write first lines to log file
dirstring = ""
for directory in datadirs:
    dirstring += '\n\t'+directory
write_log("Reading i3 files from:"+dirstring, logfilename)
if filekeyword:
    write_log("  filtered by keyword: "+filekeyword, logfilename)


# Processing files
write_log("Outputting to: "+outputdir, logfilename)
infiles = []
for directory in datadirs:
    infiles.extend(grab_filenames(directory,filekeyword,fileantikeyword))

bin_width = 1000
time_limit = 10000000
n_bins = time_limit/bin_width

hits_histogram = np.zeros(n_bins)
# trigger_histogram = np.zeros(n_bins)

i = 0
numfiles = len(infiles)
total_events = 0
for filename in infiles:
    i += 1
    datafile = dataio.I3File(filename)

    write_log("Processing file "+filename+\
                "  ("+str(i)+"/"+str(numfiles)+")", logfilename)

    # Grab each minbias-passed frame and group them as events with
    # one Q frame followed by any number of P frames
    minbias_events = []
    event = []
    for frame in datafile:
        if 'QFilterMask' in frame:
            for filtername,result in frame['QFilterMask']:
                if ('FilterMinBias' in filtername) and \
                not('SDST' in filtername):
                    if result.condition_passed and result.prescale_passed:
                        if frame.Stop.id=="Q":
                            if len(event)>0:
                                minbias_events.append(event)
                            event = [frame]
                        elif frame.Stop.id=="P":
                            event.append(frame)

    # For each event, get the trigger window from each P frame with
    # that information available, then add the pulses from that frame's
    # pulse map into the histogram, adjusting the times relative to the
    # hit above 5 PE
    for event in minbias_events:
        q_frame = event[0]
        frame_not_analyzed = True
        for p_frame in event[1:]:
            if 'I3TriggerHierarchy' in p_frame:
                # for key,value in p_frame['I3TriggerHierarchy'].iteritems():
                #     if value.key.type==value.key.type.MERGED:
                #         trigger_window = value
                #         break

                pulse_map = \
                dataclasses.I3RecoPulseSeriesMap.from_frame(p_frame,
                                                            'InIcePulses')

                for dom,pulses in pulse_map.iteritems():
                    time_offset = 0
                    for pulse in pulses:
                        if pulse.charge>=5:
                            time_offset = pulse.time
                            break

                    if time_offset>0:
                        for pulse in pulses:
                            time_index = int((pulse.time-time_offset)/bin_width)
                            if time_index>0 and time_index<n_bins:
                                hits_histogram[time_index] += pulse.charge
                        total_events += 1
                        frame_not_analyzed = False

                # trig_window_start = int(trigger_window.time/bin_width)
                # trig_window_stop = int((trigger_window.time+\
                #                     trigger_window.length)/bin_width)

                # for time_index in range(trig_window_start,
                #                         trig_window_stop+1):
                #     if time_index<len(trigger_histogram):
                #         trigger_histogram[time_index] += 1

                # for pulse_time in times:
                #     time_index = int(pulse_time/bin_width)
                #     if time_index>=trig_window_start and \
                #         time_index<=trig_window_stop:
                #         hits_histogram[time_index] += 1

        # if frame_not_analyzed:
        #     write_log("  Frame not analyzed",logfilename)


# Data histogram provided by dividing hits histogram by trigger window hist
# data_histogram = np.zeros(n_bins)
# for i in range(len(trigger_histogram)):
#     if trigger_histogram[i]==0:
#         data_histogram[i] = 0
#     else:
#         data_histogram[i] = hits_histogram[i]/trigger_histogram[i]

plot_title = str(total_events)+" DOM events recentered"
plt.figure()
plt.plot(hits_histogram)
plt.axis([0,25,0,total_events])
plt.title(plot_title)
plt.xlabel("Time (microsecond bins relative to DOM event)")
plt.ylabel("Charge per bin")
plotfilename = os.path.join(outputdir,plot_title.replace(" ","_")+".png")
plt.savefig(plotfilename)
if showplots:
    plt.show()


if picklefilename!=None:
    picklefilename = os.path.join(outputdir,picklefilename)
    hists = {}
    hists['num_events'] = total_events
    hists['hits'] = hits_histogram
    # Store data into pickle
    write_log("Storing histograms to pickle file "+picklefilename,
              logfilename)
    with open(picklefilename, 'wb') as picklefile:
        pickle.dump(hists, picklefile, protocol=pickle.HIGHEST_PROTOCOL)
