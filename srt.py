
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
import json

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
    
    def text(self):
        return '\n'.join(self.lines)
    
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
    
    def json(self):
        start = []
        end = []
        text = []
        for frame in self.frames:
            start.append(frame.start.milliseconds())
            end.append(frame.end.milliseconds())
            text.append(frame.text())
        return json.dumps({
            'start' : start,
            'end' : end,
            'text' : text,
        }, indent=4)
            
    
        
            
        
    
               

#################################################
# .srt parsing
#################################################

def get_file_type(file_path):
    if file_path.endswith('.sjson'):
        return 'sjson'
    elif file_path.endswith('.srt'):
        return 'srt'
    else:
        #fallback
        return 'srt'



def parse(file_path):
    type_parse_functions = {
        'sjson' : parse_sjson,
        'srt' : parse_srt,
    }
    file_handle = open(file_path, 'r')
    return type_parse_functions[get_file_type(file_path)](file_handle)

def parse_sjson(file_handle):
    """
    returns an SRTDocuement from a sjson file
    """
    json_data = json.load(file_handle)
    
    doc = SRTDocument()
    
    starts = json_data['start']
    ends = json_data['end']
    texts = json_data['text']

    for frame_index in range(len(starts)):
        start = Timecode(starts[frame_index])
        end = Timecode(ends[frame_index])
        text = texts[frame_index]
        doc = doc.add_frame(SRTFrame(start, end, text.split('\n')))
    return doc
    


def parse_srt(file_handle):
    """
    returns an SRTDocument from a .srt file
    """
    
    TIMECODE_SEP    = re.compile('[ \->]*')   
    
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


def command_delete(args):
    """python srt.py delete [filename] [start] [end]
    
    deletes the segment described by [start] [end]

    start and end should be a HH:MM:SS,MMM timestamp
    they can also be the words 'start' or 'end'

    this prints the new file to stdout
    """
    if not args:
        raise ValueError("delete must be called with a filename argument")
    
    filename = args.pop(0)
    doc = parse(filename)
        
    
    start_string = args[0]
    end_string = args[1]
    
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
    

    result = left.add(right).normalize()
    print result
    return result

def command_split(args):
    """python srt.py split [filename] [timestamp]+
    
    splits the file at the given timestamps
    timestamp has format HH:MM:SS,MMM
    
    The timestamps should be in increasing order!
    
    writes the files out with format [infile]_0.srt
    with the digit ranging up
    """
    if not args:
        raise ValueError("Split must be given arguments!")
    
    filename = args.pop(0)
    doc = parse(filename)
    
    if not args:
        raise ValueError("Split must be called with at least one timestamp")
    
    out_list = []
    current = doc
    for arg in args:
        timecode = Timecode.from_string(arg)
        left, right = current.split(timecode)
        out_list.append(left)
        current = right
    out_list.append(current)
    
    out_list = [srt_document.normalize() for srt_document in out_list]
    
    # ok, now we have to print them
    
    # lets get our format... lets strip a .srt if there is one
    if filename.endswith('.srt'):
        filename = filename[:-4]
        
    FORMAT_STRING = "%s_%%d.srt" % filename
    
    for index, srt_document in enumerate(out_list):
        out_file_handle = open(FORMAT_STRING % index, 'w')
        out_file_handle.write(str(srt_document))
        out_file_handle.close()
        
def command_srt2sjson(args):
    """python srt.py srt2sjson [filename | -]
    
    converts the file name given to a sjson file
    accepts input from stdin by giving a dash
    
    prints result to stdout
    """
    
    try:
        filename = args[0]
    except IndexError:
        filename = '-'
        
    if filename == '-':
        file_handle = sys.stdin
    else:
        file_handle = open(filename, 'r')
        
    doc = parse_srt(file_handle)
    print doc.json()
    
def command_sjson2srt(args):
    """python srt.py srt2sjson [filename | -]

    converts the file name given to a sjson file
    accepts input from stdin by giving a dash

    prints result to stdout
    """

    try:
        filename = args[0]
    except IndexError:
        filename = '-'

    if filename == '-':
        file_handle = sys.stdin
    else:
        file_handle = open(filename, 'r')

    doc = parse_sjson(file_handle)
    print str(doc)

        
    

def command_cat(args):
    """python srt.py cat [file1] [file2]...
    
    Concatenates the given SRT files (in the order given)
    and prints the result to stdout.
    """
    
    if not args:
        raise ValueError("Cannot concatenate no files!")

    first = args[0]
    output_type = get_file_type(first)

    srt_docs = []
    for filename in args:
        srt_docs.append(parse(filename))
    
    
    
def command_help(args):
    """python srt.py help [command]
    
    Prints usage information
    """
    try:
        command = args[0]
    except IndexError:
        command = None
    
    
    if command:
        try:
            help_target_function = command_dict[command]
        except KeyError:
            print "command %s not found" % command
        else:
            print help_target_function.__doc__
            return
    
    print "Commands:"
    for command, function in commands:
        print command
    
    print "-"*10
    
    for command, function in commands:
        print "%s:" % command
        print function.__doc__
        print
        

commands = [
    ('delete', command_delete),
    ('split', command_split),
    ('srt2sjson', command_srt2sjson),
    ('sjson2srt', command_sjson2srt),
    ('help', command_help),
]

command_dict = dict(commands)

if __name__ == '__main__':

    try:
        command = argv[1]
        args = argv[2:]
    except IndexError:
        if command == "help":
            command_help()
        else:
            print """
Usage:
python srt.py [command] [args]

try python srt.py help for info
"""
        sys.exit(1)

    
    try:
        command_function = command_dict[command]
    except KeyError:
        print "command not found..\n\ntry python srt.py help for info"
        sys.exit(1)
    
    command_function(args)
