import datetime
import pathlib

import fileinfo
import playlister


class FilterSet:
    def __init__(self):
        self.include_filters = []
        self.exclude_filters = []

    def __len__(self):
        return len(self.include_filters) + len(self.exclude_filters)

    def matches(self, filename: str) -> bool:
        keep = False
        for filt in self.include_filters:
            if filt.matches(filename):
                keep = True
                break
        for filt in self.exclude_filters:
            if len(self.exclude_filters) == 0:
                break
            if filt.matches(filename):
                keep = False
                break
        return keep

    def add_include_filter(self, filt):
        self.include_filters.append(filt)

    def add_exclude_filter(self, filt):
        self.exclude_filters.append(filt)


class Filter:
    def __init__(self, filter_func, param):
        self.filter_func = filter_func
        self.param = param

    def matches(self, filename: str) -> bool:
        return self.filter_func(self.param, filename)


def new_filter(filter_func, params: list) -> Filter:
    return Filter(filter_func, params)


def matches_all(filters: list, filename: str) -> bool:
    for filt in filters:
        if not filt.matches(filename):
            return False
    return True


def matches_none(filters: list, filename: str) -> bool:
    for filt in filters:
        if filt.matches(filename):
            return False
    return True


def does_not_match_all(filters: list, filename: str) -> bool:
    if matches_all(filters, filename):
        return False
    return True


def contains(terms: list, filename: str) -> bool:
    for param in terms:
        if param.lower() in filename.lower():
            return True
    return False


def has_file_extension(extensions: list, filename: str) -> bool:
    if pathlib.PurePath(filename).suffix in extensions:
        return True
    return False


def is_older_than(date: datetime.datetime, filename: str) -> bool:
    if fileinfo.get_file_cdate(filename) <= date:
        return True
    return False


def is_newer_than(date: datetime.datetime, filename: str) -> bool:
    if fileinfo.get_file_cdate(filename) >= date:
        return True
    return False
