#!/usr/bin/env python3

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
            if isinstance(block, dict):
                location = block["location"]
                min_ts = block["min_ts"]
                max_ts = block["max_ts"]
            elif hasattr(block, "location") and hasattr(block, "min_ts") and hasattr(block, "max_ts"):
                location = block.location
                min_ts = block.min_ts
                max_ts = block.max_ts
            elif isinstance(block, (tuple, list)) and len(block) >= 3:
                location, min_ts, max_ts = block[0], block[1], block[2]
            else:
                raise TypeError(f"Unsupported block format: {type(block)}")

            data.append({
                "location": location,
                "min_ts": min_ts,
                "max_ts": max_ts
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
        os.makedirs(self.index_dir, exist_ok=True)


    # --------------------------------------------------------- atomic helpers
    def _atomic_write_json(self, path: str, payload: Dict[str, Any]) -> None:
        """
        Write JSON atomically: write to a temp file in the same dir, fsync,
        then os.replace() over the target. A crash leaves either the old file
        or the new file — never a truncated mix.
        """
        # TODO: tempfile.NamedTemporaryFile(dir=self.index_dir, delete=False)
        temp_fd, tmp_path = tempfile.mkstemp(dir=self.index_dir)

        # TODO: json.dump, flush, os.fsync(fd)
        with os.fdopen(temp_fd, 'w') as tmp_file:
            json.dump(payload, tmp_file)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # TODO: os.replace(tmp_path, path)
        os.replace(tmp_path, path)

    # --------------------------------------------------------- full snapshots
    def save_tag_index(self, tag_index: Dict[str, Dict[str, Set[str]]]) -> None:
        """Persist a full tag-index snapshot."""
        # TODO: serialize + _atomic_write_json to tag_index.json
        payload = self.serializer.tag_index_to_dict(tag_index)
        path = os.path.join(self.index_dir, "tag_index.json")
        self._atomic_write_json(path, payload)

    def load_tag_index(self) -> Dict[str, Dict[str, Set[str]]]:
        """Load the tag-index snapshot (empty dict if file missing)."""
        # TODO: read JSON, dict_to_tag_index; handle missing file gracefully
        path = os.path.join(self.index_dir, "tag_index.json")
        if not os.path.exists(path):
            return {}
        with open(path, 'r') as f:
            payload = json.load(f)
        return self.serializer.dict_to_tag_index(payload)

    def save_time_index(self, blocks: List[Any]) -> None:
        """Persist a full time-index snapshot."""
        # TODO
        payload = self.serializer.time_index_to_dict(blocks)
        path = os.path.join(self.index_dir, "time_index.json")
        self._atomic_write_json(path, payload)


    def load_time_index(self) -> List[Dict[str, Any]]:
        """Load time-index block dicts (empty list if missing)."""
        # TODO
        path = os.path.join(self.index_dir, "time_index.json")
        if not os.path.exists(path):
            return []
        with open(path, 'r') as f:
            payload = json.load(f)
        return self.serializer.dict_to_time_index(payload)

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
        path = os.path.join(self.index_dir, "updates.log")
        with open(path, 'a') as f:
            f.write(json.dumps(update) + "\n")
            f.flush()
            os.fsync(f.fileno())


    def read_updates(self) -> List[Dict[str, Any]]:
        """Read and parse all incremental updates in order (empty if none)."""
        # TODO: read updates.log line by line, json.loads each
        path = os.path.join(self.index_dir, "updates.log")
        if not os.path.exists(path):
            return []
        updates = []
        with open(path, 'r') as f:
            for line in f:
                updates.append(json.loads(line.strip()))
        return updates

    def compact(self, tag_index: Dict[str, Dict[str, Set[str]]]) -> None:
        """
        Fold the incremental log into a fresh full snapshot, then clear the log.

        Caller is expected to have already applied updates into `tag_index`;
        this writes the new snapshot and truncates updates.log.
        """
        # TODO: save_tag_index(tag_index); then truncate/remove updates.log
        self.save_tag_index(tag_index)
        path = os.path.join(self.index_dir, "updates.log")
        if os.path.exists(path):
            os.remove(path)

