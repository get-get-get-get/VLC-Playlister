#!/usr/bin/env python3
import argparse
import datetime
import os
import pathlib
import random
import time
import xml.etree.cElementTree as ET

"""
Creates VLC playlists
"""


class Playlist():

    default_formats = [".avi",".mp4",".mkv"]
    playlist_extension = ".xspf"
    max_length = None
    randomize = False

    filter_exclude_terms = None
    filter_exclude_dirs = None
    filter_exclude_formats = None
    filter_include_terms = None
    filter_include_dirs = None

    # Filter by datetime.datetime
    filter_include_after = None
    filter_include_before = None


    def __init__(self, dir, dest_file, include_formats=None, recursive=True):
        """ 
        Instantiate Playlist

        Keyword arguments:
        include_formats -- list or set of file formats to include in playlist. 
        recursive -- include subdirectories in search
        """

        # Possible errors (TODO: raise actual error)
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
        
        self.recursive = recursive
        
        self.unfiltered_files = []
        self.playlist_files = []


    def add_filters(self, exclude_terms=None, exclude_dirs=None, exclude_formats=None, include_after=None, include_before=None,
    include_terms=None, include_dirs=None, include_formats=None):
        """
        Add restriction on what files are included in Playlist

        Keyword arguments:
        exclude_terms -- list of strings that playlist files must not contain in their filepath
        exclude_dirs -- list/set of strings of dir paths that will not be included in search for files
        exclude_formats -- list/set of strings representing file formats to exclude from playlist
        include_terms -- list of strings that playlist files must contain in their filepath
        include_dirs -- list of strings of dir paths that files must be under to include
        include_formats -- list/set of strings representing file formats to include in playlist
        include_after -- datetime.datetime of oldest modification date allowed for included files
        include_before -- datetime.datetime of most recent modification date allowed for included files
        """

        if exclude_terms:
            if not self.filter_exclude_terms:
                self.filter_exclude_terms = exclude_terms
            else:
                for term in exclude_terms:
                    self.filter_exclude_terms.append(term)

        if exclude_dirs:
            if not self.filter_exclude_dirs:
                self.filter_exclude_dirs = set(pathlib.Path(p).resolve() for p in parse_comma_list(exclude_dirs))
            else:
                for dir in parse_comma_list(exclude_dirs):
                    self.filter_exclude_dirs.add(dir)

        if exclude_formats:
            if not self.filter_exclude_formats:
                self.filter_exclude_formats = set("." + fmt.lstrip(".") for fmt in exclude_formats)
            else:
                for fmt in parse_comma_list(exclude_formats):
                    self.filter_exclude_formats.add(fmt)
        
        if include_before:
            self.filter_include_before = include_before
        if include_after:
            self.filter_include_after = include_after
        
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
        """
        Sets self.unfiltered_files with all filepaths within directories that are not filtered.

        NOTE: doesn't consider recursive option, and will always be recursive
        """
    
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
        """
        Sets self.playlist_files with according to instance's filter variables
        """
        for f in self.unfiltered_files:
            if self.file_is_allowed(f):
                self.playlist_files.append(f)
        
        if self.randomize:
            random.seed()
            random.shuffle(self.playlist_files)
        
        if self.max_length:
            self.playlist_files = self.playlist_files[:self.max_length]


    def file_is_allowed(self, f) -> bool:
        """ 
        Returns True if file passes all filters
        """

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
        
        # Filter by file creation date
        if self.filter_include_after or self.filter_include_before:
            created = get_file_cdate(fpath_str)
            if self.filter_include_after:
                if created < self.filter_include_after:
                    return False
            if self.filter_include_before:
                if created > self.filter_include_before:
                    return False

        return True

    def make(self):
        """
        Convenience function that gets files, filters them, and then saves the playlist to disk
        """
        self.get_all_files()
        self.filter_files()
        self.make_playlist()

    def make_playlist(self):
        """
        Format Playlist in VLC-compatible XML and save to file.
        """

        # Create 'playlist' as root Element
        playlist = ET.Element("playlist")
        playlist.set("xmlns", "http://xspf.org/ns/0/")
        playlist.set("xmlns:vlc", "http://www.videolan.org/vlc/playlist/ns/0/")
        playlist.set("version", "1")

        # Set title
        title = str(self.dest_path).rstrip(self.dest_path.suffix)
        ET.SubElement(playlist, "Title").text = title

        # Create tracklist
        tracklist = ET.SubElement(playlist, "trackList")

        # Add tracks to tracklist
        file_format = "file:///{}"
        for i, name in enumerate(self.playlist_files):
            track_title = make_video_title(name)
            track = ET.SubElement(tracklist, "track")
            ET.SubElement(track, "location").text = file_format.format(name)
            # TODO: make optional? will not show metadata
            ET.SubElement(track, "title").text = track_title
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


def parse_comma_list(arg, normalize_case=True) -> list:
    """
    Return list by splitting string with comma

    Keyword arguments:
    normalize_case -- return lowercased strings 
    """
    if not normalize_case:
        parsed = [x.strip() for x in arg.split(",") if x != ""]
    else:
        parsed = [x.strip().lower() for x in arg.split(",")]
    return parsed

def comma_list(s) -> list:
    return parse_comma_list(s, normalize_case=False)

def comma_list_cased(s) -> list:
    return parse_comma_list(s, normalize_case=True)


# datetime of last file modification
def get_file_mdate(fpath) -> datetime.datetime:
        mtime = os.path.getmtime(fpath)
        return datetime.datetime.strptime(time.ctime(mtime), "%a %b %d %H:%M:%S %Y")


# datetime of file creation
def get_file_cdate(fpath) -> datetime.datetime:
        ctime = os.path.getctime(fpath)
        return datetime.datetime.strptime(time.ctime(ctime), "%a %b %d %H:%M:%S %Y")


def make_video_title(fpath) -> str:
    """
    Given absolute filepath as str, return filename w/ suffix removed, and underscores replaced with spaces
    """
    return pathlib.PurePath(fpath).stem.replace("_", " ")


def duration_string(s) -> datetime.datetime:
    """
    Returns datetime.datetime from parsing some string formatted like "2w5d" (2 weeks 5 days) to represent period of time

    s = seconds
    m = minutes
    h = hours
    d = days
    w = weeks
    y = years

    Other letters cause error. If nothing precedes letter that can be cast as int, it will be 1 (e.g. "2dy" is 2 days 1 year. "www" is 3 weeks)
    Not case sensitive
    """

    ago = {
        "s": 0,
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
        except ValueError as e:
            if ago.get(c, False) is False:
                raise e            
            if int_buf == "":
                amt = 1
            else:
                amt = int(int_buf)
                int_buf = ""
            ago[c] += amt

    # datetime.datetime objects don't do "years" so multiply days by 365 for each year
    ago["d"] += 365 * ago["y"]
    
    ago_date = datetime.datetime.now() - datetime.timedelta(
        seconds=ago["s"],
        minutes=ago["m"],
        hours=ago["h"],
        days=ago["d"],
        weeks=ago["w"],
    )

    return ago_date


def parse_args() -> argparse.Namespace:
    """
    Returns argarse.Namespace representing command line input
    """

    parser = argparse.ArgumentParser(
        description="Create playlists for VLC media player",
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
        type=comma_list,
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
        type=comma_list,
        help="Comma-separated list of strings to require"
    )
    parser.add_argument(
        "-m",
        "--max-length",
        default=0,
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
        "--before",
        "--older-than",
        dest="before",
        type=duration_string,
        help="Include videos created before this age. Format as [int][unit]..., where [unit] is exactly one of [h (hour), d (day), w (week), m (month)]"
    )
    parser.add_argument(
        "--after",
        "--newer-than",
        dest="after",
        type=duration_string,
        help="Include videos created after this age. Format as [int][unit]..., where [unit] is exactly one of [h (hour), d (day), w (week), m (month)]"
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

def new_playlist_from_args(args) -> Playlist:
    """
    Returns Playlist instantiated from parsed command-line arguments
    """

    if args.formats:
        formats = args.formats
        if formats[0].startswith("+"):
            formats[0] = formats[0].lstrip("+")
            formats = Playlist.default_formats + formats
        formats = ["." + fmt.lstrip(".") for fmt in formats]   
    else:
        formats = None

    playlist = Playlist(args.directory, args.output, include_formats=formats)

    playlist.add_filters(
        exclude_terms=args.exclude,
        exclude_dirs=None,
        exclude_formats=args.exclude_formats,

        include_before=args.before,
        include_after=args.after,
        include_terms=args.include,
        include_dirs=None,    
    )

    playlist.randomize = args.random
    playlist.max_length = args.max_length
    
    return playlist

def main():
    
    args = parse_args()
    playlist = new_playlist_from_args(args)
    
    playlist.make()

    # Make .xspf playlist
    video_count = len(playlist.playlist_files)
    print(f"{playlist.dest_path} created with {video_count} videos.")


if __name__ == '__main__':

    main()