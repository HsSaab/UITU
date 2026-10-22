"""Independently open and render the delivered RSF files using Ramus itself.

Supply the official Ramus Next 3.1.1 application jar (the desktop fat jar also
contains its headless MCP entry point). No desktop window or installed MCP
configuration is needed. The Java process runs read-only on a temporary copy.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse,base64,hashlib,json,queue,shutil,subprocess,threading
from diagrams import MODELS

ROOT=Path(__file__).resolve().parents[1]

class Engine:
 def __init__(self,jar,path,home,log):
  self.process=subprocess.Popen(['java','-Djava.awt.headless=true','-Dfile.encoding=UTF-8',
    '-Dstdout.encoding=UTF-8','-Duser.language=ru','-Duser.country=RU',f'-Duser.home={home}', '-cp',str(jar),
    'com.ramussoft.mcp.RamusMcpServer',str(path),'--read-only'],
    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log)
  self.queue=queue.Queue();self.serial=0;self.log=log
  def read():
   for line in self.process.stdout:
    try:self.queue.put(json.loads(line))
    except (ValueError,UnicodeError):pass
   self.queue.put(None)
  threading.Thread(target=read,daemon=True).start()
 def send(self,method,params=None,reply=True):
  self.serial+=1;msg={'jsonrpc':'2.0','method':method}
  if reply:msg['id']=self.serial
  if params is not None:msg['params']=params
  self.process.stdin.write((json.dumps(msg,ensure_ascii=False)+'\n').encode());self.process.stdin.flush()
  if not reply:return
  while True:
   try:answer=self.queue.get(timeout=45)
   except queue.Empty:raise RuntimeError('Ramus did not answer within 45 seconds')
   if answer is None:
    self.log.flush();self.log.seek(0)
    raise RuntimeError('Ramus exited: '+self.log.read().decode(errors='replace')[-4000:])
   if answer.get('id')==self.serial:
    if 'error' in answer:raise RuntimeError(answer['error'])
    return answer['result']
 def call(self,name,args):
  result=self.send('tools/call',{'name':name,'arguments':args})
  if result.get('isError'):raise RuntimeError(result)
  return result
 def close(self):
  try:
   self.process.stdin.close();self.process.wait(timeout=5)
  except (BrokenPipeError,subprocess.TimeoutExpired):
   self.process.kill();self.process.wait()


def decoded(result):
 return json.loads('\n'.join(c['text'] for c in result['content'] if c['type']=='text'))


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--engine-jar',type=Path,required=True)
 args=parser.parse_args();jar=args.engine_jar.resolve()
 evidence_path=ROOT/'evidence/ramus-validation.json'
 evidence=json.loads(evidence_path.read_text())
 for model in evidence['models']:
  path=ROOT/model['file'];key='vps' if 'Аренда' in path.name else 'monitoring'
  source=next(m for m in MODELS if m['key']==key)
  assert hashlib.sha256(path.read_bytes()).hexdigest()==model['sha256']
  print('Opening in Ramus:',path.name,flush=True)
  with TemporaryDirectory(prefix='uitu-ramus-engine-') as folder:
   tmp=Path(folder);copy=tmp/path.name;shutil.copyfile(path,copy)
   (tmp/'home').mkdir()
   with (tmp/'engine.log').open('w+b') as log:
    engine=Engine(jar,copy,tmp/'home',log)
    try:
     init=engine.send('initialize',{'protocolVersion':'2024-11-05','capabilities':{},
                                  'clientInfo':{'name':'uitu-rsf-validation','version':'1'}})
     engine.send('notifications/initialized',reply=False)
     tree=decoded(engine.call('get_function_tree',{'depth':4}))
     root=tree['tree'];assert root['code']=='A0' and root['name']==source['name']
     assert len(root['children'])==4
     assert sum(1+len(a['children']) for a in root['children'])+1==17
     checked=[]
     expected={'A-0':[source['name']],'A0':[s['name'] for s in source['stages']]}
     expected.update({f'A{i+1}':s['steps'] for i,s in enumerate(source['stages'])})
     for sheet in model['diagrams']:
      node=sheet['node'];identifier=sheet['parent_id']
      result=decoded(engine.call('get_diagram',{'activity':identifier,'include_geometry':True}))
      assert [a['name'] for a in result['children']]==expected[node]
      assert len(result['arrows_drawn'])==sheet['arrow_segments'],(node,'native arrow count mismatch')
      for child in result['children']:
       assert child['arrows'].get('control') and child['arrows'].get('output'),(node,child)
      image=engine.call('render_diagram',{'activity':identifier})
      picture=next(c for c in image['content'] if c['type']=='image')
      data=base64.b64decode(picture['data']);assert data.startswith(b'\x89PNG\r\n\x1a\n')
      target=ROOT/'diagrams/ramus/previews'/f'{key}_{node.replace("-","minus")}.png'
      target.parent.mkdir(exist_ok=True);target.write_bytes(data)
      checked.append({'node':node,'activities':len(result['children']),
                      'arrow_segments':len(result['arrows_drawn']),
                      'rendered':str(target.relative_to(ROOT)),
                      'render_sha256':hashlib.sha256(data).hexdigest()})
      print('  '+node+': read and rendered by Ramus',flush=True)
     model['native_engine']={'server':init['serverInfo'],'tree':root,'diagrams':checked,'status':'passed'}
    finally:engine.close()
  assert hashlib.sha256(path.read_bytes()).hexdigest()==model['sha256']
 evidence['engine_jar_sha256']=hashlib.sha256(jar.read_bytes()).hexdigest()
 evidence['native_engine_status']='passed'
 evidence_path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
 print('Both native RSF projects opened; all 12 diagrams read and rendered by Ramus.')

if __name__=='__main__':main()
