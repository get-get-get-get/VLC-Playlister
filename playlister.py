#!/usr/bin/env python3
import os
import pathlib
import random
import xml.etree.cElementTree as ET

import cmd
import ffprobe
import filters
from cmd import parse_args

"""
Creates VLC playlists
"""


class Playlist:
    default_formats = [".avi", ".mp4", ".mkv"]
    playlist_extension = ".xspf"
    max_length = None
    randomize = False

    def __init__(self, directory, dest_file):
        """ 
        Instantiate Playlist

        Keyword arguments:
        include_formats -- list or set of file formats to include in playlist. 
        recursive -- include subdirectories in search
        """

        self.root_dir = pathlib.Path(directory).resolve()
        self.dest_path = pathlib.Path(dest_file).resolve()
        if self.dest_path.suffix != '':
            self.playlist_extension = self.dest_path.suffix

        self.filter_set = filters.FilterSet()
        self.unfiltered_files = []
        self.playlist_files = []

    def use_filter_set(self, filter_set):
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
        self.filter_set = filter_set

        # if exclude_terms:
        #     if not self.filter_exclude_terms:
        #         self.filter_exclude_terms = exclude_terms
        #     else:
        #         for term in exclude_terms:
        #             self.filter_exclude_terms.append(term)
        #
        # if exclude_dirs:
        #     if not self.filter_exclude_dirs:
        #         self.filter_exclude_dirs = set(pathlib.Path(p).resolve() for p in parse_comma_list(exclude_dirs))
        #     else:
        #         for dir in parse_comma_list(exclude_dirs):
        #             self.filter_exclude_dirs.add(dir)
        #
        # if exclude_formats:
        #     if not self.filter_exclude_formats:
        #         self.filter_exclude_formats = set("." + fmt.lstrip(".") for fmt in exclude_formats)
        #     else:
        #         for fmt in parse_comma_list(exclude_formats):
        #             self.filter_exclude_formats.add(fmt)
        #
        # if include_before:
        #     self.filter_include_before = include_before
        # if include_after:
        #     self.filter_include_after = include_after
        #
        # if include_terms:
        #     if not self.filter_include_terms:
        #         self.filter_include_terms = include_terms
        #     else:
        #         for term in include_terms:
        #             self.filter_include_terms.append(term)
        #
        # if include_dirs:
        #     if not self.filter_include_dirs:
        #         self.filter_include_dirs = [pathlib.Path(p).resolve() for p in include_dirs]
        #     else:
        #         for d in include_dirs:
        #             self.filter_include_dirs.append(pathlib.Path(d).resolve())
        #
        # if include_formats:
        #     if not self.allowed_formats:
        #         self.allowed_formats = set(include_formats)
        #     else:
        #         for fmt in include_formats:
        #             self.allowed_formats.add(fmt)

    def get_all_files(self):
        """
        Sets self.unfiltered_files with all filepaths within directories that are not filtered.

        NOTE: doesn't consider recursive option, and will always be recursive
        """

        for root_dir, dirs, filenames in os.walk(str(self.root_dir)):
            # allowed = []
            # for d in dirs:
            #     d_pure = pathlib.Path(os.path.join(root_dir, d)).resolve()
            # for inc_dir in self.filter_include_dirs:
            #     if inc_dir == d_pure or inc_dir in d_pure.parents:
            #         allowed.append(d)
            #         break
            for fname in filenames:
                self.unfiltered_files.append(
                    pathlib.PurePath(os.path.abspath(os.path.join(root_dir, fname))).as_posix())
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
        return self.filter_set.matches(str(fpath))

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


def make_video_title(fpath: str) -> str:
    """
    Given absolute filepath as str, return filename w/ suffix removed, and underscores replaced with spaces
    """
    return pathlib.PurePath(fpath).stem.replace("_", " ")


def new_playlist_from_args(args) -> Playlist:
    """
    Returns Playlist instantiated from parsed command-line arguments
    """
    playlist = Playlist(args.directory, args.output)

    filter_set = filters.FilterSet()
    must_match_filters = []
    must_not_match_filters = []

    if args.ffprobe:
        ffprobe.FFPROBE_PATH = args.ffprobe

    # File extension filters
    if args.formats:
        formats = args.formats
        if formats[0].startswith("+"):
            formats[0] = formats[0].lstrip("+")
            formats = Playlist.default_formats + formats
        formats = [fmt for fmt in formats]
    else:
        formats = Playlist.default_formats
    must_match_filters.append(filters.Filter(filters.has_file_extension, formats))

    if args.exclude_formats:
        must_not_match_filters.append(filters.Filter(filters.has_file_extension, formats))

    # Term filters
    if args.exclude:
        must_not_match_filters.append(filters.Filter(filters.contains, args.exclude))
    if args.include:
        must_match_filters.append(filters.Filter(filters.contains, args.include))

    # Time filters
    time_filters = filters.FilterSet()
    if args.before:
        time_filters.add_include_filter(filters.Filter(filters.is_older_than, args.before))
    if args.after:
        time_filters.add_include_filter(filters.Filter(filters.is_newer_than, args.after))
    if len(time_filters) > 0:
        must_match_filters.append(time_filters)

    # Length filters
    length_filters = []
    if args.max_length:
        length_filters.append(filters.Filter(filters.is_shorter_than, args.max_length))
    if args.min_length:
        length_filters.append(filters.Filter(filters.is_longer_than, args.min_length))
    if len(length_filters) > 0:
        if args.max_length and args.min_length:
            must_match_filters.append(length_filters[0])
            must_match_filters.append(length_filters[1])
        else:
            must_match_filters.append(length_filters[0])

    # Add filters to Playlister
    if len(must_match_filters) > 0:
        filter_set.add_include_filter(filters.Filter(filters.matches_all, must_match_filters))
    if len(must_not_match_filters) > 0:
        filter_set.add_exclude_filter(filters.Filter(filters.matches_none, must_not_match_filters))
    playlist.use_filter_set(filter_set)

    playlist.randomize = args.random
    playlist.max_length = args.max_videos

    return playlist


def main():
    args = cmd.Arguments().parse_args()
    playlist = new_playlist_from_args(args)

    playlist.make()

    # Make .xspf playlist
    video_count = len(playlist.playlist_files)
    print(f"{playlist.dest_path} created with {video_count} videos.")


if __name__ == '__main__':
    main()
