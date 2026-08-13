from __future__ import annotations

import json
import pathlib
from contextlib import redirect_stdout
from io import StringIO
import unittest

import adam_cli
from adam_quotes import CATEGORIES, QUOTES, select_quote


class AdamQuotesTest(unittest.TestCase):
    def test_same_seed_is_reproducible(self) -> None:
        first = select_quote("anvil-shell|drew|red-team")
        second = select_quote("anvil-shell|drew|red-team")
        self.assertEqual(first, second)

    def test_categories_are_complete_and_filterable(self) -> None:
        self.assertEqual(CATEGORIES, {"bible", "literature", "history"})
        for category in sorted(CATEGORIES):
            self.assertEqual(select_quote("same-seed", category).category, category)

    def test_corpus_is_unique_and_source_carrying(self) -> None:
        self.assertEqual(len({quote.identifier for quote in QUOTES}), len(QUOTES))
        self.assertTrue(all(quote.source_url.startswith("https://") for quote in QUOTES))
        self.assertTrue(all(quote.text.strip() for quote in QUOTES))

    def test_cli_json_is_machine_clean_and_seeded(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = adam_cli.quote_command(
                ["--seed", "receipt-42", "--category", "bible", "--json"],
                pathlib.Path("/tmp"),
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["seed"], "receipt-42")
        self.assertEqual(payload["category"], "bible")

    def test_unknown_category_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            select_quote("seed", "horoscope")


if __name__ == "__main__":
    unittest.main()
