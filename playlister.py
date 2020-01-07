#!/usr/bin/env python3
import argparse
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


# Globals
FORMATS = "avi,mp4,mkv"


# Restrict files to in playlist. Not case sensitive
def filter_files(files, randomize=False, max_len=None, extensions=None, includes=None, excludes=None, max_age=None):

    filtered_files = []

    # Get current time (epoch seconds)
    time_now = int(time.time())

    for __ in range(len(files)):
        # Flags a file for exclusion
        censor = False

        file = files.pop()

        # Exclude files w/ wrong extension
        if extensions:
            try: 
                if file[file.rindex(".") + 1:].lower() not in extensions:
                    censor = True
            except ValueError:
                pass

        # Exclude files with a given string
        if excludes and not censor:
            for x in excludes:
                if x in file.lower():
                    censor = True
                    break

        # Exclude files without a given string
        if includes and not censor:
            welcome = False     # TODO: this could probably be better
            for x in includes:
                if x in file.lower():
                    welcome = True
            if not welcome:
                censor = True
        
        # Exclude files based on age
        if max_age and not censor:
            mtime = int(os.path.getmtime(file))
            min_time = time_now - max_age
            if not mtime >= min_time:
                censor = True

        # Add files that have not been flagged for exclusion
        if not censor:
            filtered_files.append(file)

    if randomize:
        random.seed()
        # Certainly not guilty of unnecessary optimizing...
        print(f"Shuffling {len(filtered_files)} potential videos...")
        random.shuffle(filtered_files)
        print("Done shuffling!")
    
    if max_len:
        filtered_files = filtered_files[:max_len]

    return filtered_files


# Return list of files under folder (recursive)
def get_files(directory):
    files = []
    for basepath, __, filenames in os.walk(str(directory)):
        for file in filenames:
            filepath = pathlib.PurePath(os.path.join(basepath, file)).as_posix()
            files.append(filepath)

    return files

# Takes param formatted as [int][unit], where [unit] is of [h,d,w,m]. Returns as seconds
def get_epoch_time(max_age):

    unit = max_age[-1]
    unit_count = int(max_age[:-1])

    # Use unit to see how much to multiply unit_count by: 
    if unit == "h":
        multiplier = 3600
    elif unit == "d":
        multiplier = 86400
    elif unit == "w":
        multiplier = 604800
    elif unit == "m":
        multiplier = 18144000
    
    return unit_count * multiplier

    

# Make playlist .xspf (aka xml)
def make_playlist(videos, title):

    # Create 'playlist' as root Element
    playlist = ET.Element("playlist")
    playlist.set("xmlns", "http://xspf.org/ns/0/")
    playlist.set("xmlns:vlc", "http://www.videolan.org/vlc/playlist/ns/0/")
    playlist.set("version", "1")

    # Set title
    ET.SubElement(playlist, "title").text = title

    # Create tracklist
    tracklist = ET.SubElement(playlist, "trackList")

    # Add tracks to tracklist
    file_format = "file:///{}"
    for i, name in enumerate(videos):
        track = ET.SubElement(tracklist, "track")
        ET.SubElement(track, "location").text = file_format.format(name)
        ET.SubElement(track, "duration")

        extension = ET.SubElement(track, "extension")
        extension.set("application", "http://www.videolan.org/vlc/playlist/0")
        ET.SubElement(extension, "vlc:id").text = str(i)

    # Last element
    ext = ET.SubElement(playlist, "extension")
    ext.set("application", "http://www.videolan.org/vlc/playlist/0")
    for i in range(len(videos)):
        ET.SubElement(ext, "vlc:item").set("tid", str(i))

    tree = ET.ElementTree(playlist)
    filename = f"{title}.xspf"

    # Remove playlist if it already exists
    if os.path.exists(filename):
        os.remove(filename)

    tree.write(filename, encoding="utf-8", xml_declaration=True)


def main():
    
    # Instantiate paths as Path
    directory = pathlib.Path(args.directory)
    output = pathlib.Path(args.output)

    # Get all files
    files = get_files(str(directory))
    if args.verbose:
        print(f"Discovered {len(files)} files")

    # Parse acceptable formats
    global FORMATS
    default_formats = set(FORMATS.lower().split(","))

    if args.formats:
        # Allow appending to default formats w/ '+' operator
        if args.formats.startswith("+"):
            extensions = args.formats.lstrip("+")
            extensions = set(extensions.lower().split(","))
            extensions = extensions.union(default_formats)
        else:
            extensions = args.formats.lower().split(",")
    else:
        extensions = default_formats


    # Cast filters to lowercase set
    if args.include:
        includes = set(args.include.lower().split(","))
    else:
        includes = None
        
    if args.exclude:
        excludes = set(args.exclude.lower().split(","))
    else:
        excludes = None
    
    # Convert args.latest to format workable w/ os.path.getmtime (seconds since epoch)
    if args.max_age:
        max_age = get_epoch_time(args.max_age)
    else:
        max_age = None

    # Verbose output
    if args.verbose:
        print(f"EXTENSIONS: {extensions}")
        print(f"Including: {includes}")
        print(f"Excluding: {excludes}")
    
    # Remove unwanted files
    filtered = filter_files(
        files,
        randomize=args.random,
        max_len=args.max_len,
        extensions=extensions,
        includes=includes,
        excludes=excludes,
        max_age=max_age
    )

    # Make .xspf playlist
    video_count = len(filtered)
    make_playlist(filtered, str(output))
    print(f"{output}.xspf created with {video_count} videos.")


if __name__ == '__main__':

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
        default="VLC-Playlist",
        help="Title of playlist"
    )
    parser.add_argument(
        "-f",
        "--formats",
        help="Comma-separated list of formats to include. Prepending '+' appends to defaults"
    )
    parser.add_argument(
        "-x",
        "--exclude",
        default=None,
        help="Comma-separated list of strings to censor"
    )
    parser.add_argument(
        "-n",
        "--include",
        default=None,
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
        "--max-age",
        default=None,
        help="Only videos this age or newer. Format as [int][unit], where [unit] is exactly one of [h (hour), d (day), w (week), m (month)]"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    args = parser.parse_args()

    main()

