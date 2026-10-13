import unittest
from playwright.sync_api import expect
import test_enterprise_browser as fixtures


class ClientCaseBrowser(unittest.TestCase):
    setUpClass = classmethod(fixtures.EnterpriseBrowser.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.EnterpriseBrowser.tearDownClass.__func__)
    setUp = fixtures.EnterpriseBrowser.setUp
    tearDown = fixtures.EnterpriseBrowser.tearDown
    login = fixtures.EnterpriseBrowser.login

    def test_dashboard_case_save_planning_assignment_and_reload(self):
        self.login()
        self.page.get_by_role('button', name='Basisschool De Egel', exact=True).click()
        self.page.locator('[name=week_start]').fill('2030-01-07')
        self.page.locator('[name=confirmed]').check()
        self.page.get_by_role('button', name='Klantdossier opslaan en openen').click()
        expect(self.page.locator('#modalbg')).to_contain_text('460 uur per jaar')
        expect(self.page.locator('#modalbg')).not_to_contain_text('presentatie')
        expect(self.page.locator('#modalbg')).to_contain_text('Europalaan 44, 1111 AA Eindhoven')
        self.assertEqual(self.page.get_by_role('button', name='Werkbon #').count(), 9)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), 391)
        self.page.get_by_role('button', name='Weekplanning openen').click()
        expect(self.page.locator('#v5body')).to_contain_text('Basisschool De Egel')
        self.assertEqual(self.page.locator('.v5-shift').count(), 6)
        self.page.reload(); self.page.locator('.daily-home').wait_for()
        self.page.get_by_role('button', name='Basisschool De Egel', exact=True).click()
        self.page.get_by_role('button', name='Werkbon #').first.click()
        self.page.get_by_role('button', name='Medewerkers voorstellen').click()
        self.page.get_by_role('button', name='Inplannen', exact=True).first.click()
        # Wait for the persisted assignment, then inspect the same existing slot.
        self.page.get_by_role('button', name='Terug naar opdracht').click()
        expect(self.page.locator('#modalbg')).to_contain_text('Medewerker #')
        case = self.s.request('/api/v5/customer-presentation', token=self.admin)[1]
        self.assertEqual(len(case['shifts']), 9)
        self.assertEqual(sum(bool(s['employee_id']) for s in case['shifts']), 1)
        self.assertEqual(case['hours'], [])
        self.assertEqual(case['invoices'], [])
