import parse
import os

REX_SAVE_NAME = "/Game/PrimalEarth/Dinos/Rex/Rex_Character_BP.Rex_Character_BP_C"

parse.init("data/TheIsland_WP.ark")
dinos = parse.get_matching_dinos(name_filter=REX_SAVE_NAME)
os.makedirs('output', exist_ok=True)
with open("output/server_info.json", "w+") as f:
    f.write(parse.ServerInfo(dinos=dinos).model_dump_json(indent=4))
