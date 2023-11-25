import parse

REX_SAVE_NAME = "/Game/PrimalEarth/Dinos/Rex/Rex_Character_BP.Rex_Character_BP_C"
REX_STATS_NAME = "/Game/PrimalEarth/CoreBlueprints/DinoCharacterStatusComponent_BP_Rex.DinoCharacterStatusComponent_BP_Rex_C"

dinos = parse.get_matching_dinos(name_filter=REX_SAVE_NAME)
dinos = {
    REX_SAVE_NAME: [dino2 for dino2 in dinos[REX_SAVE_NAME] if dino2.stats_raw != b'']
}
for dino in dinos[REX_SAVE_NAME]:
    print(dino)