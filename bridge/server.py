from http.server import BaseHTTPRequestHandler,HTTPServer
import json, os
HOST='127.0.0.1'; PORT=int(os.getenv('GLABS_BRIDGE_PORT','18923'))
class H(BaseHTTPRequestHandler):
 def sendj(self,x):
  b=json.dumps(x).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def do_GET(self): self.sendj({'ok':True,'service':'G-Labs Studio Bridge','path':self.path})
 def log_message(self,*a): pass
if __name__=='__main__': HTTPServer((HOST,PORT),H).serve_forever()
