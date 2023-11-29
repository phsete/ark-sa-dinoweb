#!/usr/bin/env python3

import sqlite3
from typing import Dict
import pydantic

ids: dict
con: sqlite3.Connection

class DinoStatPoints(pydantic.BaseModel):
    health: int
    stamina: int
    oxygen: int
    food: int
    weight: int
    damage: int

class Dino(pydantic.BaseModel):
    info_uuid: str
    stats_uuid: str
    save_file_id: str
    dino_id_1: int
    dino_id_2: int
    tamed_name: str | None
    base_level: int
    base_stat_points: DinoStatPoints
    tamed_applied_stat_points: DinoStatPoints
    mutation_applied_stat_points: DinoStatPoints
    _info_raw: bytes
    _stats_raw: bytes

    def __str__(self):
        if self.tamed_name != None:
            return f'Rex with ID {self.save_file_id} and name {self.tamed_name}'
        else:
            return f'Rex with ID {self.save_file_id} and no name :('
        
class ServerInfo(pydantic.BaseModel):
    dinos: Dict[str, list[Dino]]

def init(path_to_ark_file: str):
    global con
    global ids
    con = sqlite3.connect(path_to_ark_file)
    _, ids = do_header()

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

def parse_file(data: bytes):
    data = parse_uuid(parse_file_header(data))
    dino_id_1: int = 0
    dino_id_2: int = 0
    while len(data) > 0:
        data, hex_prop_name, name_prop_name = get_ark_name_from_hex(data)
        data, hex_prop_type, name_prop_type = get_ark_name_from_hex(data)
        data, value, _ = handle_property(data, name_prop_name, name_prop_type)
        if name_prop_name == "DinoID1":
            dino_id_1 = value
        if name_prop_name == "DinoID2":
            dino_id_2 = value
        # print(f"Value: {hex_prop_name}: {name_prop_name}, Property: {name_prop_type}: {value}")
    return dino_id_1, dino_id_2

def parse_stats_file(data: bytes):
    data = parse_uuid(parse_file_header(data, True))
    base_stat_points: DinoStatPoints = DinoStatPoints(health=0, stamina=0, oxygen=0, food=0, weight=0, damage=0)
    tamed_stat_points: DinoStatPoints = DinoStatPoints(health=0, stamina=0, oxygen=0, food=0, weight=0, damage=0)
    mutation_stat_points: DinoStatPoints = DinoStatPoints(health=0, stamina=0, oxygen=0, food=0, weight=0, damage=0)
    base_level: int = 0
    while len(data) > 0:
        data, hex_prop_name, name_prop_name = get_ark_name_from_hex(data)
        data, hex_prop_type, name_prop_type = get_ark_name_from_hex(data)
        data, value, index = handle_property(data, name_prop_name, name_prop_type)
        if name_prop_name == "NumberOfLevelUpPointsApplied":
            match index:
                case 0:
                    base_stat_points.health = value
                case 1:
                    base_stat_points.stamina = value
                case 3:
                    base_stat_points.oxygen = value
                case 4:
                    base_stat_points.food = value
                case 7:
                    base_stat_points.weight = value
                case 8:
                    base_stat_points.damage = value
                case _:
                    print("Error parsing stats file: Found unknown stat!")
        if name_prop_name == "NumberOfLevelUpPointsAppliedTamed":
            match index:
                case 0:
                    tamed_stat_points.health = value
                case 1:
                    tamed_stat_points.stamina = value
                case 3:
                    tamed_stat_points.oxygen = value
                case 4:
                    tamed_stat_points.food = value
                case 7:
                    tamed_stat_points.weight = value
                case 8:
                    tamed_stat_points.damage = value
                case _:
                    print("Error parsing stats file: Found unknown stat!")
        if name_prop_name == "NumberOfMutationsAppliedTamed":
            match index:
                case 0:
                    mutation_stat_points.health = value
                case 1:
                    mutation_stat_points.stamina = value
                case 3:
                    mutation_stat_points.oxygen = value
                case 4:
                    mutation_stat_points.food = value
                case 7:
                    mutation_stat_points.weight = value
                case 8:
                    mutation_stat_points.damage = value
                case _:
                    print("Error parsing stats file: Found unknown stat!")
        if name_prop_name == "BaseCharacterLevel":
            base_level = value
        # print(f"Value: {hex_prop_name}: {name_prop_name}, Property: {name_prop_type}: {value}")
    return base_stat_points, base_level, tamed_stat_points, mutation_stat_points

def int_to_ark_name(hex_as_int: int):
    return ids[hex_as_int] if hex_as_int in ids else "N/A"

def parse_file_header(data: bytes, is_stats_file: bool = False):
    if is_stats_file:
        return data[37:]
    return data[29:]

def parse_uuid(data: bytes):
    return data[:-32]

def skip_zeros(data: bytes, x_times_4: int = 1):
    return data[4 * x_times_4:]

def get_float_or_double(data):
    data, length = read_from(data, "I")
    data, index = read_from(data, "I")
    data = data[1:]# randomly appearing \x00
    if length == 4:
        data, value = read_from(data, "f")
    elif length == 8:
        data, value = read_from(data, "d")
    else:
        print(f"Unknown Float Length {length}")
        data = data[length:]
    return data, value, None

def handle_property(data: bytes, ark_name: str, type_ark_name: str):
    match type_ark_name:
        case "BoolProperty":
            data = skip_zeros(data, 2)
            data, value = read_from(data, "?")
            data = data[1:]
            return data, value, None
        case "ByteProperty":
            data, byte_length = read_from(data, "I")
            data, index = read_from(data, "I")
            data, _, index2 = get_ark_name_from_hex(data) # wrongly removes follwoing 4 bytes (look at notes below with 8 bytes for ark names)
            data = data[1:] # randomly appearing \x00
            if byte_length == 1: # int
                value = int(data[0])
                data = data[1:]
                return data, value, index
            elif byte_length == 8: # ark name
                data, _, value = get_ark_name_from_hex(data) # uses 8 Bytes for Ark Name -> Potential Bug with endianess: 8 Bytes with Big Endian as 64Bit Int would be the same as 4 Bytes with Big Endian as 32Bit Int
                return data, value, None
            else:
                print("Unknown Byte Length!")
                return data[byte_length:], "N/A", None
        case "StrProperty":
            data, offset_from_back = read_from(data, "I")
            data = data[5:] # no clue why there are 5 \x00's
            data, length = read_from(data, "I")
            value = data[:length-1].decode("utf-8") # -1 to remove null termination
            data = data[length:]
            return data, value, None
        case "NameProperty":
            data, length = read_from(data, "I")
            data = data[5:] # randomly appearing \x00 and remove first 4 Bytes of Name (always zero?)
            data, _, value = get_ark_name_from_hex(data) # uses 8 Bytes for Ark Name -> Potential Bug with endianess: 8 Bytes with Big Endian as 64Bit Int would be the same as 4 Bytes with Big Endian as 32Bit Int
            return data, value, None
        case "FloatProperty" | "DoubleProperty":
            return get_float_or_double(data)
        case "IntProperty" | "UInt32Property":
            data, length = read_from(data, "I")
            data, index = read_from(data, "I")
            data = data[1:]# randomly appearing \x00
            data, value = read_from(data, "I")
            return data, value, None
        case "UInt16Property":
            data, length = read_from(data, "I")
            data, index = read_from(data, "I")
            data = data[1:]# randomly appearing \x00
            data, value = read_from(data, "H")
            return data, value, None
        case "StructProperty":
            data, length = read_from(data, "I")
            data = skip_zeros(data)
            data, _, ark_name = get_ark_name_from_hex(data)
            if ark_name == "Vector": # probably 3 times double value following
                data = data[17+length:]
                return data, "Not Implemented", None # return "Not Implemented" (WIP!)
            if ark_name == "Quat": # WIP
                data = data[17+length:]
                return data, "Not Implemented", None # return "Not Implemented" (WIP!)
            if ark_name == "DinoAncestorsEntry": # Complex Part following -> ToDo for later
                data = data[17+length:]
                return data, "Not Implemented", None # return "Not Implemented" (WIP!)
            else:
                print(f"Unknown Struct content {ark_name}")
                data = data[17+length:] # only a guess that other content has the same 17 Bytes Padding
                return data, "Not Implemented", None # return "Not Implemented" (WIP!)
        case "ObjectProperty":
            data, length = read_from(data, "I")
            data = data[5+length:] # skip for now
            return data, "Not Implemented", None # return "Not Implemented" (WIP!)
            # worked for some parts:
            # data = data[11:] # only a guess, might be different for other ObjectProperties
            # data, _, ark_name = get_ark_name_from_hex(data)
            # return data, ark_name
        case "ArrayProperty":
            data, length = read_from(data, "I")
            data = skip_zeros(data)
            data = data[9+length:] # skip everything for now
            return data, "Not Implemented", None # return "Not Implemented" (WIP!)
        case _:
            print(f"Unknown Property {type_ark_name}")
            return data, "Not Implemented", None # return "Not Implemented" (WIP!)

def get_ark_name_from_hex(data: bytes, skip_after: bool = True):
    data, value = read_from(data, "I")
    if skip_after:
        data = skip_zeros(data)
    return data, value, int_to_ark_name(value)

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
    
def is_tamed(data: bytes):
    try:
        is_tamed = data.index(b"\x04\x4C\xEB\x71") is not None
    except ValueError:
        is_tamed = False
    return is_tamed

def get_matching_dinos(name_filter: str):
    from uuid import UUID
    import struct

    cur = con.cursor()
    hex_code_filter = [id for id, name in ids.items() if name == name_filter][0]
    hex_start = struct.pack("<I", hex_code_filter).hex()
    hex_end = struct.pack("<I", hex_code_filter + 16777216).hex()
    res = cur.execute("SELECT key, value FROM game WHERE value >= x'" + str(hex_start) + "' AND value < x'" + str(hex_end) + "'")
    rows = res.fetchall()

    dinos: dict[str, list[Dino]] = {}

    for row in rows:
        info_uuid = UUID(bytes_le=row[0])
        _, tid = read_from(row[1], "I")
        tname = ids[tid]

        if not tname in dinos:
            dinos[tname] = []
        id = get_id(row[1]).hex()
        stats_data, stats_uuid = get_stats_data(id)
        tamed_name = get_tamed_name(row[1])
        if stats_data != b'':
            if is_tamed(row[1]):
                dino_id_1, dino_id_2 = parse_file(row[1])
                base_stat_points, base_level, tamed_stat_points, mutation_stat_points = parse_stats_file(stats_data)
                dinos[tname].append(Dino(info_uuid=info_uuid.hex, stats_uuid=stats_uuid.hex, save_file_id=id, info_raw=row[1], _stats_raw=stats_data, tamed_name=tamed_name, base_stat_points=base_stat_points, tamed_applied_stat_points=tamed_stat_points, mutation_applied_stat_points=mutation_stat_points, dino_id_1=dino_id_1, dino_id_2=dino_id_2, base_level=base_level))
        else:
            # print("No Stats Data found")
            pass
    return dinos

def get_stats_data(id: str):
    import struct
    from uuid import UUID

    hex_start = struct.pack(">I", int(id, 16)).hex()
    hex_end = struct.pack(">I", int(id, 16) + 1).hex()

    cur = con.cursor()
    res = cur.execute(f"SELECT key, value FROM game WHERE value >= x'E97920CD0000000000000000020000000C55428D0000000004425610{str(hex_start)}' AND value < x'E97920CD0000000000000000020000000C55428D0000000004425610{str(hex_end)}'")
    rows = res.fetchall()

    if len(rows) > 0:
        uuid = UUID(bytes_le=rows[0][0])
        return rows[0][1], uuid
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
            dinos[tname].append(Dino(info_uuid=uuid.hex, info_raw=row[1]))
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
