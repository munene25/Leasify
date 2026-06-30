import pytest
from payments.mpesa.auth import get_access_token
from payments.mpesa import initiate_stk_push, query_payment_status, make_timestamp, make_password
from payments.mpesa.parser import parse_callback_response
from payments.mpesa import STKResult, STKInitialResponse
from unittest.mock import MagicMock
from freezegun import freeze_time
from zoneinfo import ZoneInfo


class TestUtils:
    def test_make_password(self):
        """Test M-Pesa password generation."""

        import base64

        shortcode = "174379"
        passkey = "bfb279f9ba9b9d1ddb1f1a8c1b7c7cd5"
        timestamp = "20231218091430"

        result = make_password(shortcode, passkey, timestamp)

        # Verify it's base64
        assert isinstance(result, str)
        try:
            base64.b64decode(result)
        except Exception:
            pytest.fail("Result is not valid base64")

        # Verify determinism (same input = same output)
        assert result == make_password(shortcode, passkey, timestamp)

        # Verify it's different with different inputs
        assert result != make_password(shortcode, passkey, "20231218091431")

    def test_make_timestamp(self):
        """Test that the string generated matches expected output"""
        # Expected: YYYY MM DD HH mm SS
        from datetime import datetime

        d = datetime(2024, 12, 1, 2, 0, 30, tzinfo=ZoneInfo("Africa/Nairobi"))
        with freeze_time(d):
            timestamp = make_timestamp()
            assert timestamp == "20241201020030"


class TestParser:
    def test_parse_callback_response(self, stk_callback_fail: dict, stk_callback_sucess: dict):
        """Parsing the mpesa response for a payment"""
        # test with failed response
        test1 = parse_callback_response(stk_callback_fail)
        assert isinstance(test1, STKResult)
        assert test1.checkout_id == "ws_CO_21072024125243250722943992"
        assert test1.success == False
        assert test1.result_desc == "Request cancelled by user"
        assert test1.receipt_no == None
        assert test1.metadata == {"merchant_id": "f1e2-4b95-a71d-b30d3cdbb7a7942864"}

        # Test with successful response
        test2 = parse_callback_response(stk_callback_sucess)
        assert isinstance(test2, STKResult)
        assert test2.checkout_id == "ws_CO_191220191020363925"
        assert test2.success == True
        assert test2.result_desc == "The service request is processed successfully."
        assert test2.receipt_no == "NLJ7RT61SV"
        assert len(test2.metadata) == 4




