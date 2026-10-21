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
        self._lock = threading.Lock()
        os.makedirs(self.data_dir, exist_ok=True)   # create data/ if missing
        self._recover()                              # rebuild _data from old logs
        self._wal = open(self._wal_path(self._wal_gen), "a", encoding="utf-8")

    def get(self, key):
        with self._lock:
            if key in self._data:
                return True, self._data[key]
            return False, None

    def put(self, key, value):
        with self._lock:
            existed = key in self._data
            self._append({"op": "put", "key": key, "value": value})
            self._data[key] = value
            return existed

    def delete(self, key):
        with self._lock:
            if key not in self._data:
                return False
            self._append({"op": "del", "key": key})
            del self._data[key]
            return True

    def __len__(self):
        with self._lock:
            return len(self._data)

    def close(self):
        pass

    def _wal_path(self, n):
        return os.path.join(self.data_dir, f"wal-{n}.log")

    def _wal_numbers(self):
        """Numbers of the log files that exist, smallest first: [1, 2, 3]."""
        numbers = []
        for name in os.listdir(self.data_dir):
            if name.startswith("wal-") and name.endswith(".log"):
                numbers.append(int(name[4:-4]))   # "wal-12.log" -> 12
        return sorted(numbers)

    def _append(self, record):
        self._wal.write(json.dumps(record) + "\n")
        self._wal.flush()
        if self.fsync:
            os.fsync(self._wal.fileno())

    def _recover(self):
        last = 0
        for n in self._wal_numbers():
            self._replay(self._wal_path(n))
            last = n
        self._wal_gen = last + 1        # this run writes to a brand-new file

    def _replay(self, path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("Skipping broken line in %s", path)
                    continue
                if record["op"] == "put":
                    self._data[record["key"]] = record["value"]
                elif record["op"] == "del":
                    self._data.pop(record["key"], None)