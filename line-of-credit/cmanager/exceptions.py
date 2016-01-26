class SystemFailed(Exception):
    pass

class InvalidParameterValue(Exception):
    pass

class InvalidPayment(InvalidParameterValue):
    pass

class InvalidWithdrawal(InvalidParameterValue):
    pass

class WithdrawalDenied(Exception):
    pass

class InvalidOutstandingInvocation(Exception):
    pass
