"""Serverrechten. Onbekende rollen krijgen geen toegang."""
from domain import Problem
ROLES={'admin':'Systeembeheerder','company_admin':'Bedrijfsbeheerder','director':'Directeur','operations':'Operationeel manager','planner':'Planner','supervisor':'Leidinggevende','employee':'Medewerker','finance':'Financieel beheerder','auditor':'Auditor'}
ADMIN={'admin','company_admin'}
OPS={'customers','objects','contracts','employees','shifts','workorders','availability','leave','assets','vehicles','inspections','logbook','orders','keys','alerts','documents'}
FIN={'customers','objects','contracts','hours','invoices','quotes','ledger','payroll','documents'}
READ={'operations':OPS|{'hours','reports'},'planner':OPS-{'contracts'}|{'hours'},'supervisor':{'objects','shifts','workorders','hours','availability','leave','inspections','logbook','assets','documents'},'finance':FIN|{'reports','workorders'}}
WRITE={'operations':OPS|{'hours'},'planner':{'shifts','workorders','availability','leave','assets','vehicles'},'supervisor':{'workorders','hours','leave','inspections','logbook'},'finance':FIN-{'customers','objects','contracts','hours'}}
def permitted(user,module,write=False):
    role=user['role']
    if role in ADMIN:return True
    if role in {'director','auditor'}:return not write and module not in {'users','payroll'}
    return module in (WRITE if write else READ).get(role,set())
def require(user,module,write=False):
    if not permitted(user,module,write):raise Problem('Geen toegang tot deze handeling.',403)
def legacy_access(user,path,method,modules):
    """Alleen expliciete routes voor bedrijfsrollen. Geen impliciete adminrechten."""
    if user['role'] in ADMIN:return
    write=method!='GET'
    if path in {'/api/me','/api/logout','/api/modules','/api/lookups','/api/messages'}:return
    if path.startswith('/api/records/'):
        require(user,path.split('/')[3],write);return
    if path in {'/api/planning/overview','/api/planning/suggest'}:require(user,'shifts',path.endswith('suggest'));return
    if path=='/api/dashboard' and not write:return
    if path=='/api/audit' and not write and user['role'] in {'director','auditor','operations'}:return
    raise Problem('Geen toegang tot deze functie.',403)
