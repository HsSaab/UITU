"""Validate delivered artifacts against the rendered documents and live evidence."""
from pathlib import Path
import re,json,hashlib
from zipfile import ZipFile
from docx import Document
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from lxml import etree
import fitz
from PIL import Image
from finalize_reports import NORM
ROOT=Path(__file__).resolve().parents[1]
NAMES=['Тарасов Арсений Максимович','Дементиевский Дмитрий Максимович','Тыцкий Богдан Максимович']

FIGURE_CAPTION=re.compile(r'^Рисунок (\d+)\.(\d+) — \S')
FORBIDDEN=re.compile(r'[\u2013\u2014\[\]]')


def paragraph_value(paragraph, name, default=None):
 value=getattr(paragraph.paragraph_format,name)
 if value is not None:return value
 style=paragraph.style
 while style is not None:
  value=getattr(style.paragraph_format,name)
  if value is not None:return value
  style=style.base_style
 return default


def centered_without_indent(paragraph, context):
 assert paragraph_value(paragraph,'alignment')==WD_ALIGN_PARAGRAPH.CENTER,context
 for name in ['first_line_indent','left_indent','right_indent']:
  value=paragraph_value(paragraph,name,0)
  assert abs(value)<10,(context,name,value)


def empty_paragraph(paragraph):
 return not paragraph.text.strip() and not paragraph._p.xpath('.//w:drawing')


def has_black_outline(page, rectangle):
 """Match a thin vector rectangle or the four strokes of its outline."""
 edges=set()
 for drawing in page.get_drawings():
  color=drawing.get('color')
  if color is None or any(abs(component)>.01 for component in color):continue
  if not .05<=drawing.get('width',0)<=.5:continue
  if drawing.get('fill') is not None:continue
  bounds=fitz.Rect(drawing['rect'])
  if max(abs(a-b) for a,b in zip(bounds,rectangle))<=1:
   return True
  if bounds.height<=1 and bounds.x0<=rectangle.x0+1 and bounds.x1>=rectangle.x1-1:
   if abs(bounds.y0-rectangle.y0)<=1:edges.add('top')
   if abs(bounds.y0-rectangle.y1)<=1:edges.add('bottom')
  if bounds.width<=1 and bounds.y0<=rectangle.y0+1 and bounds.y1>=rectangle.y1-1:
   if abs(bounds.x0-rectangle.x0)<=1:edges.add('left')
   if abs(bounds.x0-rectangle.x1)<=1:edges.add('right')
 return len(edges)==4


results=[]
for number in [4,5,6]:
 path=ROOT/'reports'/f'УИТУ_Практическая_{number}_ТехноСервис.docx'
 with ZipFile(path) as z:assert z.testzip() is None
 doc=Document(path);pdf=fitz.open(path.with_suffix('.pdf'))
 text='\n'.join(p.text for p in doc.paragraphs)
 xml_text=''.join(doc._element.xpath('.//w:t/text()'))
 figure_paragraphs=[p for p in doc.paragraphs if p.text.startswith('Рисунок ')]
 figure_elements={p._p for p in figure_paragraphs}
 for paragraph in doc._element.xpath('.//w:p'):
  visible=''.join(paragraph.xpath('.//w:t/text()'))
  if paragraph in figure_elements and FIGURE_CAPTION.match(visible):
   visible=visible.replace(' — ',' - ',1)
  assert not FORBIDDEN.search(visible),(path.name,'forbidden punctuation in DOCX',visible)
 assert not re.search(r'PAGE_COUNT|FIGURE_COUNT|TABLE_COUNT|SOURCE_COUNT|Содержание обновляется',text)
 assert all(n in xml_text for n in NAMES)
 assert 'ИКБО-74-23' in xml_text and 'Демидов Н.А.' in xml_text
 assert 'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ' not in xml_text
 for title in ['ЦЕЛЬ ПРАКТИЧЕСКОЙ РАБОТЫ','ВЫПОЛНЕНИЕ РАБОТЫ','Вывод по работе']:
  assert any(p.text==title and p.style.name=='Heading 1' for p in doc.paragraphs)
 sec=doc.sections[0]
 for attr,value in [('page_width',21),('page_height',29.7),('left_margin',3),('right_margin',1.5),('top_margin',2),('bottom_margin',2)]:
  assert abs(getattr(sec,attr).cm-value)<.01,(path.name,attr)
 assert sec.different_first_page_header_footer
 normal=doc.styles['Normal'];assert normal.font.name=='Times New Roman' and normal.font.size.pt==14
 assert normal.paragraph_format.line_spacing==1.5
 assert abs(normal.paragraph_format.first_line_indent.cm-1.25)<.01
 figures=[p.text for p in figure_paragraphs]
 assert doc.styles['Caption'].font.italic is True
 assert doc.styles['Caption'].font.name=='Times New Roman'
 assert doc.styles['Caption'].font.size.pt==14
 for caption in figure_paragraphs:
  assert caption.style.name=='Caption'
  centered_without_indent(caption,(path.name,'figure caption'))
  assert all(run.italic is not False for run in caption.runs)
  assert all(run.font.size is None or run.font.size.pt==14 for run in caption.runs)
  assert all(run.font.name is None or run.font.name=='Times New Roman' for run in caption.runs)
 tables=[p.text for p in doc.paragraphs if p.text.startswith('Таблица ')]
 section=None;section_counts={};table_numbers=[];figure_counts={};figure_numbers=[]
 paragraphs=doc.paragraphs;figure_dimensions={}
 for index,paragraph in enumerate(paragraphs):
  if paragraph.style.name in ['Heading 1','Heading 2','Heading 3']:
   match=re.match(r'^(\d+)(?:\.|\s)',paragraph.text)
   if match:section=int(match.group(1))
  if paragraph.text.startswith('Таблица '):
   match=re.match(r'^Таблица (\d+)\.(\d+) - ',paragraph.text)
   assert match,(path.name,'table must use section.table numbering',paragraph.text)
   assert int(match.group(1))==section,(path.name,'wrong table section',paragraph.text)
   section_counts[section]=section_counts.get(section,0)+1
   assert int(match.group(2))==section_counts[section]
   table_numbers.append('.'.join(match.groups()))
  if paragraph.text.startswith('Рисунок '):
   match=FIGURE_CAPTION.match(paragraph.text)
   assert match,(path.name,'figure must use section.figure numbering and em dash',paragraph.text)
   assert int(match.group(1))==section,(path.name,'wrong figure section',paragraph.text)
   figure_counts[section]=figure_counts.get(section,0)+1
   assert int(match.group(2))==figure_counts[section],(path.name,'wrong figure ordinal',paragraph.text)
   label='.'.join(match.groups());figure_numbers.append(label)
   assert index>=3 and index+1<len(paragraphs)
   reference,blank_before,picture=paragraphs[index-3:index]
   blank_after=paragraphs[index+1]
   assert re.search(r'на рисунке '+re.escape(label)+r'\.',reference.text),(path.name,'reference must precede figure',label)
   assert empty_paragraph(blank_before) and blank_before.style.name=='Normal',(path.name,'blank line before figure',label)
   assert empty_paragraph(blank_after) and blank_after.style.name=='Normal',(path.name,'blank line after caption',label)
   assert picture.text=='', (path.name,'picture paragraph has text',label)
   assert len(picture._p.xpath('.//w:drawing'))==1,(path.name,'picture missing',label)
   centered_without_indent(picture,(path.name,'figure',label))
   outline=picture._p.xpath('.//pic:spPr/a:ln')
   assert len(outline)==1 and outline[0].get('w')=='3175',(path.name,'0.25 pt picture outline',label)
   color=outline[0].find(qn('a:solidFill')+'/'+qn('a:srgbClr'))
   assert color is not None and color.get('val')=='000000',(path.name,'black picture outline',label)
   assert outline[0].find(qn('a:noFill')) is None
   inline=picture._p.xpath('.//wp:inline')
   assert len(inline)==1
   assert all(inline[0].get('dist'+side)=='0' for side in ['T','B','L','R']),(path.name,'picture wrap distances must be zero',label)
   effect=inline[0].xpath('./wp:effectExtent')
   assert len(effect)==1 and all(effect[0].get(side)=='0' for side in ['l','t','r','b']),(path.name,'picture effect extents must be zero',label)
   extent=picture._p.xpath('.//wp:inline/wp:extent')
   assert len(extent)==1
   figure_dimensions[label]=(int(extent[0].get('cx'))/12700,int(extent[0].get('cy'))/12700)
   if index+2<len(paragraphs):
    assert not empty_paragraph(paragraphs[index+2]),(path.name,'more than one blank line after caption',label)
 sources=[p for p in doc.paragraphs if p.style.name=='Bibliography']
 assert not sources
 assert len(figures)+1==len(doc.inline_shapes)
 assert doc.inline_shapes[0]._inline.docPr.get('descr')=='Эмблема РТУ МИРЭА'
 for label in table_numbers:
  assert f'в таблице {label}.' in text
  assert any(page.search_for('Таблица '+label+' -') for page in pdf),(path.name,label)
 # Check actual PDF captions and the adjacent raster illustration plus border.
 center=(sec.page_width.pt+sec.left_margin.pt-sec.right_margin.pt)/2
 for caption,label in zip(figures,figure_numbers):
  target=NORM(caption);found=False
  for page in pdf:
   lines=[line for block in page.get_text('dict')['blocks'] if block['type']==0 for line in block['lines']]
   for start,line in enumerate(lines):
    first=''.join(span['text'] for span in line['spans'])
    if not first.startswith(f'Рисунок {label} — '):continue
    for count in range(1,5):
     selected=lines[start:start+count]
     spans=[span for item in selected for span in item['spans'] if span['text'].strip()]
     if NORM(''.join(span['text'] for span in spans))==target:
      assert all(span['flags'] & 2 for span in spans),(path.name,'nonitalic PDF caption',caption)
      assert all(abs(span['size']-14)<.15 for span in spans),(path.name,'PDF caption must be 14 pt',caption)
      for item in selected:
       bounds=fitz.Rect(item['bbox'])
       assert abs((bounds.x0+bounds.x1)/2-center)<3,(path.name,'PDF caption off center',caption)
      caption_top=min(span['bbox'][1] for span in spans)
      images=[image for image in page.get_image_info() if image['bbox'][3]<=caption_top+1]
      assert images,(path.name,'figure and caption split across pages',label)
      image=max(images,key=lambda image:image['bbox'][3]);bounds=fitz.Rect(image['bbox'])
      assert abs((bounds.x0+bounds.x1)/2-center)<1,(path.name,'PDF figure off center',label)
      width,height=figure_dimensions[label]
      assert abs(bounds.width-width)<.75 and abs(bounds.height-height)<.75,(path.name,'wrong PDF figure dimensions',label)
      assert has_black_outline(page,bounds),(path.name,'PDF picture outline missing',label)
      reference=page.search_for(f'на рисунке {label}.')
      assert reference and any(rect.y1<bounds.y0 for rect in reference),(path.name,'PDF reference not above figure',label)
      found=True;break
   if found:break
  assert found,(path.name,'caption not found in PDF',caption)
 headings=[p for p in doc.paragraphs if p.style.name in ['Heading 1','Heading 2','Heading 3']]
 cached=doc._element.body.xpath('./w:sdt[w:sdtPr/w:tag[@w:val="UITU_TOC"]]/w:sdtContent/w:p')
 assert len(headings)==len(cached)
 assert any('TOC ' in (x.text or '') for x in doc._element.body.xpath('.//w:instrText'))
 from finalize_reports import get_pages
 _,pages=get_pages(path.with_suffix('.pdf'),[(p.text,1) for p in headings])
 for p,entry in zip(headings,cached):
  links=entry.xpath('./w:hyperlink');assert len(links)==1
  link=links[0]
  title=link.xpath('./w:r/w:t')[0].text
  number_text=link.xpath('./w:r/w:t')[-1].text
  assert title==p.text and int(number_text)==pages[p.text]
  assert link.xpath('./w:r/w:tab') and not entry.xpath('./w:r/w:t')
  anchor=link.get(qn('w:anchor'))
  starts=p._p.xpath('./w:bookmarkStart');ends=p._p.xpath('./w:bookmarkEnd')
  assert any(s.get(qn('w:name'))==anchor and any(e.get(qn('w:id'))==s.get(qn('w:id')) for e in ends) for s in starts)
 # Check the actual PDF link hit areas, including page numbers and leaders.
 toc_start=next(i for i,page in enumerate(pdf) if any(line.strip()=='СОДЕРЖАНИЕ' for line in page.get_text().splitlines()))
 toc_end=pages['ЦЕЛЬ ПРАКТИЧЕСКОЙ РАБОТЫ']-1
 toc_lines=[]
 for page_index in range(toc_start,toc_end):
  for block in pdf[page_index].get_text('rawdict')['blocks']:
   if block['type']!=0:continue
   for line in block['lines']:
    chars=[c for span in line['spans'] for c in span['chars']]
    toc_lines.append((page_index,chars,''.join(c['c'] for c in chars)))
 from finalize_reports import NORM
 for heading in headings:
  matches=[row for row in toc_lines if NORM(row[2]).startswith(NORM(heading.text))]
  assert len(matches)==1,(path.name,heading.text,'TOC row not found')
  page_index,chars,line=matches[0]
  digits=re.search(r'(\d+)\s*$',line);assert digits
  assert int(digits.group(1))==pages[heading.text]
  dots=list(re.finditer(r'\.{3,}',line));assert dots
  indices=[0,digits.start(),(dots[-1].start()+dots[-1].end())//2]
  for index in indices:
   rect=fitz.Rect(chars[index]['bbox']);point=(rect.tl+rect.br)/2
   active=[l for l in pdf[page_index].get_links() if l['kind']==fitz.LINK_GOTO and point in l['from']]
   assert active and all(l['page']==pages[heading.text]-1 for l in active),(path.name,heading.text,'nonclickable or incorrect TOC target',index)
 for i,page in enumerate(pdf):
  assert 'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ' not in page.get_text()
  for line in page.get_text().splitlines():
   allowed=re.sub(r'^(\s*Рисунок \d+\.\d+) — ',r'\1 - ',line)
   assert not FORBIDDEN.search(allowed),(path.name,i+1,'forbidden punctuation in PDF',line)
  assert len(page.get_text().strip())>220,(path.name,'unexpected short page',i+1)
  bottom=page.get_text(clip=fitz.Rect(0,795,page.rect.width,page.rect.height)).strip()
  assert bottom==('' if i==0 else str(i+1)),(path.name,i+1,bottom)
  for block in page.get_text('dict')['blocks']:
   if block['type']==0:
    x0,y0,x1,y1=block['bbox'];assert x0>=25 and x1<=page.rect.width-20 and y0>=20 and y1<=page.rect.height-10
 hashes={suffix:hashlib.sha256(path.with_suffix(suffix).read_bytes()).hexdigest() for suffix in ['.docx','.pdf']}
 results.append({'report':number,'pages':len(pdf),'figures':len(figures),'figure_captions':'centered, 14 pt italic in DOCX and PDF','figure_numbers':figure_numbers,'figure_layout':'one blank line before illustration and after caption; centered; black 0.25 pt border; prior references verified','tables':len(tables),'table_numbers':table_numbers,'sources':len(sources),'toc':'verified against PDF; title, leaders and page number clickable','toc_links':len(headings),'sha256':hashes})
 pdf.close()
index=json.loads((ROOT/'diagrams/idef0-index.json').read_text());assert len(index)==12
for key in ['vps','monitoring']:
 nodes={m['node'] for m in index if m['stem'].startswith(key)};assert nodes=={'A-0','A0','A1','A2','A3','A4'}
for item in index:
 for extension in ['.drawio','.svg']:etree.parse(str(ROOT/'diagrams'/(item['stem']+extension)))
 tree=etree.parse(str(ROOT/'diagrams'/(item['stem']+'.drawio')))
 cells={c.get('id'):c for c in tree.iter('mxCell')}
 for cell in cells.values():
  if cell.get('edge')!='1':continue
  for side in ['source','target']:
   key=cell.get(side)
   if not key:continue
   box=cells[key].find('mxGeometry')
   x,y,w,h=[float(box.get(a)) for a in ['x','y','width','height']]
   point=cell.find(f'mxGeometry/mxPoint[@as="{side}Point"]')
   px,py=float(point.get('x')),float(point.get('y'))
   assert x<=px<=x+w and y<=py<=y+h,(item['stem'],'arrow outside function')
   assert min(abs(px-x),abs(px-x-w),abs(py-y),abs(py-y-h))<.01
 with Image.open(ROOT/'diagrams/png'/(item['stem']+'.png')) as im:assert im.width>=2400
api=json.loads((ROOT/'evidence/api-results.json').read_text());assert api['executed']==20 and api['failed']==api['errors']==0
browser=json.loads((ROOT/'evidence/browser-results.json').read_text());assert browser['executed']==13 and browser['failed']==0
units=json.loads((ROOT/'evidence/unit-results.json').read_text());assert len(units)==10 and all(x['status']=='passed' for x in units)
for p in (ROOT/'docs/practices').glob('*.docx'):
 originals=list(Path('/workspace/attachments').rglob(p.name))
 if originals:assert p.read_bytes()==originals[0].read_bytes()
(ROOT/'evidence/document-validation.json').write_text(json.dumps({'reports':results,'idef0_diagrams':12,'unit_tests':10,'api_tests':20,'browser_checks':13,'status':'passed'},ensure_ascii=False,indent=2))
for r in results:print(f'Report {r["report"]}: {r["pages"]} pages, {r["figures"]} figures, {r["tables"]} tables; validated')
print('All documents, TOCs, page numbers, diagrams and test evidence validated.')
