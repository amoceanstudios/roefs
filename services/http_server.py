"""Begrensde requestconcurrentie; reverse proxy/TLS blijven deploymenttaken."""
import os,threading
from http.server import ThreadingHTTPServer

class BoundedHTTPServer(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=128
    def __init__(self,*args,**kwargs):
        self.max_workers=int(os.environ.get('ROEFS_MAX_REQUEST_WORKERS','64'))
        if not 4<=self.max_workers<=128:raise ValueError('ROEFS_MAX_REQUEST_WORKERS moet tussen 4 en 128 liggen.')
        self.slots=threading.BoundedSemaphore(self.max_workers)
        super().__init__(*args,**kwargs)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            try:
                request.settimeout(1)
                body=b'{"error":"Server bezet. Probeer later opnieuw.","code":"capacity"}'
                request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nCache-Control: no-store\r\nRetry-After: 2\r\nConnection: close\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body)
            except OSError:pass
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()
