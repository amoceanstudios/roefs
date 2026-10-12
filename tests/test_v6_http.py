import socket,threading,time,unittest
from http.server import BaseHTTPRequestHandler
from unittest.mock import patch
from services.http_server import BoundedHTTPServer
class V6HTTP(unittest.TestCase):
 def test_worker_limit_rejects_then_recovers(self):
  gate=threading.Event();entered=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    entered.append(1);gate.wait(5);self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'OK')
  with patch.dict('os.environ',{'ROEFS_MAX_REQUEST_WORKERS':'4'}):server=BoundedHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();connections=[]
  try:
   for _ in range(4):
    s=socket.create_connection(server.server_address,timeout=5);s.sendall(b'GET / HTTP/1.0\r\n\r\n');connections.append(s)
   deadline=time.monotonic()+3
   while len(entered)<4 and time.monotonic()<deadline:time.sleep(.01)
   self.assertEqual(len(entered),4)
   with socket.create_connection(server.server_address,timeout=5) as extra:
    extra.sendall(b'GET / HTTP/1.0\r\n\r\n');self.assertIn(b'503 Service Unavailable',extra.recv(4096))
   gate.set()
   for s in connections:
    received=b''
    while True:
     part=s.recv(4096)
     if not part:break
     received+=part
    self.assertIn(b'200 OK',received)
   with socket.create_connection(server.server_address,timeout=5) as recovered:
    recovered.sendall(b'GET / HTTP/1.0\r\n\r\n');self.assertIn(b'200 OK',recovered.recv(4096))
  finally:
   gate.set()
   for s in connections:s.close()
   server.shutdown();server.server_close();thread.join()
