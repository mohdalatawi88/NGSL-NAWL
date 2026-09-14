import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import response_validator as rv  # noqa: E402


class ResponseValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = rv.ProjectData(ROOT)

    def test_valid_response_passes(self):
        response = """The answer is accurate.
Her report is accurate.

الإجابة دقيقة.
تقريرها دقيق.

المعاني الشائعة: 1 — دقيق؛ صحيح
القائمة: NGSL
العائلة: accurate (NGSL) ↔ accurately (NAWL)
"""
        result = rv.validate("accurate", response, self.data)
        self.assertTrue(result.ok, result.errors)

    def test_wrong_membership_fails(self):
        response = """The answer is accurate.
Her report is accurate.

الإجابة دقيقة.
تقريرها دقيق.

المعاني الشائعة: 1 — دقيق؛ صحيح
القائمة: NAWL
العائلة: accurate (NGSL) ↔ accurately (NAWL)
"""
        result = rv.validate("accurate", response, self.data)
        self.assertFalse(result.ok)
        self.assertTrue(any("Incorrect list membership" in e for e in result.errors))

    def test_missing_translation_fails(self):
        response = """The answer is accurate.
Her report is accurate.

الإجابة دقيقة.

المعاني الشائعة: 1 — دقيق؛ صحيح
القائمة: NGSL
العائلة: accurate (NGSL) ↔ accurately (NAWL)
"""
        result = rv.validate("accurate", response, self.data)
        self.assertFalse(result.ok)
        self.assertTrue(any("Arabic translations" in e for e in result.errors))

    def test_unbolded_known_phrase_fails(self):
        response = """I refer to accurate data.
The figures are accurate.

أشير إلى بيانات دقيقة.
الأرقام دقيقة.

المعاني الشائعة: 1 — دقيق؛ صحيح
القائمة: NGSL
العائلة: accurate (NGSL) ↔ accurately (NAWL)
"""
        result = rv.validate("accurate", response, self.data)
        self.assertFalse(result.ok)
        self.assertTrue(any("must be bold" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
