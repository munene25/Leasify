import pytest
from payments.mpesa import auth, parser, initiate_stk_push, query_payment_status, make_timestamp, make_password
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


class TestSTKInitialResponseParse:

    def test_parse_callback_response(self, stk_callback_fail: dict, stk_callback_sucess: dict):
        """Parsing the mpesa response for a payment"""
        # test with failed response
        test1 = parser.parse_callback_response(stk_callback_fail)
        assert isinstance(test1, STKResult)
        assert test1.checkout_id == "ws_CO_12345"
        assert test1.success == False
        assert test1.result_desc == "Request cancelled by user"
        assert test1.receipt_no == None
        assert test1.metadata == {"merchant_id": "f1e2-4b95-a71d-b30d3cdbb7a7942864"}

        # Test with successful response
        test2 = parser.parse_callback_response(stk_callback_sucess)
        assert isinstance(test2, STKResult)
        assert test2.checkout_id == "ws_CO_12345"
        assert test2.success == True
        assert test2.result_desc == "The service request is processed successfully."
        assert test2.receipt_no == "NLJ7RT61SV"
        assert len(test2.metadata) == 4

class TestInitiateSTKPush:

    def test_success(self, monkeypatch: pytest.MonkeyPatch, stk_initial_response: dict, patch_mpesa_auth: MagicMock):
        """Test successful STK push initiation."""
        mock_response = MagicMock()
        mock_response.json.return_value = stk_initial_response
        mock_response.raise_for_status.return_value = None
        
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr('payments.mpesa.handlers.requests.post', mock_post)

        
        result = initiate_stk_push(
            phone_number="254712345678",
            amount=1000,
            account_ref="JAN-2024",
            description="Rent",
            timestamp="20240101120000"
        )
        
        assert isinstance(result, STKInitialResponse)
        assert result.checkout_id == "ws_CO_12345"
        assert result.success is True
        mock_post.assert_called_once()
        patch_mpesa_auth.assert_called_once()
    
    def test_account_ref_too_long(self):
        """Test validation of account_ref length."""
        with pytest.raises(ValueError, match="Account Reference.*too long"):
            initiate_stk_push(
                phone_number="254712345678",
                amount=1000,
                account_ref="THIS_IS_TOO_LONG_OVER_12",
                description="Rent",
                timestamp="20240101120000"
            )
    
    def test_description_too_long(self):
        """Test validation of description length."""
        with pytest.raises(ValueError, match="Description.*too long"):
            initiate_stk_push(
                phone_number="254712345678",
                amount=1000,
                account_ref="JAN-2024",
                description="This description is too long",
                timestamp="20240101120000"
            )

    
    def test_http_error(self, monkeypatch: pytest.MonkeyPatch, stk_initial_response: dict, patch_mpesa_auth: MagicMock):
        """Test handling of HTTP errors."""
        import requests

        mock_response = MagicMock()
        mock_response.json.return_value = stk_initial_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr('payments.mpesa.handlers.requests.post', mock_post)
        
        with pytest.raises(requests.exceptions.HTTPError):
            initiate_stk_push(
                phone_number="254712345678",
                amount=1000,
                account_ref="JAN-2024",
                description="Rent",
                timestamp="20240101120000"
            )
    
    def test_payload_structure(self, monkeypatch: pytest.MonkeyPatch, patch_mpesa_auth: MagicMock, stk_initial_response):
        """Test that the payload sent is correct."""
            
        mock_response = MagicMock()
        mock_response.json.return_value = stk_initial_response
        mock_response.raise_for_status.return_value = None
        
        mock_post = MagicMock(return_value=mock_response)
        monkeypatch.setattr('payments.mpesa.handlers.requests.post', mock_post)
        
        initiate_stk_push(
            phone_number="254712345678",
            amount=1000,
            account_ref="JAN-2024",
            description="Rent",
            timestamp="20240101120000"
        )
        
        # Verify the payload
        call_args = mock_post.call_args
        url = call_args.args[0]
        payload = call_args.kwargs['json']
        headers = call_args.kwargs["headers"]
        
        assert "https://sandbox.safaricom.co.ke" in url
        assert "stkpush" in url
        assert headers["Authorization"] == "Bearer secret_token"
        assert payload["Amount"] == 1000
        assert payload["PhoneNumber"] == "254712345678"
        assert payload["AccountReference"] == "JAN-2024"
        assert payload["TransactionDesc"] == "Rent"
        assert payload["Timestamp"] == "20240101120000"