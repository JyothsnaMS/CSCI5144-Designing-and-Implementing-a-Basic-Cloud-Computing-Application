import threading
from store import KVStore

for run in range(10):
    s = KVStore()
    s.put("x", 1)
    start_gun = threading.Barrier(20)   # makes all 20 threads start at the same instant
    results = []

    def worker():
        start_gun.wait()
        results.append(s.delete("x"))

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()                         # wait for all of them to finish
    print("run", run, "successful deletes:", results.count(True))