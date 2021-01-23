import re
from typing import *

from sqlalchemy import util
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql.type_api import TypeEngine

# https://trino.io/docs/current/language/types.html
_type_map = {
    # === Boolean ===
    'boolean': sqltypes.BOOLEAN,

    # === Integer ===
    'tinyint': sqltypes.SMALLINT,
    'smallint': sqltypes.SMALLINT,
    'integer': sqltypes.INTEGER,
    'bigint': sqltypes.BIGINT,

    # === Floating-point ===
    'real': sqltypes.FLOAT,
    'double': sqltypes.FLOAT,

    # === Fixed-precision ===
    'decimal': sqltypes.DECIMAL,

    # === String ===
    'varchar': sqltypes.VARCHAR,
    'char': sqltypes.CHAR,
    'varbinary': sqltypes.VARBINARY,
    'json': sqltypes.JSON,

    # === Date and time ===
    'date': sqltypes.DATE,
    'time': sqltypes.Time,
    'time with time zone': sqltypes.Time,
    'timestamp': sqltypes.TIMESTAMP,
    'timestamp with time zone': sqltypes.TIMESTAMP,

    # 'interval year to month': IntervalOfYear,  # TODO
    'interval day to second': sqltypes.Interval,

    # === Structural ===
    'array': sqltypes.ARRAY,
    # 'map': MAP
    # 'row': ROW

    # === Mixed ===
    # 'ipaddress': IPADDRESS
    # 'uuid': UUID,
    # 'hyperloglog': HYPERLOGLOG,
    # 'p4hyperloglog': P4HYPERLOGLOG,
    # 'qdigest': QDIGEST,
    # 'tdigest': TDIGEST,
}


class MAP(TypeEngine):
    pass


class ROW(TypeEngine):
    pass


def split(string: str, delimiter: str = ',',
          quote: str = '"', escaped_quote: str = r'\"',
          open_bracket: str = '(', close_bracket: str = ')') -> Iterator[str]:
    """
    A split function that is aware of quotes and brackets/parentheses.

    :param string: string to split
    :param delimiter: string defining where to split, usually a comma or space
    :param quote: string, either a single or a double quote
    :param escaped_quote: string representing an escaped quote
    :param open_bracket: string, either [, {, < or (
    :param close_bracket: string, either ], }, > or )
    """
    parens = 0
    quotes = False
    i = 0
    for j, character in enumerate(string):
        complete = parens == 0 and not quotes
        if complete and character == delimiter:
            yield string[i:j]
            i = j + len(delimiter)
        elif character == open_bracket:
            parens += 1
        elif character == close_bracket:
            parens -= 1
        elif character == quote:
            if quotes and string[j - len(escaped_quote) + 1: j + 1] != escaped_quote:
                quotes = False
            elif not quotes:
                quotes = True
    yield string[i:]


def parse_sqltype(type_str: str) -> TypeEngine:
    type_str = type_str.strip().lower()
    match = re.match(r'^(?P<type>\w+)\s*(?:\((?P<options>.*)\))?', type_str)
    if not match:
        util.warn(f"Could not parse type name '{type_str}'")
        return sqltypes.NULLTYPE
    type_name = match.group("type")
    type_opts = match.group("options")

    if type_name == "array":
        item_type = parse_sqltype(type_opts)
        return sqltypes.ARRAY(item_type)
    elif type_name == "map":
        key_type_str, value_type_str = split(type_opts)
        key_type = parse_sqltype(key_type_str)
        value_type = parse_sqltype(value_type_str)
        return MAP(key_type, value_type)
    elif type_name == "row":
        attr_types = split(type_opts)
        return ROW()  # TODO

    if type_name not in _type_map:
        util.warn(f"Did not recognize type '{type_name}'")
        return sqltypes.NULLTYPE
    type_class = _type_map[type_name]
    type_args = [int(o.strip()) for o in type_opts.split(',')] if type_opts else []
    if type_name in ('time', 'timestamp'):
        type_kwargs = dict(timezone=type_str.endswith("with time zone"))
        return type_class(**type_kwargs)  # TODO: handle time/timestamp(p) precision
    return type_class(*type_args)