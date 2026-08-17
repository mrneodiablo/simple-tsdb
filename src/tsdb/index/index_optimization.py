#!/usr/bin/env python3

import math
import hashlib
from typing import List, Any, Iterable, Dict
from dataclasses import dataclass


@dataclass
class BloomStats:
    """Describes a Bloom filter's configuration and load."""

    num_bits: int = 0
    num_hashes: int = 0
    num_items: int = 0

    @property
    def estimated_false_positive_rate(self) -> float:
        """
        Estimated FP rate given current load:
            (1 - e^(-k*n/m)) ^ k
        where k=num_hashes, n=num_items, m=num_bits.
        """
        # TODO: implement the formula (guard against num_bits == 0)
        if self.num_bits == 0:
            return 0.0
        k = self.num_hashes
        n = self.num_items
        m = self.num_bits
        return (1 - math.exp(-k * n / m)) ** k


class BloomFilter:
    """
    Space-efficient probabilistic set membership.

    Guarantees:
    - might_contain(x) == False  => x was DEFINITELY never added
    - might_contain(x) == True   => x was PROBABLY added (could be a false +)

    There are NO false negatives, which is what makes it safe for "skip this
    file" decisions: if it says "not present", you can skip safely.
    """

    def __init__(self, expected_items: int, false_positive_rate: float = 0.01):
        """
        Size the filter from the expected item count and target FP rate.

        Optimal sizing:
            m = -(n * ln(p)) / (ln 2)^2      # number of bits
            k = (m / n) * ln 2               # number of hash functions
        """
        # TODO: compute m (num_bits) and k (num_hashes) from the formulas above
        m = -(expected_items * math.log(false_positive_rate)) / (math.log(2) ** 2)
        k = (m / expected_items) * math.log(2)

        # TODO: round m and k up to at least 1; store an integer bit array
        #       (a Python int used as a bitset, or a bytearray)
        self.num_bits = max(1, int(math.ceil(m)))
        self.num_hashes = max(1, int(math.ceil(k)))

        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate
        self._bits = 0  # use a big int as the bit array (bit i = (self._bits >> i) & 1)
        self._count = 0


    def _hashes(self, item: Any) -> List[int]:
        """
        Produce `num_hashes` independent bit positions for `item`.

        Double hashing trick: derive two base hashes h1, h2 from a single digest
        and combine them: g_i = (h1 + i * h2) % num_bits.
        """
        # TODO: hash str(item) with hashlib (e.g. md5/sha1), split digest into
        #       two ints h1, h2, then return [(h1 + i*h2) % num_bits for i in
        #       range(num_hashes)]
        item_str = str(item).encode('utf-8')
        digest = hashlib.md5(item_str).digest()  # 16 bytes
        h1 = int.from_bytes(digest[:8], 'big')  # first 8 bytes
        h2 = int.from_bytes(digest[8:], 'big')
        return [(h1 + i * h2) % self.num_bits for i in range(self.num_hashes)]

    def add(self, item: Any) -> None:
        """Add an item: set all of its hash-position bits to 1."""
        # TODO: for pos in self._hashes(item): self._bits |= (1 << pos)
        for pos in self._hashes(item):
            self._bits |= (1 << pos)

        # TODO: increment self._count
        self._count += 1

    def might_contain(self, item: Any) -> bool:
        """True if ALL the item's hash bits are set (possibly present)."""
        # TODO: return all((self._bits >> pos) & 1 for pos in self._hashes(item))
        return all((self._bits >> pos) & 1 for pos in self._hashes(item))

    def add_all(self, items: Iterable[Any]) -> None:
        """Convenience: add many items."""
        # TODO
        for item in items:
            self.add(item)

    def stats(self) -> BloomStats:
        """Return a BloomStats snapshot of this filter."""
        # TODO
        return BloomStats(
            num_bits=self.num_bits,
            num_hashes=self.num_hashes,
            num_items=self._count,
        )

class OptimizedTagIndex:
    """
    A tag index wrapper that keeps one Bloom filter PER location, summarizing
    which tag values live in that location. Lets a lookup skip locations that
    definitely don't contain the requested value before consulting the real
    posting lists.

    Pairs with Day 8's TagIndex (injected) for the exact answers.
    """

    def __init__(self, tag_index, expected_items_per_location: int = 1000):
        self.tag_index = tag_index
        self.expected = expected_items_per_location
        self._filters: Dict[str, BloomFilter] = {}  # location -> BloomFilter

    def _token(self, tag_key: str, tag_value: str) -> str:
        """Canonical token added to a location's filter."""
        return f"{tag_key}={tag_value}"

    def index_location(self, location: str, tag_pairs: Iterable[tuple]) -> None:
        """
        Build/extend the Bloom filter for a location from its (key, value) pairs.
        Also forwards to the underlying tag_index so exact lookups still work.
        """
        # TODO: create a BloomFilter for `location` if missing
        if location not in self._filters:
            self._filters[location] = BloomFilter(expected_items=self.expected)

        # TODO: for (k, v) in tag_pairs: filter.add(token); tag_index.add_entry(k, v, location)
        for k, v in tag_pairs:
            token = self._token(k, v)
            self._filters[location].add(token)
            self.tag_index.add_entry(k, v, location)


    def might_have(self, location: str, tag_key: str, tag_value: str) -> bool:
        """Cheap pre-check: could this location contain tag_key=tag_value?"""
        # TODO: if no filter for location -> be safe and return True
        if location not in self._filters:
            return True
        # TODO: else return filter.might_contain(token)
        return self._filters[location].might_contain(self._token(tag_key, tag_value))

    def lookup_with_skip(self, tag_key: str, tag_value: str, candidate_locations: List[str]) -> tuple[List[str], List[str]]:
        """
        Among candidate_locations, return (matches, skipped) where:
          - matches: locations the exact index confirms contain the value
          - skipped: locations the bloom filter let us skip without checking
        """
        # TODO: for each candidate, if not might_have -> count as skipped;
        #       else confirm via self.tag_index.lookup(tag_key, tag_value)
        matches = []
        skipped = []
        for loc in candidate_locations:
            if not self.might_have(loc, tag_key, tag_value):
                skipped.append(loc)
            else:
                if loc in self.tag_index.lookup(tag_key, tag_value):
                    matches.append(loc)
        return matches, skipped

