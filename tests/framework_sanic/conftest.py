import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

import asyncio
from sanic.request import Request

_coverage_source = [
    'newrelic.hooks.framework_sanic',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (framework_sanic)',
        default_settings=_default_settings)


@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass


@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass


def create_request_class(method, url, headers=None):
    _request = Request(
        method=method.upper(),
        url_bytes=url.encode('utf-8'),
        headers=headers,
        version='1.0',
        transport=None,
    )
    return _request


def create_request_coroutine(app, method, url, headers=None, responses=None):
    if responses is None:
        responses = []

    def write_callback(response):
        response.raw_headers = response.output()
        responses.append(response)

    async def stream_callback(response):
        response.raw_headers = response.get_headers()
        responses.append(response)

    headers = headers or {}
    coro = app.handle_request(
        create_request_class(method, url, headers),
        write_callback,
        stream_callback,
    )
    return coro


def request(app, method, url, headers=None):
    responses = []
    coro = create_request_coroutine(app, method, url, headers, responses)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(coro)
    return responses[0]


class TestApplication(object):
    def __init__(self, app):
        self.app = app

    def fetch(self, method, url, headers=None):
        return request(self.app, method, url, headers)


@pytest.fixture()
def app():
    from _target_application import app
    return TestApplication(app)
