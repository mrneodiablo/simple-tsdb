#!/usr/bin/env python3
"""
Day 11: Index Persistence
=========================

Problem: Indexes are built in memory but must survive a restart. Save the tag
index, time index, and series registry to disk, load them back exactly, and
support incremental (append-only) updates so you don't rewrite everything on
each change.

Learning Objectives:
- Serialize in-memory structures (sets, dicts) to a stable on-disk format
- Reload them losslessly (round-trip correctness)
- Version your format so future changes don't corrupt old files
- Append incremental updates (a write-ahead style log) and replay them
- Atomic writes: never leave a half-written index file

Real-World Connection:
InfluxDB persists its TSI to disk and loads it on startup; rebuilding indexes
from raw data on every boot would be far too slow. It also writes incremental
changes and periodically compacts them — the pattern you implement here.
"""

import os
import json
import tempfile
from typing import Dict, Any, List, Set


INDEX_FORMAT_VERSION = 1


class IndexSerializer:
    """
    Convert index structures <-> JSON-serializable dicts.

    JSON can't store Python `set`, so sets become sorted lists on the way out
    and sets again on the way in. Keeping lists SORTED makes files diff-friendly
    and deterministic.
    """

    def tag_index_to_dict(self, tag_index: Dict[str, Dict[str, Set[str]]]) -> Dict[str, Any]:
        """
        tag_index example:
        {
            "host":   {"server1": {"loc1", "loc2"}, "server2": {"loc3"}},
            "region": {"us-west": {"loc1"},         "us-east": {"loc2", "loc3"}},
        }
        Serialize the Day 8 tag index ({key:{value:set}}) to a plain dict.

        Wrap it with a version + type so the loader can validate it.
        """
        # TODO: Convert each inner set -> sorted list
        data = {}
        for k ,v in tag_index.items():
            data[k] = {}
            for vk, vv in v.items():
                data[k][vk] = sorted(vv)

        # TODO: Return {"version": INDEX_FORMAT_VERSION, "type": "tag_index",
        #               "data": {...}}
        return {"version": INDEX_FORMAT_VERSION, "type": "tag_index", "data": data}

    def dict_to_tag_index(self, payload: Dict[str, Any]) -> Dict[str, Dict[str, Set[str]]]:
        """Inverse: validate version/type, rebuild sets from lists."""
        # TODO: Check payload["version"] == INDEX_FORMAT_VERSION (else raise)
        if payload.get("version") != INDEX_FORMAT_VERSION:
            raise ValueError(f"Unsupported index format version: {payload.get('version')}")
        # TODO: Rebuild {key: {value: set(list)}}
        if payload.get("type") != "tag_index":
            raise ValueError(f"Invalid index type: {payload.get('type')}")
        data = payload.get("data", {})
        tag_index = {}
        for k, v in data.items():
            tag_index[k] = {}
            for vk, vv in v.items():
                tag_index[k][vk] = set(vv)
        return tag_index

    def time_index_to_dict(self, blocks: List[Any]) -> Dict[str, Any]:
        """
        Serialize Day 9 blocks. `blocks` is a list of objects/tuples carrying
        (location, min_ts, max_ts). Store them as a list of small dicts.
        """
        # TODO: Map each block -> {"location":..., "min_ts":..., "max_ts":...}
        data = []
        for block in blocks:
            data.append({
                "location": block.location,
                "min_ts": block.min_ts,
                "max_ts": block.max_ts
            })
        return {"version": INDEX_FORMAT_VERSION, "type": "time_index", "data": data}

    def dict_to_time_index(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Inverse: return the list of block dicts (ready to feed add_blocks)."""
        # TODO: Validate version, return payload["data"]
        if payload.get("version") != INDEX_FORMAT_VERSION:
            raise ValueError(f"Unsupported index format version: {payload.get('version')}")
        if payload.get("type") != "time_index":
            raise ValueError(f"Invalid index type: {payload.get('type')}")
        return payload.get("data", [])


class IndexPersistence:
    """
    Save/load index files on disk with atomic writes and an incremental log.

    Layout under `index_dir`:
        index_dir/
            tag_index.json        # full snapshot
            time_index.json       # full snapshot
            series.json           # full snapshot
            updates.log           # append-only incremental changes (JSON lines)
    """

    def __init__(self, index_dir: str) -> None:
        self.index_dir = index_dir
        self.serializer = IndexSerializer()
        # TODO: Ensure index_dir exists (os.makedirs(..., exist_ok=True))
        raise NotImplementedError

    # --------------------------------------------------------- atomic helpers
    def _atomic_write_json(self, path: str, payload: Dict[str, Any]) -> None:
        """
        Write JSON atomically: write to a temp file in the same dir, fsync,
        then os.replace() over the target. A crash leaves either the old file
        or the new file — never a truncated mix.
        """
        # TODO: tempfile.NamedTemporaryFile(dir=self.index_dir, delete=False)
        # TODO: json.dump, flush, os.fsync(fd)
        # TODO: os.replace(tmp_path, path)
        raise NotImplementedError

    # --------------------------------------------------------- full snapshots
    def save_tag_index(self, tag_index: Dict[str, Dict[str, Set[str]]]) -> None:
        """Persist a full tag-index snapshot."""
        # TODO: serialize + _atomic_write_json to tag_index.json
        raise NotImplementedError

    def load_tag_index(self) -> Dict[str, Dict[str, Set[str]]]:
        """Load the tag-index snapshot (empty dict if file missing)."""
        # TODO: read JSON, dict_to_tag_index; handle missing file gracefully
        raise NotImplementedError

    def save_time_index(self, blocks: List[Any]) -> None:
        """Persist a full time-index snapshot."""
        # TODO
        raise NotImplementedError

    def load_time_index(self) -> List[Dict[str, Any]]:
        """Load time-index block dicts (empty list if missing)."""
        # TODO
        raise NotImplementedError

    # ------------------------------------------------------ incremental log
    def append_update(self, update: Dict[str, Any]) -> None:
        """
        Append one incremental change to updates.log as a single JSON line.

        Example update:
            {"op": "add", "tag_key": "host", "tag_value": "s1", "location": "f1"}

        Appending is O(1) and crash-safe-ish; you replay these on top of the
        last full snapshot at load time, then occasionally compact.
        """
        # TODO: open(updates.log, "a"), write json.dumps(update) + "\n"
        raise NotImplementedError

    def read_updates(self) -> List[Dict[str, Any]]:
        """Read and parse all incremental updates in order (empty if none)."""
        # TODO: read updates.log line by line, json.loads each
        raise NotImplementedError

    def compact(self, tag_index: Dict[str, Dict[str, Set[str]]]) -> None:
        """
        Fold the incremental log into a fresh full snapshot, then clear the log.

        Caller is expected to have already applied updates into `tag_index`;
        this writes the new snapshot and truncates updates.log.
        """
        # TODO: save_tag_index(tag_index); then truncate/remove updates.log
        raise NotImplementedError


def test_index_persistence():
    """Test cases for index persistence."""
    print("Testing Index Persistence...")

    import shutil
    test_dir = "test_index_persist"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    persist = IndexPersistence(test_dir)

    # Test 1: tag index round-trip
    tag_index = {
        "host": {"server1": {"loc1", "loc2"}, "server2": {"loc3"}},
        "region": {"us-west": {"loc1"}},
    }
    persist.save_tag_index(tag_index)
    loaded = persist.load_tag_index()
    assert loaded == tag_index, f"Tag index round-trip failed: {loaded}"
    print("✓ Test 1 passed: tag index save/load round-trip")

    # Test 2: loading a missing index is empty, not an error
    fresh = IndexPersistence(test_dir + "_empty")
    assert fresh.load_tag_index() == {}
    print("✓ Test 2 passed: missing index loads as empty")

    # Test 3: time index round-trip
    blocks = [
        {"location": "f1", "min_ts": 100.0, "max_ts": 200.0},
        {"location": "f2", "min_ts": 200.0, "max_ts": 300.0},
    ]
    # accept simple dict-like blocks for the serializer
    persist.save_time_index(blocks)
    loaded_blocks = persist.load_time_index()
    assert len(loaded_blocks) == 2
    assert loaded_blocks[0]["location"] == "f1"
    print("✓ Test 3 passed: time index save/load round-trip")

    # Test 4: version is recorded on disk
    with open(os.path.join(test_dir, "tag_index.json")) as f:
        raw = json.load(f)
    assert raw["version"] == INDEX_FORMAT_VERSION
    print("✓ Test 4 passed: format version persisted")

    # Test 5: incremental updates append + read in order
    persist.append_update({"op": "add", "tag_key": "host", "tag_value": "s9", "location": "f9"})
    persist.append_update({"op": "add", "tag_key": "host", "tag_value": "s10", "location": "f10"})
    updates = persist.read_updates()
    assert len(updates) == 2 and updates[0]["tag_value"] == "s9"
    print("✓ Test 5 passed: incremental update log")

    # Test 6: compaction clears the log
    persist.compact(tag_index)
    assert persist.read_updates() == [], "Log should be empty after compaction"
    print("✓ Test 6 passed: compaction folds + clears log")

    shutil.rmtree(test_dir, ignore_errors=True)
    shutil.rmtree(test_dir + "_empty", ignore_errors=True)
    print("\n🎉 All index persistence tests passed!")


if __name__ == "__main__":
    """
    Instructions:
    1. Implement IndexSerializer + IndexPersistence methods.
    2. Run: python day11_index_persistence.py
    3. All 6 tests should pass.

    Success criteria:
    - save -> load reproduces the exact in-memory structure (sets included)
    - writes are atomic (temp file + os.replace)
    - incremental updates append cheaply and replay in order
    - a stored format version guards against future format drift

    Next steps:
    - Day 12 uses these reloaded indexes to actually answer queries.
    - Think about: how often should you compact vs. append? What's the cost of
      replaying a huge updates.log on startup?
    """
    test_index_persistence()


# ========================================
# Concepts and Theory
# ========================================
"""
Key Concepts:

1. Serialization Gaps
   - JSON has no `set`; convert to sorted lists and back. Sorting keeps files
     deterministic and diffable.

2. Atomic Writes
   - Write to a temp file in the SAME directory, fsync, then os.replace().
     os.replace is atomic on POSIX/Windows, so readers never see a half file.

3. Snapshot + Log (a mini WAL)
   - Full snapshot = cheap to load, expensive to write.
   - Incremental log = cheap to write, expensive to replay if it grows.
   - Compaction periodically folds the log into a new snapshot — the classic
     LSM/WAL trade-off you also saw with Week 1 writes.

4. Versioning
   - Embedding a format version lets a newer loader detect/upgrade/refuse old
     files instead of silently misreading them.

Connection to InfluxDB:
- TSI files are persisted and memory-mapped on startup; the WAL captures recent
  changes and compaction merges everything into immutable index files.

Trade-offs:
- Snapshot-only: simple but rewrites everything per change.
- Log-only: fast writes but slow, unbounded startup replay.
- Snapshot + periodic compaction: best of both, more moving parts.
"""
