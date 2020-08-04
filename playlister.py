#!/usr/bin/env python3
import argparse
import datetime
import os
import pathlib
import random
import sys
import time
import xml.etree.cElementTree as ET

'''
Creates VLC playlist (extension: '.xspf') of all videos of a given format within a directory/folder (recursive)

TODO: Figure out why it's ElementTree writes to a single line. It doesn't break the playlist, but it's ugly
'''


class Playlist():

    default_formats = [".avi",".mp4",".mkv"]
    playlist_extension = ".xspf"
    recursive = True

    filter_exclude_terms = None
    filter_exclude_dirs = None
    filter_exclude_formats = None
    filter_include_terms = None
    filter_include_dirs = None
    allowed_formats = None

    # Filter by datetime.datetime
    filter_exclude_before = None
    filter_exclude_after = None


    def __init__(self, dir, dest_file, include_formats=None, recursive=True):

        if not os.path.isdir(dir):
            return None                 # TODO: make proper error
        if os.path.isdir(dest_file):
            return None                 # TODO: make proper error
        self.root_dir = pathlib.Path(dir).resolve()
        self.dest_path = pathlib.Path(dest_file).resolve()
        if self.dest_path.suffix != '':
            self.playlist_extension = self.dest_path.suffix

        if include_formats:
            self.allowed_formats = set(include_formats)
        else:
            self.allowed_formats = set(self.default_formats)
        
        self.unfiltered_files = []
        self.playlist_files = []


    def add_filters(self, exclude_terms=None, exclude_dirs=None, exclude_formats=None, exclude_before=None, exclude_after=None,
    include_terms=None, include_dirs=None, include_formats=None):
        
        if exclude_terms:
            if not self.filter_exclude_terms:
                self.filter_exclude_terms = exclude_terms
            else:
                for term in exclude_terms:
                    self.filter_exclude_terms.append(term)

        if exclude_dirs:
            if not self.filter_exclude_dirs:
                self.filter_exclude_dirs = set(pathlib.Path(p).resolve() for p in parse_arg_to_list(exclude_dirs))
            else:
                for dir in parse_arg_to_list(exclude_dirs):
                    self.filter_exclude_dirs.add(dir)

        if exclude_formats:
            if not self.filter_exclude_formats:
                self.filter_exclude_formats = set("." + fmt.lstrip(".") for fmt in exclude_formats)
            else:
                for fmt in parse_arg_to_list(exclude_formats):
                    self.filter_exclude_formats.add(fmt)

        if exclude_before:
            self.filter_exclude_before = parse_time_str_ago(exclude_before)         # Will return None if error parsing, which could be sneaky bug
        if exclude_after:
            self.filter_exclude_after = parse_time_str_ago(exclude_after)           # Will return None if error parsing, which could be sneaky bug
 
        
        if include_terms:
            if not self.filter_include_terms:
                self.filter_include_terms = include_terms
            else:
                for term in include_terms:
                    self.filter_include_terms.append(term)

        if include_dirs:
            if not self.filter_include_dirs:
                self.filter_include_dirs = [pathlib.Path(p).resolve() for p in include_dirs]
            else:
                for d in include_dirs:
                    self.filter_include_dirs.append(pathlib.Path(d).resolve())
        if include_formats:
            if not self.allowed_formats:
                self.allowed_formats = set(include_formats)
            else:
                for fmt in include_formats:
                    self.allowed_formats.add(fmt)

    
    def get_all_files(self):
        '''
        Gets all filepaths within directories that are not filtered

        NOTE: doesn't consider recursive option, and will always be recursive
        '''
    
        for root_dir, dirs, filenames in os.walk(str(self.root_dir)):
            # Don't traverse excluded dirs
            if self.filter_exclude_dirs:
                dirs[:] = [d for d in dirs if pathlib.Path(d).resolve() not in self.filter_exclude_dirs]
            # Maybe don't do it this way
            if self.filter_include_dirs:
                allowed = []
                for d in dirs:
                    d_pure = pathlib.Path(os.path.join(root_dir, d)).resolve()
                    for inc_dir in self.filter_include_dirs:
                        if inc_dir == d_pure or inc_dir in d_pure.parents:
                            allowed.append(d)
                            break

            for fname in filenames:
                self.unfiltered_files.append(pathlib.PurePath(os.path.abspath(os.path.join(root_dir, fname))).as_posix())
        return
    
    def filter_files(self):
        for f in self.unfiltered_files:
            if self.file_is_allowed(f):
                self.playlist_files.append(f)

    def file_is_allowed(self, f):
        ''' 
        returns True if file passes all filters
        '''

        fpath = pathlib.PurePath(f)

        # Filter by file extension
        if fpath.suffix not in self.allowed_formats:
            return False
        if self.filter_exclude_formats:
            if fpath.suffix in self.filter_exclude_formats:
                return False

        # Filter by key terms
        fpath_str = str(fpath)
        if self.filter_exclude_terms:
            for term in self.filter_exclude_terms:
                if term in fpath_str.lower():
                    return False
        if self.filter_include_terms:
            included = False
            for term in self.filter_include_terms:
                if term in fpath_str:
                    included = True
            if not included:
                return False
        
        # Filter by file modification date
        mtime = os.path.getmtime(fpath_str)
        mdate = datetime.datetime.strptime(time.ctime(mtime), "%a %b %d %H:%M:%S %Y")
        if self.filter_exclude_before:
            if mdate < self.filter_exclude_before:
                return False
        if self.filter_exclude_after:
            if mdate > self.filter_exclude_after:
                return False
        
        return True

    def make(self):
        self.get_all_files()
        self.filter_files()
        self.make_playlist()

    def make_playlist(self):

        # Create 'playlist' as root Element
        playlist = ET.Element("playlist")
        playlist.set("xmlns", "http://xspf.org/ns/0/")
        playlist.set("xmlns:vlc", "http://www.videolan.org/vlc/playlist/ns/0/")
        playlist.set("version", "1")

        # Set title
        title = str(self.dest_path).rstrip(self.dest_path.suffix)
        ET.SubElement(playlist, "title").text = title

        # Create tracklist
        tracklist = ET.SubElement(playlist, "trackList")

        # Add tracks to tracklist
        file_format = "file:///{}"
        for i, name in enumerate(self.playlist_files):
            track = ET.SubElement(tracklist, "track")
            ET.SubElement(track, "location").text = file_format.format(name)
            ET.SubElement(track, "duration")

            extension = ET.SubElement(track, "extension")
            extension.set("application", "http://www.videolan.org/vlc/playlist/0")
            ET.SubElement(extension, "vlc:id").text = str(i)

        # Last element
        ext = ET.SubElement(playlist, "extension")
        ext.set("application", "http://www.videolan.org/vlc/playlist/0")
        for i in range(len(self.playlist_files)):
            ET.SubElement(ext, "vlc:item").set("tid", str(i))

        tree = ET.ElementTree(playlist)
        filename = f"{title}{self.playlist_extension}"

        # Remove playlist if it already exists
        if os.path.exists(filename):
            os.remove(filename)

        tree.write(filename, encoding="utf-8", xml_declaration=True)


def parse_arg_to_list(arg, normalize_case=True):
    '''
    Split string by commas, for args
    '''
    if not arg:
        return None

    if not normalize_case:
        parsed = [x.strip() for x in arg.split(",") if x != ""]
    else:
        parsed = [x.strip().lower() for x in arg.split(",")]
    return parsed

def comma_list(s):
    return parse_arg_to_list(s, normalize_case=False)

def comma_list_cased(s):
    return parse_arg_to_list(s, normalize_case=True)

def parse_time_str_ago(s):
    '''
    Takes some string formatted like "2w5d" and returns a datetime.datetime object representing the time that many units ago (e.g. 2 weeks and 5 days ago).

    m = minutes
    h = hours
    d = days
    w = weeks
    y = years

    Other letters cause error. If nothing precedes letter that can be cast as int, it will be 1 (e.g. "2dy" is 2 days 1 year. "www" is 3 weeks)
    Not case sensitive
    '''

    ago = {
        "m": 0,
        "h": 0,
        "d": 0,
        "w": 0,
        "y": 0,
    }

    int_buf = ""
    for c in s.lower():
        try:
            __ = int(c)
            int_buf += c
        except ValueError:
            if ago.get(c, False) is False:
                return None                 # TODO: return error
            if int_buf == "":
                amt = 1
            else:
                amt = int(int_buf)
                int_buf = ""
            ago[c] += amt

    # datetime.datetime objects don't do "years" so multiply days by 365 for each year
    ago["d"] += 365 * ago["y"]
    
    ago_date = datetime.datetime.now() - datetime.timedelta(
        minutes=ago["m"],
        hours=ago["h"],
        days=ago["d"],
        weeks=ago["w"],
    )

    return ago_date


def parse_args():


    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "directory",
        help="Directory containing video files"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="untitled-playlist",
        help="Title of playlist / Path to playlist"
    )
    parser.add_argument(
        "-f",
        "--formats",
        default=None,
        help="Comma-separated list of formats to include. Prepending '+' appends to defaults"
    )
    parser.add_argument(
        "-x",
        "--exclude",
        type=comma_list,
        help="Comma-separated list of strings to censor"
    )
    parser.add_argument(
        "-n",
        "--include",
        default=None,
        action="append",
        help="Comma-separated list of strings to require"
    )
    parser.add_argument(
        "-m",
        "--max-len",
        default=None,
        type=int,
        help="Maximum # of videos in playlist"
    )
    parser.add_argument(
        "-r", 
        "--random",
        default=False,
        action="store_true",
        help="Random videos, so if max=100 and there are 200 videos, they won't be uniform"
    )
    parser.add_argument(
        "--exclude-before",
        default=None,
        help="Exclude videos modified before this age. Format as [int][unit]..., where [unit] is exactly one of [h (hour), d (day), w (week), m (month)]"
    )
    parser.add_argument(
        "--exclude-after",
        default=None,
        help="Exclude videos modified after this age. Format as [int][unit]..., where [unit] is exactly one of [h (hour), d (day), w (week), m (month)]"
    )
    parser.add_argument(
        "--exclude-formats",
        default=None,
        help="Exclude videos modified after this age. Format as [int][unit]..., where [unit] is exactly one of [h (hour), d (day), w (week), m (month)]"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    return parser.parse_args()

def main():
    
    args = parse_args()

    # Instantiate 
    directory = args.directory
    output = args.output

    if args.formats:
        formats = args.formats
        if formats[0] == "+":
            formats = Playlist.default_formats + formats[1:]
    else:
        formats = None
    playlist = Playlist(directory, output, include_formats=formats)

    

    playlist.add_filters(
        exclude_terms=args.exclude,
        exclude_dirs=None,
        exclude_formats=args.exclude_formats,
        exclude_before=args.exclude_before,

        include_terms=args.include,
        include_dirs=None,    
    )
    
    playlist.make()


    # Make .xspf playlist
    video_count = len(playlist.playlist_files)
    print(f"{playlist.dest_path} created with {video_count} videos.")


if __name__ == '__main__':

    main()
