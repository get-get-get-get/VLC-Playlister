import argparse
import datetime


class Arguments:
    def __init__(self):
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
            type=comma_list_stripped,
            help="Comma-separated list of formats to include. Prepending '+' appends to defaults"
        )
        parser.add_argument(
            "-x",
            "--exclude",
            default=None,
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
            "--max-videos",
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
            type=datetime_string,
            help="Include videos created before this age. Format as [int][unit]..., where [unit] is exactly one of [h ("
                 "hour), d (day), w (week), m (month)] "
        )
        parser.add_argument(
            "--after",
            "--newer-than",
            dest="after",
            type=datetime_string,
            help="Include videos created after this age. Format as [int][unit]..., where [unit] is exactly one of [h ("
                 "hour), d (day), w (week), m (month)] "
        )
        parser.add_argument(
            "--exclude-formats",
            default=None,
            type=comma_list_stripped,
            help="Exclude videos modified after this age. Format as [int][unit]..., where [unit] is exactly one of [h ("
                 "hour), d (day), w (week), m (month)] "
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Verbose output"
        )
        parser.add_argument(
            "--ffprobe",
            help="Path to ffprobe",
        )
        parser.add_argument(
            "--max-length",
            "--longer-than",
            type=duration_string,
            help="Maximum length of video",
        )
        parser.add_argument(
            "--min-length",
            "--shorter-than",
            type=duration_string,
            help="Minimum length of video",
        )
        parser.add_argument(
            "--require-audio",
            action="store_true",
            help="Only include files with audio",
        )
        self.parser = parser

    def parse_args(self) -> argparse.Namespace:
        return self.parser.parse_args()


def parse_comma_list(arg, normalize_case=True) -> list:
    """
    Return list by splitting string with comma

    Keyword arguments:
    normalize_case -- return lowercase strings
    """
    if not normalize_case:
        parsed = [x.strip() for x in arg.split(",") if x != ""]
    else:
        parsed = [x.strip().lower() for x in arg.split(",")]
    return parsed


def comma_list(s: str) -> list:
    return parse_comma_list(s, normalize_case=False)


def comma_list_stripped(s: str) -> list:
    return [x.lstrip(".") for x in parse_comma_list(s, normalize_case=True)]


def parse_args() -> argparse.Namespace:
    return Arguments().parse_args()


def comma_list_cased(s: str) -> list:
    return parse_comma_list(s, normalize_case=True)


def datetime_string(s: str) -> datetime.datetime:
    """
    Returns datetime.datetime by parsing some string formatted like "2w5d" (2 weeks 5 days) to represent period of time

    s = seconds
    m = minutes
    h = hours
    d = days
    w = weeks
    y = years

    Other letters cause error. If nothing precedes letter that can be cast as int, it will be 1
    (e.g. "2dy" is 2 days 1 year. "www" is 3 weeks)
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


# Returns length of time in seconds
def duration_string(s: str) -> int:
    """
       Returns time.struct_time by parsing some string formatted like "2w5d" (2 weeks 5 days) to represent length of time

       s = seconds
       m = minutes
       h = hours
       d = days
       w = weeks
       y = years

       Other letters cause error. If nothing precedes letter that can be cast as int, it will be 1
       (e.g. "2dy" is 2 days 1 year. "www" is 3 weeks)
       Not case sensitive
       """

    dur = {
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
            if dur.get(c, False) is False:
                raise e
            if int_buf == "":
                amt = 1
            else:
                amt = int(int_buf)
                int_buf = ""
            dur[c] += amt

    # I'm a genious
    dur["w"] += dur["y"] * 52
    dur["d"] += dur["w"] * 7
    dur["h"] += dur["d"] * 24
    dur["m"] += dur["h"] * 60
    dur["s"] += dur["m"] * 60
    return dur["s"]
