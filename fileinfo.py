import datetime
import os
import time


# datetime of file creation
def get_file_cdate(fpath: str) -> datetime.datetime:
    ctime = os.path.getctime(fpath)
    return datetime.datetime.strptime(time.ctime(ctime), "%a %b %d %H:%M:%S %Y")

# datetime of last file modification
def get_file_mdate(fpath: str) -> datetime.datetime:
    mtime = os.path.getmtime(fpath)
    return datetime.datetime.strptime(time.ctime(mtime), "%a %b %d %H:%M:%S %Y")