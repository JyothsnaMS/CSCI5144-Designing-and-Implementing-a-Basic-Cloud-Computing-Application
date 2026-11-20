
import hashlib
import bisect


class ConsistentHashRing:

    def __init__(self, replicas=100):
        if replicas <= 0:
            raise ValueError("Replicas must be greater than zero.")

        self.replicas = replicas
        self.ring = {}
        self.sorted_keys = []
        self.nodes = set()

    @staticmethod
    def _hash(value):
        digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
        return int(digest, 16)

    def add_node(self, node):
        if not node:
            raise ValueError("Node identifier cannot be empty.")

        if node in self.nodes:
            return

        self.nodes.add(node)

        for replica in range(self.replicas):
            virtual_node = f"{node}#{replica}"
            position = self._hash(virtual_node)
            self.ring[position] = node

        self.sorted_keys = sorted(self.ring.keys())

    def remove_node(self, node):
        if node not in self.nodes:
            return

        self.nodes.remove(node)

        for replica in range(self.replicas):
            virtual_node = f"{node}#{replica}"
            position = self._hash(virtual_node)
            self.ring.pop(position, None)

        self.sorted_keys = sorted(self.ring.keys())

    def get_node(self, key):
        if not self.ring:
            raise ValueError("No nodes available in the hash ring.")

        position = self._hash(key)
        index = bisect.bisect_left(self.sorted_keys, position)

        if index == len(self.sorted_keys):
            index = 0

        return self.ring[self.sorted_keys[index]]

    def get_nodes(self):
        return sorted(self.nodes)
