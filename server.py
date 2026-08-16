"""YouR Party Rentals admin server. Run with: python3 server.py"""
import base64,json,mimetypes,os,re,uuid
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlparse
ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; UPLOADS=ROOT/'uploads'/'gallery'; GALLERY=DATA/'gallery.json'; SETTINGS=DATA/'business-settings.json'; AVAILABILITY=DATA/'dropoff-availability.json'; CATALOG=DATA/'catalog.json'; AUTH=DATA/'admin-auth.json'; USER=os.getenv('GALLERY_ADMIN_USERNAME','admin'); PASSWORD=os.getenv('GALLERY_ADMIN_PASSWORD','yourr-admin')
SLOTS=['08:00','10:00','12:00','14:00','16:00','18:00']; ITEMS=[('tables','Tables','Rectangular and round event tables for dining and display.',10,100),('chairs','Chairs','Comfortable, stackable seating for indoor and outdoor events.',2,250),('canopies','Canopies','Shade coverage for backyard celebrations and open spaces.',75,20),('fans','Fans','Portable cooling fans to keep guests comfortable all day.',20,30),('iceChests','Ice Chests','Large-capacity coolers for drinks, food storage, and service.',15,40)]
def write(path,value): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,indent=2),encoding='utf-8')
def load(path,default):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except(FileNotFoundError,json.JSONDecodeError):return default
def ensure():
 DATA.mkdir(exist_ok=True); UPLOADS.mkdir(parents=True,exist_ok=True)
 for path,default in [(GALLERY,[]),(SETTINGS,{k:'' for k in ['accountHolder','bankName','accountNumber','routingNumber','notificationEmail','notificationPhone']}),(AVAILABILITY,{}),(CATALOG,{'items':[{'key':k,'name':n,'description':d,'price':p,'inventory':i} for k,n,d,p,i in ITEMS],'packages':[]}),(AUTH,{'username':USER,'password':PASSWORD})]:
  if not path.exists():write(path,default)
def credentials():
 value=load(AUTH,{'username':USER,'password':PASSWORD}); return {'username':str(value.get('username') or USER),'password':str(value.get('password') or PASSWORD)}
def authorized(value):
 try:user,password=base64.b64decode((value or '').split(' ',1)[1]).decode().split(':',1); c=credentials(); return user==c['username'] and password==c['password']
 except Exception:return False
def catalog():
 value=load(CATALOG,{'items':[],'packages':[]}); return {'items':value.get('items',[]),'packages':value.get('packages',[])[:4]}
def save_catalog(payload):
 source={i.get('key'):i for i in payload.get('items',[]) if isinstance(i,dict)}; result=[]
 for key,name,description,price,inventory in ITEMS:
  item={"key":key,"name":name,"description":description,"price":price,"inventory":inventory}; item.update(source.get(key,{})); item['key']=key; item['price']=max(0,round(float(item.get('price',price)),2)); item['inventory']=max(0,int(item.get('inventory',inventory))); item['description']=str(item.get('description',description))[:240]; result.append(item)
 packages=[]
 for p in payload.get('packages',[])[:4]:
  if str(p.get('name','')).strip(): packages.append({'id':p.get('id') or uuid.uuid4().hex,'name':str(p.get('name',''))[:80],'description':str(p.get('description',''))[:240],'price':max(0,round(float(p.get('price',0)),2)),'items':{k:max(0,int(p.get('items',{}).get(k,0))) for k,_,_,_,_ in ITEMS}})
 value={'items':result,'packages':packages}; write(CATALOG,value); return value
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send_json(self,status,value):
  body=json.dumps(value).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
 def unauthorized(self):self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="Gallery Admin"');self.end_headers()
 def body(self):return json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))).decode())
 def do_GET(self):
  path=urlparse(self.path).path
  if path=='/api/catalog':self.send_json(200,catalog());return
  if path=='/api/dropoff-slots':self.send_json(200,load(AVAILABILITY,{}).get(parse_qs(urlparse(self.path).query).get('date',[''])[0],SLOTS));return
  if path.startswith('/api/admin/'):
   if not authorized(self.headers.get('Authorization')):self.unauthorized();return
   if path=='/api/admin/ping':self.send_json(200,{'ok':True});return
   if path=='/api/admin/auth':self.send_json(200,{'username':credentials()['username']});return
   if path=='/api/admin/catalog':self.send_json(200,catalog());return
   if path=='/api/admin/settings':self.send_json(200,load(SETTINGS,{}));return
   if path=='/api/admin/availability':self.send_json(200,load(AVAILABILITY,{}));return
  if path in ('/','/index.html','/admin-gallery.html','/script.js','/admin-gallery.js','/admin-auth.js','/styles.css','/config.js'):
   file=ROOT/('index.html' if path=='/' else path[1:]); data=file.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'text/plain');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if path.startswith('/uploads/gallery/'):self._file(UPLOADS/os.path.basename(path));return
  self.send_json(404,{'error':'Not found.'})
 def _file(self,file):
  if not file.exists():self.send_json(404,{'error':'Not found.'});return
  data=file.read_bytes();self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_PUT(self):
  path=urlparse(self.path).path
  if not authorized(self.headers.get('Authorization')):self.unauthorized();return
  value=self.body()
  if path=='/api/admin/auth':
   username=str(value.get('username','')).strip();password=str(value.get('password',''))
   if len(username)<3 or len(password)<8:self.send_json(400,{'error':'Username must be at least 3 characters and password at least 8 characters.'});return
   write(AUTH,{'username':username[:80],'password':password[:200]});self.send_json(200,{'username':username[:80]});return
  if path=='/api/admin/catalog':self.send_json(200,save_catalog(value));return
  if path=='/api/admin/settings':write(SETTINGS,value);self.send_json(200,value);return
  if path=='/api/admin/availability':
   data=load(AVAILABILITY,{});data[str(value.get('date',''))]=value.get('slots',[]);write(AVAILABILITY,data);self.send_json(200,{'date':value.get('date'),'slots':value.get('slots',[])});return
  self.send_json(404,{'error':'Not found.'})
def main():ensure();port=int(os.getenv('PORT','3002'));print(f'YouR Party Rentals admin server running at http://localhost:{port}');ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
if __name__=='__main__':main()
