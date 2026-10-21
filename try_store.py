from store import KVStore

s = KVStore()
print(s.put("a", 1))    # expect False (new key)
print(s.put("a", 2))    # expect True  (already existed)
print(s.get("a"))       # expect (True, 2)
print(s.delete("a"))    # expect True
print(s.delete("a"))    # expect False
print(s.get("a"))       # expect (False, None)
print(len(s))           # expect 0