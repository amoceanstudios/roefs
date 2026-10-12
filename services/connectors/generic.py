"""Gedocumenteerd ROEFS JSON-syncprotocol; standaard uitsluitend allowlisted HTTPS."""
import hashlib,ipaddress,json,os,socket,urllib.parse,urllib.request,urllib.error
from domain import Problem

class RemoteError(Exception):
    def __init__(self,message,retryable=True,status=None):super().__init__(message);self.retryable=retryable;self.status=status
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RemoteError('Omleiding geweigerd; configureer het definitieve API-adres.',False)

def validate_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:raise Problem('Gebruik een API-basisadres zonder gebruikersgegevens, query of fragment.')
    host=parsed.hostname.lower();allowed={x.strip().lower() for x in os.environ.get('ROEFS_SYNC_ALLOWED_HOSTS','').split(',') if x.strip()}
    if host not in allowed:raise Problem('API-host is niet toegestaan. Voeg uitsluitend de gewenste host toe aan ROEFS_SYNC_ALLOWED_HOSTS.')
    testing=os.environ.get('ROEFS_SYNC_ALLOW_LOOPBACK_TEST')=='1' and host in {'127.0.0.1','localhost','::1'}
    if parsed.scheme!='https' and not (testing and parsed.scheme=='http'):raise Problem('Externe synchronisatie vereist HTTPS.')
    try:addresses=socket.getaddrinfo(host,parsed.port or (443 if parsed.scheme=='https' else 80),type=socket.SOCK_STREAM)
    except OSError:raise RemoteError('API-host kon niet worden opgezocht.')
    for address in addresses:
        ip=ipaddress.ip_address(address[4][0])
        if not ip.is_global and not (testing and ip.is_loopback):raise Problem('Interne, lokale en metadata-adressen zijn niet toegestaan voor externe connectors.')
    return parsed

class Connector:
    def __init__(self,config):
        self.base=config['base_url'].rstrip('/');validate_url(self.base)
        ref=config['secret_env'];self.secret=os.environ.get(ref,'') if ref else ''
        if not self.secret:raise RemoteError('API-toegang ontbreekt: vul de geconfigureerde omgevingsvariabele in.',False)
        self.opener=urllib.request.build_opener(NoRedirect())
    def request(self,path,method='GET',payload=None,headers=None):
        # Iedere oproep wordt opnieuw gecontroleerd; redirects geven nooit het toegangstoken door.
        validate_url(self.base);url=self.base+'/'+path.lstrip('/')
        req=urllib.request.Request(url,method=method,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers={'Authorization':'Bearer '+self.secret,'Content-Type':'application/json','Accept':'application/json',**(headers or {})})
        try:
            with self.opener.open(req,timeout=10) as response:
                if response.headers.get_content_type()!='application/json':raise RemoteError('De API geeft geen JSON terug.',False)
                raw=response.read(2000001)
                if len(raw)>2000000:raise RemoteError('API-antwoord overschrijdt 2 MB.',False)
                data=json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise RemoteError({401:'API-toegang geweigerd: token ontbreekt of verlopen.',403:'API-rechten onvoldoende.',409:'Externe wijziging botst met deze wijziging.',412:'Externe versie is gewijzigd.',429:'API-limiet bereikt; poging wordt later hervat.'}.get(exc.code,'Externe API-fout (HTTP '+str(exc.code)+').'),exc.code in (408,429) or exc.code>=500,exc.code)
        except (urllib.error.URLError,TimeoutError,OSError):raise RemoteError('Externe API niet bereikbaar; poging wordt later hervat.')
        except (ValueError,UnicodeDecodeError):raise RemoteError('Ongeldig JSON-antwoord van externe API.',False)
        if not isinstance(data,dict):raise RemoteError('Verwacht een JSON-object van de externe API.',False)
        return data
    def capabilities(self):
        data=self.request('capabilities')
        if data.get('protocol')!='roefs-sync-v1':raise RemoteError('API ondersteunt het vereiste roefs-sync-v1-protocol niet.',False)
        return data
    def list_records(self,category):
        cursor='';seen=set()
        for _ in range(100):
            data=self.request('records/'+category+('?cursor='+urllib.parse.quote(cursor,safe='') if cursor else ''))
            items=data.get('items')
            if not isinstance(items,list) or len(items)>500:raise RemoteError('Ongeldige synchronisatiepagina (maximaal 500 records).',False)
            yield items
            cursor=data.get('next_cursor') or ''
            if not isinstance(cursor,str) or len(cursor)>2000:raise RemoteError('Ongeldige paginacursor.',False)
            if not cursor:return
            if cursor in seen:raise RemoteError('API herhaalt dezelfde paginacursor.',False)
            seen.add(cursor)
        raise RemoteError('API overschrijdt 100 pagina’s per categorie.',False)
    def put(self,category,payload,key,external_id=None,revision=None):
        headers={'Idempotency-Key':key}
        if external_id:
            if not revision:raise RemoteError('Externe versie ontbreekt; update geweigerd.',False)
            headers['If-Match']=revision
        else:headers['If-None-Match']='*'
        return self.request('records/'+category+('/'+urllib.parse.quote(external_id,safe='') if external_id else ''),'PUT' if external_id else 'POST',payload,headers)
