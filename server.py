"""GeoVision public website and SMTP contact endpoint, behind a local reverse proxy."""
import os
import json
import ssl
import smtplib
import uuid
import re
import time
import threading
import mimetypes
from collections import deque
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).parent / 'site'
FIELDS = ('nom','entreprise','email','telephone','service','type','lieu','delai','projet')
EMAIL = re.compile(r'^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$')
MIMES = {'.woff':'font/woff','.woff2':'font/woff2','.webp':'image/webp','.svg':'image/svg+xml','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.html':'text/html; charset=utf-8'}
LOCK = threading.Lock()
ATTEMPTS = deque()
LIMIT = 30

def configuration():
    required = ('SITE_ORIGIN','SMTP_HOST','SMTP_PORT','SMTP_USER','SMTP_PASSWORD','MAIL_FROM','MAIL_TO')
    cfg = {k:os.getenv(k,'').strip() for k in required}
    if not all(cfg.values()) or not EMAIL.fullmatch(cfg['MAIL_FROM']) or not EMAIL.fullmatch(cfg['MAIL_TO']):
        raise ValueError('SMTP ou destinataire non configuré')
    origin = urlsplit(cfg['SITE_ORIGIN'])
    if origin.scheme != 'https' or not origin.hostname or origin.path or origin.query or origin.fragment:
        raise ValueError('SITE_ORIGIN doit être une origine HTTPS')
    if int(cfg['SMTP_PORT']) not in (465,587):
        raise ValueError('Utiliser SMTP TLS 465 ou STARTTLS 587')
    return cfg

def validate(data):
    if not isinstance(data,dict) or data.get('website'):
        raise ValueError('Demande invalide.')
    out = {}
    for k in FIELDS:
        v = data.get(k)
        if not isinstance(v,str) or len(v) > (4000 if k=='projet' else 250):
            raise ValueError('Champ invalide : '+k)
        v = v.strip()
        if k != 'telephone' and not v:
            raise ValueError('Veuillez compléter les champs obligatoires.')
        if k != 'projet' and ('\r' in v or '\n' in v):
            raise ValueError('Champ invalide : '+k)
        out[k] = v
    if not EMAIL.fullmatch(out['email']):
        raise ValueError('Adresse e-mail invalide.')
    return out

def admit():
    with LOCK:
        now=time.monotonic()
        while ATTEMPTS and ATTEMPTS[0] < now-600:
            ATTEMPTS.popleft()
        if len(ATTEMPTS)>=LIMIT:
            return False
        ATTEMPTS.append(now)
        return True

def deliver(data, cfg, reference):
    msg=EmailMessage()
    msg['From']=cfg['MAIL_FROM']
    msg['To']=cfg['MAIL_TO']
    msg['Reply-To']=data['email']
    msg['Subject']='GeoVision – Nouvelle demande '+reference
    msg.set_content('Demande reçue via le site GeoVision.\nRéférence : '+reference+'\n\n'+'\n'.join(k+' : '+v for k,v in data.items()))
    ctx=ssl.create_default_context()
    port=int(cfg['SMTP_PORT'])
    if port==465:
        client=smtplib.SMTP_SSL(cfg['SMTP_HOST'],port,timeout=12,context=ctx)
    else:
        client=smtplib.SMTP(cfg['SMTP_HOST'],port,timeout=12)
    with client as smtp:
        if port==587:
            smtp.ehlo();smtp.starttls(context=ctx);smtp.ehlo()
        smtp.login(cfg['SMTP_USER'],cfg['SMTP_PASSWORD'])
        refused=smtp.send_message(msg)
        if refused:
            raise RuntimeError('Destinataire refusé')

class Handler(BaseHTTPRequestHandler):
    server_version='GeoVision'
    sys_version=''
    def setup(self):
        super().setup()
        self.connection.settimeout(15)
    def log_message(self, fmt, *args):
        # Do not retain query strings or contact details.
        print(f'{self.command} {urlsplit(self.path).path[:120]}',flush=True)
    def respond(self, status, body, content_type='application/json; charset=utf-8', cache='no-store', head=False):
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control',cache)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'")
        self.end_headers()
        if not head:
            self.wfile.write(body)
    def reply(self,status,data):
        self.respond(status,json.dumps(data,ensure_ascii=False).encode())
    def do_GET(self):
        self.serve()
    def do_HEAD(self):
        self.serve(head=True)
    def serve(self,head=False):
        path=unquote(urlsplit(self.path).path)
        if path=='/healthz':
            return self.respond(200,b'{"status":"ok"}',head=head)
        if path=='/':
            path='/index.html'
        if not (path in ('/index.html','/detection.html','/georeferencement.html','/cartographie.html','/informations.html','/brand.js','/commercial.js','/photos.js','/visual-v4.js','/portal.js','/detail.css','/typography.css','/premium.css','/robots.txt') or path.startswith(('/images/','/fonts/'))):
            return self.respond(404,b'Page introuvable', 'text/plain; charset=utf-8',head=head)
        file=(ROOT/path.lstrip('/')).resolve()
        if not file.is_relative_to(ROOT.resolve()) or not file.is_file():
            return self.respond(404,b'Page introuvable','text/plain; charset=utf-8',head=head)
        typ=MIMES.get(file.suffix,mimetypes.guess_type(file)[0] or 'application/octet-stream')
        self.respond(200,file.read_bytes(),typ,'no-cache' if file.suffix=='.html' else 'public, max-age=3600',head)
    def do_POST(self):
        if self.path!='/api/contact':
            return self.reply(404,{'error':'Route inconnue.'})
        try:
            cfg=configuration()
        except (ValueError,TypeError):
            return self.reply(503,{'error':'Le service de contact n’est pas encore configuré.'})
        if self.headers.get('Origin')!=cfg['SITE_ORIGIN']:
            return self.reply(403,{'error':'Origine non autorisée.'})
        if self.headers.get_content_type()!='application/json':
            return self.reply(415,{'error':'Format non pris en charge.'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=16000:
                return self.reply(413,{'error':'Taille de demande invalide.'})
            data=validate(json.loads(self.rfile.read(n)))
        except (ValueError,UnicodeError,TypeError):
            return self.reply(400,{'error':'Veuillez vérifier les informations saisies.'})
        if not admit():
            return self.reply(429,{'error':'Trop de demandes. Réessayez dans quelques minutes.'})
        reference='GV-'+uuid.uuid4().hex[:12].upper()
        try:
            deliver(data,cfg,reference)
        except (OSError,smtplib.SMTPException,RuntimeError):
            return self.reply(502,{'error':'Le service de messagerie est momentanément indisponible.'})
        return self.reply(200,{'reference':reference})

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
