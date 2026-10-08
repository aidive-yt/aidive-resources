# explore: ground truth (tinydb @ 18d73a1)

- The query cache is `Table._query_cache`, an `LRUCache` (tinydb/utils.py) created in
  `Table.__init__` (tinydb/table.py, `query_cache_class = LRUCache`, capacity
  `default_query_cache_capacity = 10`). It is filled in `Table.search`.
- Invalidation happens in one place: `Table._update_table()` (tinydb/table.py) ends with
  `self.clear_cache()`, and `Table.clear_cache()` does `self._query_cache.clear()`.
- Every public write goes through `_update_table`, so these trigger it:
  `insert`, `insert_multiple`, `update` (all three branches: callable/fields, by doc_ids, by cond),
  `update_multiple`, `upsert` (via `update` or `insert`), `remove` (by cond or doc_ids), `truncate`.
  `Table.__init__(persist_empty=True)` also calls it. `clear_cache()` itself is public.
  `TinyDB` (tinydb/database.py) forwards these via `__getattr__` to the default table;
  `drop_table`/`drop_tables` do not clear a cache, they forget the `Table` instances (`self._tables`).

## Check rule (check.py explore)
PASS iff the final answer
1. contains `table.py`, AND
2. contains `clear_cache` or `_query_cache`, AND
3. names at least 3 distinct methods among
   insert, insert_multiple, update, update_multiple, upsert, remove, truncate (word match, case-insensitive).
