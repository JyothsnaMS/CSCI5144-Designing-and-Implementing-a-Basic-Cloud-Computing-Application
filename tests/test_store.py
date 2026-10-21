import os
import sys
import threading

# lets this file import store.py from the folder above
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from store import KVStore


def crash(store):
    """Pretend the server died: close the log file but skip close()."""
    store._wal.close()


def test_put_get_delete(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    assert s.put("a", 1) is False
    assert s.put("a", 2) is True
    assert s.get("a") == (True, 2)
    assert s.delete("a") is True
    assert s.delete("a") is False
    assert s.get("a") == (False, None)
    s.close()


def test_none_value_is_found(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    s.put("n", None)
    assert s.get("n") == (True, None)
    s.close()


def test_concurrent_deletes_one_winner(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    s.put("x", 1)
    start_gun = threading.Barrier(20)
    results = []

    def worker():
        start_gun.wait()
        results.append(s.delete("x"))

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1
    assert results.count(False) == 19
    s.close()


def test_concurrent_puts_same_key(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    threads = [threading.Thread(target=s.put, args=("hot", i)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    found, final = s.get("hot")
    assert found and final in range(50)
    crash(s)
    s2 = KVStore(str(tmp_path), snapshot_interval=0)
    assert s2.get("hot") == (True, final)   # the log replays to the same winner
    s2.close()


def test_clean_restart(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    s.put("a", 1)
    s.put("b", 2)
    s.delete("a")
    s.close()
    s2 = KVStore(str(tmp_path), snapshot_interval=0)
    assert s2.get("a") == (False, None)
    assert s2.get("b") == (True, 2)
    s2.close()


def test_crash_recovery(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    s.put("a", 1)
    s.snapshot()            # some data in the snapshot...
    s.put("b", 2)           # ...and some only in the log
    s.delete("a")
    crash(s)
    s2 = KVStore(str(tmp_path), snapshot_interval=0)
    assert s2.get("a") == (False, None)
    assert s2.get("b") == (True, 2)
    s2.close()


def test_broken_line_is_skipped(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    s.put("good", 1)
    s._wal.write('{"op": "put", "key": "hal')   # half a line, like a crash mid-write
    crash(s)
    s2 = KVStore(str(tmp_path), snapshot_interval=0)
    assert s2.get("good") == (True, 1)
    assert s2.get("hal") == (False, None)
    s2.put("after", 2)
    crash(s2)
    s3 = KVStore(str(tmp_path), snapshot_interval=0)
    assert s3.get("after") == (True, 2)       # new writes are not lost
    s3.close()


def test_snapshot_cleans_up_logs(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0)
    for i in range(100):
        s.put("k", i)
    s.snapshot()
    logs = [f for f in os.listdir(tmp_path) if f.startswith("wal-")]
    assert len(logs) == 1
    assert os.path.getsize(os.path.join(tmp_path, logs[0])) == 0
    s.close()


def test_background_snapshot(tmp_path):
    s = KVStore(str(tmp_path), snapshot_interval=0.2)
    s.put("a", 1)
    threading.Event().wait(0.6)
    assert os.path.exists(os.path.join(tmp_path, "snapshot.json"))
    s.close()