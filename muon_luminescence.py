#! /usr/bin/env python
#
# muon_luminescence.py
# Script for plotting hits after MinBias events from i3 files
#
#
# Ben Hokanson-Fasig
# Created   01/18/17
# Last edit 01/18/17
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
                    name, uses 'hese_lum_processing.log'. Existing file will
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
    return []



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
    for filename in infiles:
        extension_index = filename.index(".i3")
        outfilename = filename[:extension_index]+"_minbias"+\
                      filename[extension_index:]
        infile = dataio.I3File(filename)
        outfile = dataio.I3File(outfilename,dataio.I3File.Writing)

# Processing files
else:
    write_log("Outputting to: "+outputdir, logfilename)
