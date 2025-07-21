import sys
import types
import importlib.util


def load_main_module():
    # Stub external dependencies used by main.py so it can be imported without
    # installing them.
    flask = types.ModuleType('flask')
    class FakeFlask:
        def __init__(self, *a, **k):
            pass

        def route(self, *a, **k):
            def decorator(func):
                return func
            return decorator

    flask.Flask = FakeFlask
    flask.request = None
    flask.jsonify = lambda *a, **k: None
    sys.modules.setdefault('flask', flask)

    firecrawl = types.ModuleType('firecrawl')
    class FirecrawlApp:
        def __init__(self, *a, **k):
            pass
        def extract(self, *a, **k):
            pass
    firecrawl.FirecrawlApp = FirecrawlApp
    sys.modules.setdefault('firecrawl', firecrawl)

    openai = types.ModuleType('openai')
    class OpenAI:
        def __init__(self, *a, **k):
            pass
    openai.OpenAI = OpenAI
    sys.modules.setdefault('openai', openai)

    pydantic = types.ModuleType('pydantic')
    class BaseModel:
        @classmethod
        def model_json_schema(cls):
            return {}
    pydantic.BaseModel = BaseModel
    sys.modules.setdefault('pydantic', pydantic)

    spec = importlib.util.spec_from_file_location('main', 'main.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
