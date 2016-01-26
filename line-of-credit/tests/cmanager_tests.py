import unittest
import psycopg2
import psycopg2.extras
from decimal import Decimal
from datetime import datetime, date, timedelta

from settings import DB_CONN_STRING

from cmanager import CreditManager
from cmanager.exceptions import (
    InvalidPayment, InvalidWithdrawal,
    WithdrawalDenied, InvalidParameterValue, SystemFailed,
    InvalidOutstandingInvocation
)

class CreditManagerTest(unittest.TestCase):
    """`CreditManagerTest` defines all the unit test
    cases for the cmanager module.
    """
    def setUp(self):
        """`setUp` prepares the data before each test case.
        """
        # set up the test constants
        self.apr = Decimal('0.350')  # 35%
        self.limit = Decimal('1000.000')  # credit limit in USD
        self.period = 30  # payment period in days

        # create a database connection to the test db based on the settings
        conn = psycopg2.connect(DB_CONN_STRING)

        # NOTE: this ideally should not be done and instead each
        # transaction has to be handled based on the application
        # logic. Since we know that there will not be many
        # simultaneous connections to the database in our usecase,
        # it is okay to autocommit each SQL query to simply some code.
        conn.autocommit = True
        
        # get the cursor object to make queries
        self.cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # set up initial seed data
        today = date.today()
        self.cursor.execute("""
            INSERT INTO 
                transaction (tstamp, amount, balance, type, description)
            VALUES ('%s', 0, %s, 'eot', 'opening balance');
        """ % (today, self.limit))  # eot -- END of Term (payment term)

        # create the credit manager object
        self.cm = CreditManager(self.apr, self.limit, self.period)
        
    def tearDown(self):
        """`tearDown` restores the state of the system after each test case.
        """
        # reset the database by deleting all the data.
        self.cursor.execute("TRUNCATE transaction;");

    def test_if_payment_on_zero_outstanding_allowed(self):
        # make a payment without any withdrawal
        self.cm.pay(Decimal('100.00'), 'sample payment')

        # check the current due
        self.assertEqual(Decimal('-100.00'), self.cm.get_current_due()) 

    def test_payment_of_zero_or_less_amount(self):
        self.assertRaises(
            InvalidPayment,
            self.cm.pay,
            amount=Decimal('0.000'),
            description='payment number 01'
        )

        self.assertRaises(
            InvalidPayment,
            self.cm.pay,
            amount=Decimal('-100.000'),
            description='payment number 02'
        )

    def test_payment_with_proper_amount(self):
        now1 = datetime.now()

        # make a payment
        self.assertEqual(self.cm.pay(Decimal('100.000'), 'payment 001'), None)

        # verify that the payment is made successfully.
        self.cursor.execute("SELECT * FROM transaction OFFSET 1;")  # ignore the first one.
        results = self.cursor.fetchall()

        # check that only one record exists
        self.assertEqual(len(results), 1)

        # inspect the record
        self.assertTrue(results[0]['tstamp'] >= now1)
        self.assertEqual(results[0]['amount'], Decimal('100.000'))
        self.assertEqual(results[0]['balance'], Decimal('1100.000')) # payment + balance
        self.assertEqual(results[0]['description'], 'payment 001')
        self.assertEqual(results[0]['type'], 'payment')

        now2 = datetime.now()
        # make another payment
        self.assertEqual(self.cm.pay(Decimal('10.000'), 'payment 002'), None)
        
        # verify that the payment is made successfully.
        self.cursor.execute("SELECT * FROM transaction OFFSET 1;")  # ignore the first one.
        results = self.cursor.fetchall()

        # check that two records exist
        self.assertEqual(len(results), 2)

        # inspect the record
        self.assertTrue(results[1]['tstamp'] >= now2 and results[1]['tstamp'] > now1)
        self.assertEqual(results[1]['amount'], Decimal('10.000'))
        self.assertEqual(results[1]['balance'], Decimal('1110.000')) # payment + balance
        self.assertEqual(results[1]['description'], 'payment 002')
        self.assertEqual(results[0]['type'], 'payment')

    def test_withdrawal_of_zero_less_amount(self):
        self.assertRaises(
            InvalidWithdrawal,
            self.cm.withdraw,
            Decimal('0.000'),
            'swiped at starbucks'
        )

        self.assertRaises(
            InvalidWithdrawal,
            self.cm.withdraw,
            Decimal('-10.000'),
            'swiped at starbucks'
        )

    def test_withdrawal_with_proper_amount(self):
        now1 = datetime.now()

        # make a withdrawal
        self.assertEqual(self.cm.withdraw(Decimal('100.000'), 'jewel osco'), None)

        # verify that the withdrawal is made successfully.
        self.cursor.execute("SELECT * FROM transaction OFFSET 1;")  # ignore the first one.
        results = self.cursor.fetchall()

        # check that only one record exists
        self.assertEqual(len(results), 1)

        # inspect the record
        self.assertTrue(results[0]['tstamp'] >= now1)
        self.assertEqual(results[0]['amount'], Decimal('-100.000'))
        self.assertEqual(results[0]['balance'], Decimal('900.000')) # payment + balance
        self.assertEqual(results[0]['description'], 'jewel osco')
        self.assertEqual(results[0]['type'], 'withdrawal')

        now2 = datetime.now()

        # make another withdrawal
        self.cm.withdraw(Decimal('10.000'), 'walmart')
        
        # verify that the withdrawal is made successfully.
        self.cursor.execute("SELECT * FROM transaction OFFSET 1;")  # ignore the first one.
        results = self.cursor.fetchall()

        # check that two records exist
        self.assertEqual(len(results), 2)

        # inspect the record
        self.assertTrue(results[1]['tstamp'] >= now2 and results[1]['tstamp'] > now1)
        self.assertEqual(results[1]['amount'], Decimal('-10.000'))
        self.assertEqual(results[1]['balance'], Decimal('890.000')) # payment + balance
        self.assertEqual(results[1]['description'], 'walmart')
        self.assertEqual(results[1]['type'], 'withdrawal') 
    
    def test_withdrawal_on_zero_balance(self):
        # withdraw the entire amount specified in the limit
        self.cm.withdraw(self.limit, 'walmart')

        # then try again.
        self.assertRaises(
            WithdrawalDenied,
            self.cm.withdraw,
            Decimal('10.000'),
            'walmart'
        )

    def test_statement_with_no_transactions(self):
        results = self.cm.get_statement()

        # inspect the results
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].has_key('tstamp'))
        self.assertEqual(results[0]['amount'], Decimal('0.000'))
        self.assertEqual(results[0]['type'], 'eot')
        self.assertEqual(results[0]['description'], 'opening balance')

    def test_statement_with_multiple_transactions(self):
        now = datetime.now()
        
        # make three different transactions
        self.cm.withdraw(Decimal('10.000'), 'walmart')
        self.cm.withdraw(Decimal('20.000'), 'jewel osco')
        self.cm.pay(Decimal('10.000'), 'payment 001')

        results = self.cm.get_statement()
        
        # inspect the results
        self.assertEqual(len(results), 4)

        # results[0] will be the opening balance line, ignore.

        self.assertTrue(results[1]['tstamp'] > now)
        self.assertEqual(results[1]['amount'], Decimal('-10.000'))
        
        self.assertTrue(results[2]['tstamp'] > now)
        self.assertEqual(results[2]['amount'], Decimal('-20.000'))
        
        self.assertTrue(results[3]['tstamp'] > now)
        self.assertEqual(results[3]['amount'], Decimal('10.000'))
        
        # TODO: test statement with transaction dates
        
    def test_due_when_no_transactions_are_done(self):
        self.assertEqual(Decimal('0.000'), self.cm.get_current_due())

    def test_compute_outstanding_case_02(self):
        # case 02: mentioned in the github problem statement
        # https://github.com/avantcredit/programming_challenges/blob/master/line_of_credit_test#L32-L35

        # on day 1: (ie. after 0 days logically) draws $500 on day 1 (his balance / remaining credit limit is now $500)
        day00 = datetime.now()
        self.cm.withdraw(Decimal('500.000'), 'first withdraw', day00)

        # after 15 days: pays back $200
        day15 = day00 + timedelta(days=15) 
        self.cm.pay(Decimal('200.000'), 'first payment', day15)

        # after 25 days: draws another $100
        day25 = day00 + timedelta(days=25)
        self.cm.withdraw(Decimal('100.000'), 'second withdraw', day25)

        # after 29 days: time to check the total payment which he has to make (a.k.a outstanding)
        day29 = day00 + timedelta(days=29)
        self.assertEqual(self.cm.get_current_due(day29), Decimal('400.000'))

        # after 29 days: try calling compute_outstanding. It should fail since
        # we haven't reached 30 days.
        self.assertRaises(
            Exception,
            self.cm.compute_outstanding,
            day29
        )

        # after 30 days: 30 days have passed. Let us now compute the outstanding
        # and check the total due.
        day30 = day00 + timedelta(days=30)
        self.assertEqual(self.cm.compute_outstanding(day30), Decimal('411.99'))

    def test_compute_outstanding_case_01(self):
        # case 01: mentioned in the github problem statement
        # https://github.com/avantcredit/programming_challenges/blob/master/line_of_credit_test#L22-L26

        # on day 1 (after 0 days technically): draws $500 on day 1 (his balance / remaining credit limit is now $500)
        day00 = datetime.now()
        self.cm.withdraw(Decimal('500.000'), 'first withdraw', day00)

        # after 30 days: 30 days have passed. Let us now compute the outstanding
        # and check the total due.
        day30 = day00 + timedelta(days=30)
        self.assertEqual(self.cm.compute_outstanding(day30), Decimal('514.39'))

    def test_compute_outstanding_case_03(self):
        # additional: case 03
        # on day 1: draws $500
        day00 = datetime.now()
        self.cm.withdraw(Decimal('500.000'), 'first withdraw', day00)

        # after 25 days: he repays the amount (with $100 extra)
        day25 = day00 + timedelta(days=25)
        self.cm.pay(Decimal('600.000'), 'first payment', day25)

        # after 27 days: he draws $150 more
        day27 = day00 + timedelta(days=27)
        self.cm.withdraw(Decimal('150.000'), 'second withdraw', day27)

        # after 30 days: 30 days have passed. Let us now compute the outstanding
        # and check the total due.
        day30 = day00 + timedelta(days=30)
        self.assertEqual(self.cm.compute_outstanding(day30), Decimal('50.00'))

    def test_withdrawal_on_excess_payment(self):
        self.assertEqual(self.cm.pay(Decimal('2000.00'), 'making extra payment'), None)
        self.assertEqual(self.cm.withdraw(Decimal('2500.00'), 'withdrawing more than the limit'), None)

        # check the due
        self.assertEqual(self.cm.get_current_due(), Decimal('500.000'))

def main():
    unittest.main()

if __name__ == '__main__':
    main()
