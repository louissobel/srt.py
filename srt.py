
#################################################
# srt.py
#
# A Python script to manipulate .srt subtitles
#
# Version:  0.1
# Author:   Riobard
# Email:    me@riobard.com
# Web:      http://riobard.com

# Version:  0.2
# Author:   sobel
# Email:    louis.a.sobel@gmail.com
#################################################

import functools
import re
from sys import argv
from itertools import count
import sys


@functools.total_ordering
class Timecode(object):
    """
    Wrapper over a time code
    Includes comparisons,
    and ways for it to convert to and from a string
    """
    
    @classmethod
    def from_string(cls, tc):
        """
        Parses the timecode and creates a Timecode isntance
        with the milliseconds stored internally
        """
        sign    = 1
        if tc[0] in "+-":
            sign    = -1 if tc[0] == "-" else 1
            tc  = tc[1:]

        TIMECODE_RE     = re.compile('(?:(?:(?:(\d?\d):)?(\d?\d):)?(\d?\d))?(?:[,.](\d?\d?\d))?')
        # NOTE the above regex matches all following cases
        # 12:34:56,789
        # 01:02:03,004
        # 1:2:3,4   => 01:02:03,004
        # ,4        => 00:00:00,004
        # 3         => 00:00:03,000
        # 3,4       => 00:00:03,004
        # 1:2       => 00:01:02,000
        # 1:2,3     => 00:01:03,003
        # 1:2:3     => 01:02:03
        # also accept "." instead of "," as millsecond separator
        match   = TIMECODE_RE.match(tc)
        try: 
            assert match is not None
        except AssertionError:
            print tc
        hh,mm,ss,ms = map(lambda x: 0 if x==None else int(x), match.groups())
        return cls(((hh*3600 + mm*60 + ss) * 1000 + ms) * sign)
     
    def __init__(self, ms):
        '''
        Construct a Timecode object from string representation or milliseconds
        '''

        self._milliseconds = ms   
    
    def copy(self):
        return Timecode(self.milliseconds())
    
    def milliseconds(self):
        return self._milliseconds
        
    def __len__(self):
        return self.milliseconds()
        
    def __str__(self):
        ''' convert millisecond to timecode ''' 
        ms = self._milliseconds
        sign    = '-' if ms < 0 else ''
        ms      = abs(ms)
        ss, ms  = divmod(ms, 1000)
        hh, ss  = divmod(ss, 3600)
        mm, ss  = divmod(ss, 60)
        TIMECODE_FORMAT = '%s%02d:%02d:%02d,%03d'
        return TIMECODE_FORMAT % (sign, hh, mm, ss, ms) 

    def __eq__(self, other):
        return self.milliseconds() == other.milliseconds()
        
    def __lt__(self, other):
        return self.milliseconds() < other.milliseconds()
        
    def __sub__(self, other):
        return Timecode(self.milliseconds() - other.milliseconds())
    
    def __add__(self, other):
        return Timecode(self.milliseconds() + other.milliseconds())

@functools.total_ordering
class SRTFrame(object):
    """
    An object representing an SRT Frame
    """
    
    def __init__(self, start, end, lines=None):
        """
        Start, end are Timecode instances
        Words is a string
        """
        self.start = start
        self.end = end
        self.lines = lines or []
        
    def copy(self):
        return SRTFrame(self.start.copy(), self.end.copy(), [l for l in self.lines])
    
    def split(self, time):
        """
        returns two timecodes, with the same words.
        
        BUT
        if time is before start or after end,
        one of the timecodes will have no words
        """
        if time < self.start:
            first = SRTFrame(time, self.start)
            second = self
        
        elif time > self.end:
            first = self
            second = SRTFrame(self.end, time)
            
        else:
            first = SRTFrame(self.start, time, self.lines[:])
            second = SRTFrame(time, self.end, self.lines[:])
            
        return (first, second)
        
    def shift(self, time):
        """
        will shift the frame by the given time (instance of Timecode)
        if time is negative, it will move backwards!
        if time is positive, it will move forwards!
        """
        if isinstance(time, int):
            time = Timecode(time)
        
        start = self.start + time
        end = self.end + time

        return SRTFrame(start, end, self.lines[:])
        
    def __str__(self):
        HEADERFORMAT = "%s --> %s\n"
        
        out = ""
        out += HEADERFORMAT % (str(self.start), str(self.end))
        
        for line in self.lines:
            out += line + '\n'
            
        return out
        
    ## total ordering is by start time.
    ## should be OK  
    def __eq__(self, other):
        return self.start == other.start
        
    def __lt__(self, other):
        return self.start < other.start


class SRTDocument(object):
    """
    Represents a set of SRT frames
    uses a list to hold them,
    just calls sort after each insert
    
    """
    
    def __init__(self, frames=None):
        """
        frames is an optional LIST of frames
        """
        self.frames = frames or []
        self.frames = [f.copy() for f in self.frames]
        
        self._sort()
        
    def _sort(self):
        # because of the total ordering on 
        # frames, this should be sufficient
        self.frames.sort()
        return self
        
    def add_frame(self, frame):
        return SRTDocument(self.frames + [frame])
    
    def copy(self):
        return SRTDocument(self.frames)
    
    def split(self, time):
        """
        splits the document at the given time
        """
        
        if not self.frames:
            # so if I don't have any frames:
            # return two empty documents. fine
            first = SRTDocument()
            second = SRTDocument()
            
        else:
            
            first_frame = self.frames[0]
            if time <= first_frame.start:
                first = SRTDocument()
                second = self.copy()
            else:
                # lets find the first frame
                # whose end is >= time
                frame_iter = iter(self.frames)
                
                splitframe = frame_iter.next() # we have at least one, so this is safe
                splitindex = 0
                while splitframe.end < time:
                    try:
                        splitframe = frame_iter.next()
                        splitindex += 1
                    except StopIteration:
                        splitframe = None
                        break
                
                #ok cool. so split frame is the frame we split at.
                # but, if time == splitframe.end, we don't split ()
                # AND, if split frame is none, we need an empty document
                
                if splitframe is None:
                    # this is the condition
                    # of time being after the end
                    first = self.copy()
                    second = SRTDocument()
                
                else:
                    # lets check if time is on the end of splitframe
                    if time == splitframe.end:
                        first = SRTDocument(self.frames[:splitindex + 1])
                        second = SRTDocument(self.frames[splitindex + 1:])
                    else:
                        #ok so now this is an internal, internal case
                        left, right = splitframe.split(time)
                                                
                        first_frames = self.frames[:splitindex] + [left]
                        second_frames = [right] + self.frames[splitindex + 1:]
                        
                        first = SRTDocument(first_frames)
                        second = SRTDocument(second_frames)
                        
        return (first, second)
            
    def normalize(self):
        """
        makes sure that first frame starts at 0
        """
        if not self.frames:
            return self
        
        # we have at least one
        start = self.frames[0].start.milliseconds()
        
        
        if start: # does not equal 0
             return SRTDocument([frame.shift(start * -1) for frame in self.frames])

        return self
        
    def shift(self, ms):
        """
        shifts the given SRT by this many millisecods
        """
        return SRTDocument([frame.shift(ms) for frame in self.frames])
        
    
    def add(self, other):
        """
        adds other to the end of self
        if other starts before self ends,
        throws an error
        """
        if not other.frames:
            return self.copy()
            
        if not self.frames:
            return other.copy()
        
        #other.frames is at elast one
        other_start = other.frames[0].start
        
        self_end = self.frames[-1].end
        
        if other_start < self_end:
            raise ValueError("Other cannot start before this SRTDocument ends! (in add)")
            
        shift_duration = self_end - other_start
        other.shift(shift_duration) #other now starts right when self ends. so we can just glob them
        
        for frame in other.frames:
            self = self.add_frame(frame)
        
        return self
        
        
    def __str__(self):
        out = "\n"
        index = 1
        
        for frame in self.frames:
            out += "%d\n" % index
            out += str(frame)
            out += "\n"
            index += 1
        return out
        
    
        
            
        
    
               

#################################################
# .srt parsing
#################################################

def parse(file_path):
    """
    returns an SRTDocument
    """
    
    TIMECODE_SEP    = re.compile('[ \->]*')

    
    file_handle = open(file_path, 'r')
    
    
    state = 'waiting' # or timerange or lines
    
    doc = SRTDocument()

    start = None
    end = None
    lines = []

    for line in file_handle:
        line = line.strip()
        
        if state == 'waiting':
            #assume its a valid SRT
            if line:
                state = 'time'
        elif state == 'time':
            start, end = map(Timecode.from_string, TIMECODE_SEP.split(line))
            state = 'text'
        elif state == 'text':
            if line == '':
                # switch 
                doc = doc.add_frame(SRTFrame(start, end, lines))
                start = None
                end = None
                lines = []
                state = 'waiting'
            else:
                lines.append(line)
                
    if start:
        doc = doc.add_frame(SRTFrame(start, end, lines))
    return doc


def command_delete(doc, start_string, end_string):

    if start_string == 'start':
        start = Timecode(0)
    else:
        start =  Timecode.from_string(start_string)    
    
    if end_string == 'end':
        end = Timecode(sys.maxint)
    else:
        end = Timecode.from_string(end_string)
        
    
    left, right = doc.split(start)
    gone, right = right.split(end)
    

    return left.add(right).normalize()
    



if __name__ == '__main__':

    try:
        
        filename = argv[1]
        command = argv[2]
    
        start_string = argv[3]
        end_string = argv[4]
    except IndexError:
        print """
Usage:
python srt.py delete [start] [end]

start and end should be a HH:MM:SS,MMM timestamp
they can also be the words 'start' or 'end'

this prints the new file to stdout
"""
        sys.exit(1)
    
    
    doc = parse(filename)
    
    cut = command_delete(doc, start_string, end_string)
    
    print cut
