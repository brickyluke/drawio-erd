#!/usr/bin/env python3
"""Generate a draw.io ERD .drawio file from a CSV data dictionary.

Input CSV columns: table_name, column_name, key_type, data_type, column_id, references
Output: .drawio XML file with shape=table containers, shape=tableRow rows,
        shape=partialRectangle key/value cells, and ERone→ERzeroToMany edges.
"""

import csv
import os
import sys
import uuid
from collections import OrderedDict
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

TABLE_WIDTH   = 180
ROW_HEIGHT    = 30
HEADER_HEIGHT = 30
TABLE_GAP_X   = 140
START_X       = 120
START_Y       = 150

STYLE_TABLE = (
    'shape=table;startSize=30;container=1;collapsible=1;childLayout=tableLayout;'
    'fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;html=1;'
)
STYLE_ROW = (
    'shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=0;'
    'fillColor=none;collapsible=0;dropTarget=0;'
    'points=[[0,0.5],[1,0.5]];portConstraint=eastwest;'
    'top=0;left=0;right=0;bottom={bottom};'
)
STYLE_KEY_PK   = 'shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;fontStyle=1;overflow=hidden;whiteSpace=wrap;html=1;'
STYLE_KEY_OTHER= 'shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;editable=1;overflow=hidden;whiteSpace=wrap;html=1;'
STYLE_VAL_PK   = 'shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;spacingLeft=6;fontStyle=5;overflow=hidden;whiteSpace=wrap;html=1;'
STYLE_VAL_OTHER= 'shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;spacingLeft=6;overflow=hidden;whiteSpace=wrap;html=1;'
STYLE_EDGE = (
    'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;'
    'html=1;endArrow=ERzeroToMany;endFill=0;startArrow=ERone;startFill=0;'
)


def new_id():
    return uuid.uuid4().hex[:20]


def geo(parent, x=None, y=None, width=None, height=None, relative=None):
    attrs = {}
    if x        is not None: attrs['x']        = str(x)
    if y        is not None: attrs['y']        = str(y)
    if width    is not None: attrs['width']     = str(width)
    if height   is not None: attrs['height']    = str(height)
    if relative is not None: attrs['relative']  = str(relative)
    el = SubElement(parent, 'mxGeometry', **attrs)
    el.set('as', 'geometry')
    return el


def alt_bounds(geo_el, width, height):
    rb = SubElement(geo_el, 'mxRectangle', width=str(width), height=str(height))
    rb.set('as', 'alternateBounds')


def parse_csv(path):
    """Return (tables, references).

    tables: OrderedDict[table_name -> list of col dicts]
    references: dict[fk_column_id -> pk_column_id]
    """
    tables = OrderedDict()
    references = {}
    with open(path, newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            tname = row['table_name'].strip()
            if not tname:
                continue
            tables.setdefault(tname, []).append({
                'column_name': row['column_name'].strip(),
                'key_type':    row['key_type'].strip(),
                'data_type':   row['data_type'].strip(),
                'column_id':   row['column_id'].strip(),
            })
            ref = row['references'].strip()
            if ref:
                references[row['column_id'].strip()] = ref
    return tables, references


def build_xml(tables, references):
    mxfile = Element('mxfile',
        host='Python',
        agent=f'Python script: {os.path.basename(__file__)}',
        version='28.2.5')
    diagram = SubElement(mxfile, 'diagram', name='Page-1', id=new_id())
    model = SubElement(diagram, 'mxGraphModel',
        dx='1106', dy='881', grid='1', gridSize='10',
        guides='1', tooltips='1', connect='1', arrows='1', fold='1',
        page='1', pageScale='1', pageWidth='1169', pageHeight='827',
        math='0', shadow='0')
    root = SubElement(model, 'root')
    SubElement(root, 'mxCell', id='0')
    SubElement(root, 'mxCell', id='1', parent='0')

    # column_id -> row mxCell id (used to wire FK edges)
    row_ids = {}

    x = START_X
    for table_name, columns in tables.items():
        table_id = new_id()
        height = HEADER_HEIGHT + len(columns) * ROW_HEIGHT

        # Table container
        tc = SubElement(root, 'mxCell',
            id=table_id, value=table_name,
            style=STYLE_TABLE, vertex='1', parent='1')
        geo(tc, x=x, y=START_Y, width=TABLE_WIDTH, height=height)

        for i, col in enumerate(columns):
            is_pk = col['key_type'] == 'PK'
            is_fk = col['key_type'] == 'FK'

            row_id = new_id()
            row_ids[col['column_id']] = row_id

            # Row
            row = SubElement(root, 'mxCell',
                id=row_id, value='',
                style=STYLE_ROW.format(bottom='1' if is_pk else '0'),
                vertex='1', parent=table_id)
            geo(row, y=HEADER_HEIGHT + i * ROW_HEIGHT,
                width=TABLE_WIDTH, height=ROW_HEIGHT)

            # Key cell (left 30 px)
            key_val   = col['key_type'] if col['key_type'] else ''
            key_style = STYLE_KEY_PK if is_pk else STYLE_KEY_OTHER
            kc = SubElement(root, 'mxCell',
                id=new_id(), value=key_val,
                style=key_style, vertex='1', parent=row_id, connectable='0')
            kg = geo(kc, width=30, height=30)
            alt_bounds(kg, 30, 30)

            # Value cell (remaining 150 px)
            val_label = f"{col['column_name']}: {col['data_type']}"
            val_style = STYLE_VAL_PK if is_pk else STYLE_VAL_OTHER
            vc = SubElement(root, 'mxCell',
                id=new_id(), value=val_label,
                style=val_style, vertex='1', parent=row_id, connectable='0')
            vg = geo(vc, x=30, width=150, height=30)
            alt_bounds(vg, 150, 30)

        x += TABLE_WIDTH + TABLE_GAP_X

    # FK edges: source = PK row, target = FK row
    for fk_col_id, pk_col_id in references.items():
        if fk_col_id not in row_ids or pk_col_id not in row_ids:
            print(f'Warning: cannot resolve reference {fk_col_id} -> {pk_col_id}',
                  file=sys.stderr)
            continue
        ec = SubElement(root, 'mxCell',
            id=new_id(), value='',
            style=STYLE_EDGE, edge='1', parent='1',
            source=row_ids[pk_col_id],
            target=row_ids[fk_col_id])
        geo(ec, relative=1)

    return mxfile


def pretty(element):
    raw = tostring(element, encoding='unicode')
    dom = parseString(raw)
    lines = dom.toprettyxml(indent='  ').splitlines()
    # drop the <?xml ...?> declaration minidom prepends
    return '\n'.join(line for line in lines if not line.startswith('<?xml'))


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate a draw.io ERD .drawio file from a CSV data dictionary.',
        epilog='Input CSV columns: table_name, column_name, key_type, data_type, column_id, references',
    )
    parser.add_argument('input_csv', metavar='INPUT.csv',
                        help='CSV data dictionary file')
    parser.add_argument('-o', '--output', metavar='OUTPUT.drawio',
                        help='output .drawio file (default: <INPUT>.drawio)')
    parser.add_argument('-f', '--force', action='store_true',
                        help='overwrite output file if it already exists')
    args = parser.parse_args()

    input_csv = args.input_csv
    if args.output:
        output_xml = args.output
    else:
        base = os.path.splitext(os.path.basename(input_csv))[0]
        output_xml = base + '.drawio'

    if os.path.exists(output_xml) and not args.force:
        parser.error(f'{output_xml} already exists; use --force to overwrite')

    tables, references = parse_csv(input_csv)
    mxfile = build_xml(tables, references)

    with open(output_xml, 'w', encoding='utf-8') as fh:
        fh.write(pretty(mxfile))

    print(f'Written {output_xml}  ({len(tables)} tables, {len(references)} FK edges)')


if __name__ == '__main__':
    main()
