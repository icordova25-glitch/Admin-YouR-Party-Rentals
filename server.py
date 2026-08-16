"""YouR Party Rentals admin/backend server. Run with: python3 server.py"""
import base64,json,mimetypes,os,re,uuid
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlparse
ROOT=Path(__file__).resolve().parent; DATA_DIR=ROOT/'data'; UPLOADS_DIR=ROOT/'uploads'/'gallery'; GALLERY_PATH=DATA_DIR/'gallery.json'; SETTINGS_PATH=DATA_DIR/'business-settings.json'; AVAILABILITY_PATH=DATA_DIR/'dropoff-availability.json'; CATALOG_PATH=DATA_DIR/'catalog.json'; USER=os.getenv('GALLERY_ADMIN_USERNAME','admin'); PASSWORD=os.getenv('GALLERY_ADMIN_PASSWORD','yourr-admin')
DEFAULT_SLOTS=['08:00','10:00','12:00','14:00','16:00','18:00']; DEFAULT_ITEMS=[('tables','Tables','Rectangular and round event tables for dining and display.',10,100),('chairs','Chairs','Comfortable, stackable seating for indoor and outdoor events.',2,250),('canopies','Canopies','Shade coverage for backyard celebrations and open spaces.',75,20),('fans','Fans','Portable cooling fans to keep guests comfortable all day.',20,30),('iceChests','Ice Chests','Large-capacity coolers for drinks, food storage, and service.',15,40)]
def write(path,data): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2),encoding='utf-8')
def ensure():
 DATA_DIR.mkdir(exist_ok=True); UPLOADS_DIR.mkdir(parents=True,exist_ok=True)
 if not GALLERY_PATH.exists(): write(GALLERY_PATH,[])
 if not SETTINGS_PATH.exists(): write(SETTINGS_PATH,{k:'' for k in ['accountHolder','bankName','accountNumber','routingNumber','notificationEmail','notificationPhone']})
 if not AVAILABILITY_PATH.exists(): write(AVAILABILITY_PATH,{})
 if not CATALOG_PATH.exists(): write(CATALOG_PATH,{'items':[{'key':k,'name':n,'description':d,'price':p,'inventory':i} for k,n,d,p,i in DEFAULT_ITEMS],'packages':[]})
def load(path,default):
 try: value=json.loads(path.read_text(encoding='utf-8')); return value
 except (FileNotFoundError,json.JSONDecodeError): return default
def auth(value):
 try: user,pwd=base64.b64decode((value or '').split(' ',1)[1]).decode().split(':',1); return user==USER and pwd==PASSWORD
 except Exception: return False
def catalog():
 ensure(); value=load(CATALOG_PATH,{'items':[],'packages':[]}); return {'items':value.get('items',[]),'packages':value.get('packages',[])[:4]}
def save_catalog(payload):
 source={item.get('key'):item for item in payload.get('items',[]) if isinstance(item,dict)}; items=[]
 for k,n,d,p,i in DEFAULT_ITEMS:
  item={**{'key':k,'name':n,'description':d,'price':p,'inventory':i},**source.get(k,{})}; item['key']=k; item['price']=max(0,round(float(item.get('price',p)),2)); item['inventory']=max(0,int(item.get('inventory',i))); item['description']=str(item.get('description',d))[:240]; items.append(item)
 packages=[]
 for item in payload.get('packages',[])[:4]:
  if str(item.get('name','')).strip(): packages.append({'id':item.get('id') or uuid.uuid4().hex,'name':str(item.get('name',''))[:80],'description':str(item.get('description',''))[:240],'price':max(0,round(float(item.get('price',0)),2)),'items':{k:max(0,int(item.get('items',{}).get(k,0))) for k,_,_,_,_ in DEFAULT_ITEMS}})
 value={'items':items,'packages':packages}; write(CATALOG_PATH,value); return value
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def json(self,status,data): body=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
 def unauthorized(self): self.send_response(401); self.send_header('WWW-Authenticate','Basic realm="Gallery Admin"'); self.end_headers()
 def body(self): return json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))).decode())
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/api/catalog': self.json(200,catalog()); return
  if path=='/api/dropoff-slots': self.json(200,load(AVAILABILITY_PATH,{}).get(parse_qs(urlparse(self.path).query).get('date',[''])[0],DEFAULT_SLOTS)); return
  if path.startswith('/api/admin/'):
   if not auth(self.headers.get('Authorization')): self.unauthorized(); return
   if path=='/api/admin/ping': self.json(200,{'ok':True}); return
   if path=='/api/admin/catalog': self.json(200,catalog()); return
   if path=='/api/admin/settings': self.json(200,load(SETTINGS_PATH,{})); return
   if path=='/api/admin/availability': self.json(200,load(AVAILABILITY_PATH,{})); return
  if path in ('/','/index.html','/admin-gallery.html','/script.js','/admin-gallery.js','/styles.css','/config.js'):
   file=ROOT/('index.html' if path=='/' else path.lstrip('/')); data=file.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'text/plain'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data); return
  self.json(404,{'error':'Not found.'})
 def do_PUT(self):
  path=urlparse(self.path).path
  if not auth(self.headers.get('Authorization')): self.unauthorized(); return
  value=self.body()
  if path=='/api/admin/catalog': self.json(200,save_catalog(value)); return
  if path=='/api/admin/settings': write(SETTINGS_PATH,value); self.json(200,value); return
  if path=='/api/admin/availability':
   slots=value.get('slots',[]); data=load(AVAILABILITY_PATH,{}); data[value['date']]=slots; write(AVAILABILITY_PATH,data); self.json(200,{'date':value['date'],'slots':slots}); return
  self.json(404,{'error':'Not found.'})
 def do_POST(self): self.json(404,{'error':'Not found.'})
def main(): ensure(); port=int(os.getenv('PORT','3002')); print(f'YouR Party Rentals admin server running at http://localhost:{port}'); ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
if __name__=='__main__': main()
