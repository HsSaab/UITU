from pathlib import Path
from playwright.sync_api import sync_playwright
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 c=b.new_context(device_scale_factor=2)
 for svg in sorted((ROOT/'diagrams').glob('*.svg')):
  r=ET.parse(svg).getroot();w=int(r.attrib['width']);h=int(r.attrib['height'])
  page=c.new_page();page.set_viewport_size({'width':w,'height':h});page.set_content(svg.read_text())
  outside=page.locator('svg text').evaluate_all('(nodes, size)=>nodes.map(e=>({text:e.textContent,r:e.getBBox()})).filter(e=>e.r.x<0||e.r.y<0||e.r.x+e.r.width>size.w||e.r.y+e.r.height>size.h).map(e=>e.text)', {'w':w,'h':h})
  assert not outside,(svg.name,outside)
  page.locator('svg').screenshot(path=str(ROOT/'diagrams/png'/(svg.stem+'.png')),scale='device');page.close()
 b.close()
print('Rendered and checked',len(list((ROOT/'diagrams').glob('*.svg'))),'diagrams at 2x resolution.')
