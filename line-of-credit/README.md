Credit Manager
==============

Credit Manager is a simple Python library that can be used to manage a credit. The library uses [PostgreSQL]() to store all the transaction records.

## Getting started

* Get the source code by cloning this repository

```
git clone https://github.com/sandeepraju/a.git
```

* Navigate to the Credit Manager directory

```
cd a/line-of-credit/
```

* This library uses Postgres database to store all the transactions and hence depends on [PsycoPG2](https://github.com/psycopg/psycopg2/) to connect with Postgres from Python. To install this dependency, run the following commands

```
virtualenv venv  # create a new virtual environment
source ./venv/bin/activate # activate the virtual environment
pip install -r requirements.txt
```

* Create a database in Postgres and run the supplied `bootstrap.sql` file. This creates the transaction table needed for the library to store it's transactions.

## Running the test cases

* To run the test cases, navigate to the tests folder

```
cd a/line-of-credit/tests/
```

* Open the `settings.py` with the editor of your choice and update the database settings.
* Once this is done, return back to the directory which has the `Makefile`.

```
cd ../
```

* Start the test by running the following command

```
make test
```

## Examples

* Creating an instance of `CreditManager`

```python
from decimal import Decimal  # for numeric precision when handling currency.
from cmanager import CreditManager
cm = CreditManager(
	apr=Decimal('0.350'),  # APR is 35%
	limit=Decimal('1000.000'),  # Credit limit is 1000 USD
	period=30  # Payment period is 30 days
)
```

* Making a withdrawal

```python
cm.withdraw(Decimal('100.00'), 'Payment at Walmart')
```

* Making a payment

```python
cm.pay(Decimal('100.00'), 'Payment for the month of Jan')
```

* Compute Outstanding (with interest) at the end of payment period

```python
cm.compute_outstanding()
```

* Get the amount due at any time.

```python
cm.get_current_due()
```

* Get a list of transactions as a statement.

```python
cm.get_statement(from_date, to_date)
```

## How does it work

* Uses Postgres to store all the transaction records.
* At each payment or withdrawal, adds a new transaction.
* At the end of payment period, a function is run to compute the interest (if any).
* Implements all the logic based on various queries performed on the database.

## Assumptions made

* Interest is calculated at the end of the payment cycle.
* Partial payments waive off the interest first and then the principal.
* Excess payments work intuitively (if credit limit is $1000 and user pays $3000, total available balance is $4000 which the user can withdraw at any time).
* Withdrawal limit is based on the the total amount due at any point of time (this includes any interest if applicable).
