#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT combo/stable
#
# muon_lum_plot_qvt.py
# Script for plotting pulse charges from muon events
#
#
# Ben Hokanson-Fasig
# Created   05/23/17
# Last edit 05/23/17


from __future__ import division, print_function
import argparse

parser_desc = """Script for plotting pulse charges from muon events"""
parser_ep = """Note that this script depends on the standard python libraries
               numpy, matplotlib; and the IceCube project's custom
               libraries icecube, I3Tray"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('infiles', nargs='+',
                    help="input i3 file(s) of muon events")
parser.add_argument('--plotfile',
                    help="""output plot file name. Defaults to plot title
                    in current directory""")
parser.add_argument('--showplots', action='store_true')
args = parser.parse_args()

# Store arguments to variables for rest of the script
infilenames = args.infiles
plotfilename = args.plotfile
showplots = args.showplots


# Standard libraries
import numpy as np
import matplotlib.pyplot as plt

# IceCube libraries
from icecube import icetray, dataio, dataclasses
from icecube.phys_services import I3Calculator
from I3Tray import I3Tray



total_events = 0
for filename in infilenames:
    datafile = dataio.I3File(filename)

    # Find Geometry
    omgeo = None
    for frame in datafile:
        if frame.Stop==frame.Geometry:
            omgeo = frame["I3Geometry"].omgeo
            break
    if omgeo is None:
        print("No geometry found in file",filename)
        continue

    tmin = -1000
    tmax = 10000 #in microseconds
    tstep = 1 #in microseconds
    times = np.arange(0,tmax-tmin,tstep)
    charges = np.zeros(len(times))
    # For each P frame, add pulse charges to their time bins
    for frame in datafile:
        if frame.Stop==frame.Physics:
            if 'SPEFitSingle' in frame and 'I3TriggerHierarchy' in frame:
                for key,value in frame['I3TriggerHierarchy'].iteritems():
                    if value.key.type==value.key.type.MERGED:
                        trigger_window = value
                        break

                # Ignore events with trigger window larger than 15 microseconds
                # Should cut out coincident muons and slow particle triggers
                if trigger_window.length>15000:
                    continue

                pulse_map = \
                dataclasses.I3RecoPulseSeriesMap.from_frame(frame,'InIcePulses')

                fit_particle = frame['SPEFitSingle']


                event_pulses = []
                late_pulses = []
                for om,pulses in pulse_map.iteritems():
                    for pulse in pulses:
                        t_res = I3Calculator.time_residual(fit_particle,
                                                 om_geometry[om].position,
                                                 pulse.time)
                        if t_res>=tmax or t_res<tmin:
                            continue
                        else:
                            tindex = int((t_res-tmin)/tstep)
                            charges[tindex] += pulse.charge

                total_events += 1


# Plot total late charge vs total event charge for each event
plot_title = "Charge vs time of "+str(total_events)+" minbias events"
plt.figure()
plt.plot(times,charges)
plt.axvline(-tmin/tstep)
plt.title(plot_title)
plt.xlabel("Residual Time ("+str(tmin)+r" $\mu$s to "+str(tmax)+r" $\mu$s in "\
           +str(tstep)+r" $\mu$s bins)")
plt.ylabel("Charge (p.e.)")
if plotfilename is None:
    plotfilename = plot_title.replace(" ","_").lower()+".png"
plt.savefig(plotfilename)
if showplots:
    plt.show()
