"""Begrensde CSV/OOXML-invoer; geen formule-evaluatie of externe verbindingen."""
import zlib,posixpath
import csv,datetime as dt,io,re,zipfile,xml.etree.ElementTree as ET
from decimal import Decimal
from xml.sax.saxutils import escape
from domain import Problem
MAX_BYTES=10*1024*1024
MAX_ROWS=25000
MAX_COLUMNS=100
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def xml(data):
 if b'<!DOCTYPE' in data.replace(b'\x00',b'').upper() or b'<!ENTITY' in data.replace(b'\x00',b'').upper():raise Problem('XML-entiteiten zijn niet toegestaan.')
 try:return ET.fromstring(data)
 except ET.ParseError:raise Problem('Beschadigd spreadsheetbestand.')

def validate_table(table):
 table=iter(table)
 first=next(table,None)
 if first is None:raise Problem('Bestand bevat geen kolomkoppen.')
 headers=[str(v).strip() for v in first]
 if not 1<=len(headers)<=MAX_COLUMNS or any(not x or len(x)>100 for x in headers) or len(set(headers))!=len(headers):raise Problem('Gebruik unieke, niet-lege kolomkoppen (maximaal 100).')
 rows=[]
 for index,row in enumerate(table,2):
  if not any(str(x).strip() for x in row):continue
  if len(row)>len(headers):raise Problem(f'Rij {index}: meer velden dan kolomkoppen.')
  row=[str(x) for x in row]+['']*(len(headers)-len(row))
  if any(len(x)>2000 or '\x00' in x for x in row):raise Problem(f'Rij {index}: veld te lang of ongeldige tekens.')
  if any(re.match(r'^\s*(=|@|\+[^0-9]|-[^0-9])',x) for x in row):raise Problem(f'Rij {index}: formuleachtige inhoud is niet toegestaan.')
  rows.append({'line':index,'values':row})
  if len(rows)>MAX_ROWS:raise Problem('Bestand bevat meer dan 25.000 gegevensrijen.',413)
 if not rows:raise Problem('Bestand bevat geen gegevensrijen.')
 return headers,rows

def read(name,data):
 if not 0<len(data)<=MAX_BYTES:raise Problem('Bestand leeg of groter dan 10 MiB.',413)
 if name.lower().endswith('.csv'):
  try:content=data.decode('utf-8-sig')
  except UnicodeDecodeError:raise Problem('Sla CSV op als UTF-8.')
  try:
   dialect=csv.Sniffer().sniff(content[:65536],delimiters=';,\t|')
  except csv.Error:dialect=csv.excel
  try:table=csv.reader(io.StringIO(content),dialect)
  except csv.Error:raise Problem('CSV kan niet worden gelezen.')
 elif name.lower().endswith('.xlsx'):
  try:table=read_xlsx(data)
  except (zipfile.BadZipFile,zlib.error,KeyError,ValueError,RuntimeError,OSError):raise Problem('Beschadigd of niet-ondersteund XLSX-bestand.')
 else:raise Problem('Gebruik een CSV- of XLSX-bestand.')
 try:return validate_table(table)
 except csv.Error:raise Problem('CSV bevat een ongeldig of te groot veld.')

def read_xlsx(data):
 try:z=zipfile.ZipFile(io.BytesIO(data))
 except zipfile.BadZipFile:raise Problem('Geen geldig XLSX-bestand.')
 with z:
  entries=z.infolist();names=[x.filename for x in entries]
  if len(entries)>1000 or len(names)!=len(set(names)) or sum(x.file_size for x in entries)>50*1024*1024:raise Problem('Spreadsheet overschrijdt de veilige uitpakgrens.',413)
  if any(x.flag_bits&1 or x.file_size>30*1024*1024 for x in entries):raise Problem('Versleuteld of te groot spreadsheetonderdeel.',413)
  if any(n.startswith('/') or '..' in n.split('/') or '\\' in n for n in names):raise Problem('Onveilige spreadsheetpaden.')
  if any(re.search(r'vbaProject|externalLinks|embeddings|activeX|connections\.xml',n,re.I) for n in names):raise Problem('Macro’s, ingesloten objecten en externe koppelingen zijn niet toegestaan.')
  for name in names:
   if name.endswith('.rels'):
    if any(x.get('TargetMode')=='External' for x in xml(z.read(name))):raise Problem('Externe spreadsheetrelaties zijn niet toegestaan.')
  sheets=sorted(n for n in names if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n))
  if not sheets:raise Problem('Werkblad ontbreekt.')
  workbook=xml(z.read('xl/workbook.xml'));first=workbook.find('s:sheets/s:sheet',NS)
  if first is None:raise Problem('Eerste gegevenswerkblad ontbreekt.')
  relation=first.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
  targets=[r.get('Target','') for r in xml(z.read('xl/_rels/workbook.xml.rels')) if r.get('Id')==relation]
  if len(targets)!=1:raise Problem('Werkbladrelatie is ongeldig.')
  sheet=posixpath.normpath(targets[0].lstrip('/') if targets[0].startswith('/') else 'xl/'+targets[0])
  if sheet not in sheets:raise Problem('Eerste gegevenswerkblad ontbreekt.')
  for name in sheets:
   if xml(z.read(name)).find('.//s:f',NS) is not None:raise Problem('Formules zijn niet toegestaan; exporteer alleen waarden.')
  shared=[]
  if 'xl/sharedStrings.xml' in names:shared=[''.join(t.text or '' for t in item.findall('.//s:t',NS)) for item in xml(z.read('xl/sharedStrings.xml'))]
  styles=[];formats={}
  if 'xl/styles.xml' in names:
   style=xml(z.read('xl/styles.xml'));formats={int(x.get('numFmtId')):x.get('formatCode','') for x in style.findall('s:numFmts/s:numFmt',NS)};styles=[int(x.get('numFmtId','0')) for x in style.findall('s:cellXfs/s:xf',NS)]
  epoch=dt.datetime(1899,12,30)
  if 'xl/workbook.xml' in names:
   props=xml(z.read('xl/workbook.xml')).find('s:workbookPr',NS)
   if props is not None and props.get('date1904') in ('1','true'):epoch=dt.datetime(1904,1,1)
  table=[]
  for row in xml(z.read(sheet)).findall('s:sheetData/s:row',NS):
   values={}
   for cell in row.findall('s:c',NS):
    ref=cell.get('r','');match=re.fullmatch(r'([A-Z]+)[1-9][0-9]*',ref)
    if not match:raise Problem('Ongeldige celreferentie.')
    col=0
    for ch in match[1]:col=col*26+ord(ch)-64
    if not 1<=col<=MAX_COLUMNS or col in values:raise Problem('Te veel of dubbele spreadsheetkolommen.')
    raw=cell.find('s:v',NS);value=raw.text or '' if raw is not None else '';kind=cell.get('t','n')
    if kind=='s':
     try:
      key=int(value)
      if not 0<=key<len(shared):raise ValueError()
      value=shared[key]
     except (ValueError,IndexError):raise Problem('Ongeldige tekstverwijzing.')
    elif kind=='inlineStr':value=''.join(x.text or '' for x in cell.findall('.//s:t',NS))
    elif kind=='e':raise Problem('Spreadsheet bevat een Excel-foutwaarde.')
    elif kind not in ('n','str','b','d'):raise Problem('Onbekend celtype.')
    if kind=='n' and value:
     try:
      idx=int(cell.get('s','0'))
      if idx<0 or styles and idx>=len(styles):raise ValueError()
      fmt=styles[idx] if styles else 0;pattern=formats.get(fmt,'');number=Decimal(value)
      if not number.is_finite():raise ValueError()
      if fmt in (14,15,16,17,22) or re.search(r'[dy]',pattern,re.I):value=(epoch+dt.timedelta(days=float(number))).isoformat(timespec='seconds') if fmt==22 or 'h' in pattern.lower() else (epoch+dt.timedelta(days=float(number))).date().isoformat()
      elif fmt in (18,19,20,21,45,46,47) or re.search(r'h.*m',pattern,re.I):
       seconds=int(number*86400);value=f'{seconds//3600%24:02}:{seconds//60%60:02}'
      elif re.fullmatch('0+',pattern) and number==number.to_integral_value():value=str(int(number)).zfill(len(pattern))
     except (ValueError,IndexError,ArithmeticError,OverflowError):raise Problem('Ongeldige Excel-datum of getalwaarde.')
    values[col]=value
   table.append([values.get(i,'') for i in range(1,max(values,default=0)+1)])
   if len(table)>MAX_ROWS+1:raise Problem('Maximaal 25.000 gegevensrijen per bestand.',413)
  return table

def xlsx(sheets):
 """Schrijf uitsluitend tekstcellen, ook voor externe sleutels met voorloopnullen."""
 output=io.BytesIO()
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'+''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(sheets)+1))+'</Types>')
  z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
  z.writestr('xl/workbook.xml','<workbook xmlns="'+NS['s']+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,rows) in enumerate(sheets,1))+'</sheets></workbook>')
  z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+'</Relationships>')
  for index,(name,rows) in enumerate(sheets,1):
   chunks=[]
   for number,row in enumerate(rows,1):
    cells=[]
    for col,value in enumerate(row,1):
     letters='';n=col
     while n:n,r=divmod(n-1,26);letters=chr(65+r)+letters
     cells.append(f'<c r="{letters}{number}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>')
    chunks.append(f'<row r="{number}">'+''.join(cells)+'</row>')
   z.writestr(f'xl/worksheets/sheet{index}.xml','<worksheet xmlns="'+NS['s']+'"><sheetData>'+''.join(chunks)+'</sheetData></worksheet>')
 return output.getvalue()
