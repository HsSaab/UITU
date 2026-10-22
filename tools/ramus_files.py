"""Build native Ramus .rsf projects for practical 5 using the report's model data.

The optional writer is MIT-licensed ramus-mcp, pinned below. Its source directory
is passed explicitly; it is used as a local file-format library, without an MCP
server, configuration changes, or any network calls from this builder.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import argparse,hashlib,json,shutil,subprocess,sys
from diagrams import MODELS

ROOT=Path(__file__).resolve().parents[1]
REVISION='a311ca2fcbc5aceb2f56d2b026ff26a6c83a0164'
OUTPUT=ROOT/'diagrams/ramus'
AUTHORS='Тарасов А.М., Дементиевский Д.М., Тыцкий Б.М.'
FILES={'vps':'УИТУ5_Аренда_ВМ_ТехноСервис.rsf',
       'monitoring':'УИТУ5_Мониторинг_ТехноСервис.rsf'}


def boundary(ed,sheet,role,name,targets):
 """One inherited flow with actual junctions for the remaining consumers."""
 first=ed.add_arrow(sheet,{'frame':role},{'activity':targets[0],'role':role},name)
 for target in targets[1:]:
  ed.add_arrow(sheet,{'arrow':first['sector']},{'activity':target,'role':role})


def build_model(model,folder,ModelEditor):
 path=folder/FILES[model['key']]
 ed=ModelEditor.create(str(path),model['name'],model_name=model['service'],
                       author='ИКБО-74-23',project='УИТУ №5. ООО «ТехноСервис»')
 prefs=ed.doc.table('IDEF0/attribute_model_preferences')
 prefs.set(prefs.rows[0],USED_AT=AUTHORS.replace(', ','\n'),
           DEFINITION='Авторы: Тарасов Арсений Максимович; Дементиевский Дмитрий Максимович; Тыцкий Богдан Максимович.')
 top=next(a.element_id for a in ed.snapshot().activities().values() if a.number=='A0')
 context=next(d.parent_id for d in ed.snapshot().diagrams() if d.node=='A-0')
 ed.set_purpose('Описать предоставление услуги «'+model['service']+'» до второго уровня.',
                'Руководитель подразделения ООО «ТехноСервис».')
 ed.style_activity(top,font_size=10,fill='white',color='black')
 stages=[ed.add_activity(top,s['name'])['id'] for s in model['stages']]
 children=[[ed.add_activity(parent,name)['id'] for name in s['steps']]
           for parent,s in zip(stages,model['stages'])]
 # All descendants exist before arrows are added; Ramus can then join the
 # real parent and child endpoints rather than creating inherited placeholders.
 for role,key in [('input','inputs'),('control','controls'),('mechanism','mechanisms')]:
  for name in model[key]:boundary(ed,context,role,name,[top])
 for name in model['outputs']:
  ed.add_arrow(context,{'activity':top},{'frame':'output'},name)

 for i,name in enumerate(model['inputs']):
  target=stages[(2 if model['key']=='vps' else 1) if i==2 else 0]
  boundary(ed,top,'input',name,[target])
 for i,s in enumerate(model['stages'][:-1]):
  ed.add_arrow(top,{'activity':stages[i]},
               {'activity':stages[i+1],'role':'input'},s['outputs'][0])
 for name in model['outputs']:
  ed.add_arrow(top,{'activity':stages[-1]},{'frame':'output'},name)
 for role,key in [('control','controls'),('mechanism','mechanisms')]:
  for j,name in enumerate(model[key]):
   targets=[parent for parent,s in zip(stages,model['stages']) if j in s[key]]
   boundary(ed,top,role,name,targets)

 for parent,s,boxes in zip(stages,model['stages'],children):
  for name in s['inputs']:boundary(ed,parent,'input',name,[boxes[0]])
  for i,name in enumerate(s['flows']):
   ed.add_arrow(parent,{'activity':boxes[i]},
                {'activity':boxes[i+1],'role':'input'},name)
  for name in s['outputs']:
   ed.add_arrow(parent,{'activity':boxes[-1]},{'frame':'output'},name)
  for role,key in [('control','controls'),('mechanism','mechanisms')]:
   for j in s[key]:boundary(ed,parent,role,model[key][j],boxes)
 # The router and label placer retain all branch junctions and cross-level ids.
 # Reposition labels once the complete model is available.
 for sheet in ed.snapshot().diagrams():ed.tidy_sheet(sheet.parent_id,passes=1)
 ed.save()
 return path


def verify(path,model,RsfModel,rules):
 with ZipFile(path) as z:
  assert z.testzip() is None
  assert 'data/IDEF0/attribute_sector_points.xml' in z.namelist()
 rsf=RsfModel(str(path));diagrams={d.node:d for d in rsf.diagrams()}
 assert set(diagrams)=={'A-0','A0','A1','A2','A3','A4'}
 expected={'A-0':[model['name']], 'A0':[s['name'] for s in model['stages']]}
 expected.update({f'A{i+1}':s['steps'] for i,s in enumerate(model['stages'])})
 for node,names in expected.items():
  sheet=diagrams[node]
  assert [a.name for a in sheet.activities]==names,(node,'activity names')
  assert all(a.has_route for a in sheet.arrows),(node,'missing native arrow geometry')
  for a in sheet.arrows:
   for x,y in a.points:assert abs(x)<10000 and abs(y)<10000
  if node=='A-0' or node=='A0':item=model
  else:
   s=model['stages'][int(node[1:])-1]
   item={**s,'controls':[model['controls'][j] for j in s['controls']],
         'mechanisms':[model['mechanisms'][j] for j in s['mechanisms']]}
  for role,key in [('input','inputs'),('control','controls'),('mechanism','mechanisms'),('output','outputs')]:
   labels={a.name for a in sheet.arrows if any(e.kind=='frame' and e.role==role for e in (a.start,a.end))}
   assert labels==set(item[key]),(node,role,labels,item[key])
 findings=rules.check(rsf)
 assert not findings,[(f.sheet,f.rule,f.message) for f in findings]
 return {'file':str((OUTPUT/path.name).relative_to(ROOT)),
         'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'diagrams':[{ 'node':d.node,'parent_id':d.parent_id,
                       'activities':len(d.activities),'arrow_segments':len(d.arrows)}
                      for d in diagrams.values()],
         'activities':len(rsf.activities()),'idef0_checks':rules.summary(findings)}


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--writer-src',type=Path,required=True,
                     help='Checked-out byMERCY/ramus-mcp source directory')
 args=parser.parse_args();writer=args.writer_src.resolve()
 commit=subprocess.check_output(['git','-C',str(writer),'rev-parse','HEAD'],text=True).strip()
 if commit!=REVISION:parser.error(f'Writer revision must be {REVISION}; got {commit}')
 sys.path.insert(0,str(writer/'src'))
 from model_editor import ModelEditor
 from ramus_rsf import RsfModel
 import idef0_rules as rules
 OUTPUT.mkdir(parents=True,exist_ok=True)
 results=[]
 with TemporaryDirectory(prefix='uitu-ramus-') as temporary:
  for model in MODELS:
   print('Building:',model['service'],flush=True)
   path=build_model(model,Path(temporary),ModelEditor)
   result=verify(path,model,RsfModel,rules)
   shutil.copyfile(path,OUTPUT/path.name);results.append(result)
   print(path.name,': 6 diagrams, 17 activities; IDEF0 passed',flush=True)
 evidence={'format':'native Ramus RSF','writer':'https://github.com/byMERCY/ramus-mcp',
           'writer_commit':REVISION,'models':results,'status':'passed'}
 (ROOT/'evidence/ramus-validation.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
