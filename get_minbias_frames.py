#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT combo/stable
#
# get_minbias_frames.py
# Script for pulling frames from i3 files that pass the minbias filter
#
#
# Ben Hokanson-Fasig
# Created   05/16/17
# Last edit 05/16/17


from __future__ import division, print_function
import argparse

parser_desc = """Script for pulling frames from i3 files that pass the minbias filter"""
parser_ep = """Note that this script depends on the standard python library
               os; and the IceCube project's custom libraries icecube, I3Tray"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('datadir', nargs='+',
                    help="directories containing i3 files")
parser.add_argument('-g', '--gcdfile', default='',
                    help="""GCD file corresponding to i3 files in datadir.
                    If not provided and only one file containing 'GCD' is
                    found in the directory, it will be used""")
parser.add_argument('-o', '--outfile', default='./minbias_frames.i3',
                    help="""output file name. Defaults to 'minbias_frames.i3' in
                    current directory""")
parser.add_argument('-k', '--keyword', nargs='+', default=[''], type=str,
                    help="""keyword(s) for grabbing specific files from data
                    directory/directories (any files containing the keyword)""")
parser.add_argument('--antikeyword', nargs='+', type=str,
                    default=['thisISanANTIKEYWORDandHOPEFULLYitISlongANDobscureENOUGHthatNOfileCOULDpossiblyHAVEit'],
                    help="""keyword(s) for grabbing specific files from data
                    directory/directories (any files NOT containing the
                    antikeyword)""")
args = parser.parse_args()

# Store arguments to variables for rest of the script
datadirs = args.datadir
gcdfilename = args.gcdfile
outfilename = args.outfile
filekeywords = args.keyword
fileantikeywords = args.antikeyword


# Standard libraries
import os

# IceCube libraries
from icecube import icetray
from I3Tray import I3Tray


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



# Filtering function
def minBiasOnly(frame):
    """Passes only frames which pass the min bias filter"""
    if 'QFilterMask' not in frame:
        return False
    for filtername,result in frame['QFilterMask'].iteritems():
        if ('FilterMinBias' in filtername) and not('SDST' in filtername):
            if result.condition_passed and result.prescale_passed:
                return True
    return False


# Try to find GCD file if none provided
if not(gcdfilename) and len(datadirs)==1:
    gcdantikeywords = [word for word in fileantikeywords if word!="GCD"]
    possiblegcd = grab_filenames(datadirs[0],"GCD",gcdantikeywords)
    if len(possiblegcd)==1:
        gcdfilename = possiblegcd[0]
        print("Using found GCD file",gcdfilename)

# Make GCD file the first input file
if gcdfilename:
    infiles = [gcdfilename]
else:
    infiles = []

# Grab the rest of the input files
for directory in datadirs:
    infiles.extend(grab_filenames(directory,filekeywords,fileantikeywords))


# Use icetray to filter all the minbias frames into a single file
tray = I3Tray()
tray.Add('I3Reader',"reader",FileNameList=infiles)
tray.Add(minBiasOnly,"filter",Streams=[icetray.I3Frame.DAQ,icetray.I3Frame.Physics])
tray.Add('I3Writer',"writer",FileName=outfilename)
tray.Execute()
tray.Finish()

