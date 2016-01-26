import psycopg2
import psycopg2.extras
from decimal import Decimal, ROUND_UP
from datetime import datetime, timedelta, date

from settings import DB_CONN_STRING

from exceptions import (
    InvalidPayment, InvalidWithdrawal,
    WithdrawalDenied, InvalidParameterValue, SystemFailed,
    InvalidOutstandingInvocation
)

class CreditManager(object):
    """`CreditManager` class provides a simple mechanism to
    manage credit without understanding the lower level details
    of how the credit management works.
    """
    
    def __init__(self, apr, limit, period):
        try:
            # get a connection to database.
            conn = psycopg2.connect(DB_CONN_STRING)
        except Exception as e:
            raise SystemFailed(e.message)
        
        # NOTE: this ideally should not be done and instead each
        # transaction has to be handled based on the application
        # logic. Since we know that there will not be many
        # simultaneous connections to the database in our usecase,
        # it is okay to autocommit each SQL query to simply some code.
        conn.autocommit = True
                    
        # get the cursor object to make queries
        self.cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # check for apr validity
        if apr <= Decimal('0.000'):
            raise InvalidParameterValue("Invalid apr value")
        self.apr = apr

        # check for credit limit validity
        if limit <= Decimal('0.000'):
            raise InvalidParameterValue("Invalid credit limit value")
        self.limit = limit

        # check for payment period
        if period <= 0:
            raise InvalidParameterValue("Invalid payment period value")
        self.period = period

    def pay(self, amount, description, tstamp=None):
        """`pay` will create a transaction indicating
        a payment made to the user's credit.
        """
        # check if the amount is valid
        if amount <= Decimal('0.000'):
            raise InvalidPayment("Payment amount should be greater than 0.000 USD")

        # insert the transaction into the database.
        tstamp = tstamp or datetime.now()
        self.cursor.execute("""
            INSERT INTO 
                transaction (tstamp, amount, balance, description, type)
            VALUES ('%s', %s, (
                SELECT 
                    balance
                FROM
                    transaction
                ORDER BY 
                    tstamp 
                DESC LIMIT 1) + %s, '%s', 'payment');
        """ % (tstamp, amount, amount, description))

    def withdraw(self, amount, description, tstamp=None):
        """`withdraw` will create a transaction indicating
        a withdrawal from the user's credit.
        """
        # check if the amount is valid
        if amount <= Decimal('0.000'):
            raise InvalidWithdrawal("Withdrawal amount should be greater than 0.000 USD")

        # check if this withdrawal will take the user below the accepted limit.
        self.cursor.execute("""
            SELECT 
                balance 
            FROM 
                transaction 
            ORDER BY 
                tstamp 
            DESC LIMIT 1;""")
        balance = self.cursor.fetchone()['balance']
        if (balance - amount) < Decimal('0.0000'):
            # yes, this withdrawal will take the user below the accepted limit.
            raise WithdrawalDenied("Withdrawal crosses the credit limit - Denied")

        # insert the transaction into the database.
        tstamp = tstamp or datetime.now()
        self.cursor.execute("""
            INSERT INTO 
                transaction (tstamp, amount, balance, description, type)
            VALUES ('%s', %s, (
                SELECT 
                    balance 
                FROM 
                    transaction 
                ORDER BY 
                    tstamp 
                DESC LIMIT 1) - %s, '%s', 'withdrawal');
        """ % (tstamp, -amount, amount, description))

    def get_current_due(self, as_of=None):
        """`get_current_due` computes the amount due in the user's
        credit account at any point of time.
        """
        # fetch the balance from the database
        as_of = as_of or (date.today() + timedelta(days=1))
        self.cursor.execute("""
            SELECT
                balance
            FROM
                transaction
            WHERE 
                tstamp < '%s' 
            ORDER BY 
                tstamp 
            DESC LIMIT 1;
        """ % as_of)

        # compute the due from the balance and return it (rount to two decimals)
        return (self.limit - self.cursor.fetchone()['balance']).quantize(Decimal('.01'), rounding=ROUND_UP)

    def compute_outstanding(self, as_of=None):
        """`compute_outstanding` runs at the intervals 
        defined by the user's payment period and computes 
        the interest and hence the total outstanding.
        """
        interest = Decimal('0.000')

        # fetch the day on which the previous outstanding was computed.
        self.cursor.execute("""
            SELECT 
                tstamp 
            FROM 
                transaction 
            WHERE 
                type='eot' 
            ORDER BY 
                tstamp 
            LIMIT 1;
        """);
        previous_eot = self.cursor.fetchone()['tstamp']

        # check if we are running this function on the correct day (after the period)
        # NOTE: this check basically acts as a sanity check to make sure the function
        # cannot be run multiple times on the system and create inconsistencies.
        today = as_of or date.today()
        if (today - previous_eot).days < self.period:
            # we haven't yet passed the number of days specified in the period. Wait.
            raise InvalidOutstandingInvocation(
                "Outstanding should be calcualted once a %d day period is complete" % self.period
            )

        # compute the due for the current day (NOTE: this is total due).
        due = self.get_current_due(today)
        
        # get the total balance at the end of previous eot day.
        self.cursor.execute("""
            SELECT 
                balance 
            FROM 
                transaction 
            WHERE 
                tstamp < '%s' 
            ORDER BY 
                tstamp 
            DESC LIMIT 1
        """ % (previous_eot + timedelta(days=1)))
        # compute the current outstanding based on the balance.
        outstanding = self.limit - self.cursor.fetchone()['balance']
        
        if outstanding > Decimal('0.000'):
            # check if the payment has been made in this month to clear things off.
            self.cursor.execute("""
                SELECT 
                    SUM(amount) AS amounts 
                FROM 
                    transaction 
                WHERE 
                    type='payment' AND tstamp >= '%s' 
                LIMIT 1;
            """ % previous_eot)
            # fetch the total payment this month
            payments = self.cursor.fetchone()['amounts']
            if payments < outstanding:
                # not all outstanding has been cleared.
                # start to compute the interest that needs to be computed.
                self.cursor.execute("""
                    SELECT 
                        balance, tstamp 
                    FROM 
                        transaction 
                    WHERE 
                        tstamp >= '%s' 
                    ORDER BY 
                        tstamp;
                """ % previous_eot)
                prev_transaction = self.cursor.next()
                for transaction in self.cursor:
                    # compute the due for this period.
                    due = self.limit - prev_transaction['balance']
                    # compute the interest for this period
                    interest += (transaction['tstamp'].date() - prev_transaction['tstamp'].date()).days * (self.apr/Decimal('365.00')) * due
                    prev_transaction = transaction

                # finally compute from the last transaction until current
                due = self.limit - prev_transaction['balance']
                interest += (as_of.date() - prev_transaction['tstamp'].date()).days * (self.apr/Decimal('365.00')) * due

        # write a record for this outstanding calculation
        description = 'added interest of %s USD on the due amount past %s day payment period' % (interest, self.period)
        self.cursor.execute("""
            INSERT INTO 
                transaction (tstamp, amount, balance, description, type) 
            VALUES ('%s', 0, %s, '%s', 'eot');
        """ % (today, interest+due, description))

        # round to two decimals
        return (interest + due).quantize(Decimal('.01'), rounding=ROUND_UP)

    def get_statement(self, start_date=None, end_date=None):
        """`get_statement` gets a detailed credit account statement
        of all the transaction over a time period.
        """
        start_date = start_date or date(day=1,month=1,year=1970)
        end_date = end_date or (date.today() + timedelta(days=1))
        self.cursor.execute("""
            SELECT 
                tstamp, amount, type, description 
            FROM 
                transaction 
            WHERE 
                tstamp >= '%s' AND tstamp < '%s' 
            ORDER BY id;
        """ % (start_date, end_date))

        # return all the results as a list of lists.
        return self.cursor.fetchall()

