#! /usr/bin/env python
#
# hese_luminescence.py
# Script for plotting hits after hese event(s) in a hese hitspool file
#
#
# Ben Hokanson-Fasig
# Created   10/27/16
# Last edit 10/27/16
#


from __future__ import division, print_function
import argparse

parser_desc = """Script for plotting hits after hese event(s) in a hese
                 hitspool file"""
parser_ep = """Note that this script depends on the standard python libraries
                sys, os, os.path, datetime, numpy, matplotlib.pyplot; and the
                custom library hsreader"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('datadir',
                    help="directory containing zipped data")
parser.add_argument('-l', '--logfile',
                    nargs='?', const='hese_lum_processing.log',
                    help="""log file in which to write progress, instead of
                    printing to stdout. If flag present without file
                    name, uses 'hese_lum_processing.log'. Existing file will
                    be overwritten""")
parser.add_argument('-o', '--outputdir', default='.',
                    help="""directory to place output. Defaults to current directory""")
parser.add_argument('-k', '--keyword', default='HESE', type=str,
                    help="""keyword for grabbing specific HESE files from data
                    directory (in case there are multiple HESE sets)""")
parser.add_argument('-t', '--time', default=1, type=int,
                    help="""length of HESE file in seconds (default is 1s)""")
args = parser.parse_args()

# Store arguments to variables for rest of the script
datadir = args.datadir
logfilename = args.logfile
outputdir = args.outputdir
filekeyword = args.keyword
filelength = args.time


# Standard libraries
import sys, os, os.path
import datetime
import numpy as np
import matplotlib.pyplot as plt

# Custom libraries
from hsreader import load_stream


# # Function for writing log statements
# def write_log(logline, logfilestr):
#     # Writes a line to the log file, or stdout if logfilename is None
#     # Done this way so the file updates each time a line is written
#     if logfilestr==None:
#         print(logline)
#     else:
#         with open(logfilestr, 'a') as logfile:
#             logfile.write(logline+"\n")
#             logfile.close()
#
#
#
# # Clear log file of old information
# if logfilename!=None:
#     with open(logfilename, 'w') as logfile:
#         logfile.close()
#
# # Write first line to log file
# write_log("Reading data from: "+datadir+"\n\twith keyword:"+filekeyword,
#           logfilename)


# Bin hits to a histogram with microsecond bins
hit_stream = load_stream(datadir,keyword=filekeyword)
bin_width = 10000
n_bins = 1000000*filelength
histo = np.zeros(n_bins,'d')
t0 = None
print("Finding fullest bins")
for hit in hit_stream:
    if t0==None:
        t0 = hit.utc
    dt = hit.utc-t0
    time_index = int(dt/bin_width)
    histo[time_index] += 1


# Find all bins with 90% or more of the hits in the bin with the most hits
maximum = np.max(histo)
mean = np.mean(histo)
pulse_bins = [i for i in range(len(histo)) if histo[i]>=.8*maximum]


# Function for creating plot of luminescence data
def luminescence_plot(data,title="plot",extra_text=None):
    plt.figure()
    plt.semilogx(data)
    plt.axhline(y=mean, color='k')
    plt.title(title)
    plt.xlabel("Time since event (microseconds)")
    plt.ylabel("Hits per microsecond bin")
    if extra_text:
        plt.text(1.2,np.max(data)*7/8,extra_text)
    filename = title.replace(" ","_")
    plt.savefig(filename+".png")
    # plt.show()


# Plot hits after an event
# Ignore DOMs that have been hit more than once in the first 12 microseconds
hit_stream = load_stream(datadir,keyword=filekeyword,reuse_data=True)
for i in range(len(pulse_bins)):
    print("Plotting",i+1,"of",len(pulse_bins))
    event_time = t0+pulse_bins[i]*bin_width
    lum_bin_width = 10000
    lum_n_bins = 1000
    lum_time_window = lum_n_bins*lum_bin_width
    mean = mean*lum_bin_width/bin_width

    # Get to the event in the hit stream
    hit = hit_stream.next()
    if hit.utc>event_time:
        hit_stream = load_stream(datadir,keyword=filekeyword,reuse_data=True)
        hit = hit_stream.next()
    while hit.utc<event_time:
        hit = hit_stream.next()

    # Find any DOMs hit twice in the first 32 microseconds
    hit_doms = []
    dead_doms = []
    lum_data = np.zeros(lum_n_bins,'d')
    while hit.utc<event_time+320000:
        if hit.omkey in hit_doms:
            dead_doms.append(hit.omkey)
        else:
            hit_doms.append(hit.omkey)
        # dt = hit.utc-event_time
        # time_index = int(dt/lum_bin_width)
        # lum_data[time_index] += 1
        hit = hit_stream.next()

    # Get to the event in the hit stream again
    if hit.utc>event_time:
        hit_stream = load_stream(datadir,keyword=filekeyword,reuse_data=True)
        hit = hit_stream.next()
    while hit.utc<event_time:
        hit = hit_stream.next()

    # Create histogram, excluding the dead DOMs
    while hit.utc<event_time+lum_time_window:
        if hit.omkey in dead_doms:
            hit = hit_stream.next()
            continue
        dt = hit.utc-event_time
        time_index = int(dt/lum_bin_width)
        lum_data[time_index] += 1
        hit = hit_stream.next()

    luminescence_plot(lum_data,title=filekeyword+" "+str(i+1),
                      extra_text=str(len(dead_doms))+" DOMs ignored\n"+\
                                 str(int(histo[pulse_bins[i]]))+\
                                 " hits in event bin")
