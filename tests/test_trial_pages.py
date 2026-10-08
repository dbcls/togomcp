"""Test landing-page routes without initializing external MCP dependencies."""
import ast
import asyncio
import unittest
from pathlib import Path
from starlette.requests import Request
from starlette.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]


class TrialPagesTest(unittest.TestCase):
    def test_routes_serve_existing_files_with_correct_media_types(self):
        tree = ast.parse((ROOT / 'togo_mcp/server.py').read_text())
        namespace = {'Request': Request, 'FileResponse': FileResponse,
                     'CWD': ROOT / 'togo_mcp/data'}
        for name, suffix, media in [
            ('japanese_index', 'docs/togomcp-intro-ja.html', 'text/html'),
            ('widget_asset', 'docs/assets/llm-meta-widget.js', 'application/javascript'),
        ]:
            function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            function.decorator_list = []
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<route>', 'exec'), namespace)
            response = asyncio.run(namespace[name](None))
            self.assertEqual(response.media_type, media)
            self.assertEqual(Path(response.path), namespace['CWD'] / suffix)
            self.assertTrue(Path(response.path).is_file())


if __name__ == '__main__':
    unittest.main()
