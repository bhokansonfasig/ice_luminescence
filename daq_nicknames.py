# Import operating system and regular expression libraries for this chunk
import os, re

# Class for pulling the names and other information of doms based on their keys
class Nicknames:
    def __init__(self, filename):
        pattern = re.compile('([0-9a-f]{12})\s+(\w{8})\s+(\w+)\s+([0-9A-Z]{2}\-[0-9]{2}).*')
        self.mpat = re.compile('[0-9a-f]{12}')
        self.dpat = re.compile('([ATUX][EP][0-9][HPY][0-9]{4})')
        self.lpat = re.compile('\w{2}\-[0-9]{2}')
        f = open(filename)
        self.by_mbid  = dict()
        self.by_domid = dict()
        self.by_name  = dict()
        self.by_loc   = dict()
        self.domdb    = [ ]
        while 1:
            s = f.readline()
            if len(s) == 0: break
            m = pattern.match(s)
            if m is not None: self.domdb.append(m.groups())
        f.close()
        for index in range(len(self.domdb)):
            mbid, domid, name, loc = self.domdb[index]
            self.by_mbid[mbid] = index
            self.by_domid[domid] = index
            self.by_name[name] = index
            self.by_loc[loc] = index

    def lookup(self, key):
        """
        Do a smart lookup of a DOM.  It knows what you are asking.
        """
        # Lookup can pull information based on a single piece of information about the DOM
        if self.mpat.match(key):
            return self.domdb[self.by_mbid[key]]
        elif self.dpat.match(key):
            return self.domdb[self.by_domid[key]]
        elif self.lpat.match(key):
            return self.domdb[self.by_loc[key]]
        else:
            return self.domdb[self.by_name[key]]


# Location of the nickname file to pull DOM information from
nickdef = Nicknames('/home/fasig/nicknames.txt')

def lookup(key):
    if nickdef is None: return None
    return nickdef.lookup(key)
