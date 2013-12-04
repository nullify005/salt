# -*- coding: utf-8 -*-

# Import python libs
import os
import logging

from mock import patch, MagicMock

# Import Salt Testing libs
from salttesting import skipIf
from salttesting.helpers import (
    destructiveTest,
    ensure_in_syspath,
    requires_system_grains
)
ensure_in_syspath('../../')

# Import salt libs
import integration
import salt.utils
from salt.modules import mysql as mysqlmod

log = logging.getLogger(__name__)

NO_MYSQL = False
try:
    import MySQLdb
except Exception:
    NO_MYSQL = True


@skipIf(NO_MYSQL, 'Install MySQL bindings and a MySQL Server before running MySQL integration tests.')
class MysqlModuleDbTest(integration.ModuleCase,
                      integration.SaltReturnAssertsMixIn):

    user = 'root'
    password = 'poney'

    @destructiveTest
    def setUp(self):
        '''
        Test presence of MySQL server, enforce a root password
        '''
        super(MysqlModuleDbTest, self).setUp()
        NO_MYSQL_SERVER = True
        # now ensure we know the mysql root password
        # one of theses two at least should work
        ret1 = self.run_state(
            'cmd.run',
             name='mysqladmin -u '
               + self.user
               + ' flush-privileges password "'
               + self.password
               + '"'
        )
        ret2 = self.run_state(
            'cmd.run',
             name='mysqladmin -u '
               + self.user
               + ' --password="'
               + self.password
               + '" flush-privileges password "'
               + self.password
               + '"'
        )
        key, value = ret2.popitem()
        if value['result']:
            NO_MYSQL_SERVER = False
        else:
            self.skipTest('No MySQL Server running, or no root access on it.')

    def _db_creation_loop(self, db_name, returning_name, **kwargs):
        '''
        Used in testCase, create, check existence, check name in db list and removes database
        '''
        ret = self.run_function(
            'mysql.db_create',
            name=db_name,
            **kwargs
        )
        self.assertEqual(True, ret, 'Problem while creating db for db name: {0!r}'.format(db_name))
        # test db exists
        ret = self.run_function(
            'mysql.db_exists',
            name=db_name,
            **kwargs
        )
        self.assertEqual(True, ret, 'Problem while testing db exists for db name: {0!r}'.format(db_name))
        # List db names to ensure db is created with the right utf8 string
        ret = self.run_function(
            'mysql.db_list',
            **kwargs
        )
        if not isinstance(ret, list):
            raise AssertionError(
                    'Unexpected query result while retrieving databases list {0!r} for {1!r} test'.format(
                         ret,
                         db_name
                    )
                )
        self.assertIn(returning_name,
                      ret,
                      ('Problem while testing presence of db name in db lists'
                       ' for db name: {0!r} in list {1!r}').format(
                          db_name,
                          ret
                     ))
        # Now remove database
        ret = self.run_function(
            'mysql.db_remove',
            name=db_name,
            **kwargs
        )
        self.assertEqual(True, ret, 'Problem while removing db for db name: {0!r}'.format(db_name))

    @destructiveTest
    def test_database_creation_level1(self):
        '''
        Create database, test presence, then drop db. All theses with complex names.
        '''
        # name with space
        db_name = 'foo 1'
        self._db_creation_loop(db_name=db_name,
                               returning_name=db_name,
                               connection_user=self.user,
                               connection_pass=self.password
        )

        # ```````
        # create
        # also with character_set and collate only
        ret = self.run_function(
          'mysql.db_create',
          name='foo`2',
          character_set='utf8',
          collate='utf8_general_ci',
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(True, ret)
        # test db exists
        ret = self.run_function(
          'mysql.db_exists',
          name='foo`2',
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(True, ret)
        # redoing the same should fail
        # even with other character sets or collations
        ret = self.run_function(
          'mysql.db_create',
          name='foo`2',
          character_set='utf8',
          collate='utf8_general_ci',
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(False, ret)
        # redoing the same should fail
        ret = self.run_function(
          'mysql.db_create',
          name='foo`2',
          character_set='utf8',
          collate='utf8_general_ci',
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(False, ret)
        # Now remove database
        ret = self.run_function(
          'mysql.db_remove',
          name='foo`2',
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(True, ret)

        # '''''''
        # create
        # also with character_set only
        db_name = "foo'3"
        self._db_creation_loop(db_name=db_name,
                               returning_name=db_name,
                               character_set='utf8',
                               connection_user=self.user,
                               connection_pass=self.password
        )

        # """"""""
        # also with collate only
        db_name = 'foo"4'
        self._db_creation_loop(db_name=db_name,
                               returning_name=db_name,
                               collate='utf8_general_ci',
                               connection_user=self.user,
                               connection_pass=self.password
        )
        # fuzzy
        db_name = '<foo` --"5>'
        self._db_creation_loop(db_name=db_name,
                               returning_name=db_name,
                               connection_user=self.user,
                               connection_pass=self.password
        )

    @destructiveTest
    def test_database_creation_utf8(self):
        '''
        Test support of utf8 in database names
        '''
        # Simple accents : using utf8 string
        db_name_unicode = u'notam\xe9rican'
        # same as 'notamérican' because of file encoding
        # but ensure it on this test
        db_name_utf8 = 'notam\xc3\xa9rican'
        db_name = db_name_utf8
        self._db_creation_loop(db_name=db_name_utf8,
                               returning_name=db_name_utf8,
                               connection_user=self.user,
                               connection_pass=self.password,
                               connection_use_unicode=True,
                               connection_charset='utf8',
                               saltenv={"LC_ALL": "en_US.utf8"}
        )
        # test unicode entry will also return utf8 name
        self._db_creation_loop(db_name=db_name_unicode,
                               returning_name=db_name_utf8,
                               connection_user=self.user,
                               connection_pass=self.password,
                               connection_use_unicode=True,
                               connection_charset='utf8',
                               saltenv={"LC_ALL": "en_US.utf8"}
        )
        # Using more complex unicode characters:
        db_name_unicode = u'\u6a19\u6e96\u8a9e'
        # same as '標準語' because of file encoding
        # but ensure it on this test
        db_name_utf8 = '\xe6\xa8\x99\xe6\xba\x96\xe8\xaa\x9e'
        self._db_creation_loop(db_name=db_name_utf8,
                               returning_name=db_name_utf8,
                               connection_user=self.user,
                               connection_pass=self.password,
                               connection_use_unicode=True,
                               connection_charset='utf8',
                               saltenv={"LC_ALL": "en_US.utf8"}
        )
        # test unicode entry will also return utf8 name
        self._db_creation_loop(db_name=db_name_unicode,
                               returning_name=db_name_utf8,
                               connection_user=self.user,
                               connection_pass=self.password,
                               connection_use_unicode=True,
                               connection_charset='utf8',
                               saltenv={"LC_ALL": "en_US.utf8"}
        )

    @destructiveTest
    def test_database_maintenance(self):
        '''
        Test maintenance operations on a created database
        '''
        dbname = u"foo'-- `\"'"
        # create database
        # but first silently try to remove it
        # in case of previous tests failures
        ret = self.run_function(
          'mysql.db_remove',
          name=dbname,
          connection_user=self.user,
          connection_pass=self.password
        )
        ret = self.run_function(
          'mysql.db_create',
          name=dbname,
          character_set='utf8',
          collate='utf8_general_ci',
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(True, ret)
        # test db exists
        ret = self.run_function(
          'mysql.db_exists',
          name=dbname,
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(True, ret)
        # Create 3 tables
        tablenames = {'Atable "`1': 'MYISAM', 'Btable \'`2': 'InnoDB', 'Ctable --`3': 'MEMORY'}
        for tablename, engine in iter(sorted(tablenames.iteritems())):
            # prepare queries
            create_query = ('CREATE TABLE %(tblname)s ('
                ' id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,'
                ' data VARCHAR(100)) ENGINE=%(engine)s;') % dict(
                    tblname=mysqlmod.quote_identifier(tablename),
                    engine=engine,
                )
            insert_query = ('INSERT INTO %(tblname)s (data)'
                ' VALUES ') % dict(tblname=mysqlmod.quote_identifier(tablename))
            delete_query = ('DELETE from  %(tblname)s'
                ' order by rand() limit 50;') % dict(tblname=mysqlmod.quote_identifier(tablename))
            for x in range(100):
                insert_query += "('foo"+str(x)+"'),"
            insert_query += "('bar');"

            # populate database
            log.info('Adding table{0!r}'.format(tablename,))
            ret = self.run_function(
              'mysql.query',
              database=dbname,
              query=create_query,
              connection_user=self.user,
              connection_pass=self.password
            )
            if not isinstance(ret, dict) or 'rows affected' not in ret:
                raise AssertionError(
                    'Unexpected query result while populating test table {0!r} : {1!r}'.format(
                         tablename,
                         ret,
                    )
                )
            self.assertEqual(ret['rows affected'], 0)
            log.info('Populating table{0!r}'.format(tablename,))
            ret = self.run_function(
              'mysql.query',
              database=dbname,
              query=insert_query,
              connection_user=self.user,
              connection_pass=self.password
            )
            if not isinstance(ret, dict) or 'rows affected' not in ret:
                raise AssertionError(
                    'Unexpected query result while populating test table {0!r} : {1!r}'.format(
                         tablename,
                         ret,
                    )
                )
            self.assertEqual(ret['rows affected'], 101)
            log.info('Removing some rows on table{0!r}'.format(tablename,))
            ret = self.run_function(
              'mysql.query',
              database=dbname,
              query=delete_query,
              connection_user=self.user,
              connection_pass=self.password
            )
            if not isinstance(ret, dict) or 'rows affected' not in ret:
                raise AssertionError(
                    ('Unexpected query result while removing rows on test table'
                     ' {0!r} : {1!r}').format(
                         tablename,
                         ret,
                    )
                )
            self.assertEqual(ret['rows affected'], 50)
        # test check/repair/opimize on 1 table
        tablename = 'Atable "`1'
        ret = self.run_function(
          'mysql.db_check',
          name=dbname,
          table=tablename,
          connection_user=self.user,
          connection_pass=self.password
        )
        # Note that returned result does not quote_identifier of table and db
        self.assertEqual(ret, [{'Table': dbname+'.'+tablename, 'Msg_text': 'OK', 'Msg_type': 'status', 'Op': 'check'}])
        ret = self.run_function(
          'mysql.db_repair',
          name=dbname,
          table=tablename,
          connection_user=self.user,
          connection_pass=self.password
        )
        # Note that returned result does not quote_identifier of table and db
        self.assertEqual(ret, [{'Table': dbname+'.'+tablename, 'Msg_text': 'OK', 'Msg_type': 'status', 'Op': 'repair'}])
        ret = self.run_function(
          'mysql.db_optimize',
          name=dbname,
          table=tablename,
          connection_user=self.user,
          connection_pass=self.password
        )
        # Note that returned result does not quote_identifier of table and db
        self.assertEqual(ret, [{'Table': dbname+'.'+tablename, 'Msg_text': 'OK', 'Msg_type': 'status', 'Op': 'optimize'}])

        # test check/repair/opimize on all tables
        ret = self.run_function(
          'mysql.db_check',
          name=dbname,
          connection_user=self.user,
          connection_pass=self.password
        )
        expected = []
        for tablename, engine in iter(sorted(tablenames.iteritems())):
            if engine is 'MEMORY':
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': "The storage engine for the table doesn't support check",
                    'Msg_type': 'note',
                    'Op': 'check'
                }])
            else:
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': 'OK',
                    'Msg_type': 'status',
                    'Op': 'check'
                }])
        self.assertEqual(ret, expected)

        ret = self.run_function(
          'mysql.db_repair',
          name=dbname,
          connection_user=self.user,
          connection_pass=self.password
        )
        expected = []
        for tablename, engine in iter(sorted(tablenames.iteritems())):
            if engine is 'MYISAM':
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': 'OK',
                    'Msg_type': 'status',
                    'Op': 'repair'
                }])
            else:
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': "The storage engine for the table doesn't support repair",
                    'Msg_type': 'note',
                    'Op': 'repair'
                }])
        self.assertEqual(ret, expected)

        ret = self.run_function(
          'mysql.db_optimize',
          name=dbname,
          connection_user=self.user,
          connection_pass=self.password
        )

        expected = []
        for tablename, engine in iter(sorted(tablenames.iteritems())):
            if engine is 'MYISAM':
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': 'OK',
                    'Msg_type': 'status',
                    'Op': 'optimize'
                }])
            elif engine is 'InnoDB':
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': ("Table does not support optimize, "
                                 "doing recreate + analyze instead"),
                    'Msg_type': 'note',
                    'Op': 'optimize'
                },
                {
                    'Table': dbname+'.'+tablename,
                    'Msg_text': 'OK',
                    'Msg_type': 'status',
                    'Op': 'optimize'
                }])
            elif engine is 'MEMORY':
                expected.append([{
                    'Table': dbname+'.'+tablename,
                    'Msg_text': "The storage engine for the table doesn't support optimize",
                    'Msg_type': 'note',
                    'Op': 'optimize'
                }])
        self.assertEqual(ret, expected)
        # Teardown, remove database
        ret = self.run_function(
          'mysql.db_remove',
          name=dbname,
          connection_user=self.user,
          connection_pass=self.password
        )
        self.assertEqual(True, ret)


@skipIf(NO_MYSQL, 'Install MySQL bindings and a MySQL Server before running MySQL integration tests.')
class MysqlModuleUserTest(integration.ModuleCase,
                      integration.SaltReturnAssertsMixIn):

    user = 'root'
    password = 'poney'

    @destructiveTest
    def setUp(self):
        '''
        Test presence of MySQL server, enforce a root password
        '''
        super(MysqlModuleUserTest, self).setUp()
        NO_MYSQL_SERVER = True
        # now ensure we know the mysql root password
        # one of theses two at least should work
        ret1 = self.run_state(
            'cmd.run',
             name='mysqladmin -u '
               + self.user
               + ' flush-privileges password "'
               + self.password
               + '"'
        )
        ret2 = self.run_state(
            'cmd.run',
             name='mysqladmin -u '
               + self.user
               + ' --password="'
               + self.password
               + '" flush-privileges password "'
               + self.password
               + '"'
        )
        key, value = ret2.popitem()
        if value['result']:
            NO_MYSQL_SERVER = False
        else:
            self.skipTest('No MySQL Server running, or no root access on it.')


    def _userCreationLop(self, uname, host, password=None, new_password=None, new_password_hash=None, **kwargs):
        '''
        Perform some tests around creation of the given user
        '''
        # First silently remove it, in case of
        ret = self.run_function(
            'mysql.user_remove',
            user=uname,
            host=host,
            **kwargs
        )
        # creation
        ret = self.run_function(
            'mysql.user_create',
            user=uname,
            host=host,
            password=password,
            **kwargs
        )
        self.assertEqual(True, ret, ('Calling user_create on'
            ' user {0!r} did not return True: {1}').format(
            uname,
            repr(ret)
        ))
        # double creation failure
        ret = self.run_function(
            'mysql.user_create',
            user=uname,
            host=host,
            password=password,
            **kwargs
        )
        self.assertEqual(False, ret, ('Calling user_create a second time on'
            ' user {0!r} did not return False: {1}').format(
            uname,
            repr(ret)
        ))
        # Alter password
        if not new_password is None or new_password_hash is not None:
            ret = self.run_function(
                'mysql.user_chpass',
                user=uname,
                host=host,
                password=new_password,
                password_hash=new_password_hash,
                connection_user=self.user,
                connection_pass=self.password,
                connection_use_unicode=True,
                connection_charset='utf8',
                saltenv={"LC_ALL": "en_US.utf8"}
            )
            self.assertEqual(True, ret, ('Calling user_chpass on'
                ' user {0!r} did not return True: {1}').format(
                uname,
                repr(ret)
            ))


    def _chck_userinfo(self, user, host, check_user, check_hash):
        '''
        Internal routine to check user_info returned results
        '''
        ret = self.run_function(
            'mysql.user_info',
            user=user,
            host=host,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        if not isinstance(ret, dict):
            raise AssertionError(
                'Unexpected result while retrieving user_info for {0!r}'.format(
                    user
                )
            )
        self.assertEqual(ret['Host'],host)
        self.assertEqual(ret['Password'], check_hash)
        self.assertEqual(ret['User'], check_user)

    def _chk_remove_user(self, user, host, **kwargs):
        '''
        Internal routine to check user_remove
        '''
        ret = self.run_function(
            'mysql.user_remove',
            user=user,
            host=host,
            **kwargs
        )
        self.assertEqual(True,ret, ('Assertion failed  while removing user'
            ' {0!r} on host {1!r}: {2}').format(
            user,
            host,
            repr(ret)
        ))

    @destructiveTest
    def test_user_management(self):
        '''
        Test various users creation settings
        '''
        
        # Create users with rights on this database
        # and rights on other databases
        user1 = "user '1"
        user1_pwd = 'pwd`\'"1b'
        user1_pwd_hash = '*4DF33B3B12E43384677050A818327877FAB2F4BA'
        # this is : user "2'標
        user2 = 'user "2\'\xe6\xa8\x99'
        user2_pwd = 'user "2\'\xe6\xa8\x99b'
        user2_pwd_hash = '*3A38A7B94B024B983687BB9B44FB60B7AA38FE61'
        user3 = 'user "3;,?:@=&/'
        user3_pwd = 'user "3;,?:@=&/'
        user3_pwd_hash = '*AA3B1D4105A45D381C23A5C221C47EA349E1FD7D'
        # this is : user ":=;4標 in unicode instead of utf-8
        # if unicode char is counted as 1 char we hit the max user 
        # size (16)
        user4 = u'user":;,?:@=&/4\u6a19'
        user4_utf8 = 'user":;,?:@=&/4\xe6\xa8\x99'
        user4_pwd = 'user "4;,?:@=&/'
        user4_pwd_hash = '*FC8EF8DBF27628E4E113359F8E7478D5CF3DD57C'
        user5 = u'user ``"5'
        user5_utf8 = 'user ``"5'
        # this is 標標標\
        user5_pwd = '\xe6\xa8\x99\xe6\xa8\x99\\'
        # this is password('標標\\')
        user5_pwd_hash = '*3752E65CDD8751AF8D889C62CFFC6C998B12C376'
        user6 = u'user %--"6'
        user6_utf8 = 'user %--"6'
        # this is : --'"% SIX標b
        user6_pwd_u = u' --\'"% SIX\u6a19b'
        user6_pwd_utf8 = ' --\'"% SIX\xe6\xa8\x99b'
        # this is password(' --\'"% SIX標b')
        user6_pwd_hash = '*90AE800593E2D407CD9E28CCAFBE42D17EEA5369'
        self._userCreationLop(
            uname=user1,
            host='localhost',
            password='pwd`\'"1',
            new_password='pwd`\'"1b',
            connection_user=self.user,
            connection_pass=self.password
        )
        # Now check for results
        ret = self.run_function(
            'mysql.user_exists',
            user=user1,
            host='localhost',
            password=user1_pwd,
            password_hash=None,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' existence failed').format(user1, 'localhost')
        )

        self._userCreationLop(
            uname=user2,
            host='localhost',
            password=None,
            # this is his name hash : user "2'標
            password_hash='*EEF6F854748ACF841226BB1C2422BEC70AE7F1FF',
            # and this is the same with a 'b' added
            new_password_hash=user2_pwd_hash,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        # user2 can connect from other places with other password
        self._userCreationLop(
            uname=user2,
            host='10.0.0.1',
            allow_passwordless=True,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self._userCreationLop(
            uname=user2,
            host='10.0.0.2',
            allow_passwordless=True,
            unix_socket=True,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        # Now check for results
        ret = self.run_function(
            'mysql.user_exists',
            user=user2,
            host='localhost',
            password=None,
            password_hash=user2_pwd_hash,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' failed').format(user2, 'localhost')
        )
        ret = self.run_function(
            'mysql.user_exists',
            user=user2,
            host='10.0.0.1',
            allow_passwordless=True,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' without password failed').format(user2, '10.0.0.1')
        )
        ret = self.run_function(
            'mysql.user_exists',
            user=user2,
            host='10.0.0.2',
            allow_passwordless=True,
            unix_socket=True,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' without password failed').format(user2, '10.0.0.2')
        )

        # Empty password is not passwordless (or is it a bug?)
        self._userCreationLop(
            uname=user3,
            host='localhost',
            password='',
            connection_user=self.user,
            connection_pass=self.password
        )
        # user 3 on another host with a password
        self._userCreationLop(
            uname=user3,
            host='%',
            password='foo',
            new_password=user3_pwd,
            connection_user=self.user,
            connection_pass=self.password
        )
        # Now check for results
        ret = self.run_function(
            'mysql.user_exists',
            user=user3,
            host='localhost',
            password='',
            connection_user=self.user,
            connection_pass=self.password
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' without empty password failed').format(user3, 'localhost')
        )
        ret = self.run_function(
            'mysql.user_exists',
            user=user3,
            host='%',
            password=user3_pwd,
            connection_user=self.user,
            connection_pass=self.password
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' with password failed').format(user3, '%')
        )

        # check unicode name, and password > password_hash
        self._userCreationLop(
            uname=user4,
            host='%',
            password=user4_pwd,
            # this is password('foo')
            password_hash='*F3A2A51A9B0F2BE2468926B4132313728C250DBF',
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        # Now check for results
        ret = self.run_function(
            'mysql.user_exists',
            user=user4_utf8,
            host='%',
            password=user4_pwd,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' with password take from password and not password_hash'
            ' failed').format(user4_utf8, '%')
        )
        self._userCreationLop(
            uname=user5,
            host='localhost',
            password='\xe6\xa8\x99\xe6\xa8\x99',
            new_password=user5_pwd,
            unix_socket=True,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        ret = self.run_function(
            'mysql.user_exists',
            user=user5_utf8,
            host='localhost',
            password=user5_pwd,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' with utf8 password failed').format(user5_utf8, 'localhost')
        )
        # for this one we give password in unicode and check it in utf-8
        self._userCreationLop(
            uname=user6,
            host='10.0.0.1',
            password=' foobar',
            new_password=user6_pwd_u,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        # Now check for results
        ret = self.run_function(
            'mysql.user_exists',
            user=user6_utf8,
            host='10.0.0.1',
            password=user6_pwd_utf8,
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertEqual(True, ret, ('Testing final user {0!r} on host {1!r}'
            ' with unicode password failed').format(user6_utf8,'10.0.0.1')
        )
        # Final result should be:
        # mysql> select Host, User, Password from user where user like 'user%';
        # +--------------------+-----------+-------------------------------------------+
        # | User               | Host      | Password                                  |
        # +--------------------+-----------+-------------------------------------------+
        # | user "2'標         | 10.0.0.1  |                                           |
        # | user "2'標         | 10.0.0.2  |                                           |
        # | user "2'標         | localhost | *3A38A7B94B024B983687BB9B44FB60B7AA38FE61 |
        # | user "3;,?:@=&/    | %         | *AA3B1D4105A45D381C23A5C221C47EA349E1FD7D |
        # | user "3;,?:@=&/    | localhost |                                           |
        # | user %--"6         | 10.0.0.1  | *90AE800593E2D407CD9E28CCAFBE42D17EEA5369 |
        # | user '1            | localhost | *4DF33B3B12E43384677050A818327877FAB2F4BA |
        # | user ``"5          | localhost | *3752E65CDD8751AF8D889C62CFFC6C998B12C376 |
        # | user":;,?:@=&/4標  | %         | *FC8EF8DBF27628E4E113359F8E7478D5CF3DD57C |
        # +--------------------+-----------+-------------------------------------------
        self._chck_userinfo(user=user2,
                            host='10.0.0.1',
                            check_user=user2,
                            check_hash=''
        )
        self._chck_userinfo(user=user2,
                            host='10.0.0.2',
                            check_user=user2,
                            check_hash=''
        )
        self._chck_userinfo(user=user2,
                            host='localhost',
                            check_user=user2,
                            check_hash=user2_pwd_hash
        )
        self._chck_userinfo(user=user3,
                            host='%',
                            check_user=user3,
                            check_hash=user3_pwd_hash
        )
        self._chck_userinfo(user=user3,
                            host='localhost',
                            check_user=user3,
                            check_hash=''
        )
        self._chck_userinfo(user=user4,
                            host='%',
                            check_user=user4_utf8,
                            check_hash=user4_pwd_hash
        )
        self._chck_userinfo(user=user6,
                            host='10.0.0.1',
                            check_user=user6_utf8,
                            check_hash=user6_pwd_hash
        )
        self._chck_userinfo(user=user1,
                            host='localhost',
                            check_user=user1,
                            check_hash=user1_pwd_hash
        )
        self._chck_userinfo(user=user5,
                            host='localhost',
                            check_user=user5_utf8,
                            check_hash=user5_pwd_hash
        )
        # check user_list function
        ret = self.run_function(
            'mysql.user_list',
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertIn({'Host': 'localhost', 'User': user1}, ret)
        self.assertIn({'Host': 'localhost', 'User': user2}, ret)
        self.assertIn({'Host': '10.0.0.1', 'User': user2}, ret)
        self.assertIn({'Host': '10.0.0.2', 'User': user2}, ret)
        self.assertIn({'Host': '%', 'User': user3}, ret)
        self.assertIn({'Host': 'localhost', 'User': user3}, ret)
        self.assertIn({'Host': '%', 'User': user4_utf8}, ret)
        self.assertIn({'Host': 'localhost', 'User': user5_utf8}, ret)
        self.assertIn({'Host': '10.0.0.1', 'User': user6_utf8}, ret)
        
        # And finally, test connections on MySQL with theses users
        ret = self.run_function(
            'mysql.query',
            database='information_schema',
            query='SELECT 1',
            connection_user=user1,
            connection_pass='pwd`\'"1b',
            connection_host='localhost'
        )
        if not isinstance(ret, dict) or not 'results' in ret:
            raise AssertionError(
                ('Unexpected result while testing connection'
                ' with user {0!r}: {1}').format(
                    user1,
                    repr(ret)
                )
            )
        self.assertEqual([['1']], ret['results'])
        
        # FIXME: still failing, but works by hand...
        # mysql --user="user \"2'標" --password="user \"2'標b" information_schema
        # Seems to be a python-mysql library problem with user names containing
        # utf8 characters
        #import urllib
        #ret = self.run_function(
        #    'mysql.query',
        #    database='information_schema',
        #    query='SELECT 1',
        #    connection_user=urllib.quote_plus(user2),
        #    connection_pass=urllib.quote_plus(user2_pwd),
        #    connection_host='localhost',
        #    connection_use_unicode=True,
        #    connection_charset='utf8',
        #    saltenv={"LC_ALL": "en_US.utf8"}
        #)
        #if not isinstance(ret, dict) or not 'results' in ret:
        #    raise AssertionError(
        #        ('Unexpected result while testing connection'
        #        ' with user {0!r}: {1}').format(
        #            user2,
        #            repr(ret)
        #        )
        #    )
        #self.assertEqual([['1']], ret['results'])
        ret = self.run_function(
            'mysql.query',
            database='information_schema',
            query='SELECT 1',
            connection_user=user3,
            connection_pass='',
            connection_host='localhost',
        )
        if not isinstance(ret, dict) or not 'results' in ret:
            raise AssertionError(
                ('Unexpected result while testing connection'
                ' with user {0!r}: {1}').format(
                    user3,
                    repr(ret)
                )
            )
        self.assertEqual([['1']], ret['results'])
        # FIXME: Failing
        #ret = self.run_function(
        #    'mysql.query',
        #    database='information_schema',
        #    query='SELECT 1',
        #    connection_user=user4_utf8,
        #    connection_pass=user4_pwd,
        #    connection_host='localhost',
        #    connection_use_unicode=True,
        #    connection_charset='utf8',
        #    saltenv={"LC_ALL": "en_US.utf8"}
        #)
        #if not isinstance(ret, dict) or not 'results' in ret:
        #    raise AssertionError(
        #        ('Unexpected result while testing connection'
        #        ' with user {0!r}: {1}').format(
        #            user4_utf8,
        #            repr(ret)
        #        )
        #    )
        #self.assertEqual([['1']], ret['results'])
        ret = self.run_function(
            'mysql.query',
            database='information_schema',
            query='SELECT 1',
            connection_user=user5_utf8,
            connection_pass=user5_pwd,
            connection_host='localhost',
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        if not isinstance(ret, dict) or not 'results' in ret:
            raise AssertionError(
                ('Unexpected result while testing connection'
                ' with user {0!r}: {1}').format(
                    user5_utf8,
                   repr(ret)
                )
            )
        self.assertEqual([['1']], ret['results'])

        # Teardown by deleting with user_remove
        self._chk_remove_user(user=user2,
                              host='10.0.0.1',
                              connection_user=self.user,
                              connection_pass=self.password,
                              connection_use_unicode=True,
                              connection_charset='utf8',
                              saltenv={"LC_ALL": "en_US.utf8"}
        )
        self._chk_remove_user(user=user2,
                              host='10.0.0.2',
                              connection_user=self.user,
                              connection_pass=self.password,
                              connection_use_unicode=True,
                              connection_charset='utf8',
                              saltenv={"LC_ALL": "en_US.utf8"}
        )
        self._chk_remove_user(user=user2,
                              host='localhost',
                              connection_user=self.user,
                              connection_pass=self.password,
                              connection_use_unicode=True,
                              connection_charset='utf8',
                              saltenv={"LC_ALL": "en_US.utf8"}
        )
        self._chk_remove_user(user=user3,
                              host='%',
                              connection_user=self.user,
                              connection_pass=self.password,
        )
        self._chk_remove_user(user=user3,
                              host='localhost',
                              connection_user=self.user,
                              connection_pass=self.password,
        )
        self._chk_remove_user(user=user4,
                              host='%',
                              connection_user=self.user,
                              connection_pass=self.password,
                              connection_use_unicode=True,
                              connection_charset='utf8',
                              saltenv={"LC_ALL": "en_US.utf8"}
        )
        self._chk_remove_user(user=user6,
                              host='10.0.0.1',
                              connection_user=self.user,
                              connection_pass=self.password,
        )
        self._chk_remove_user(user=user1,
                              host='localhost',
                              connection_user=self.user,
                              connection_pass=self.password,
        )
        self._chk_remove_user(user=user5,
                              host='localhost',
                              connection_user=self.user,
                              connection_pass=self.password,
        )
        # Final verification of the cleanup
        ret = self.run_function(
            'mysql.user_list',
            connection_user=self.user,
            connection_pass=self.password,
            connection_use_unicode=True,
            connection_charset='utf8',
            saltenv={"LC_ALL": "en_US.utf8"}
        )
        self.assertNotIn({'Host': 'localhost', 'User': user1}, ret)
        self.assertNotIn({'Host': 'localhost', 'User': user2}, ret)
        self.assertNotIn({'Host': '10.0.0.1', 'User': user2}, ret)
        self.assertNotIn({'Host': '10.0.0.2', 'User': user2}, ret)
        self.assertNotIn({'Host': '%', 'User': user3}, ret)
        self.assertNotIn({'Host': 'localhost', 'User': user3}, ret)
        self.assertNotIn({'Host': '%', 'User': user4_utf8}, ret)
        self.assertNotIn({'Host': 'localhost', 'User': user5_utf8}, ret)
        self.assertNotIn({'Host': '10.0.0.1', 'User': user6_utf8}, ret)

if __name__ == '__main__':
    from integration import run_tests
    run_tests(MysqlModuleDbTest,MysqlModuleUserTest)
