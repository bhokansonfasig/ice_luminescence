#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#
# muon_luminescence.py
# Script for plotting hits after MinBias events from i3 files
#
#
# Ben Hokanson-Fasig
# Created   01/18/17
# Last edit 01/19/17
#


from __future__ import division, print_function
import argparse

parser_desc = """Script for plotting hits after MinBias events from i3 files"""
parser_ep = """Note that this script depends on the standard python libraries
               sys, os, os.path, datatime, numpy, matplotlib.pyplot;
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
                    directory/directories (any files containing keyword)""")
parser.add_argument('--filter', action='store_true')
args = parser.parse_args()

# Store arguments to variables for rest of the script
datadirs = args.datadir
logfilename = args.logfile
outputdir = args.outputdir
filekeyword = args.keyword
filteri3 = args.filter


# Standard libraries
import sys, os, os.path
import datetime
import numpy as np
import matplotlib.pyplot as plt

# IceCube libraries
from icecube import dataio, dataclasses


# Function for writing log statements
def write_log(logline, logfilestr):
    # Writes a line to the log file, or stdout if logfilename is None
    # Done this way so the file updates each time a line is written
    if logfilestr==None:
        print(logline)
    else:
        with open(logfilestr, 'a') as logfile:
            logfile.write(logline+"\n")
            logfile.close()


def grab_filenames(datadir,keyword):
    """Returns a list of file names in datadir containing the keyword"""
    allfiles = os.listdir(datadir)
    matching = []
    for filename in allfiles:
        if ".i3" in filename and filekeyword in filename:
            matching.append(os.path.join(datadir,filename))
    return matching



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


# Filtering files
if filteri3:
    write_log("Filtering files and placing in: "+outputdir, logfilename)
    infiles = []
    for directory in datadirs:
        infiles.extend(grab_filenames(directory,filekeyword))

    i = 0
    numfiles = len(infiles)
    total_events = 0
    for filename in infiles:
        i += 1
        extension_index = filename.index(".i3")
        outfilename = filename[:extension_index]+"_minbias"+\
                      filename[extension_index:]
        write_log("Processing file "+filename+\
                  "  ("+str(i)+"/"+str(numfiles)+")", logfilename)
        infile = dataio.I3File(filename)
        outfile = dataio.I3File(outfilename,dataio.I3File.Writing)

        file_events = 0
        # Push any minbias-passed frames to output file
        for frame in infile:
            if 'QFilterMask' in frame:
                for filtername,result in frame['QFilterMask']:
                    if ('FilterMinBias' in filtername) and \
                    not('SDST' in filtername):
                        if result.condition_passed and result.prescale_passed:
                            outfile.push(frame)
                            if frame.Stop.id=="Q":
                                file_events += 1

        write_log(str(file_events)+" events collected; total - "+\
                  str(total_events), logfilename)

        infile.close()
        outfile.close()


# Processing files
else:
    write_log("Outputting to: "+outputdir, logfilename)
    infiles = []
    for directory in datadirs:
        infiles.extend(grab_filenames(directory,filekeyword))

    bin_width = 1000
    time_limit = 100000
    n_bins = time_limit/bin_width

    histo = np.zeros(n_bins,'d')

    i = 0
    numfiles = len(infiles)
    total_events = 0
    for filename in infiles:
        i += 1
        datafile = dataio.I3File(filename)

        write_log("Processing file "+filename+\
                  "  ("+str(i)+"/"+str(numfiles)+")", logfilename)

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

        total_events += len(minbias_events)

        for event in minbias_events:
            q_frame = event[0]
            for p_frame in event[1:]:
                if 'InIcePulses' in p_frame:
                    pulse_map = \
                    dataclasses.I3RecoPulseSeriesMap.from_frame(p_frame,
                                                     'InIcePulses')
                    pulses = []
                    for key,value in pulse_map.iteritems():
                        pulses.extend(value)
                    times = []
                    for pulse in pulses:
                        times.append(pulse.time)

                    for pulse_time in times:
                        time_index = int(pulse_time/bin_width)
                        if time_index<len(histo):
                            histo[time_index] += 1

                else:
                    write_log("  InIcePulses not found in frame", logfilename)


    plot_title = str(total_events)+" minbias events"
    plt.figure()
    plt.plot(histo)
    # plt.axhline(y=mean, color='k')
    plt.title(plot_title)
    plt.xlabel("Time (microseconds)")
    plt.ylabel("Hits per microsecond bin")
    plotfilename = os.path.join(outputdir,plot_title.replace(" ","_")+".png")
    plt.savefig(plotfilename)
    # plt.show()
