#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT offline-software/trunk
#
# muon_luminescence.py
# Script for plotting hits after MinBias events from i3 files
#
#
# Ben Hokanson-Fasig
# Created   01/18/17
# Last edit 02/28/17


from __future__ import division, print_function
import argparse

parser_desc = """Script for plotting hits after MinBias events from i3 files"""
parser_ep = """Note that this script depends on the standard python libraries
               sys, os, os.path, numpy, matplotlib.pyplot, cPickle;
               and the IceCube project's custom library icecube"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('datadir', nargs='+',
                    help="directory containing zipped i3 files")
parser.add_argument('-g', '--gcdfile', default='',
                    help="""GCD file corresponding to i3 files in datadir.
                    If not provided and only one file containing 'GCD' is
                    found in the directory, it will be used""")
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
                    default='thisISanANTIKEYWORDandHOPEFULLYitISlongANDobscureENOUGHthatNOfileCOULDpossiblyHAVEit',
                    help="""keyword for grabbing specific files from data
                    directory/directories (any files NOT containing the
                    antikeyword)""")
parser.add_argument('--filter', action='store_true')
parser.add_argument('--showplots', action='store_true')
args = parser.parse_args()

# Store arguments to variables for rest of the script
datadirs = args.datadir
gcdfilename = args.gcdfile
logfilename = args.logfile
outputdir = args.outputdir
filekeyword = args.keyword
fileantikeyword = args.antikeyword
filteri3 = args.filter
showplots = args.showplots


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
from icecube.phys_services import I3Calculator


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


# Filtering files
if filteri3:
    write_log("Filtering files and placing in: "+outputdir, logfilename)
    infiles = []
    for directory in datadirs:
        infiles.extend(grab_filenames(directory,filekeyword,fileantikeyword))

    i = 0
    numfiles = len(infiles)
    total_events = 0
    for filename in infiles:
        i += 1
        start_index = filename.rfind("/")+1
        extension_index = filename.index(".i3")
        outfilename = os.path.join(outputdir,
                                   filename[start_index:extension_index]+\
                                   "_minbias"+filename[extension_index:])
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
        total_events += file_events

        write_log(str(file_events)+" events collected; total - "+\
                  str(total_events), logfilename)

        infile.close()
        outfile.close()


# Processing files
else:
    write_log("Outputting to: "+outputdir, logfilename)
    infiles = []
    for directory in datadirs:
        infiles.extend(grab_filenames(directory,filekeyword,fileantikeyword))

    if not(gcdfilename):
        possiblegcd = grab_filenames(directory,"GCD",fileantikeyword)
        if len(possiblegcd)==1:
            gcdfilename = possiblegcd[0]

    if gcdfilename:
        gcdfile = dataio.I3File(gcdfilename)
        write_log("Using GCD file "+gcdfilename, logfilename)
    else:
        write_log("No unique GCD file found. Provide GCD filename in "+ \
                  "command arguments.", logfilename)


    geometry_frame = gcdfile.pop_frame()
    om_geometry = geometry_frame['I3Geometry'].omgeo

    event_charges = []
    late_charges = []

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

        # For each event in each P frame, get the reconstructed particle track
        # Then evaluate residual times for each pulse to determine if the pulse
        # is in a DOM on the particle track or is a late pulse
        for event in minbias_events:
            q_frame = event[0]
            frame_not_analyzed = True
            for p_frame in event[1:]:
                if 'SPEFitSingle' in p_frame and 'I3TriggerHierarchy' in p_frame:
                    for key,value in p_frame['I3TriggerHierarchy'].iteritems():
                        if value.key.type==value.key.type.MERGED:
                            trigger_window = value
                            break

                    # Ignore events with trigger window larger than 10 microseconds
                    # Should cut out coincident muons and slow particle triggers
                    if trigger_window.length>10000:
                        continue

                    pulse_map = \
                    dataclasses.I3RecoPulseSeriesMap.from_frame(p_frame,'InIcePulses')

                    fit_particle = p_frame['SPEFitSingle']


                    event_pulses = []
                    late_pulses = []
                    for om,pulses in pulse_map.iteritems():
                        for pulse in pulses:
                            t_res = I3Calculator.time_residual(fit_particle,
                                                               om_geometry[om].position,
                                                               pulse.time)
                            if t_res>-75 and t_res<200:
                                event_pulses.append(pulse)
                            elif t_res>1000:
                                late_pulses.append(pulse)

                    event_charge = 0
                    for pulse in event_pulses:
                        event_charge += pulse.charge
                    event_charges.append(event_charge)

                    late_charge = 0
                    for pulse in late_pulses:
                        late_charge += pulse.charge
                    late_charges.append(late_charge)

                    total_events += 1
                    frame_not_analyzed = False

            if frame_not_analyzed:
                write_log("  I3TriggerHierarchy not found in frame",logfilename)


    # Plot total late charge vs total event charge for each event
    plot_title = "Charges of "+str(total_events)+" minbias events"
    plt.figure()
    plt.plot(event_charges,late_charges)
    plt.title(plot_title)
    plt.xlabel("Total Event Charge")
    plt.ylabel("Total Late Charge")
    plotfilename = os.path.join(outputdir,plot_title.replace(" ","_")+".png")
    plt.savefig(plotfilename)
    if showplots:
        plt.show()
