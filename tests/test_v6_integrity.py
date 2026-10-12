import base64,sqlite3,tempfile,unittest
from pathlib import Path
from support import LiveServer
from services import encrypted_backup
class V6Integrity(unittest.TestCase):
 def setUp(self):self.s=LiveServer();self.token=self.s.login()
 def tearDown(self):self.s.close()
 def test_encrypted_backup_restore_wrong_key_and_corruption(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);key=root/'key';wrong=root/'wrong';archive=root/'backup.enc';encrypted_backup.generate(key);encrypted_backup.generate(wrong)
   encrypted_backup.backup(self.s.db,archive,key);self.assertNotIn(b'SQLite format',archive.read_bytes())
   with self.assertRaises(ValueError):encrypted_backup.restore(archive,root/'bad',wrong)
   self.assertFalse((root/'bad').exists());encrypted_backup.restore(archive,root/'restored',key)
   with sqlite3.connect(root/'restored/roefs.db') as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
   archive.write_bytes(archive.read_bytes()[:-10]+b'corruption')
   with self.assertRaises(ValueError):encrypted_backup.restore(archive,root/'corrupt',key)
 def test_audit_modification_detected_and_unauthorized_check_denied(self):
  self.s.request('/api/v5/settings','PUT',{'organization':'Fictief testbedrijf'},self.token)
  code,result,_=self.s.request('/api/v5/security/audit-integrity',token=self.token);self.assertEqual(code,200);self.assertTrue(result['ok']);self.assertGreater(result['checked'],0)
  emp=self.s.login('Bart van Aalde','Amocean2!');self.assertEqual(self.s.request('/api/v5/security/audit-integrity',token=emp)[0],403)
  with sqlite3.connect(self.s.db) as c:c.execute("UPDATE audit SET detail='Onbevoegd gewijzigd' WHERE id=(SELECT MAX(id) FROM audit)")
  self.assertFalse(self.s.request('/api/v5/security/audit-integrity',token=self.token)[1]['ok'])
 def test_pdf_quarantine_text_delete_version_and_backup(self):
  from unittest.mock import patch
  from services.file_scanning import scan
  with patch('services.file_scanning.shutil.which',return_value=None):self.assertEqual(scan(Path('/not-used'),'application/pdf')[0],'Quarantaine')
  code,file,_=self.s.request('/api/v5/files','POST',{'name':'fictief.pdf','customer_id':1,'content':base64.b64encode(b'%PDF-1.4\n%%EOF').decode()},self.token);self.assertEqual(code,200,file)
  self.assertEqual(self.s.request('/api/v5/files/'+str(file['id']),token=self.token)[0],423)
  code,txt,_=self.s.request('/api/v5/files','POST',{'name':'tekst.txt','customer_id':1,'content':base64.b64encode(b'Fictieve bijlage').decode()},self.token);self.assertEqual(code,200)
  self.assertEqual(self.s.request('/api/v5/files/'+str(txt['id']),token=self.token)[0],200)
  body={'version':1,'reason':'Fictieve bewaartermijn verstreken'}
  self.assertEqual(self.s.request('/api/v5/files/'+str(txt['id']),'DELETE',body,self.token)[0],200)
  self.assertEqual(self.s.request('/api/v5/files/'+str(txt['id']),token=self.token)[0],410)
  self.assertEqual(self.s.request('/api/v5/files/'+str(txt['id']),'DELETE',body,self.token)[0],409)
