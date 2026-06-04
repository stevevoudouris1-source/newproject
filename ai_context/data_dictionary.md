# Data dictionary — index

**Status: placeholder (not yet built).**

This file is the **index** to Turn 5's database/warehouse schema as it's relevant
to this app. The company has many tables and views, so the actual definitions
live in per-domain files under [`ai_context/data_dictionary/`](data_dictionary/),
one file per area (e.g. `inventory.md` holds the tables/views describing how
inventory is stored). This index links to each of them.

## How this gets built

This dictionary is **not** built speculatively. When Claude is first given access
to a company database (e.g. the Azure data warehouse via `WAREHOUSE_DATABASE_URL`):

1. Claude asks whether you'd like it to build a data dictionary for the tables/
   views this app will commonly reference — **or** whether you already have one it
   can use (paste it / point to it, and Claude will adapt it into this format).
2. If yes, Claude profiles the relevant tables (names, columns, types, keys,
   meaning, gotchas) and writes a per-domain file under
   `ai_context/data_dictionary/`, then adds a row to the index below.
3. Keep it scoped to what the app actually uses — don't document the whole
   warehouse. Add domains as new features need them.

Record only schema/structure here — **never** credentials or row-level data
(those rules in [CLAUDE.md](../CLAUDE.md) → Security still apply).

## Index

| Domain | File | Description |
|---|---|---|
| _none yet_ | — | Add a row here when a domain file is created under `ai_context/data_dictionary/`. |

<!--
Example once populated:
| Inventory | [data_dictionary/inventory.md](data_dictionary/inventory.md) | Stock levels, warehouses, SKUs, availability views |
| Orders    | [data_dictionary/orders.md](data_dictionary/orders.md)       | Order headers/lines, fulfillment, returns |
-->
