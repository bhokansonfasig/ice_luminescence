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
                sys, os, os.path, datetime, numpy, matplotlib.pyplot"""

# Parse command line arguments
parser = argparse.ArgumentParser(description=parser_desc, epilog=parser_ep)

args = parser.parse_args()

# Store arguments to variables for rest of the script



# Standard libraries
import sys, os, os.path
import datetime
import numpy as np
import matplotlib.pyplot as plt
