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
    config.Config.set("server", "api_port", value="8090")
    config.Config.set("server", "response_delay_seconds", value=0.0)
    config.Config.set("server", "logging_enabled", value=True)
    config.Config.set("server", "random_response_enabled", value=False)

    engine = FastAPIServerEngine("127.0.0.1", 8090)
    engine.start()
    time.sleep(1) # wait for uvicorn to initialize

    api_base_url = "http://127.0.0.1:8090"
    post_endpoint = "/p2b/payments/verify-reserve-buyer-iban"
    merchant_post_endpoint = "/p2b/payments/verify-reserve-merchant-iban"
    sct_post_endpoint = "/p2b/payments/sct-initiation"
    debtor_post_endpoint = "/payments/verify-debtor-account"
    sct_v2_post_endpoint = "/payments/sct-initiation"
    delete_endpoint_tpl = "/payments/reserve/{transactionId}"

    def get_sct_test_headers(idempotency_key=None):
        ikey = idempotency_key or f"IDEMP-{uuid.uuid4().hex[:10]}"
        return {
            "Content-Type": "application/json",
            "x-idempotency-key": ikey,
            "x-request-id": f"REQ-{uuid.uuid4().hex[:10]}",
            "x-timestamp": datetime.now().isoformat(),
            "client-id": "client-test-id-12345",
            "authorization": "Bearer dummy_test_token_eyJhbGciOiJSUzI1NiIs...",
            "x-jws-signature": "eyJ0eXAiOiJKV1QiLC...",
            "BankUserId": "0000627978",
            "authorizationType": "01",
            "x-channel-name": "APP"
        }

    def get_sct_test_payload(tx_id=None, merchant_trx_id=None, use_iban=True):
        tid = tx_id or f"P2B{uuid.uuid4().hex[:16]}"
        mtrx = merchant_trx_id or f"MTRX-{uuid.uuid4().hex[:8]}"
        
        merchant = {
            "bankCode": "80754",
            "mcc": "9999",
            "merchantName": "John Smith Ltd",
            "merchantId": "SP808LX",
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
            "refTransactionId": f"P2B{uuid.uuid4().hex[:16]}",
            "refAuthorizationId": f"authId{uuid.uuid4().hex[:8]}",
            "amount": {
                "requested": 505.10,
                "currency": "AED"
            },
            "reason": "Soccer shoes",
            "merchant": merchant,
            "buyer": buyer,
            "requestToPay": False,
            "merchantTrxId": mtrx,
            "refMerchantTrxId": f"MTRX-REF-{uuid.uuid4().hex[:8]}",
            "transactionType": "P7IN",
            "categoryPurpose": "CCP"
        }

    def get_debtor_test_headers(idempotency_key=None):
        ikey = idempotency_key or f"IDEMP-{uuid.uuid4().hex[:10]}"
        return {
            "Content-Type": "application/json",
            "x-idempotency-key": ikey,
            "x-request-id": f"REQ-{uuid.uuid4().hex[:10]}",
            "x-timestamp": datetime.now().isoformat(),
            "client-id": "client-test-id-12345",
            "authorization": "Bearer dummy_test_token_eyJhbGciOiJSUzI1NiIs...",
            "x-jws-signature": "Detached signature",
            "debtorBankUserId": "0000627978",
            "x-channel-name": "APP"
        }

    def get_debtor_test_payload(tx_id=None, merchant_trx_id=None, use_iban=True):
        tid = tx_id or f"P2B{uuid.uuid4().hex[:16]}"
        mtrx = merchant_trx_id or f"MTRX-{uuid.uuid4().hex[:8]}"
        
        creditor = {
            "creditorAccount": {
                "creditorName": "Mark Brown"
            },
            "groupCode": "09999",
            "bankCode": "09999",
            "mcc": "7890",
            "label": "happy grocery",
            "merchantId": "12345678",
            "storeId": "00004",
            "cashDeskId": 10000001,
            "vat": "1234567890123456"
        }
        if use_iban:
            creditor["creditorAccount"]["iban"] = "AE2900078115245785609"
        else:
            creditor["creditorAccount"]["accountIdentifier"] = "30404040Y78115245785609"

        debtor = {
            "debtorAccount": {
                "debtorName": "Mark Brown"
            },
            "groupCode": "09999",
            "bankCode": "09999",
            "mobile": "+971581234567",
            "mcc": "7890",
            "label": "happy grocery",
            "merchantId": "12345678",
            "storeId": "00004",
            "cashDeskId": 10000001,
            "vat": "1234567890123456"
        }
        if use_iban:
            debtor["debtorAccount"]["iban"] = "AE2900078115245785609"
        else:
            debtor["debtorAccount"]["accountIdentifier"] = "4141414141414141"

        return {
            "payment": {
                "amount": 505.10,
                "currency": "AED",
                "transactionType": "P101",
                "transactionId": tid,
                "refTransactionId": f"P2B{uuid.uuid4().hex[:16]}",
                "refMerchantTrxId": f"MTRX-{uuid.uuid4().hex[:8]}",
                "merchantTrxId": mtrx,
                "requestToPay": False,
                "reservefunds": False
            },
            "categoryPurpose": "CCP",
            "creditor": creditor,
            "debtor": debtor
        }


    def get_merchant_test_headers(idempotency_key=None):
        ikey = idempotency_key or f"IDEMP-{uuid.uuid4().hex[:10]}"
        return {
            "Content-Type": "application/json",
            "x-idempotency-key": ikey,
            "x-request-id": f"REQ-{uuid.uuid4().hex[:10]}",
            "x-timestamp": datetime.now().isoformat(),
            "client-id": "client-test-id-12345",
            "authorization": "Bearer dummy_test_token_eyJhbGciOiJSUzI1NiIs...",
            "x-jws-signature": "eyJ0eXAiOiJKV1QiLC...",
            "merchantBankUserId": "0000621358",
            "x-channel-name": "APP"
        }

    def get_merchant_test_payload(tx_id=None, merchant_trx_id=None, use_iban=True):
        tid = tx_id or f"P2B{uuid.uuid4().hex[:16]}"
        mtrx = merchant_trx_id or f"MTRX-{uuid.uuid4().hex[:8]}"
        
        merchant = {
            "bankCode": "80754",
            "mcc": "9999",
            "merchantName": "John Smith Ltd",
            "merchantId": "SP808LX",
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
            "refTransactionId": f"P2B{uuid.uuid4().hex[:16]}",
            "amount": {
                "requested": 505.10,
                "currency": "AED"
            },
            "reason": "Soccer shoes",
            "merchant": merchant,
            "buyer": buyer,
            "requestToPay": False,
            "merchantTrxId": mtrx,
            "refMerchantTrxId": f"MTRX-REF-{uuid.uuid4().hex[:8]}",
            "transactionType": "P7IN",
            "categoryPurpose": "CCP"
        }

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
    # TEST 5: MERCHANT SYNCHRONOUS FLOW (POST 201)
    # ----------------------------------------------------
    print("\n[TEST 5] Merchant POST Verify Reserve -> HTTP 201 (Sync Flow)")
    config.Config.set("server", "post_response_mode", value="201")
    
    headers = get_merchant_test_headers()
    payload = get_merchant_test_payload()
    
    try:
        url = api_base_url + merchant_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        assert resp.json()["outcome"] == "000", "Expected outcome '000'"
        assert resp.json()["merchantTrxId"] == payload["merchantTrxId"], "merchantTrxId mismatch"
        print("-> [PASS] Merchant synchronous POST 201 flow is correct.")
    except Exception as e:
        print(f"-> [FAIL] Test 5 failed: {e}")

    # ----------------------------------------------------
    # TEST 6: MERCHANT ASYNCHRONOUS FLOW (POST 202 + GET Polling)
    # ----------------------------------------------------
    print("\n[TEST 6] Merchant POST Verify Reserve -> HTTP 202 & GET Polling (Async Flow)")
    config.Config.set("server", "post_response_mode", value="202")
    config.Config.set("server", "get_response_mode", value="200")
    config.Config.set("server", "poll_success_count", value=3)
    
    headers = get_merchant_test_headers()
    payload = get_merchant_test_payload()
    tx_id = payload["transactionId"]
    merchant_trx_id = payload["merchantTrxId"]

    try:
        # Send POST request
        url = api_base_url + merchant_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"POST Status Code: {resp.status_code}")
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
        
        # Poll GET
        poll_url = f"{api_base_url}{merchant_post_endpoint}?transactionId={tx_id}&merchantTrxId={merchant_trx_id}"
        
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
        assert resp_poll3.json()["transactionType"] == "P7IN", "Expected transactionType P7IN"

        print("-> [PASS] Merchant asynchronous polling flow behaves correctly (202, 202, 200).")
    except Exception as e:
        print(f"-> [FAIL] Test 6 failed: {e}")

    # ----------------------------------------------------
    # TEST 7: MERCHANT SCHEMA VALIDATION ERRORS
    # ----------------------------------------------------
    print("\n[TEST 7] Merchant Schema Validation Exception (Header/Body error checks)")
    
    # 7a: Missing mandatory header (merchantBankUserId)
    try:
        bad_headers = get_merchant_test_headers()
        bad_headers.pop("merchantBankUserId") # Missing!
        
        url = api_base_url + merchant_post_endpoint
        resp = requests.post(url, json=get_merchant_test_payload(), headers=bad_headers)
        print(f"Missing Header Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "merchantBankUserId" in resp.json()["errorMsg"]
        print("-> [PASS] Missing merchantBankUserId header is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 7a failed: {e}")

    # 7b: Invalid body schema (missing categoryPurpose field)
    try:
        bad_payload = get_merchant_test_payload()
        bad_payload.pop("categoryPurpose") # Missing!
        
        url = api_base_url + merchant_post_endpoint
        resp = requests.post(url, json=bad_payload, headers=get_merchant_test_headers())
        print(f"Missing categoryPurpose Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "categoryPurpose" in resp.json()["errorMsg"]
        print("-> [PASS] Missing categoryPurpose in body is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 7b failed: {e}")

    # ----------------------------------------------------
    # TEST 8: SCT SYNCHRONOUS FLOW (POST 201)
    # ----------------------------------------------------
    print("\n[TEST 8] SCT POST Initiation -> HTTP 201 (Sync Flow)")
    config.Config.set("server", "post_response_mode", value="201")
    
    headers = get_sct_test_headers()
    payload = get_sct_test_payload()
    
    try:
        url = api_base_url + sct_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        assert resp.json()["outcome"] == "000", "Expected outcome '000'"
        assert resp.json()["merchantTrxId"] == payload["merchantTrxId"], "merchantTrxId mismatch"
        assert "TRN" in resp.json(), "TRN should be present in 201 response"
        print("-> [PASS] SCT synchronous POST 201 flow is correct.")
    except Exception as e:
        print(f"-> [FAIL] Test 8 failed: {e}")

    # ----------------------------------------------------
    # TEST 9: SCT ASYNCHRONOUS FLOW (POST 202 + GET Polling)
    # ----------------------------------------------------
    print("\n[TEST 9] SCT POST Initiation -> HTTP 202 & GET Polling (Async Flow)")
    config.Config.set("server", "post_response_mode", value="202")
    config.Config.set("server", "get_response_mode", value="200")
    config.Config.set("server", "poll_success_count", value=3)
    
    headers = get_sct_test_headers()
    payload = get_sct_test_payload()
    tx_id = payload["transactionId"]

    try:
        # Send POST request
        url = api_base_url + sct_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"POST Status Code: {resp.status_code}")
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
        
        # Poll GET
        poll_url = f"{api_base_url}{sct_post_endpoint}?transactionId={tx_id}"
        
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
        assert resp_poll3.json()["transactionType"] == "P7IN", "Expected transactionType P7IN"
        assert "TRN" in resp_poll3.json(), "TRN should be present in 200 response"

        print("-> [PASS] SCT asynchronous polling flow behaves correctly (202, 202, 200).")
    except Exception as e:
        print(f"-> [FAIL] Test 9 failed: {e}")

    # ----------------------------------------------------
    # TEST 10: SCT SCHEMA VALIDATION ERRORS
    # ----------------------------------------------------
    print("\n[TEST 10] SCT Schema Validation Exception (Header/Body error checks)")
    
    # 10a: Missing BankUserId header
    try:
        bad_headers = get_sct_test_headers()
        bad_headers.pop("BankUserId") # Missing!
        
        url = api_base_url + sct_post_endpoint
        resp = requests.post(url, json=get_sct_test_payload(), headers=bad_headers)
        print(f"Missing BankUserId Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "BankUserId" in resp.json()["errorMsg"]
        print("-> [PASS] Missing BankUserId header is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 10a failed: {e}")

    # 10b: Missing categoryPurpose body parameter
    try:
        bad_payload = get_sct_test_payload()
        bad_payload.pop("categoryPurpose") # Missing!
        
        url = api_base_url + sct_post_endpoint
        resp = requests.post(url, json=bad_payload, headers=get_sct_test_headers())
        print(f"Missing categoryPurpose Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "categoryPurpose" in resp.json()["errorMsg"]
        print("-> [PASS] Missing categoryPurpose in body is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 10b failed: {e}")

    # ----------------------------------------------------
    # TEST 11: DEBTOR VERIFY SYNCHRONOUS FLOW
    # ----------------------------------------------------
    print("\n[TEST 11] Debtor Verify POST -> HTTP 201 (Sync Flow)")
    config.Config.set("server", "post_response_mode", value="201")
    
    headers = get_debtor_test_headers()
    payload = get_debtor_test_payload()
    
    try:
        url = api_base_url + debtor_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        assert resp.json()["outcome"] == "000", "Expected outcome '000'"
        assert "authorizationID" in resp.json(), "authorizationID should be present"
        assert "debtorAccount" in resp.json(), "debtorAccount should be present"
        print("-> [PASS] Debtor verify synchronous POST 201 flow is correct.")
    except Exception as e:
        print(f"-> [FAIL] Test 11 failed: {e}")

    # ----------------------------------------------------
    # TEST 12: DEBTOR VERIFY ASYNCHRONOUS FLOW (POST 202 + GET Polling)
    # ----------------------------------------------------
    print("\n[TEST 12] Debtor Verify POST -> HTTP 202 & GET Polling (Async Flow)")
    config.Config.set("server", "post_response_mode", value="202")
    config.Config.set("server", "get_response_mode", value="200")
    config.Config.set("server", "poll_success_count", value=3)
    
    headers = get_debtor_test_headers()
    payload = get_debtor_test_payload()
    tx_id = payload["payment"]["transactionId"]

    try:
        url = api_base_url + debtor_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"POST Status Code: {resp.status_code}")
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
        
        poll_url = f"{api_base_url}{debtor_post_endpoint}?transactionId={tx_id}"
        
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
        assert "authorizationID" in resp_poll3.json(), "authorizationID should be present"

        print("-> [PASS] Debtor verify asynchronous polling flow behaves correctly (202, 202, 200).")
    except Exception as e:
        print(f"-> [FAIL] Test 12 failed: {e}")

    # ----------------------------------------------------
    # TEST 13: SCT V2 SYNCHRONOUS FLOW (POST 201)
    # ----------------------------------------------------
    print("\n[TEST 13] SCT V2 POST Initiation -> HTTP 201 (Sync Flow)")
    config.Config.set("server", "post_response_mode", value="201")
    
    headers = get_debtor_test_headers()
    payload = get_debtor_test_payload()
    
    try:
        url = api_base_url + sct_v2_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
        assert resp.json()["outcome"] == "000", "Expected outcome '000'"
        assert "TRN" in resp.json(), "TRN should be present in 201 response"
        print("-> [PASS] SCT V2 synchronous POST 201 flow is correct.")
    except Exception as e:
        print(f"-> [FAIL] Test 13 failed: {e}")

    # ----------------------------------------------------
    # TEST 14: SCT V2 ASYNCHRONOUS FLOW (POST 202 + GET Polling via Path Param)
    # ----------------------------------------------------
    print("\n[TEST 14] SCT V2 POST Initiation -> HTTP 202 & GET Polling via Path Param (Async Flow)")
    config.Config.set("server", "post_response_mode", value="202")
    config.Config.set("server", "get_response_mode", value="200")
    config.Config.set("server", "poll_success_count", value=3)
    
    headers = get_debtor_test_headers()
    payload = get_debtor_test_payload()
    tx_id = payload["payment"]["transactionId"]

    try:
        url = api_base_url + sct_v2_post_endpoint
        resp = requests.post(url, json=payload, headers=headers)
        print(f"POST Status Code: {resp.status_code}")
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}"
        
        poll_url = f"{api_base_url}{sct_v2_post_endpoint}/{tx_id}"
        
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
        assert "TRN" in resp_poll3.json(), "TRN should be present in 200 response"

        print("-> [PASS] SCT V2 asynchronous polling flow behaves correctly.")
    except Exception as e:
        print(f"-> [FAIL] Test 14 failed: {e}")

    # ----------------------------------------------------
    # TEST 15: DEBTOR / SCT V2 SCHEMA VALIDATION ERRORS
    # ----------------------------------------------------
    print("\n[TEST 15] Debtor / SCT V2 Schema Validation Exception (Header/Body error checks)")
    
    # 15a: Missing debtorBankUserId header
    try:
        bad_headers = get_debtor_test_headers()
        bad_headers.pop("debtorBankUserId") # Missing!
        
        url = api_base_url + debtor_post_endpoint
        resp = requests.post(url, json=get_debtor_test_payload(), headers=bad_headers)
        print(f"Missing debtorBankUserId Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "debtorBankUserId" in resp.json()["errorMsg"]
        print("-> [PASS] Missing debtorBankUserId header is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 15a failed: {e}")

    # 15b: Missing payment body parameter
    try:
        bad_payload = get_debtor_test_payload()
        bad_payload.pop("payment") # Missing!
        
        url = api_base_url + debtor_post_endpoint
        resp = requests.post(url, json=bad_payload, headers=get_debtor_test_headers())
        print(f"Missing payment Status Code: {resp.status_code}")
        print("Response JSON:", json.dumps(resp.json(), indent=2))
        assert resp.status_code == 422
        assert resp.json()["outcome"] == "999"
        assert "payment" in resp.json()["errorMsg"]
        print("-> [PASS] Missing payment in body is caught and returned as structured UAEIPP error.")
    except Exception as e:
        print(f"-> [FAIL] Test 15b failed: {e}")

    # Clean Up
    print("\nStopping server...")
    engine.stop()
    print("==================================================")
    print("   INTEGRATION TESTING COMPLETED                  ")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
