#!/usr/bin/env python3

import sqlite3
from typing import Dict
import pydantic

class Dino(pydantic.BaseModel):
    uuid: str
    id: str
    tamed_name: str | None
    info_raw: bytes
    stats_raw: bytes

    def __str__(self):
        if self.tamed_name != None:
            return f'Rex with ID {self.id} and name {self.tamed_name}'
        else:
            return f'Rex with ID {self.id} and no name :('

con = sqlite3.connect("data/TheIsland_WP.ark")

def read_from(data, form):
    import struct
    n = struct.calcsize(form)
    # print(f"n:{n}, nn:{struct.unpack_from(form, data)[0]}")
    return data[n:], struct.unpack_from(form, data)[0]


def read_string(data):
    data, n = read_from(data, "I")
    if n == 0:
        return data, None
    # print(data[:n-1].decode('utf-8'))
    return data[n:], data[:n-1].decode('utf-8')

def do_header():
    cur = con.cursor()
    res = cur.execute("SELECT value FROM custom WHERE key = 'SaveHeader'")
    row = res.fetchone()[0]

    data = row[18:]
    parts = []
    while True:
        data, s = read_string(data)
        if s is None:
            break
        parts.append(s)
        data, _ = read_from(data, "I") # always -1

    data = data[8:]

    ids = {}
    while data:
        data, tid = read_from(data, "I")
        data, name = read_string(data)
        ids[tid] = name

    return parts, ids

_, ids = do_header()

def do_game(tids, name_filter = None):
    from os import makedirs
    from uuid import UUID
    import struct

    cur = con.cursor()
    if name_filter:
        hex_code_filter = [id for id, name in tids.items() if name == name_filter][0]
        hex_start = struct.pack("<I", hex_code_filter).hex()
        hex_end = struct.pack("<I", hex_code_filter + 16777216).hex()
        res = cur.execute("SELECT key, value FROM game WHERE value >= x'" + str(hex_start) + "' AND value < x'" + str(hex_end) + "'")
    else:
        res = cur.execute("SELECT key, value FROM game")

    rows = res.fetchall()
    for row in rows:
        uuid = UUID(bytes_le=row[0])
        _, tid = read_from(row[1], "I")
        tname = tids[tid]

        makedirs(f"data/{tname}", exist_ok=True)
        with open(f"data/{tname}/{uuid}", "wb") as out:
            out.write(row[1])

def find_string_from_hex():
    import struct
    import sys
    from tkinter import Tk # in Python 2, use "Tkinter" instead 
    
    r = Tk()
    r.withdraw()

    if len(sys.argv) > 2:
        print("Using parameter...")
        tag_to_search = sys.argv[2]
    else:
        print("Using clipboard...")
        tag_to_search = r.clipboard_get()

    print(f"Searching for: {tag_to_search} ...")
    try:
        tag_to_search_hex = struct.unpack("<I", struct.pack(">I", int(tag_to_search, 16)))[0]
        result = ids[tag_to_search_hex]
        print(result)
        r.clipboard_clear()
        r.clipboard_append(result)
        r.update() # now it stays on the clipboard after the window is closed
        r.destroy()
    except:
        pass

def get_id(data: bytes):
    rex_character_bp_c_index = data.index(b"\x04\x42\x56\x10")
    # print(rex_character_bp_c_index)
    return data[rex_character_bp_c_index+4:rex_character_bp_c_index+8]

def get_tamed_name(data: bytes):
    import struct
    try:
        tamed_name_index = data.index(b'\x51\xDA\x5A\x7C')
        string_length = struct.unpack("<I", data[tamed_name_index+25:tamed_name_index+29])[0]
        tamed_name = data[tamed_name_index+29:tamed_name_index+28+string_length].decode("utf-8") # 28 to remove null termination
        return tamed_name
    except ValueError as e:
        # print("Not a named Dino")
        return None

def get_matching_dinos(name_filter: str):
    from uuid import UUID
    import struct

    cur = con.cursor()
    hex_code_filter = [id for id, name in ids.items() if name == name_filter][0]
    hex_start = struct.pack("<I", hex_code_filter).hex()
    hex_end = struct.pack("<I", hex_code_filter + 16777216).hex()
    res = cur.execute("SELECT key, value FROM game WHERE value >= x'" + str(hex_start) + "' AND value < x'" + str(hex_end) + "'")
    rows = res.fetchall()

    dinos: Dict[str, list[Dino]] = {}

    for row in rows:
        uuid = UUID(bytes_le=row[0])
        _, tid = read_from(row[1], "I")
        tname = ids[tid]

        if not tname in dinos:
            dinos[tname] = []
        id = get_id(row[1]).hex()
        stats_data = get_stats_data(id)
        if stats_data != b'':
            dinos[tname].append(Dino(uuid=uuid.hex, id=id, info_raw=row[1], stats_raw=stats_data, tamed_name=get_tamed_name(row[1])))
        else:
            # print("No Stats Data found")
            pass
    return dinos

def get_stats_data(id: str):
    import struct

    hex_start = struct.pack(">I", int(id, 16)).hex()
    hex_end = struct.pack(">I", int(id, 16) + 1).hex()

    cur = con.cursor()
    res = cur.execute(f"SELECT key, value FROM game WHERE value >= x'E97920CD0000000000000000020000000C55428D0000000004425610{str(hex_start)}' AND value < x'E97920CD0000000000000000020000000C55428D0000000004425610{str(hex_end)}'")
    rows = res.fetchall()

    if len(rows) > 0:
        return rows[0][1]
    else:
        return b''
        

def save_file_from_hex(save = True):
    from os import makedirs
    from uuid import UUID

    cur = con.cursor()
    res = cur.execute("SELECT key, value FROM game WHERE value >= x'E97920CD0000000000000000020000000C55428D00000000044256107970f77f' AND value < x'E97920CD0000000000000000020000000C55428D00000000044256107970f780'")
    rows = res.fetchall()

    dinos: Dict[str, list[Dino]] = {}

    for row in rows:
        print("1")
        uuid = UUID(bytes_le=row[0])
        _, tid = read_from(row[1], "I")
        tname = ids[tid]

        if save:
            makedirs(f"data/{tname}", exist_ok=True)
            with open(f"data/{tname}/{uuid}", "wb") as out:
                out.write(row[1])
        else:
            if not tname in dinos:
                dinos[tname] = []
            dinos[tname].append(Dino(uuid=uuid.hex, info_raw=row[1]))
    if not save:
        return dinos

def find_file_from_string():
    import sys
    do_game(ids, sys.argv[2])

def print_usage():
    print("USAGE: python3 parse.py [-sffx(savefilefromhex)|-fsfx(findstringfromhex)|-fffs(findfilefromstring)] (SEARCHTERM IN CLIPBOARD!)")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        match sys.argv[1]:
            case "-sffx":
                save_file_from_hex()
            case "-fsfx":
                find_string_from_hex()
            case "-fffs":
                find_file_from_string()
            case _:
                print_usage()
    else:
        print_usage()
