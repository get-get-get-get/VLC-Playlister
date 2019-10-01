#!/usr/bin/env python3
import os
import pathlib
import sys
import xml.etree.cElementTree as ET

'''
Creates VLC playlist (extension: '.xspf') of all videos of a given format within a directory/folder (recursive)

TODO: Figure out why it's ElementTree writes to a single line. It doesn't break the playlist, but it's ugly
'''


# Restrict files to in playlist. Not case sensitive
def filter_files(files, extensions=None, includes=None, excludes=None):

    filtered_files = []

    for __ in range(len(files)):
        # Janky workaround to my janky logic TODO: unfuck
        # Flags a file for exclusion
        censor = False

        file = files.pop()

        # Exclude files w/ wrong extension
        if extensions:
            if file[file.rindex(".") + 1:].lower() not in extensions:
                censor = True

        # Exclude files with a given string
        if excludes and not censor:
            for x in excludes:
                if x in file.lower():
                    censor = True
                    break

        # Exclude files without a given string
        if includes:
            welcome = False     # TODO: this could probably be better
            for x in includes:
                if x in file.lower():
                    welcome = True
            if not welcome:
                censor = True

        # Add files that have not been flagged for exclusion
        if not censor:
            filtered_files.append(file)

    return filtered_files


# Return list of files under folder (recursive)
def get_files(directory):
    files = []
    for basepath, __, filenames in os.walk(str(directory)):
        for file in filenames:
            filepath = pathlib.PurePath(os.path.join(basepath, file)).as_posix()
            files.append(filepath)

    return files


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
    tree.write(filename, encoding="utf-8", xml_declaration=True)


def main():
    
    # Check that folder given is actually a folder
    directory = pathlib.Path(args.directory)

    files = get_files(directory)

    # Cast filters to lowercase set
    extensions = set(args.formats.lower().split(","))
    if args.include:
        includes = set(args.include.lower().split(","))
    else:
        includes = None
    if args.exclude:
        excludes = set(args.exclude.lower().split(","))
    else:
        excludes = None

    # Remove unwanted files
    filtered = filter_files(files,
                            extensions=extensions,
                            includes=includes,
                            excludes=excludes
                            )

    # Make .xspf playlist
    make_playlist(filtered, args.output)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("directory",
                        help="Directory containing video files")
    parser.add_argument("-o", "--output",
                        default="VLC-Playlist",
                        help="Title of playlist")
    parser.add_argument("-r", "--recursive",
                        default=True,
                        help="Recursively add files to playlist")
    parser.add_argument("-f", "--formats",
                        default="avi,mp4,mkv",
                        help="Comma-separated list of formats to include")
    parser.add_argument("-x", "--exclude",
                        default=None,
                        help="Comma-separated list of strings to censor")
    parser.add_argument("-n", "--include",
                        default=None,
                        help="Comma-separated list of strings to require")
    args = parser.parse_args()

    main()

