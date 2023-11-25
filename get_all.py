import parse
import pydantic
import os

REX_SAVE_NAME = "/Game/PrimalEarth/Dinos/Rex/Rex_Character_BP.Rex_Character_BP_C"
REX_STATS_NAME = "/Game/PrimalEarth/CoreBlueprints/DinoCharacterStatusComponent_BP_Rex.DinoCharacterStatusComponent_BP_Rex_C"

dinos = parse.get_matching_dinos(name_filter=REX_SAVE_NAME)
dinos = {
    REX_SAVE_NAME: [dino2 for dino2 in dinos[REX_SAVE_NAME] if dino2.stats_raw != b'']
}
os.makedirs('output', exist_ok=True)
with open("output/dinos.json", "w+") as f:
    f.write("{\n\t\"" + REX_SAVE_NAME + "\": [\n\t\t")
    i = 0
    for dino in dinos[REX_SAVE_NAME]:
        i += 1
        f.write(dino.model_dump_json(exclude=("info_raw", "stats_raw")))
        if i < len(dinos[REX_SAVE_NAME]):
            f.write(",\n\t\t")
        else:
            f.write("\n\t")
    f.write("]\n}")
# for dino in dinos[REX_SAVE_NAME]:
#     print(dino)