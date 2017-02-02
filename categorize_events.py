#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT offline-software/trunk
#
# categorize_events.py
# Script for breaking min_bias filtered i3 file into timescale-based category
# files of events
#
# Ben Hokanson-Fasig
# Created   02/02/17
# Last edit 02/02/17


from __future__ import division, print_function
import argparse

parser_desc = """Script for breaking min_bias filtered i3 file into
                 timescale-based category files of events"""
parser_ep = """Note that this script depends on the standard python libraries
               sys, os, os.path; and the IceCube project's custom library
               icecube"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('datadir', nargs='+',
                    help="directory containing zipped i3 files")
parser.add_argument('-l', '--logfile',
                    nargs='?', const='muon_lum_separation.log',
                    help="""log file in which to write progress, instead of
                    printing to stdout. If flag present without file
                    name, uses 'muon_lum_separation.log'. Existing file will
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
args = parser.parse_args()

# Store arguments to variables for rest of the script
datadirs = args.datadir
logfilename = args.logfile
outputdir = args.outputdir
filekeyword = args.keyword
fileantikeyword = args.antikeyword


# Standard libraries
import sys, os, os.path
import datetime
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



write_log("Separating files and placing in: "+outputdir, logfilename)
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
    s_outfilename = os.path.join(outputdir,
                                 filename[start_index:extension_index]+\
                                 "_short"+filename[extension_index:])
    m_outfilename = os.path.join(outputdir,
                                 filename[start_index:extension_index]+\
                                 "_medium"+filename[extension_index:])
    l_outfilename = os.path.join(outputdir,
                                 filename[start_index:extension_index]+\
                                 "_long"+filename[extension_index:])
    write_log("Processing file "+filename+\
              "  ("+str(i)+"/"+str(numfiles)+")", logfilename)
    infile = dataio.I3File(filename)
    s_outfile = dataio.I3File(s_outfilename,dataio.I3File.Writing)
    m_outfile = dataio.I3File(m_outfilename,dataio.I3File.Writing)
    l_outfile = dataio.I3File(l_outfilename,dataio.I3File.Writing)


    # Grab each minbias-passed frame and group them as events with
    # one Q frame followed by any number of P frames
    minbias_events = []
    event = []
    for frame in infile:
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


    # For each event, get the trigger window from each P frame with that
    # information available, then add that frame to the correct category file
    for event in minbias_events:
        q_frame = event[0]
        for p_frame in event[1:]:
            if 'I3TriggerHierarchy' in p_frame:
                for key,value in p_frame['I3TriggerHierarchy'].iteritems():
                    if value.key.type==value.key.type.MERGED:
                        trigger_window = value
                        break

                # trig_window_start = int(trigger_window.time/1000)
                # trig_window_stop = int((trigger_window.time+\
                #                    trigger_window.length)/1000)

                window_size = trigger_window.length/1000

                if window_size<15:
                    s_outfile.push(q_frame)
                    s_outfile.push(p_frame)
                elif window_size>25 and window_size<35:
                    m_outfile.push(q_frame)
                    m_outfile.push(p_frame)
                elif window_size>100:
                    l_outfile.push(q_frame)
                    l_outfile.push(p_frame)

    infile.close()
    s_outfile.close()
    m_outfile.close()
    l_outfile.close()
