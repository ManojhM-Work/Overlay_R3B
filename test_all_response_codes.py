import time
import requests
import response_codes_catalog
import config
from main import FastAPIServerEngine

def test_all_codes():
    print("Testing response code parsing across all 256 catalog entries...")
    config.Config.testing_mode = True
    config.Config.set("server", "api_host", value="127.0.0.1")
    config.Config.set("server", "api_port", value="8089")
    config.Config.set("server", "ssl_enabled", value=False)
    config.Config.set("server", "response_delay_seconds", value=0.0)

    engine = FastAPIServerEngine("127.0.0.1", 8089)
    engine.start()
    time.sleep(1)

    url = "http://127.0.0.1:8089/p2b/payments/verify-reserve-buyer-iban"
    headers = {
        "Content-Type": "application/json",
        "x-idempotency-key": "IDEMP-TEST-999",
        "x-request-id": "REQ-TEST-999",
        "x-timestamp": "2026-07-29T12:00:00Z",
        "client-id": "CLIENT-001",
        "authorization": "Bearer token123"
    }

    payload = {
        "transactionId": "TRX-CATALOG-TEST",
        "amount": {
            "requested": 100.0,
            "currency": "AED"
        },
        "reason": "Test Payment",
        "merchant": {
            "name": "Test Merchant",
            "iban": "AE2377661261341267563289"
        },
        "buyer": {
            "bankCode": "02DEF",
            "mobile": "+971581234567",
            "name": "Test Buyer",
            "iban": "AE2900078115245785609"
        },
        "requestToPay": False,
        "merchantTrxId": "MTRX-CATALOG-TEST",
        "transactionType": "P613"
    }

    tested_count = 0
    passed_count = 0

    for opt in response_codes_catalog.POST_RESPONSE_OPTIONS:
        if opt in ("Timeout", "No Response"):
            continue
        
        config.Config.set("server", "post_response_mode", value=opt)
        resp = requests.post(url, json=payload, headers=headers)
        
        parts = opt.split(" - ", 2)
        expected_status = int(parts[0])
        expected_outcome = parts[1]
        
        body = resp.json()
        assert resp.status_code == expected_status, f"Expected status {expected_status}, got {resp.status_code} for {opt}"
        assert body.get("outcome") == expected_outcome, f"Expected outcome {expected_outcome}, got {body.get('outcome')} for {opt}"
        
        tested_count += 1
        passed_count += 1

    engine.stop()
    print(f"\nSUCCESS: Tested {tested_count} POST response codes. Passed: {passed_count}/{tested_count}")

if __name__ == "__main__":
    test_all_codes()
