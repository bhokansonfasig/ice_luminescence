#
#
# hsreader.py
# Library for dealing with raw hitspool files. Loads into python, writes to h5,
# loads as stream, etc.
#
# Ben Hokanson-Fasig
# Created   09/27/16
# Last edit 10/28/16
#

from __future__ import division, print_function
from struct import unpack
from daq_nicknames import lookup
import numpy as np
import sys, os, os.path


class Hit:
    """Hit object with attributes"""
    # Clean up if possible
    def __init__(self, omkey, utc, cw1, cw3):
        self.omkey = omkey
        self.utc = utc
        self.hdr = [ cw1 & 0xffffffff, cw3 & 0xffffffff]

    def __getattr__(self, name):
        if name == "hub_num":
            return int(self.omkey[0:2])
        elif name == "dom_num":
            return int(self.omkey[3:5])
        if name == "lc":
            return (self.hdr[0] >> 16) & 3
        elif name == "min_bias":
            return bool((self.hdr[0] >> 30) & 1)
        elif name == "fadc":
            return self.hdr[0] & 0x8000 != 0
        elif name == "atwd":
            return self.hdr[0] & 0x4000 != 0
        elif name == "aorb":
            return "AB"[(self.hdr[0] >> 11) & 1]
        elif name == "dig_info":
            ff = '-'
            fa = '-'
            if self.fadc: ff = 'F'
            if self.atwd: fa = self.aorb
            return ff+fa
        elif name == "trigmask":
            return (self.hdr[0] >> 18) & 0xfff
        elif name == "hit_size":
            return self.hdr[0] & 0x7ff
        elif name == "chargestamp":
            lsh = 0
            if self.hdr[1] & 0x80000000: lsh = 1
            return ((self.hdr[1] >> 27) & 0xf,
                            ((self.hdr[1] >> 18) & 0x1ff) << lsh,
                            ((self.hdr[1] >>  9) & 0x1ff) << lsh,
                            ((self.hdr[1] & 0x1ff) << lsh))
        elif name == "charge_pos":
            return self.chargestamp[0]
        elif name == "charge_pre":
            return self.chargestamp[1]
        elif name == "charge_max":
            return self.chargestamp[2]
        elif name == "charge_pst":
            return self.chargestamp[3]
        else:
            raise AttributeError, name

    def __str__(self):
        return "HIT: %s %d %x %x %3.3x %s %2d %d %d %d %d" % ( ( \
                self.omkey, self.utc, self.lc,
                self.min_bias, self.trigmask, self.dig_info, ) + self.chargestamp + ( self.hit_size, ) )

class HubStream:
    """Stream of hits from single hitspool file (passing filter)"""
    # Clean up if possible (especially lookup)
    def __init__(self, directory, hitfilter=lambda x: True):
        self.files = []
        # Grab hitspool data files
        for item in os.listdir(directory):
            if '.dat' in item:
                self.files.append(os.path.join(directory,item))

        # Make sure the hitspool files are in order
        self.files.sort()

        # Grab first file to start
        self.f = open(self.files[0])
        self.filter = hitfilter

    def __iter__(self):
        return self

    def nextFile(self):
        self.f.close()
        self.files.pop(0)
        if len(self.files)==0:
            raise StopIteration
        self.f = open(self.files[0])

    def nextRaw(self):
        buf = self.f.read(54)
        if len(buf) != 54:
            self.nextFile()
            buf = self.f.read(54)
        recl, rtyp, mbid, utc, unite, ver, fpq, domclk, w1, w3 = unpack(">iiq8xq3hq2i", buf)
        buf += self.f.read(recl - 54)
        return recl, rtyp, mbid, utc, unite, ver, fpq, domclk, w1, w3, buf

    def next(self):
        # Go through hits until one passes the filter
        while True:
            recl, rtyp, mbid, utc, unite, ver, fpq, domclk, w1, w3, buf = self.nextRaw()
            mbid = "%12.12x" % mbid
            omkey = lookup( mbid )[3]
            hit = Hit(omkey, utc, w1, w3)
            if self.filter(hit):
                return hit

class HitStream:
    """Time-sorted stream of hits from HubStreams passed"""
    def __init__(self, *streams):
        self.streams = []
        for stream in streams:
            self.streams.append(stream)

        # Buffer the first hit from each stream, and track its time
        self.tophits = []
        self.times = np.zeros(len(self.streams),'d')
        for i in range(len(self.streams)):
            self.tophits.append(self.streams[i].next())
            self.times[i] = self.tophits[i].utc

    def __iter__(self):
        return self

    def next(self):
        # Grab hit with lowest time, return it, and buffer next hit from that
        # stream
        if len(self.times)==0:
            raise StopIteration
        earliest_index = np.argmin(self.times)
        earliest_hit = self.tophits[earliest_index]
        try:
            self.tophits[earliest_index] = self.streams[earliest_index].next()
            self.times[earliest_index] = self.tophits[earliest_index].utc
        except StopIteration:
            self.times = np.delete(self.times,earliest_index)
            self.tophits.pop(earliest_index)
            self.streams.pop(earliest_index)
        return earliest_hit


# def single_load(filename, hitfilter=lambda x: True):
#     """Loads hit objects from single hitspool file (passing filter) into python
#     array"""
#     pass
#
#
# def single_write_h5(filename, outfilename, hitfilter=lambda x: True):
#     """Writes hits from single hitspool file (passing filter) to hdf5 file"""
#     pass


def list_paths(directory):
    output = os.listdir(directory)
    for i in range(len(output)):
        output[i] = os.path.join(directory,output[i])
    return output


def unzip_files(source, keyword="", destination="./hsreader_data",
                force_clear=False):
    """Unzips hitspool files (that include an optional keyword) into destination
    directory (usually clears destination directory first, so beware!)"""
    # Check if the data in destination matches the data that would come from
    # source (if so, then finish here)
    if not(force_clear):
        data_matches = True
        if os.path.isdir(destination):
            match_count = 0
            for src_item in os.listdir(source):
                src_name_i = src_item.find('.')
                src_name = src_item[:src_name_i]
                for dest_item in os.listdir(destination):
                    dest_name_i = dest_item.find('.')
                    dest_name = dest_item[:dest_name_i]
                    if dest_name in src_name:
                        match_count += 1
                        break
            if match_count/len(os.listdir(source))<.8:
                data_matches = False
        else:
            data_matches = False
        if data_matches:
            print("Existing data suspected to match source data.\n"+
                  "Skipping unzip process and using existing data in "+
                  destination)
            return list_paths(destination)

    # Clear and get rid of existing destination
    if os.path.isdir(destination):
        for item in os.listdir(destination):
            item_path = os.path.join(destination,item)
            if item[0]==".":
                continue
            if os.path.isdir(item_path):
                for subitem in os.listdir(item_path):
                    if subitem[0]==".":
                        continue
                    os.remove(os.path.join(item_path,subitem))
                os.rmdir(item_path)
            else:
                os.remove(item_path)
        os.rmdir(destination)

    # Create destination
    os.mkdir(destination)

    # Get all tar files from the passed directory that have hub data
    tarfiles = []
    for item in os.listdir(source):
        if ('ichub' in item) and ('.tar.gz' in item) and (keyword in item):
            tarfiles.append(item)

    # Throw error if no tar files found, or output directory is not a directory
    if len(tarfiles)==0:
        print("No hitspool tar files found.", file=sys.stderr)
        sys.exit(2)
    else:
        print("Unzipping files to",destination)

    # Make sure the tar files are in order
    tarfiles.sort()

    # Loop over hub files
    for gzfile in tarfiles:
        # Get index of current hub
        i = gzfile.find('ichub')
        hubindex = gzfile[i+5:i+7]
        hubstring = 'ichub'+str(hubindex).zfill(2)

        # Unzip gzfile
        os.system("tar -xzf "+os.path.join(source,gzfile)+" -C "+destination)

        # Grab bzfile
        bzfiles = []
        for item in os.listdir(destination):
            if (hubstring in item) and ('.tar.bz2' in item):
                bzfiles.append(item)

        # Throw error if not exactly one bzip file found,
        # but continue to next loop
        if len(bzfiles)!=1:
            print(len(bzfiles)," bzip tar files found from hub ",hubindex,
                ". Expected one bzip tar file.", sep="",file=sys.stderr)
            print(bzfiles, file=sys.stderr)
            print("  Error. Skipping hub "+hubindex)
            continue

        # Unzip bzfile
        os.system("tar -xjf "+os.path.join(destination,bzfiles[0])+\
                  " -C "+destination)

        # Delete the leftover xml file(s)
        xmlfiles = []
        for item in os.listdir(destination):
            if (hubstring in item) and ('.meta.xml' in item):
                xmlfiles.append(item)
        for xmlfile in xmlfiles:
            os.remove(os.path.join(destination,xmlfile))

        # Delete the bzip file
        os.remove(os.path.join(destination,bzfiles[0]))

        # Grab hitspool directory
        hsdirectories = []
        for item in os.listdir(destination):
            if (hubstring in item) and \
            os.path.isdir(os.path.join(destination,item)):
                hsdirectories.append(item)

        # Throw error if not exactly one hitspool directory found,
        # but continue to next loop
        if len(hsdirectories)!=1:
            print(len(hsdirectories)," hitspool directories found from hub ",hubindex,
                ". Expected one hitspool directory.", sep="",file=sys.stderr)
            print(hsdirectories, file=sys.stderr)
            print("  Error. Skipping hub "+hubindex)
            continue

    return list_paths(destination)



def load_stream(source_dir, keyword="", hitfilter=lambda x: True,
                data_dir="./hsreader_data", reuse_data=None):
    """Loads hit objects from hitspool files from all hub tarfiles in
    directory (time-sorted, passing filter) as a stream"""
    if reuse_data==True:
        data_directories = list_paths(data_dir)
    elif reuse_data==False:
        data_directories = \
            unzip_files(source_dir,keyword,data_dir,force_clear=True)
    else:
        data_directories = unzip_files(source_dir,keyword,data_dir)

    streams = []

    for hubdir in data_directories:
        # Form stream from hitspool directory
        streams.append(HubStream(hubdir,hitfilter))

    stream = HitStream(*streams)

    return stream


def load(source_dir, keyword="", hitfilter=lambda x: True,
         data_dir="./hsreader_data", reuse_data=None):
    """Loads hit objects from hitspool files from all hub tarfiles in
    directory (time-sorted, passing filter) to a python array"""
    hitstream = load_stream(source_dir,keyword,hitfilter,data_dir)
    hits = []
    for hit in hitstream:
        hits.append(hit)
    return hits


def write_h5(source_dir, outfilename, keyword="", hitfilter=lambda x: True,
             data_dir="./hsreader_data", reuse_data=None):
    """Writes hits from hitspool files from all hub tarfiles in
    directory (time-sorted, passing filter) to hdf5 file"""
    # Avoid this import in the main file since it is only really necessary here
    import tables

    # Prepare for hdf5 files
    class HitData(tables.IsDescription):
        omkey = tables.StringCol(8,pos=0)     # 8-character string
        hub_num = tables.Int8Col(pos=1)       # Signed 8-bit integer
        dom_num = tables.Int8Col(pos=2)       # Signed 8-bit integer
        utc = tables.Int64Col(pos=3)          # Signed 64-bit integer
        lc = tables.Int8Col(pos=4)            # Signed 8-bit integer
        min_bias = tables.BoolCol(pos=5)      # Boolean value
        trigmask = tables.StringCol(16,pos=6) # 16-character string
        dig_info = tables.StringCol(8,pos=7)  # 8-character string
        charge_pos = tables.Int16Col(pos=8)   # Signed 16-bit integer
        charge_pre = tables.Int16Col(pos=9)   # Signed 16-bit integer
        charge_max = tables.Int16Col(pos=10)  # Signed 16-bit integer
        charge_pst = tables.Int16Col(pos=11)  # Signed 16-bit integer
        hit_size = tables.Int8Col(pos=12)     # Signed 8-bit integer




    if outfilename[-3:]!=".h5" and outfilename[-5:]!=".hdf5":
        outfilename += ".h5"

    h5file = tables.openFile(outfilename, mode="w", title="HitSpool Hits")
    hittable = h5file.createTable("/", "hits", HitData, "All Hits")

    hitstream = load_stream(source_dir,keyword,hitfilter,data_dir)
    for hit in hitstream:
        # Form a row in the table for each hit
        hittable.row['omkey'] = hit.omkey
        hittable.row['hub_num'] = hit.hub_num
        hittable.row['dom_num'] = hit.dom_num
        hittable.row['utc'] = hit.utc
        hittable.row['lc'] = hit.lc
        hittable.row['min_bias'] = hit.min_bias
        hittable.row['trigmask'] = hit.trigmask
        hittable.row['dig_info'] = hit.dig_info
        hittable.row['charge_pos'] = hit.charge_pos
        hittable.row['charge_pre'] = hit.charge_pre
        hittable.row['charge_max'] = hit.charge_max
        hittable.row['charge_pst'] = hit.charge_pst
        hittable.row['hit_size'] = hit.hit_size
        hittable.row.append()

    hittable.flush()
    h5file.close()
