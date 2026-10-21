import time
from store import KVStore

s = KVStore(snapshot_interval=3)
for i in range(5):
    s.put(f"key{i}", i)
print("wait 4 seconds and watch the data folder...")
time.sleep(4)
s.put("late", "after the snapshot")
s.close()

s2 = KVStore(snapshot_interval=0)
print(len(s2), "keys after restart")   # expect 6
print(s2.get("late"))                 # expect (True, 'after the snapshot')