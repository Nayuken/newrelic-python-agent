import asyncio
from aiohttp import web


@asyncio.coroutine
def index(request):
    yield
    return web.Response(text='Hello Aiohttp!')


@asyncio.coroutine
def error(request):
    raise ValueError("I'm bad at programming...")


class HelloWorldView(web.View):

    @asyncio.coroutine
    def _respond(self):
        yield
        return web.Response(text='Hello Aiohttp!')

    get = _respond
    post = _respond
    put = _respond
    patch = _respond
    delete = _respond


class KnownException(Exception):
    pass


class KnownErrorView(web.View):

    @asyncio.coroutine
    def _respond(self):
        try:
            yield
        except KnownException:
            pass
        finally:
            return web.Response(text='Hello Aiohttp!')

    get = _respond
    post = _respond
    put = _respond
    patch = _respond
    delete = _respond


@asyncio.coroutine
def load_flame_thrower(app, handler):

    @asyncio.coroutine
    def flame_thrower(request):
        # start handler call
        coro = handler(request)
        try:
            while True:
                yield
                next(coro)
                coro.throw(KnownException)
        except StopIteration as e:
            return e.value
        except Exception as e:
            return web.Response(status=500, text=str(e))

    return flame_thrower


def make_app(with_middleware=False):
    middlewares = []
    if with_middleware:
        middlewares.append(load_flame_thrower)
    app = web.Application(middlewares=middlewares)
    app.router.add_route('*', '/coro', index)
    app.router.add_route('*', '/class', HelloWorldView)
    app.router.add_route('*', '/error', error)
    app.router.add_route('*', '/known_error', KnownErrorView)

    return app
