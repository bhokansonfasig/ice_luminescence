#!/bin/sh /cvmfs/icecube.opensciencegrid.org/py2-v2/icetray-start
#METAPROJECT combo/stable
#
# muon_lum_charges.py
# Script for calculating event and late charges from muon events
#
#
# Ben Hokanson-Fasig
# Created   05/16/17
# Last edit 05/17/17


from __future__ import division, print_function
import argparse

parser_desc = """Script for calculating event and late charges from muon events"""
parser_ep = """Note that this script depends on the IceCube project's custom
               libraries icecube, I3Tray"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)
parser.add_argument('infiles', nargs='+',
                    help="input i3 file(s) of muon events")
parser.add_argument('-o', '--outfile', default='./muon_lum_charges.i3',
                    help="""output file name. Defaults to 'muon_lum_charges.i3'
                    in current directory""")
args = parser.parse_args()

# Store arguments to variables for rest of the script
infilenames = args.infiles
outfilename = args.outfile


# Standard libraries


# IceCube libraries
from icecube import icetray, dataio, dataclasses
from icecube.phys_services import I3Calculator
from I3Tray import I3Tray



# Processing module
class ChargeModule(icetray.I3Module):
    """Module for calcualting event and late charges of physics event"""
    def __init__(self,context):
        icetray.I3Module.__init__(self,context)
        self.AddOutBox("OutBox")

    def Configure(self):
        """Set a default DOM geometry"""
        self.omgeo = {}

    def calculateCharges(self,frame):
        """Calculate the event and late charges"""
        if 'I3TriggerHierarchy' not in frame:
            return False
        if 'InIcePulses' not in frame:
            return False
        if 'SPEFitSingle' not in frame:
            return False

        for key,value in frame['I3TriggerHierarchy'].iteritems():
            if value.key.type==value.key.type.MERGED:
                trigger_window = value
                break

        # Ignore events with trigger window larger than 15 microseconds
        # Should cut out coincident muons and slow particle triggers
        if trigger_window.length>15000:
            return False

        pulse_map = dataclasses.I3RecoPulseSeriesMap.from_frame(frame,'InIcePulses')

        fit_particle = frame['SPEFitSingle']

        event_charge = 0
        late_charge = 0
        for om,pulses in pulse_map.iteritems():
            for pulse in pulses:
                t_res = I3Calculator.time_residual(fit_particle,self.omgeo[om].position,pulse.time)
                if t_res>-75 and t_res<1000:
                    event_charge += pulse.charge
                elif t_res>2000:
                    late_charge += pulse.charge

        frame["event_charge"] = dataclasses.I3Double(event_charge)
        frame["late_charge"] = dataclasses.I3Double(late_charge)

        return True


    def Geometry(self,frame):
        """Set up the DOM geometry when reaching G-frame"""
        self.omgeo = frame['I3Geometry'].omgeo
        self.PushFrame(frame)

    def Physics(self,frame):
        """Calculate charges (if possible) for each P-frame"""
        if self.calculateCharges(frame):
            self.PushFrame(frame)




# Print information about input & output files
filestring = ""
for filename in infilenames:
    filestring += '\n    '+filename
print("Reading i3 file(s):"+filestring)
print("Writing charges in P-frames to file",outfilename)


# Use icetray to calculate charges of physics frames and write to file
tray = I3Tray()
tray.Add('I3Reader',"reader",FileNameList=infilenames)
tray.Add(ChargeModule)
tray.Add('I3Writer',"writer",FileName=outfilename,
         DropOrphanStreams=[icetray.I3Frame.Calibration,icetray.I3Frame.DAQ])
tray.Execute()
tray.Finish()
