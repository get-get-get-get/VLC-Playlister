import shlex
import subprocess
import json
import time


FFPROBE_PATH = "x:/ffprobe.exe"

def get_video_info(filename: str) -> dict:
    cmd = shlex.split(f"{FFPROBE_PATH} -v quiet -print_format json -show_streams '{filename}'")
    # run the ffprobe process, decode stdout into utf-8 & convert to JSON
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"ffprobe failed to parse {filename}")
        return

    ffp_json = json.loads(result.stdout.decode('utf-8'))

    # # testing
    # import pprint
    # pp = pprint.PrettyPrinter(indent=2)
    # pp.pprint(ffp_json)
    return ffp_json


# Get video length in seconds
def get_video_length(filename: str) -> int:
    info = get_video_info(filename)
    if not info:
        return 0

    if filename.endswith("mkv"):
        length = parse_mkv_length(info)
    elif filename.endswith("mp4"):
        length = parse_mp4_length(info)
    else:
        length = 0
    return length


def parse_mkv_length(ffprobe_output: dict) -> int:
    dur = ""
    for stream in ffprobe_output["streams"]:
        if stream["tags"].get("DURATION", False):
            dur = stream["tags"]["DURATION"]
            break
    t = time.strptime(dur.split(".")[0], "%H:%M:%S")
    seconds = (t.tm_sec) + (t.tm_min * 60) + (t.tm_hour * 360)
    return seconds


def parse_mp4_length(ffprobe_output: dict) -> int:
    for stream in ffprobe_output["streams"]:
        if stream.get("duration", False):
            return int(stream["duration"].split(".")[0])
    return 0
