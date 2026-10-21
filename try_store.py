import os
import sys
from store import KVStore

s = KVStore()
if sys.argv[1] == "write":
    s.put("course", "CSCI 5144")
    s.put("temp", 1)
    s.delete("temp")
    print("written; now crashing on purpose")
    os._exit(1)            # dies instantly: no cleanup, like a real crash
else:
    print("course:", s.get("course"))   # expect (True, 'CSCI 5144')
    print("temp:", s.get("temp"))       # expect (False, None)