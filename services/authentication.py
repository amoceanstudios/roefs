"""Cookie-sessies voor de browser; bearer blijft voor bestaande API-clients."""
import hashlib,hmac,os
from http.cookies import SimpleCookie
from domain import Problem

def session_token(handler):
    auth=handler.headers.get('Authorization','')
    if auth.startswith('Bearer '):return auth[7:].strip(),False
    cookie=SimpleCookie()
    try:cookie.load(handler.headers.get('Cookie',''))
    except Exception:return '',True
    return cookie['roefs_session'].value if 'roefs_session' in cookie else '',True

def csrf(token):return hashlib.sha256(('roefs-csrf:'+token).encode()).hexdigest()
def check_csrf(handler,method):
    token,is_cookie=session_token(handler)
    if token and is_cookie and method!='GET' and not hmac.compare_digest(handler.headers.get('X-CSRF-Token',''),csrf(token)):
        raise Problem('Beveiligingscontrole mislukt. Vernieuw de pagina.',403)
def cookie(handler,token,clear=False):
    # Alleen expliciete lokale configuratie mag HTTP-cookies gebruiken. Tunnel gebruikt HTTPS.
    secure=os.environ.get('ROEFS_COOKIE_SECURE','1')!='0'
    return 'roefs_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age='+('0' if clear else '28800')+('; Secure' if secure else '')
