"""Policykern; nog geen bewijs van routebrede scopehandhaving."""
import sqlite3,unittest
from domain import Problem
from services import scopes

class ScopePolicy(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY); CREATE TABLE customers(id INTEGER PRIMARY KEY); CREATE TABLE objects(id INTEGER PRIMARY KEY,customer_id INTEGER); CREATE TABLE contacts(id INTEGER PRIMARY KEY,customer_id INTEGER); INSERT INTO users VALUES(1); INSERT INTO customers VALUES(1),(2),(3); INSERT INTO objects VALUES(1,1); INSERT INTO contacts VALUES(1,1),(2,2);')
  scopes.migrate(self.c)
  self.c.executemany('INSERT INTO record_scopes VALUES(?,?,?,?,1)', [('customers',1,'Schoonmaak','Noord'),('customers',2,'Schoonmaak','Zuid')])
  self.user={'id':1,'scope':{'enabled':True,'departments':['Schoonmaak'],'regions':['Noord'],'default_department':'Schoonmaak','default_region':'Noord'}}
 def tearDown(self):self.c.close()
 def test_scope_intersection_and_unclassified_denied(self):
  self.assertTrue(scopes.allowed(self.c,self.user,'customers',1))
  for rid in (2,3,999):self.assertFalse(scopes.allowed(self.c,self.user,'customers',rid))
  self.assertTrue(scopes.allowed(self.c,{'id':1},'customers',2))
 def test_children_inherit_parent_scope(self):
  self.assertTrue(scopes.allowed(self.c,self.user,'contacts',1));self.assertFalse(scopes.allowed(self.c,self.user,'contacts',2))
 def test_nested_references_cannot_cross_boundary(self):
  scopes.check_payload(self.c,self.user,{'rows':[{'customer_id':1}]})
  for body in ({'rows':[{'customer_id':2}]},{'customer_id':True},{'customer_id':{'id':1}}):
   with self.assertRaises(Problem):scopes.check_payload(self.c,self.user,body)
 def test_created_record_inherits_and_context_resets(self):
  token=scopes.ACTOR.set(self.user)
  try:scopes.classify_created(self.c,'objects',1,{'customer_id':1})
  finally:scopes.ACTOR.reset(token)
  self.assertIsNone(scopes.ACTOR.get());self.assertTrue(scopes.allowed(self.c,self.user,'objects',1))
  self.assertEqual(tuple(self.c.execute("SELECT department,region FROM record_scopes WHERE module='objects'").fetchone()),('Schoonmaak','Noord'))
 def test_policy_requires_explicit_consistent_defaults(self):
  policy=self.user['scope'].copy();self.assertEqual(scopes.validate(policy),policy)
  for changes in ({'departments':[],'regions':[]},{'default_region':'Zuid'},{'regions':'Noord'},{'enabled':'true'}):
   with self.assertRaises(Problem):scopes.validate({**policy,**changes})
 def test_sql_parameterizes_names_and_rejects_alias_injection(self):
  self.user['scope']['regions']=["Noord') OR 1=1 --"]
  clause,args=scopes.sql(self.user,'customers');self.assertNotIn('OR 1=1',clause)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM customers WHERE '+clause,args).fetchone()[0],0)
  with self.assertRaises(ValueError):scopes.sql(self.user,'customers','x; DROP TABLE users')
 def test_admin_routes_reject_non_admin(self):
  with self.assertRaises(Problem) as error:scopes.route(self.c,{'role':'planner'},['security','scopes'],'GET',{})
  self.assertEqual(error.exception.status,403)
 def test_migration_repeatable_and_unstructured_logs_fail_closed(self):
  scopes.migrate(self.c)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM record_scopes').fetchone()[0],2)
  for path in ('/api/audit','/api/v5/sync','/api/v5/customers/1/timeline'):
   with self.assertRaises(Problem):scopes.guard(self.c,self.user,path,'GET')
 def test_deleted_classification_cannot_be_inherited_by_reused_id(self):
  self.c.execute('DELETE FROM customers WHERE id=1');self.c.execute('INSERT INTO customers VALUES(1)')
  self.assertFalse(scopes.allowed(self.c,self.user,'customers',1))
 def test_unknown_tables_fail_closed(self):
  self.assertFalse(scopes.allowed(self.c,self.user,'unreviewed_table',1))
