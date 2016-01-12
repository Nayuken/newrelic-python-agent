from newrelic.agent import (FunctionTrace, callable_name, function_wrapper,
    wrap_function_wrapper)
from .util import (record_exception, retrieve_current_transaction,
        replace_current_transaction, create_transaction_aware_fxn)

def _nr_wrapper_Future_add_done_callback(wrapped, instance, args, kwargs):
    def _fxn_arg_extractor(fn, *args, **kwargs):
        # fn is the name of the callable argument in stack_context.wrap
        return fn

    fxn = _fxn_arg_extractor(*args, **kwargs)

    transaction_aware_fxn = create_transaction_aware_fxn(fxn)

    # If transaction_aware_fxn is None then it is already wrapped, or the fxn
    # is None.
    if transaction_aware_fxn is None:
        return wrapped(*args, **kwargs)

    transaction = retrieve_current_transaction()

    transaction_aware_fxn._nr_transaction = transaction

    # We replace the function we call in the callback with the transaction aware
    # version of the function.
    if len(args) > 0:
        args = list(args)
        args[0] = transaction_aware_fxn
    else:
        # Keyword argument name for the callable function is 'fn'.
        kwargs['fn'] = transaction_aware_fxn

    return wrapped(*args, **kwargs)

def instrument_tornado_concurrent(module):
    wrap_function_wrapper(module, 'Future.add_done_callback',
            _nr_wrapper_Future_add_done_callback)
