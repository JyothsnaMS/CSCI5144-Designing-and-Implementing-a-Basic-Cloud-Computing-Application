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
        self._stop = threading.Event()
        self._thread = None
        if self.snapshot_interval > 0:
            self._thread = threading.Thread(target=self._snapshot_loop, daemon=True)
            self._thread.start()

    def _snapshot_loop(self):
        while not self._stop.wait(self.snapshot_interval):
            try:
                self.snapshot()
            except Exception:
                log.exception("Snapshot failed")

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
        self._stop.set()          # tell the background thread to stop
        if self._thread:
            self._thread.join()   # wait until it has stopped
        self.snapshot()           # one last photo
        self._wal.close()

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
        start = 1
        if os.path.exists(self._snapshot_path()):
            with open(self._snapshot_path(), encoding="utf-8") as f:
                snap = json.load(f)
            self._data = snap["data"]
            start = snap["wal_gen"]

        last = start - 1
        for n in self._wal_numbers():
            if n < start:
                os.remove(self._wal_path(n))   # leftover, already in the snapshot
                continue
            self._replay(self._wal_path(n))
            last = n
        self._wal_gen = last + 1

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

    def snapshot(self):
        # Part 1, inside the lock (quick): copy the data, switch to a new log file
        with self._lock:
            data_copy = dict(self._data)
            self._wal.close()
            self._wal_gen += 1
            new_gen = self._wal_gen
            self._wal = open(self._wal_path(new_gen), "a", encoding="utf-8")

        # Part 2, outside the lock (slow disk work; requests keep flowing)
        tmp_path = self._snapshot_path() + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"wal_gen": new_gen, "data": data_copy}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self._snapshot_path())

        # Part 3: older logs are now inside the snapshot, so delete them
        for n in self._wal_numbers():
            if n < new_gen:
                os.remove(self._wal_path(n))
        log.info("Snapshot saved: %d keys", len(data_copy))

    def _snapshot_path(self):
        return os.path.join(self.data_dir, "snapshot.json")