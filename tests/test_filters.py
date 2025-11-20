import os
import unittest

from flask import render_template_string

from app import create_app, format_currency


class CurrencyFilterTest(unittest.TestCase):
    def setUp(self):
        os.environ["DATABASE_URI"] = "sqlite:///:memory:"
        os.environ["WTF_CSRF_ENABLED"] = "false"
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_default_locale_formatting(self):
        self.app.config.update(CURRENCY_CODE="EUR", CURRENCY_LOCALE="es_ES", CURRENCY_SYMBOL=None)
        self.assertEqual(format_currency(1234.5), "€1.234,50")

    def test_symbol_override(self):
        self.app.config.update(CURRENCY_CODE="USD", CURRENCY_LOCALE="en_US", CURRENCY_SYMBOL=None)
        self.assertEqual(format_currency(2500, symbol="$"), "$2,500.00")

    def test_invalid_input_returns_original_value(self):
        self.assertEqual(format_currency("n/a"), "n/a")

    def test_context_processor_exposes_symbol(self):
        self.app.config.update(CURRENCY_CODE="USD", CURRENCY_LOCALE="en_US", CURRENCY_SYMBOL="$")
        rendered = render_template_string("{{ currency_symbol }}")
        self.assertEqual(rendered, "$")


if __name__ == "__main__":
    unittest.main()
