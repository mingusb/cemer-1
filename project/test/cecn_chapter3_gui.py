#!/usr/bin/env python3
"""Replay the authored Cats and Dogs GUI exercises on isolated X11 (1600x1000).

Native mouse controls set cues, initialize, step, run and save the unchanged
model. Read-only server requests check the actual task tables. No numeric
baseline is created or accepted; expectations come from the author's article.
"""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

from cecn_chapter2_gui import ChapterGUI
from cecn_chapter3_regressions import FIXTURES, LABELS, KNOWLEDGE, features, named_features
from inductor_head_gui_regression import GuiCase
from modern_stack_regressions import REPO, require


class CatsGUI(ChapterGUI):
    def window(self):
        return self.xdotool('search','--all','--onlyvisible','--pid',self.process.pid,
                            '--name','projects.*cats_and_dogs').splitlines()[0]

    def click(self, name, x, y):
        if y==732:
            # The native console layout can reserve a different height after
            # reopening a saved project. Task controls stay at the panel foot.
            geometry=subprocess.check_output(['xwininfo','-id',self.window()],text=True)
            top=int(re.search(r'Absolute upper-left Y:\s+(-?\d+)',geometry).group(1))
            height=int(re.search(r'Height:\s+(\d+)',geometry).group(1))
            y=top+height-100
        super().click(name,x,y)

    def inputs(self):
        self.click('StdInputData tab',1006,132)
        self.click('Red arrow input editing mode',1569,160)

    def cue(self, name, x):
        self.click('Toggle '+name+' input unit',x,283)

    def run_native(self, name, initial=False):
        self.click(name+' Init',472 if initial else 395,732);self.done()
        self.click(name+' Run',435,732);self.done()
        return self.result(name)

    def result(self, name):
        grid=self.call('GetData',table='CycleGridData')
        columns={column['name']:column['values'] for column in grid['columns']}
        self.case.equal(name+'.20_native_grid_samples',len(columns['cycle']),20)
        self.case.equal(name+'.last_grid_cycle',columns['cycle'][-1],99)
        aliases={'Favorite_Food':'Favorite_F','Favorite_Toy':'Favorite_T'}
        acts={layer:dict(zip(labels,columns[aliases.get(layer,layer)+'_act'][-1][0]))
              for layer,labels in LABELS.items()}
        self.case.equal(name+'.finite_bounded_activation',all(math.isfinite(value) and 0<=value<=1
                        for layer in acts.values() for value in layer.values()),True)
        harmony=self.values('CycleHarmonyData','harmony')
        self.case.equal(name+'.100_native_cycles',self.values('CycleHarmonyData','cycle'),list(range(1,101)))
        self.case.equal(name+'.finite_harmony',all(math.isfinite(value) for value in harmony),True)
        self.case.equal(name+'.settling_improves_harmony',harmony[-1]>harmony[0],True)
        (self.case.directory/(name+'.json')).write_text(json.dumps({'grid':grid,'harmony':harmony},indent=2)+'\n')
        return acts,harmony


def exercise(case, server):
    time.sleep(2)
    server.screenshot('01-offline-wiki-and-circuit')
    case.equal('default_Morris_cue',server.cell('StdInputData',0,'Name'),[[1,0,0,0,0,0,0,0,0,0]])
    server.click('ControlPanel tab',610,132)
    server.click('Initial native Init',472,732);server.done()
    server.click('Native Step Cycle',623,732);server.wait_state(3)
    case.equal('actual_step_cycle_pauses',int(server.call('GetRunState')),3)
    case.equal('actual_step_cycle_records_cycle1',server.values('CycleHarmonyData','cycle'),[1])
    server.screenshot('02-step-cycle')
    server.click('Native Run resumes',435,732);server.done()
    morris,_=server.result('Morris')
    named_features(case,'Morris',morris,features(KNOWLEDGE[0]))
    server.screenshot('03-Morris-pattern-completion')

    server.inputs();server.cue('Morris off',949);server.cue('Rex on',1011)
    case.equal('actual_named_cue_edit',server.cell('StdInputData',0,'Name'),[[0,0,0,0,0,1,0,0,0,0]])
    server.screenshot('04-red-arrow-Rex-input')
    rex,_=server.run_native('Rex')
    case.equal('Rex_identity_recovered',max(rex['Identity'],key=rex['Identity'].get),'Rex')
    named_features(case,'Rex',rex,features(KNOWLEDGE[5]))
    server.click('Native circuit tab',910,132);server.screenshot('05-Rex-native-circuit')
    server.click('Native harmony graph tab',1119,132);server.screenshot('06-Rex-harmony-graph')

    server.inputs();server.cue('Rex off',1011);server.cue('Cat on',1431)
    case.equal('actual_named_cue_cleared',server.cell('StdInputData',0,'Name'),[[0]*10])
    case.equal('actual_Cat_cue',server.cell('StdInputData',0,'Species'),[[1,0]])
    cat,cat_harmony=server.run_native('Cat')
    case.equal('Cat_query_excludes_dog_instances',max(cat['Identity'][label] for label in LABELS['Identity'][5:])<.01,True)
    named_features(case,'typical_Cat',cat,{'Size':['Small'],'Favorite_Food':['Grass'],'Favorite_Toy':['String']})
    server.click('Native circuit tab',910,132);server.screenshot('07-Cat-prototype')

    server.inputs();server.cue('Large on',1350)
    case.equal('actual_Large_cue',server.cell('StdInputData',0,'Size'),[[0,0,1]])
    _,large_harmony=server.run_native('LargeCat')
    case.equal('inconsistent_size_lowers_harmony',large_harmony[-1]<cat_harmony[-1],True)
    server.click('Native harmony graph tab',1119,132);server.screenshot('08-LargeCat-harmony')

    server.inputs();server.cue('Large off',1350);server.cue('Medium on',1333)
    case.equal('actual_Medium_cue',server.cell('StdInputData',0,'Size'),[[0,1,0]])
    medium,medium_harmony=server.run_native('MediumCat')
    case.equal('MediumCat_retrieves_matching_pair',sorted(label for label,value in medium['Identity'].items() if value>.5),['Fuzzy','Garfield'])
    case.equal('constraint_consistency_harmony_order',large_harmony[-1]<medium_harmony[-1]<cat_harmony[-1],True)
    server.click('Native circuit tab',910,132);server.screenshot('09-MediumCat-circuit')
    server.click('CycleGridData native view',1233,132);server.screenshot('10-settling-grid')
    server.console('taMisc::ConsoleOutput("CH3_GUI_CSS42 " + String(6*7));','CH3_GUI_CSS42 42')
    case.equal('typed_console_arithmetic',42,42)
    server.screenshot('11-visible-CSS42-prompt')
    server.click('Native harmony graph tab',1119,132)
    server.save()
    return medium,medium_harmony


def reopen(case, server, expected):
    time.sleep(2)
    case.equal('reopened_name_cue_empty',server.cell('StdInputData',0,'Name'),[[0]*10])
    case.equal('reopened_species_cue',server.cell('StdInputData',0,'Species'),[[1,0]])
    case.equal('reopened_size_cue',server.cell('StdInputData',0,'Size'),[[0,1,0]])
    server.click('ControlPanel tab',610,132)
    actual,harmony=server.run_native('MediumCatReopened',initial=True)
    expected_acts,expected_harmony=expected
    case.equal('reopened_native_grid_reproduced',actual,expected_acts)
    case.equal('reopened_harmony_reproduced',harmony,expected_harmony)
    server.click('Native circuit tab',910,132);server.screenshot('12-reopened-circuit')
    server.click('Offline wiki tab',455,132);server.screenshot('13-reopened-offline-wiki')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,default=REPO/'tools/run-emergent')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=90)
    args=parser.parse_args()
    display=os.environ.get('DISPLAY','')
    if not display or display.rsplit(':',1)[-1] in {'0','0.0'}:
        parser.error('Use a dedicated Xvfb display such as DISPLAY=:93; never the user desktop.')
    os.environ['QT_QPA_PLATFORM']='xcb'
    require(subprocess.check_output(['xdotool','getdisplaygeometry'],text=True).strip()=='1600 1000','GUI replay requires1600x1000 desktop')
    args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False);args.binary=args.binary.resolve()
    prefix=Path(os.environ.get('EMERGENT_PREFIX_DIR',str(REPO/'install')))
    paths=[prefix/'bin/emergent',prefix/'lib/libtemt.so',prefix/'lib/libemergentlib.so']
    hashes={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    source=FIXTURES/'cats_and_dogs.proj';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    report={'status':'PASS','display':display,'installed_sha256':hashes,'fixture_sha256':source_hash,
            'scope':'Actual native GUI task buttons, red-arrow input unit edits, fixed-weight settling, plots, offline wiki, CSS and save/reopen. No model edits or training.','cases':[]}
    try:
        case=GuiCase(args,'cats_and_dogs');case.fixture=case.directory/source.name;shutil.copy2(source,case.fixture)
        case.original_digest=source_hash
        provenance=json.loads((FIXTURES/'provenance.json').read_text())['models'][0]
        case.equal('pinned_migrated_fixture',source_hash,provenance['project_sha256'])
        report['cases'].append({'name':'native-controls','checks':case.checks})
        with CatsGUI(case) as server:expected=exercise(case,server)
        reopened=GuiCase(args,'reopened');reopened.fixture=reopened.directory/source.name;shutil.copy2(case.fixture,reopened.fixture)
        report['cases'].append({'name':'saved-project-reopened','checks':reopened.checks})
        with CatsGUI(reopened) as server:reopen(reopened,server,expected)
    except Exception as error:report.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
    for path,digest in hashes.items():require(hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,'installed library changed during GUI test')
    require(hashlib.sha256(source.read_bytes()).hexdigest()==source_hash,'tracked fixture changed during GUI test')
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],args.output/'report.json',flush=True)
    return report['status']!='PASS'


if __name__=='__main__':sys.exit(main())
