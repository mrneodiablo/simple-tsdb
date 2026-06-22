#!/usr/bin/env python3
"""
Day 14: Index Optimization (Bloom Filters)
==========================================

Problem: Even with indexes, you sometimes ask "does this file contain tag
value X?" for many files. A Bloom filter answers that probabilistically in O(1)
with tiny memory: "definitely not present" or "possibly present" — letting you
SKIP files that definitely don't match before touching the real index.

Learning Objectives:
- Implement a Bloom filter (bit array + k hash functions)
- Understand the false-positive trade-off (no false negatives!)
- Size a filter for a target false-positive rate
- Combine bloom filters with the Day 8 tag index to skip work
- Measure the optimization (files skipped, estimated FP rate)

Real-World Connection:
InfluxDB and most LSM databases keep a Bloom filter per file/block so a lookup
can skip files that cannot contain a key, avoiding disk reads. It's one of the
highest-leverage optimizations in storage engines.
"""

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
        raise NotImplementedError


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
        # TODO: round m and k up to at least 1; store an integer bit array
        #       (a Python int used as a bitset, or a bytearray)
        self.expected_items = expected_items
        self.false_positive_rate = false_positive_rate
        self.num_bits = 0
        self.num_hashes = 0
        self._bits = 0  # use a big int as the bit array (bit i = (self._bits >> i) & 1)
        self._count = 0
        raise NotImplementedError

    def _hashes(self, item: Any) -> List[int]:
        """
        Produce `num_hashes` independent bit positions for `item`.

        Double hashing trick: derive two base hashes h1, h2 from a single digest
        and combine them: g_i = (h1 + i * h2) % num_bits.
        """
        # TODO: hash str(item) with hashlib (e.g. md5/sha1), split digest into
        #       two ints h1, h2, then return [(h1 + i*h2) % num_bits for i in
        #       range(num_hashes)]
        raise NotImplementedError

    def add(self, item: Any) -> None:
        """Add an item: set all of its hash-position bits to 1."""
        # TODO: for pos in self._hashes(item): self._bits |= (1 << pos)
        # TODO: increment self._count
        raise NotImplementedError

    def might_contain(self, item: Any) -> bool:
        """True if ALL the item's hash bits are set (possibly present)."""
        # TODO: return all((self._bits >> pos) & 1 for pos in self._hashes(item))
        raise NotImplementedError

    def add_all(self, items: Iterable[Any]) -> None:
        """Convenience: add many items."""
        # TODO
        raise NotImplementedError

    def stats(self) -> BloomStats:
        """Return a BloomStats snapshot of this filter."""
        # TODO
        raise NotImplementedError


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
        # TODO: for (k, v) in tag_pairs: filter.add(token); tag_index.add_entry(k, v, location)
        raise NotImplementedError

    def might_have(self, location: str, tag_key: str, tag_value: str) -> bool:
        """Cheap pre-check: could this location contain tag_key=tag_value?"""
        # TODO: if no filter for location -> be safe and return True
        # TODO: else return filter.might_contain(token)
        raise NotImplementedError

    def lookup_with_skip(self, tag_key: str, tag_value: str, candidate_locations: List[str]):
        """
        Among candidate_locations, return (matches, skipped) where:
          - matches: locations the exact index confirms contain the value
          - skipped: locations the bloom filter let us skip without checking
        """
        # TODO: for each candidate, if not might_have -> count as skipped;
        #       else confirm via self.tag_index.lookup(tag_key, tag_value)
        raise NotImplementedError


def test_index_optimization():
    """Test cases for bloom filters and optimized indexing."""
    print("Testing Index Optimization (Bloom Filters)...")

    # Test 1: no false negatives — every added item must report present
    bf = BloomFilter(expected_items=1000, false_positive_rate=0.01)
    added = [f"host=server{i}" for i in range(500)]
    bf.add_all(added)
    assert all(bf.might_contain(x) for x in added), "Bloom filter must have NO false negatives"
    print("✓ Test 1 passed: no false negatives")

    # Test 2: false-positive rate is reasonable for never-added items
    never = [f"host=ghost{i}" for i in range(5000)]
    fp = sum(1 for x in never if bf.might_contain(x)) / len(never)
    assert fp < 0.05, f"False positive rate too high: {fp:.3f}"
    print(f"✓ Test 2 passed: measured FP rate {fp:.3%} (target ~1%)")

    # Test 3: sizing formulas produce sane k and m
    s = bf.stats()
    assert s.num_bits > 0 and s.num_hashes >= 1
    assert s.num_items == 500
    assert 0.0 <= s.estimated_false_positive_rate < 0.1
    print(f"✓ Test 3 passed: stats -> bits={s.num_bits}, hashes={s.num_hashes}, "
          f"est_fp={s.estimated_false_positive_rate:.3%}")

    # Test 4: optimized index skips locations that can't match
    class FakeTagIndex:
        def __init__(self):
            self.data = {}  # (k,v) -> set(locations)
        def add_entry(self, k, v, loc):
            self.data.setdefault((k, v), set()).add(loc)
        def lookup(self, k, v):
            return set(self.data.get((k, v), set()))

    opt = OptimizedTagIndex(FakeTagIndex(), expected_items_per_location=100)
    opt.index_location("fileA", [("host", "s1"), ("region", "us-west")])
    opt.index_location("fileB", [("host", "s2"), ("region", "us-east")])
    opt.index_location("fileC", [("host", "s3"), ("region", "us-west")])

    # s1 only lives in fileA -> fileB/fileC should mostly be skipped by bloom
    matches, skipped = opt.lookup_with_skip("host", "s1", ["fileA", "fileB", "fileC"])
    assert "fileA" in matches, "fileA truly contains host=s1"
    assert skipped >= 1, "bloom filter should skip at least one non-matching file"
    print(f"✓ Test 4 passed: lookup_with_skip -> matches={sorted(matches)}, skipped={skipped}")

    # Test 5: might_have never lies about presence (no false negative at file level)
    assert opt.might_have("fileA", "host", "s1") is True
    print("✓ Test 5 passed: might_have has no false negatives")

    print("\n🎉 All index optimization tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement BloomFilter, BloomStats, and OptimizedTagIndex.
    2. Run: python day14_index_optimization.py
    3. All 5 tests should pass.

    Success criteria:
    - the filter NEVER returns a false negative
    - the measured false-positive rate is close to the configured target
    - lookup_with_skip skips files that definitely lack the value

    Next steps:
    - Run the Week 2 Integration Lab: labs/week2_lab.py
    - Think about: how does doubling the bit array change the FP rate? Why is
      "no false negatives" the property that makes skipping SAFE?
    """
    test_index_optimization()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Bloom Filter
   - A bit array + k hash functions. add() sets k bits; might_contain() checks
     that all k bits are set.
   - No false negatives (a set bit is never unset), but false positives are
     possible (bits collide). This asymmetry is exactly what "safe to skip"
     needs.

2. Sizing
   - m = -(n ln p)/(ln 2)^2 bits; k = (m/n) ln 2 hashes minimize FP for n items
     at target rate p. Over-filling (n grows past expected) raises the FP rate.

3. Double Hashing
   - Generate k positions from two base hashes: g_i = h1 + i*h2 (mod m). Cheaper
     than computing k independent hashes and works well in practice.

4. Skip Optimization
   - One filter per file/block summarizes its contents. A query checks the
     filter first and reads the file only on "possibly present". Most negative
     lookups become a single bit check.

Connection to InfluxDB:
- TSM/TSI keep per-file bloom filters so series/tag lookups skip files that
  cannot contain the key, dramatically cutting disk I/O on selective queries.

Trade-offs:
- More bits / more hashes -> lower FP rate but more memory / CPU per lookup.
- Bloom filters can't be resized or enumerate their contents; they only answer
  membership. Pair them with an exact index for the real answers.
"""
