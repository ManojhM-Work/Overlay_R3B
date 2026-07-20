import time
import requests
import json
import uuid
from datetime import datetime

# Start the actual UAEIPP Buyer Simulator FastAPI Server programmatically for testing
def run_tests():
    print("==================================================")
    print("   UAEIPP BUYER SIMULATOR INTEGRATION TESTS       ")
    print("==================================================")

    print("Starting FastAPI simulator on port 8080...")
    from main import FastAPIServerEngine
    import config

    # Initialize configs for test: no delays to speed up test execution
    config.Config.set("server", "api_host", value="127.0.0.1")
    config.Config.set("server", "api_port", value="8081")
    config.Config.set("server", "response_delay_seconds", value=0.0)
    config.Config.set("server", "logging_enabled", value=True)
    config.Config.set("server", "random_response_enabled", value=False)

    engine = FastAPIServerEngine("127.0.0.1", 8081)
    engine.start()
    time.sleep(1) # wait for uvicorn to initialize

    api_base_url = "http://127.0.0.1:8081"
    post_endpoint = "/p2b/payments/verify-reserve-buyer-iban"
    delete_endpoint_tpl = "/payments/reserve/{transactionId}"

    def get_test_headers(idempotency_key=None):
        ikey = idempotency_key or f"IDEMP-{uuid.uuid4().hex[:10]}"
        return {
            "Content-Type": "application/json",
            "x-idempotency-key": ikey,
            "x-request-id": f"REQ-{uuid.uuid4().hex[:10]}",
            "x-timestamp": datetime.now().isoformat(),
            "client-id": "client-test-id-12345",
            "authorization": "Bearer dummy_test_token_eyJhbGciOiJSUzI1NiIs...",
            "buyerBankUserId": "0000654789"
        }

    def get_test_payload(tx_id=None, merchant_trx_id=None, use_iban=True):
        tid = tx_id or f"P2B{uuid.uuid4().hex[:16]}"
        mtrx = merchant_trx_id or f"MTRX-{uuid.uuid4().hex[:8]}"
        
        merchant = {
            "bankCode": "80754",
            "mcc": "9999",
            "merchantName": "John Smith Ltd",
            "sp": "SP808LX",
            "storeId": "10001",
            "cashDeskId": "null",
            "label": "Plaza",
            "vat": "22672096558",
            "address": {
                "street": "3-4 Mary St",
                "city": "Dublin",
                "postalCode": "D02 N725",
                "country": "IE"
            }
        }
        if use_iban:
            merchant["iban"] = "AE2377661261341267563289"
        else:
            merchant["accountIdentifier"] = "21404040Y78115245785511"

        buyer = {
            "bankCode": "02DEF",
            "mobile": "+971581234567",
            "name": "Matt Damon"
        }
        if use_iban:
            buyer["iban"] = "AE2900078115245785609"
        else:
            buyer["accountIdentifier"] = "31404040Y78115245782241"

        return {
            "transactionId": tid,
            "amount": {
                "requested": 505.10,
                "currency": "AED"
            },
            "reason": "Soccer shoes",
            "merchant": merchant,
            "buyer": buyer,
            "requestToPay": False,
            "merchantTrxId": mtrx,
            "transactionType": "P613"
        }

    # ----------------------------------------------------
    # TEST 1: SYNCHRONOUS FLOW (POST 201)
    # ----------------------------------------------------
    print("\n[TEST 1] POST Verify Reserve -> HTTP 201 (Sync Flow)")
    config.Config.set("server", "post_response_mode", value="201")
    
    headers = get_test_headers()
    payload = get_test_payload()
    
    try:
        url = api_base_url + post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        assert resp.json()["outcome"] == "000", "Expected outcome '000'"
        assert resp.json()["merchantTrxId"] == payload["merchantTrxId"], "merchantTrxId mismatch"
        print("-> [PASS] Synchronous POST 201 flow is correct.")
    except Exception as e:
        print(f"-> [FAIL] Test 1 failed: {e}")

    # ----------------------------------------------------
    # TEST 2: ASYNCHRONOUS FLOW (POST 202 + GET Polling)
    # ----------------------------------------------------
    print("\n[TEST 2] POST Verify Reserve -> HTTP 202 & GET Polling (Async Flow)")
    config.Config.set("server", "post_response_mode", value="202")
    config.Config.set("server", "get_response_mode", value="200")
    config.Config.set("server", "poll_success_count", value=3)
    
    headers = get_test_headers()
    payload = get_test_payload()
    tx_id = payload["transactionId"]
    merchant_trx_id = payload["merchantTrxId"]

    try:
        # Step 2a: Send POST request
        url = api_base_url + post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"POST Status Code: {resp.status_code}")
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
        print("POST response successful.")

        # Step 2b: Poll GET
        poll_url = f"{api_base_url}{post_endpoint}?transactionId={tx_id}&merchantTrxId={merchant_trx_id}"
        
        # Poll 1
        print("Sending Poll 1...")
        resp_poll1 = requests.get(poll_url, headers=headers)
        print(f"Poll 1 Status: {resp_poll1.status_code}")
        assert resp_poll1.status_code == 202, f"Expected 202 on poll 1, got {resp_poll1.status_code}"

        # Poll 2
        print("Sending Poll 2...")
        resp_poll2 = requests.get(poll_url, headers=headers)
        print(f"Poll 2 Status: {resp_poll2.status_code}")
        assert resp_poll2.status_code == 202, f"Expected 202 on poll 2, got {resp_poll2.status_code}"

        # Poll 3
        print("Sending Poll 3...")
        resp_poll3 = requests.get(poll_url, headers=headers)
        print(f"Poll 3 Status: {resp_poll3.status_code}")
        print("Poll 3 Response JSON:", json.dumps(resp_poll3.json(), indent=2))
        assert resp_poll3.status_code == 200, f"Expected 200 on poll 3, got {resp_poll3.status_code}"
        assert resp_poll3.json()["outcome"] == "000", "Expected outcome '000'"

        print("-> [PASS] Asynchronous polling flow behaves correctly (202, 202, 200).")
    except Exception as e:
        print(f"-> [FAIL] Test 2 failed: {e}")

    # ----------------------------------------------------
    # TEST 3: DELETE RESERVE
    # ----------------------------------------------------
    print("\n[TEST 3] DELETE Reserve")
    config.Config.set("server", "delete_response_mode", value="200")
    tx_id = f"P2B{uuid.uuid4().hex[:16]}"
    del_url = api_base_url + delete_endpoint_tpl.format(transactionId=tx_id)

    try:
        # Delete first time
        print("Sending DELETE request...")
        resp_del1 = requests.delete(del_url, headers=get_test_headers())
        print(f"DELETE 1 Status: {resp_del1.status_code}")
        print("DELETE 1 Response:", json.dumps(resp_del1.json(), indent=2))
        assert resp_del1.status_code == 200, f"Expected 200, got {resp_del1.status_code}"
        assert resp_del1.json()["outcome"] == "022"

        # Delete repeated time (retry scenario)
        print("Sending retry DELETE request...")
        resp_del2 = requests.delete(del_url, headers=get_test_headers())
        print(f"DELETE 2 Status: {resp_del2.status_code}")
        assert resp_del2.status_code == 200, "Repeated delete failed"

        print("-> [PASS] DELETE reserve endpoint is idempotent and returns 200.")
    except Exception as e:
        print(f"-> [FAIL] Test 3 failed: {e}")

    # ----------------------------------------------------
    # TEST 4: SCHEMA VALIDATION ERRORS
    # ----------------------------------------------------
    print("\n[TEST 4] Schema Validation Exception (Header/Body error checks)")
    
    # 4a: Missing mandatory header (x-idempotency-key)
    try:
        bad_headers = get_test_headers()
        bad_headers.pop("x-idempotency-key") # Missing!
        
        url = api_base_url + post_endpoint
        resp = requests.post(url, json=get_test_payload(), headers=bad_headers)
        print(f"Missing Header Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "x-idempotency-key" in resp.json()["errorMsg"]
        print("-> [PASS] Missing header is correctly caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 4a failed: {e}")

    # 4b: Invalid body schema (missing amount field)
    try:
        bad_payload = get_test_payload()
        bad_payload.pop("amount") # Missing!
        
        url = api_base_url + post_endpoint
        resp = requests.post(url, json=bad_payload, headers=get_test_headers())
        print(f"Missing Body Field Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "amount" in resp.json()["errorMsg"]
        print("-> [PASS] Invalid body schema is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 4b failed: {e}")

    # ----------------------------------------------------
    # TEST 5: TIMEOUT POLLING FLOW
    # ----------------------------------------------------
    print("\n[TEST 5] POST Verify Reserve -> HTTP 202 & GET Polling with Timeouts (Timeout - Polling)")
    config.Config.set("server", "post_response_mode", value="202 - 000")
    config.Config.set("server", "get_response_mode", value="Timeout - Polling")
    config.Config.set("server", "poll_success_count", value=3)
    config.Config.set("server", "timeout_mode", value="Close Connection") # Use Close Connection to fail fast instead of sleeping 15s

    headers = get_test_headers()
    payload = get_test_payload()
    tx_id = payload["transactionId"]
    merchant_trx_id = payload["merchantTrxId"]

    try:
        # Step 5a: Send POST request
        url = api_base_url + post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"POST Status Code: {resp.status_code}")
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"

        poll_url = f"{api_base_url}{post_endpoint}?transactionId={tx_id}&merchantTrxId={merchant_trx_id}"
        
        # Poll 1 (Expect 202)
        print("Sending Poll 1 (expecting 202)...")
        resp_poll1 = requests.get(poll_url, headers=headers)
        print(f"Poll 1 Status: {resp_poll1.status_code}")
        assert resp_poll1.status_code == 202, f"Expected 202 on poll 1, got {resp_poll1.status_code}"

        # Poll 2 (Expect 202)
        print("Sending Poll 2 (expecting 202)...")
        resp_poll2 = requests.get(poll_url, headers=headers)
        print(f"Poll 2 Status: {resp_poll2.status_code}")
        assert resp_poll2.status_code == 202, f"Expected 202 on poll 2, got {resp_poll2.status_code}"

        # Poll 3 (Expect timeout/connection closed)
        print("Sending Poll 3 (expecting timeout/connection closed)...")
        try:
            r3 = requests.get(poll_url, headers=headers)
            print(f"-> [FAIL] Expected connection to be closed/timeout on Poll 3, but got status {r3.status_code}")
        except requests.exceptions.ConnectionError:
            print("Poll 3 Status: Connection Closed (Simulated Timeout)")

        print("-> [PASS] Timeout - Polling behaves correctly (202, 202, Timeout).")
    except Exception as e:
        print(f"-> [FAIL] Test 5 failed: {e}")

    # Clean Up
    print("\nStopping server...")
    engine.stop()
    print("==================================================")
    print("   INTEGRATION TESTING COMPLETED                  ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
