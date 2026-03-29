# draw.io ERD Generator

Generates a draw.io ERD (`.drawio`) file from a CSV data dictionary.

## Usage

```bash
python3 generate_erd.py [options] INPUT.csv
```

The output file defaults to `<INPUT>.drawio` in the current directory.

### Options

| Option | Description |
|---|---|
| `-o`, `--output OUTPUT.drawio` | Write output to this path instead of the default |
| `-f`, `--force` | Overwrite the output file if it already exists |
| `-h`, `--help` | Show help and exit |

The script refuses to overwrite an existing file unless `--force` is given.

## Input CSV format

| Column | Description |
|---|---|
| `table_name` | Name of the table |
| `column_name` | Display name of the column |
| `key_type` | `PK`, `FK`, or empty |
| `data_type` | e.g. `integer`, `string`, `number` |
| `column_id` | Unique dot-notation ID, e.g. `customer.id` |
| `references` | `column_id` of the referenced PK column (FK rows only) |

Example (`erd_data.csv`):

```
table_name,column_name,key_type,data_type,column_id,references
Customer,ID,PK,integer,customer.id,
Customer,Name,,string,customer.name,
Order,ID,PK,integer,order.id,
Order,Customer ID,FK,integer,order.customer_id,customer.id
```

## Output structure

The script writes a native draw.io XML file matching the built-in ERD table shape format:

- `shape=table` container per table (header + `n × 30 px` rows)
- `shape=tableRow` per column — `bottom=1` on PK rows (separator line)
- `shape=partialRectangle` key cell (left 30 px) — bold for PK, `editable=1` for FK/regular
- `shape=partialRectangle` value cell (right 150 px) — bold+underline (`fontStyle=5`) for PK
- `ERone → ERzeroToMany` orthogonal edge from PK row to FK row per `references` entry

---

## Why not draw.io CSV import?

draw.io's built-in CSV import (`Extras > Edit Diagram > CSV`) was investigated as an alternative but has fundamental limitations that make it unsuitable for generating table-structured ERDs.

### What the CSV import format is

A plain-text file with `#`-prefixed directives followed by CSV data. Each CSV row produces one shape. Key directives:

```
# label: %columnname%       — shape label (HTML supported; %col% resolved from CSV columns)
# style: shape=...          — shape style (can embed %col% for partial substitution)
# identity: col             — use this column as the cell ID
# parent: col               — nest shape inside the parent identified by this column's value
# connect: {"from":"a","to":"b","style":"..."}  — draw edges between rows
# ignore: col1,col2         — exclude columns from shape metadata
```

### Why it fails for ERD tables

**1. `label` and `style` are reserved XML attribute names.**
A CSV column named `label` conflicts with the `label` XML attribute that draw.io uses to store the display label template. The import cannot store both the template (`%label%`) and the per-row data value under the same attribute name, so `%label%` is never resolved — it appears literally in the diagram. The same applies to a column named `style`.

**2. Per-row style override (`# style: %style%`) does not work.**
While `# style:` supports partial substitution (e.g. `fillColor=%color%`), setting the entire style from a column reference stores `%style%` literally as the cell's style string rather than substituting it. There is no supported mechanism to apply a completely different style to individual rows in a single import pass.

**3. `# parent:` cannot create parent-child relationships in the same import batch.**
The `shape=table` ERD format requires a 3-level nesting: table container → tableRow → two partialRectangle cells. The `# parent:` directive is designed for swimlane/stack-layout containers and resolves parent references against shapes that already exist in the diagram. Even with `# identity:`, shapes created in the same CSV batch are not reliably available as parents during the same import ([jgraph/drawio#4121](https://github.com/jgraph/drawio/issues/4121)).

**4. `shape=table` uses `childLayout=tableLayout`, not `childLayout=stackLayout`.**
draw.io's CSV import was built around the swimlane/stack model. The table layout requires each child row to itself contain two `partialRectangle` sub-cells — one shape per CSV row cannot produce this 3-level structure.

**5. `references` is treated as a reserved/special word.**
When used as a column name, draw.io stores the column under the XML attribute name `undefined` instead of `references`, breaking the `# connect:` directive that depends on it.

### Why the list-shape approach can work (with caveats)

`shape=list` containers use `childLayout=stackLayout`, which the CSV import's `# parent:` directive was designed for. Children are simple shapes stacked vertically with a uniform style — no sub-cell nesting required. However, even this approach requires **two separate import passes**: first import the list containers, then import the list items with `# parent:` pointing to the already-existing containers.
