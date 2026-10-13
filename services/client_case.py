"""Opgegeven klantcase met expliciet bevestigde presentatieplanning.

De klantgegevens en urenafspraken komen van Roefs. De negen uitvoeringsdatums
en tijdvakken zijn presentatiegegevens, geen bevestigde productieafspraken.
"""
import datetime as dt
import json
from domain import Problem, date_value
from .common import record, insert, audit
from . import service_plans, planning, workorders

KEY = 'roefs_customer_presentation'


def allowed(user):
    if user['role'] not in ('admin', 'company_admin'):
        raise Problem('Alleen beheer heeft toegang tot de klantpresentatie.', 403)


def detail(c, user):
    allowed(user)
    stored = c.execute('SELECT value FROM settings WHERE key=?', (KEY,)).fetchone()
    if not stored:
        return {'ready': False}
    ids = json.loads(stored[0])
    contract = record(c, 'contracts', ids['contract_id'])
    customer = record(c, 'customers', contract['customer_id'])
    location = record(c, 'objects', contract['object_id'])
    result = service_plans.detail(c, user, contract['id'])
    jobs = [record(c, 'workorders', x) for x in ids['workorder_ids']]
    shifts = [record(c, 'shifts', x[0]) for x in c.execute('SELECT s.id FROM shifts s JOIN workorders w ON w.id=s.workorder_id WHERE w.contract_id=? ORDER BY s.id', (contract['id'],))]
    hours = [dict(x) for x in c.execute('SELECT h.* FROM hours h JOIN workorders w ON w.id=h.workorder_id WHERE w.contract_id=?', (contract['id'],))]
    invoices = [dict(x) for x in c.execute('SELECT i.* FROM invoices i JOIN workorders w ON w.id=i.workorder_id WHERE w.contract_id=?', (contract['id'],))]
    return {'ready': True, 'customer': customer, 'location': location,
            **result, 'workorders': jobs, 'shifts': shifts,
            'hours': hours, 'invoices': invoices,
            'week_start': ids['week_start'],
            'notice': 'Klantgegevens en urenafspraken volgens Roefs. Datums, tijdvakken en contractperiode zijn uitsluitend voor de presentatie. Medewerkers, uitgevoerd werk en tarieven zijn nog niet bevestigd.'}


def prepare(c, user, body, modules):
    allowed(user)
    existing = detail(c, user)
    if existing['ready']:
        return existing
    if body.get('confirmed') is not True:
        raise Problem('Bevestig het opslaan van de klantcase met presentatieplanning.', 400)
    first = date_value(body.get('week_start', ''))
    if first.weekday() != 0:
        raise Problem('Kies de maandag van de presentatieweek.')
    if first.year > 9998:
        raise Problem('Kies een presentatieweek waarvoor een volledig contractjaar beschikbaar is.')
    from .routes import entity_save
    customer = entity_save(c, user, 'customers', {
        'name': 'Basisschool De Egel', 'city': 'Eindhoven', 'status': 'Actief',
        'billing_address': 'Europalaan 44, 1111 AA Eindhoven'}, modules)
    location = entity_save(c, user, 'objects', {
        'name': 'Basisschool De Egel', 'customer_id': customer['id'],
        'address': 'Europalaan 44, 1111 AA', 'city': 'Eindhoven',
        'type': 'School', 'frequency': 'Ma–vr gedurende 40 lesweken; glas 4× per jaar',
        'status': 'Actief'}, modules)
    contract = entity_save(c, user, 'contracts', {
        'name': 'Basisschool De Egel · schoonmaakopdracht · presentatie',
        'customer_id': customer['id'], 'object_id': location['id'],
        'monthly_value': '0', 'start_date': str(first),
        'end_date': str(first + dt.timedelta(days=364)), 'status': 'Actief'}, modules)
    insert(c, 'contract_locations', {'contract_id': contract['id'],
                                    'object_id': location['id'],
                                    'frequency': '40 lesweken: ma 2u, di 2u, wo 3u, do 2u, vr 2,5u; glas 4× per jaar'})
    weekly = service_plans.save(c, user, contract['id'], {
        'name': 'Interieurverzorging volgens schoonmaakbestek',
        'definition': {'object_id': location['id'], 'kind': 'weekly', 'count': 40,
                       'hours': {'0': '2', '1': '2', '2': '3', '3': '2', '4': '2.5'},
                       'weeks': [str(first)],
                       'tasks': ['Interieurverzorging volgens schoonmaakbestek — bestek nog toevoegen']}})['items'][0]
    glass_dates = [str(first + dt.timedelta(weeks=13*i, days=2)) for i in range(4)]
    glass = service_plans.save(c, user, contract['id'], {
        'name': 'Glasbewassing',
        'definition': {'object_id': location['id'], 'kind': 'periodic', 'count': 4,
                       'dates': glass_dates,
                       'tasks': ['Buitenzijde gevelglas', 'Binnenzijde gevelglas', 'Separatieglas']}})['items'][1]
    job_ids, shift_ids = [], []
    for service in (weekly, glass):
        for day in service['definition']['selected']:
            weekday = date_value(day).weekday()
            start = '16:00' if service['definition']['kind'] == 'weekly' else '09:00'
            end = ['18:00', '18:00', '19:00', '18:00', '18:30'][weekday] if service['definition']['kind'] == 'weekly' else '10:00'
            work = workorders.save(c, user, {
                'contract_id': contract['id'], 'object_id': location['id'],
                'description': 'PRESENTATIE · Basisschool De Egel · ' + service['name'],
                'service': service['name'], 'date': day, 'start_time': start,
                'end_time': end, 'capacity': 1})
            for task in service['definition']['tasks']:
                insert(c, 'checklist', {'workorder_id': work['id'], 'title': task})
            insert(c, 'contract_service_jobs', {'service_id': service['id'], 'date': day, 'workorder_id': work['id']})
            shift = planning.save(c, user, {
                'workorder_id': work['id'], 'object_id': location['id'],
                'employee_id': '', 'date': day, 'start_time': start, 'end_time': end,
                'status': 'Gepland', 'planner_notes': 'Presentatieafspraak; medewerker en definitieve uitvoering nog bevestigen.'})
            job_ids.append(work['id']); shift_ids.append(shift['id'])
    ids = {'contract_id': contract['id'], 'week_start': str(first),
           'workorder_ids': job_ids, 'shift_ids': shift_ids}
    insert(c, 'settings', {'key': KEY, 'value': json.dumps(ids)})
    audit(c, user, 'presentation_created', 'contracts', contract['id'],
          'Opgegeven klantcase; 5 schoonmaakdiensten en 4 glasbezoeken als presentatieplanning. Geen gerealiseerde uren of facturen.')
    return detail(c, user)
