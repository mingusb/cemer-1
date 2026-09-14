#!/usr/bin/env python3
"""Test the authored Cats and Dogs memory and constraint-satisfaction exercises.

Expectations come from the knowledge table and questions in the cached CCNBook
article, not recorded numeric baselines. The fixed circuit is never trained.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import traceback

from modern_stack_regressions import Case, Server, REPO, require

FIXTURES = REPO/'demo/LegacyModels/cecn/chapter_3'
LABELS = {
    'Name':['Morris','Socks','Sylvester','Garfield','Fuzzy','Rex','Fido','Spot','Snoopy','Butch'],
    'Identity':['Morris','Socks','Sylvester','Garfield','Fuzzy','Rex','Fido','Spot','Snoopy','Butch'],
    'Color':['Black','White','Brown','Orange'],
    'Favorite_Food':['Bugs','Grass','Scraps','Shoe'],
    'Size':['Small','Medium','Large'],
    'Favorite_Toy':['String','Feather','Bone','Shoe'],
    'Species':['Cat','Dog'],
}
# Species, color(s), size, food, toy: the author's complete knowledge table.
KNOWLEDGE = [
    ('Cat',['Orange'],'Small','Grass','String'),
    ('Cat',['Black','White'],'Small','Bugs','Feather'),
    ('Cat',['Black','White'],'Small','Grass','String'),
    ('Cat',['Orange'],'Medium','Scraps','String'),
    ('Cat',['White'],'Medium','Grass','Feather'),
    ('Dog',['Black'],'Large','Scraps','Bone'),
    ('Dog',['Brown'],'Medium','Shoe','Shoe'),
    ('Dog',['Black','White'],'Medium','Scraps','Bone'),
    ('Dog',['Black','White'],'Medium','Scraps','Bone'),
    ('Dog',['Brown'],'Large','Shoe','Shoe'),
]


def features(row):
    species,colors,size,food,toy=row
    return {'Species':[species],'Color':colors,'Size':[size],
            'Favorite_Food':[food],'Favorite_Toy':[toy]}


def weights(server, name):
    target=server.case.directory/(name+'.wts')
    server.console('.projects[0].networks[0].SaveWeights('+json.dumps(str(target))+'); cout << "CATS_WEIGHTS_'+name+'" << endl;','CATS_WEIGHTS_'+name)
    result={}
    for layer,body in re.findall(r'<Lay ([^>]+)>(.*?)</Lay>',target.read_text(),re.S):
        for index,unit in re.findall(r'<UgUn (\d+) [^>]*>(.*?)</UgUn>',body,re.S):
            for sender,group in re.findall(r'<Cg \d+ Fm:([^>]+)>(.*?)</Cg>',unit,re.S):
                for source,value in re.findall(r'^(\d+) ([\d.eE+-]+)$',group,re.M):
                    key=(layer,int(index),sender,int(source))
                    require(key not in result,'duplicate native connection')
                    result[key]=float(value)
    require(result,'native weights missing')
    return result


def expected_weights():
    result={}
    for identity,row in enumerate(KNOWLEDGE):
        result[('Name',identity,'Identity',identity)]=1.0
        result[('Identity',identity,'Name',identity)]=1.0
        for layer,active in features(row).items():
            for index,label in enumerate(LABELS[layer]):
                # The author's fixed weights split the black-and-white color
                # association equally; each feature category totals one.
                value=float(label in active)/len(active)
                result[(layer,index,'Identity',identity)]=value
                result[('Identity',identity,layer,index)]=value
    return result


def stimulus(case, server, name, cues):
    code='DataTable* cats_data=.projects[0].data.Leaf(0); Program* cats_program=.projects[0].programs.Leaf(0); for(int ci=1;ci<8;ci++) cats_data->InitVals(0,ci);'
    for layer,label in cues.items():
        code+=' cats_data->GetValAsMatrix('+json.dumps(layer)+',0)->SetFmVar(1,'+str(LABELS[layer].index(label))+',0);'
    code+=' cats_program->Init(); cout << "CATS_INIT_'+name+'" << endl;'
    server.console(code,'CATS_INIT_'+name)
    server.run('LeabraEpoch')
    code='for(int ci=0;ci<.projects[0].networks[0].layers.leaves;ci++) { Layer* l=.projects[0].networks[0].layers.Leaf(ci); for(int ui=0;ui<l->n_units;ui++) cout << "ACT_'+name+' " << l->name << " " << ui << " " << l->GetUnitNameIdx(ui) << " " << l->GetUnitIdx(ui)->act << endl; } cout << "CATS_ACT_'+name+'" << endl;'
    text=server.console(code,'CATS_ACT_'+name)
    acts={}
    for layer,index,label,value in re.findall(r'^ACT_'+name+r' (\S+) (\d+) (.*?) (\S+)$',text,re.M):
        acts.setdefault(layer,{})[label]=float(value)
    case.equal(name+'.layer_labels',{k:list(v) for k,v in acts.items()},LABELS)
    case.equal(name+'.finite_bounded_activations',all(math.isfinite(v) and 0<=v<=1 for layer in acts.values() for v in layer.values()),True)
    harmony=server.call('GetData',table='CycleHarmonyData',row_from=0)
    columns={column['name']:column['values'] for column in harmony['columns']}
    case.equal(name+'.100_native_cycles',columns['cycle'],list(range(1,101)))
    case.equal(name+'.finite_harmony',all(math.isfinite(v) for v in columns['harmony']),True)
    case.equal(name+'.settling_improves_harmony',columns['harmony'][-1]>columns['harmony'][0],True)
    (case.directory/(name+'.json')).write_text(json.dumps({'cues':cues,'activations':acts,'harmony':harmony},indent=2)+'\n')
    return acts,columns['harmony']


def named_features(case, name, acts, expected):
    for layer,labels in expected.items():
        matching=[acts[layer][label] for label in labels]
        nonmatching=[value for label,value in acts[layer].items() if label not in labels]
        case.equal(name+'.'+layer+'_matches_author_table',min(matching)>max(nonmatching),True)
        case.equal(name+'.'+layer+'_retrieved',min(matching)>.1,True)


def run(case, provenance):
    source=FIXTURES/'cats_and_dogs.proj'
    case.equal('fixture_hash',hashlib.sha256(source.read_bytes()).hexdigest(),provenance['project_sha256'])
    case.fixture=case.directory/source.name;shutil.copy2(source,case.fixture)
    with Server(case) as server:
        for index,name in enumerate(LABELS['Name']):
            acts,_=stimulus(case,server,name,{'Name':name})
            case.equal(name+'.identity_retrieved',max(acts['Identity'],key=acts['Identity'].get),name)
            named_features(case,name,acts,features(KNOWLEDGE[index]))
        original_weights=weights(server,'named')
        case.equal('fixed_connections_match_all_author_knowledge',original_weights==expected_weights(),True)
        case.equal('native_connection_count',len(original_weights),360)
        categories={}
        for species in ['Cat','Dog']:
            acts,harmony=stimulus(case,server,species,{'Species':species});categories[species]=(acts,harmony)
            members=[name for name,row in zip(LABELS['Name'],KNOWLEDGE) if row[0]==species]
            case.equal(species+'.category_retrieves_matching_instances',max(acts['Identity'],key=acts['Identity'].get) in members,True)
            case.equal(species+'.other_species_instances_inactive',max(v for n,v in acts['Identity'].items() if n not in members)<.01,True)
            case.equal(species+'.harmony_monotonic',all(b>=a-1e-6 for a,b in zip(harmony,harmony[1:])),True)
        named_features(case,'typical_Cat',categories['Cat'][0],{'Size':['Small'],'Favorite_Food':['Grass'],'Favorite_Toy':['String']})
        named_features(case,'typical_Dog',categories['Dog'][0],{'Size':['Medium'],'Favorite_Food':['Scraps'],'Favorite_Toy':['Bone']})
        _,large=stimulus(case,server,'LargeCat',{'Species':'Cat','Size':'Large'})
        medium_acts,medium=stimulus(case,server,'MediumCat',{'Species':'Cat','Size':'Medium'})
        case.equal('inconsistent_size_lowers_harmony',large[-1]<categories['Cat'][1][-1],True)
        case.equal('medium_cat_is_more_consistent_than_large_cat',large[-1]<medium[-1]<categories['Cat'][1][-1],True)
        case.equal('medium_cat_retrieves_both_matching_instances',{n for n,v in medium_acts['Identity'].items() if v>.5},{'Garfield','Fuzzy'})
        case.equal('queries_do_not_train_or_change_weights',weights(server,'queried')==original_weights,True)
        saved=case.directory/'cats_and_dogs-saved.proj'
        server.console('.projects[0].SaveCopy('+json.dumps(str(saved))+'); cout << "CATS_SAVED" << endl;','CATS_SAVED')
    reopened=Case(case.args,'cats-and-dogs-reopened');reopened.fixture=saved
    with Server(reopened) as server:
        case.equal('saved_species_cue',server.cell('StdInputData',0,'Species'),[[1,0]])
        case.equal('saved_size_cue',server.cell('StdInputData',0,'Size'),[[0,1,0]])
        acts,harmony=stimulus(reopened,server,'MediumCatReopened',{'Species':'Cat','Size':'Medium'})
        case.equal('saved_activations_reproduced',all(math.isclose(v,medium_acts[layer][label],rel_tol=1e-6,abs_tol=1e-6) for layer,values in acts.items() for label,v in values.items()),True)
        case.equal('saved_harmony_reproduced',harmony,medium)
        case.equal('saved_fixed_weights_preserved',weights(server,'reopened')==original_weights,True)
    case.checks.extend(reopened.checks)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,default=REPO/'tools/run-emergent')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--timeout',type=float,default=90)
    args=parser.parse_args();args.binary=args.binary.resolve()
    args.output=args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='cecn-ch3-'))
    args.output.mkdir(parents=True,exist_ok=True);require(not any(args.output.iterdir()),'output must be empty')
    provenance=json.loads((FIXTURES/'provenance.json').read_text())['models'][0]
    case=Case(args,'cats-and-dogs');report={'status':'PASS','checks':case.checks,'scope':'Authored fixed-weight pattern completion, category queries and harmony exercises; no learning or captured numeric baselines.'}
    prefix=Path(os.environ.get('EMERGENT_PREFIX_DIR',str(REPO/'install')))
    runtime=[prefix/'bin/emergent',prefix/'lib/libtemt.so',prefix/'lib/libemergentlib.so']
    hashes={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest() for path in runtime}
    report['runtime_sha256']=hashes
    try:run(case,provenance)
    except Exception as error:report.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest for path,digest in hashes.items()):
        report.update(status='FAIL',error='runtime library changed during regression')
    (args.output/'report.json').write_text(json.dumps(report,indent=2,default=lambda x:sorted(x))+'\n')
    print(report['status'],args.output/'report.json',flush=True)
    return report['status']!='PASS'


if __name__=='__main__':raise SystemExit(main())
