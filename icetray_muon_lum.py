#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT offline-software/trunk
#
# muon_luminescence.py
# Script for plotting hits after MinBias events from i3 files
#
#
# Ben Hokanson-Fasig
# Created   05/16/17
# Last edit 05/16/17


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
parser.add_argument('-k', '--keyword', nargs='+', default=[''], type=str,
                    help="""keyword(s) for grabbing specific files from data
                    directory/directories (any files containing the keyword)""")
parser.add_argument('--antikeyword', nargs='+', type=str,
                    default=['thisISanANTIKEYWORDandHOPEFULLYitISlongANDobscureENOUGHthatNOfileCOULDpossiblyHAVEit'],
                    help="""keyword(s) for grabbing specific files from data
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
filekeywords = args.keyword
fileantikeywords = args.antikeyword
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
from icecube import icetray, dataio, dataclasses
from icecube.phys_services import I3Calculator
from I3Tray import I3Tray


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


def grab_filenames(datadir,keywords,antikeywords):
    """Returns a list of file names in datadir containing the keyword"""
    allfiles = os.listdir(datadir)
    matching = []
    for filename in allfiles:
        match = bool(".i3" in filename)
        for keyword in keywords:
            match = match and (keyword in filename)
        for antikeyword in antikeywords:
            match = match and not(antikeyword in filename)
        if match:
            matching.append(os.path.join(datadir,filename))
    return sorted(matching)



# Clear log file of old information
if logfilename!=None:
    with open(logfilename, 'w') as logfile:
        logfile.close()

# Write first lines to log file
dirstring = ""
for directory in datadirs:
    dirstring += '\n    '+directory
write_log("Reading i3 files from:"+dirstring, logfilename)
if filekeywords!=['']:
    write_log("  filtered by keyword: "+str(filekeywords), logfilename)
if fileantikeywords!=['thisISanANTIKEYWORDandHOPEFULLYitISlongANDobscureENOUGHthatNOfileCOULDpossiblyHAVEit']:
    write_log("  filtered by anti-keyword: "+str(fileantikeywords), logfilename)



# Filtering function
def minBiasOnly(frame):
    """Passes only frames which pass the min bias filter"""
    if 'QFilterMask' not in frame:
        return False
    for filtername,result in frame['QFilterMask']:
        if ('FilterMinBias' in filtername) and not('SDST' in filtername):
            if result.condition_passed and result.prescale_passed:
                return True
    return False



# Filtering only
if filteri3:
    write_log("Filtering files and placing in: "+outputdir, logfilename)
    infiles = []
    for directory in datadirs:
        infiles.extend(grab_filenames(directory,filekeywords,fileantikeywords))

    tray = I3Tray()
    tray.Add('I3Reader',"reader",FileNameList=files)
    tray.Add(minBiasOnly,"filter",Streams=[icetray.I3Frame.DAQ,icetray.I3Frame.Physics])
    tray.Add('I3Writer',"writer",FileName=outfile)
    tray.Execute()
    tray.Finish()


# Processing
else:
    pass

