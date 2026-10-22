"""Build the packaged Mixup input choices from real piece geometry."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from cube.articulated import MIXUP_MODELS
from cube.mixup_entry import MixupEntryDraft
from cube.mixup_assembly import assemblies,geometry_signature,CATALOG_VERSION


def build():
    data={'version':CATALOG_VERSION,'models':{}}
    for kind in MIXUP_MODELS:
        draft=MixupEntryDraft(kind);regions={};seen=set()
        for index,block in enumerate(draft.blocks):
            positions=draft.linked_positions(index)
            if block['role']=='corner' or positions in seen:continue
            seen.add(positions)
            options=assemblies(kind,draft.blocks,positions,seconds=30.,use_bundled=False)
            regions[','.join(map(str,positions))]=[{'key':option.key,'group':option.group_key,'pieces':[
                {'role':piece.role,'panels':piece.panels,'mask':piece.mask,'body':piece.body,'direction':piece.direction}
                for piece in option.pieces]} for option in options]
        data['models'][kind]={'geometry':geometry_signature(kind),'regions':regions}
        print(kind,len(regions),'positions',sum(map(len,regions.values())),'assemblies',flush=True)
    target=ROOT/'assets'/'mixup_assemblies.json'
    target.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    print(target, target.stat().st_size,'bytes',flush=True)


if __name__=='__main__':build()
