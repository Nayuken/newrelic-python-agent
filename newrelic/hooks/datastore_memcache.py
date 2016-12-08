from newrelic.agent import (wrap_object, FunctionWrapper, DatastoreTrace,
        current_transaction, wrap_datastore_trace, wrap_function_wrapper)

def _instance_info(host):
    address = host.address
    if isinstance(address, tuple):
        return (host.ip, str(host.port), None)
    else:
        return ('localhost', address, None)

def _nr_get_server_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    result = wrapped(*args, **kwargs)

    instance_info = (None, None, None)

    try:
        tracer_settings = transaction.settings.datastore_tracer
        host = result[0]

        # memcached does not set the db name attribute so there's
        # no need to check the db name reporting setting
        if tracer_settings.instance_reporting.enabled and host is not None:
            instance_info = _instance_info(host)
    except:
        instance_info = ('unknown', 'unknown', None)

    transaction._nr_datastore_instance_info = instance_info

    return result

def MemcacheSingleWrapper(wrapped, product, target, operation, module):

    def _nr_datastore_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        transaction._nr_datastore_instance_info = (None, None, None)

        dt = DatastoreTrace(transaction, product, target, operation)

        with dt:
            result = wrapped(*args, **kwargs)

            instance_info = transaction._nr_datastore_instance_info
            (host, port_path_or_id, db) = instance_info
            dt.host = host
            dt.port_path_or_id = port_path_or_id

            return result

    return FunctionWrapper(wrapped, _nr_datastore_trace_wrapper_)

def wrap_memcache_single(module, object_path, product, target, operation):
    wrap_object(module.Client, object_path, MemcacheSingleWrapper,
            (product, target, operation, module))

_memcache_client_methods = ('delete', 'incr', 'decr', 'add',
    'append', 'prepend', 'replace', 'set', 'cas', 'get', 'gets')

_memcache_multi_methods = ('delete_multi', 'get_multi', 'set_multi',
    'get_stats', 'get_slabs', 'flush_all')


def instrument_memcache(module):
    wrap_function_wrapper(module.Client, '_get_server', _nr_get_server_wrapper)

    for name in _memcache_client_methods:
        if hasattr(module.Client, name):
            wrap_memcache_single(module, name,
                    product='Memcached', target=None, operation=name)

    for name in _memcache_multi_methods:
        if hasattr(module.Client, name):
            wrap_datastore_trace(module.Client, name,
                    product='Memcached', target=None, operation=name)
