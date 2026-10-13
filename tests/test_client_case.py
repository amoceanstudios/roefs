import sqlite3
import unittest
from support import LiveServer


class ClientCase(unittest.TestCase):
    def setUp(self):
        self.s = LiveServer(); self.token = self.s.login()

    def tearDown(self):
        self.s.close()

    def call(self, body=None, token=None, status=200):
        code, data, _ = self.s.request('/api/v5/customer-presentation',
                                      'GET' if body is None else 'POST', body, token or self.token)
        self.assertEqual(code, status, data)
        return data

    def test_case_links_planning_checklists_idempotency_and_restart(self):
        self.assertEqual(self.call(), {'ready': False})
        self.call({'week_start': '2030-01-07'}, status=400)
        self.call({'confirmed': True, 'week_start': '2030-01-08'}, status=400)
        case = self.call({'confirmed': True, 'week_start': '2030-01-07'})
        self.assertEqual(case['customer']['name'], 'Basisschool De Egel')
        self.assertEqual(case['customer']['billing_address'], 'Europalaan 44, 1111 AA Eindhoven')
        self.assertEqual(str(case['location']['customer_id']), str(case['customer']['id']))
        self.assertEqual(case['items'][0]['weekly_hours'], '11.5')
        self.assertEqual(case['items'][0]['agreed_hours'], '460.0')
        self.assertEqual(case['items'][0]['selected_hours'], '11.5')
        self.assertEqual(len(case['workorders']), 9)
        self.assertEqual(len(case['shifts']), 9)
        for work, shift in zip(case['workorders'], case['shifts']):
            self.assertEqual(work['contract_id'], case['contract']['id'])
            self.assertEqual(shift['workorder_id'], work['id'])
            self.assertEqual(shift['employee_id'], '')
            self.assertEqual(work['workflow'], 'Concept')
        with sqlite3.connect(self.s.db) as c:
            ids = ','.join(str(x['id']) for x in case['workorders'])
            self.assertEqual(c.execute(f'SELECT COUNT(*) FROM checklist WHERE workorder_id IN ({ids})').fetchone()[0], 17)
            self.assertEqual(c.execute(f'SELECT COUNT(*) FROM hours WHERE workorder_id IN ({ids})').fetchone()[0], 0)
            self.assertEqual(c.execute(f'SELECT COUNT(*) FROM invoices WHERE workorder_id IN ({ids})').fetchone()[0], 0)
        self.assertEqual(self.call({'confirmed': True, 'week_start': '2031-01-06'})['contract']['id'], case['contract']['id'])
        self.s.stop(); self.s.start()
        self.assertEqual(self.call()['workorders'], case['workorders'])

    def test_only_administrators_and_duplicate_customer_rollback(self):
        employee = self.s.login('Bart van Aalde', 'Amocean2!')
        self.call(token=employee, status=403)
        self.call({'confirmed': True, 'week_start': '2030-01-07'}, token=employee, status=403)
        self.s.request('/api/v5/entities/customers', 'POST', {'name': 'Basisschool De Egel'}, self.token)
        self.call({'confirmed': True, 'week_start': '2030-01-07'}, status=409)
        self.assertEqual(self.call(), {'ready': False})

    def test_case_execution_hours_and_invoice_remain_linked(self):
        case = self.call({'confirmed': True, 'week_start': '2030-01-07'})
        work = case['workorders'][0]; shift = case['shifts'][0]
        def request(path, body=None, method='POST'):
            code, data, _ = self.s.request('/api/v5/'+path, method, body, self.token)
            self.assertEqual(code, 200, data)
            return data
        request('shifts/'+str(shift['id']), {'version': shift['version'], 'employee_id': '1'}, 'PUT')
        for state in ('Gepland', 'Toegewezen', 'In uitvoering'):
            work = request(f'workorders/{work["id"]}/transition', {'version': work['version'], 'state': state})
        details = request(f'workorders/{work["id"]}', method='GET')
        for task in details['checklist']:
            request(f'workorders/{work["id"]}/checklist', {'id': task['id'], 'version': task['version'], 'done': True})
        hours = request('hours', {'employee_id': 1, 'workorder_id': work['id'],
                                 'starts_at': '2030-01-07T16:00:00+01:00',
                                 'ends_at': '2030-01-07T18:00:00+01:00', 'break_minutes': 0})
        self.assertEqual(hours['hours'], '2.00')
        for state in ('Voltooid', 'Goedgekeurd'):
            work = request(f'workorders/{work["id"]}/transition', {'version': work['version'], 'state': state, 'completion_notes': 'Uitsluitend geautomatiseerde testuitvoering in tijdelijke database.'})
        request(f'hours/{hours["id"]}/review', {'version': hours['version'], 'status': 'Goedgekeurd'})
        work = request(f'workorders/{work["id"]}/transition', {'version': work['version'], 'state': 'Factureerbaar'})
        invoice = request('invoices/prepare', {'workorder_id': work['id'], 'version': work['version'], 'hourly_rate': '30', 'vat_rate': '21', 'lines': []})
        self.assertEqual(invoice['net_amount'], '60.00')
        result = self.call()
        self.assertEqual(result['hours'][0]['id'], hours['id'])
        self.assertEqual(result['invoices'][0]['id'], invoice['id'])
