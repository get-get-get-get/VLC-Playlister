import shlex
import subprocess
import json
import time

FFPROBE_PATH = "x:/ffprobe.exe"

# Store info in json to avoid having to re-read file twice.
examined_files = {}


def get_video_info(filename: str) -> dict:
    cmd = shlex.split(f"{FFPROBE_PATH} -v quiet -print_format json -show_streams")
    cmd.append(filename)    # avoid quotation issues in shlex by just appending
    # run the ffprobe process, decode stdout into utf-8 & convert to JSON
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"ffprobe failed to parse {filename}")
        return {}

    ffp_json = json.loads(result.stdout.decode('utf-8'))

    # # testing
    # import pprint
    # pp = pprint.PrettyPrinter(indent=2)
    # pp.pprint(ffp_json)
    return ffp_json


# Get video length in seconds
def get_video_length(filename: str) -> int:
    if examined_files.get(filename, False):
        if filename.endswith("mkv"):
            length = parse_mkv_length(examined_files[filename])
        elif filename.endswith("mp4"):
            length = parse_mp4_length(examined_files[filename])
        else:
            length = 0
        return length

    cmd = shlex.split(
        f"{FFPROBE_PATH} -v quiet -print_format json -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{filename}'")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"ffprobe failed to parse {filename}")
        return 0

    seconds = int(result.stdout.decode('utf-8').split(".")[0])
    return seconds


def parse_mkv_length(ffprobe_output: dict) -> int:
    dur = ""
    if not ffprobe_output.get("streams", False):
        return 0
    for stream in ffprobe_output["streams"]:
        if stream["tags"].get("DURATION", False):
            dur = stream["tags"]["DURATION"]
            break
    t = time.strptime(dur.split(".")[0], "%H:%M:%S")
    seconds = (t.tm_sec) + (t.tm_min * 60) + (t.tm_hour * 360)
    return seconds


def parse_mp4_length(ffprobe_output: dict) -> int:
    if not ffprobe_output.get("streams", False):
        return 0
    for stream in ffprobe_output["streams"]:
        if stream.get("duration", False):
            return int(stream["duration"].split(".")[0])
    return 0


def file_has_audio(filename: str) -> bool:
    if not examined_files.get(filename, False):
        examined_files[filename] = get_video_info(filename)
    ffprobe_output = examined_files[filename]
    if not ffprobe_output.get("streams", False):
        return False
    for stream in ffprobe_output["streams"]:
        if stream.get("codec_type", False):
            if stream["codec_type"] == "audio":
                return True
    return False
