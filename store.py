import json        # turns Python values into text and back, for saving to files
import logging     # prints warnings into the server's log
import os          # works with folders and files
import threading   # locks and background threads

log = logging.getLogger("kvstore.store")

class KVStore:
    def __init__(self, data_dir="data", snapshot_interval=30.0, fsync=False):
        self.data_dir = data_dir
        self.snapshot_interval = snapshot_interval
        self.fsync = fsync
        self._data = {}

    def get(self, key):
        if key in self._data:
            return True, self._data[key]
        return False, None

    def put(self, key, value):
        existed = key in self._data
        self._data[key] = value
        return existed

    def delete(self, key):
        if key not in self._data:
            return False
        del self._data[key]
        return True

    def __len__(self):
        return len(self._data)

    def close(self):
        pass