class KVStore:
    def __init__(self, data_dir="data", snapshot_interval=30.0, fsync=False):
        """Load existing data from data_dir (recovery) and get ready."""

    def get(self, key):
        """Return (found, value). found is True/False; value may be None."""

    def put(self, key, value):
        """Store value. Return True if the key already existed (update),
        False if it is new (create). Raise OSError if saving to disk fails."""

    def delete(self, key):
        """Remove key. Return True if it existed, False if it did not."""

    def __len__(self):
        """Number of keys."""

    def close(self):
        """Final snapshot and close files. Called once, on shutdown."""