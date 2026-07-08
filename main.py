import os
import time
import threading
import uuid
import json
import asyncio
import random
from datetime import datetime
from typing import Optional, Any
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from models import VerifyReserveRequest, VerifyReserveResponse
from logger_helper import logger
import config

# Thread-safe queue to feed dynamic traffic events directly to the Tkinter GUI thread
_traffic_queue = None

# Thread-safe global transaction counters
stats_lock = threading.Lock()
stats = {
    "total": 0,
    "processed": 0,
    "errors": 0
}

# Thread-safe global in-memory poll counter
poll_counter_lock = threading.Lock()
poll_counter = {}

# Capped list for in-memory history storage
history_lock = threading.Lock()
history_records = []
MAX_HISTORY_LEN = 1000

def set_traffic_queue(q):
    global _traffic_queue
    _traffic_queue = q

def reset_stats():
    global stats, poll_counter, history_records
    with stats_lock:
        stats = {
            "total": 0,
            "processed": 0,
            "errors": 0
        }
    with poll_counter_lock:
        poll_counter.clear()
    with history_lock:
        history_records.clear()

def add_history_record(record):
    with history_lock:
        if len(history_records) >= MAX_HISTORY_LEN:
            history_records.pop(0)
        history_records.append(record)

# FastAPI App
app = FastAPI(
    title="UAEIPP Buyer Participant Simulator",
    description="A high-performance FastAPI simulator for the UAEIPP Verify Reserve phase.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "UP", "timestamp": datetime.now().isoformat()}

# Standard UAEIPP Error Outcomes mapping
ERROR_OUTCOMES = {
    400: ("400", "Bad Request"),
    401: ("401", "Unauthorized"),
    403: ("403", "Forbidden"),
    404: ("404", "Not Found"),
    409: ("409", "Conflict"),
    422: ("422", "Unprocessable Entity"),
    429: ("429", "Too Many Requests"),
    500: ("500", "Internal Server Error"),
    502: ("502", "Bad Gateway"),
    503: ("503", "Service Unavailable"),
    504: ("504", "Gateway Timeout")
}

def make_response_headers(request_headers: dict) -> dict:
    def get_str(key, fallback="N/A"):
        val = request_headers.get(key)
        if val is None:
            # Case insensitive fallback search if key not found directly
            for k, v in request_headers.items():
                if k.lower() == key.lower() and v is not None:
                    return str(v)
            return fallback
        return str(val)

    return {
        "x-idempotency-key": get_str("x-idempotency-key"),
        "X-Request-ID": get_str("x-request-id"),
        "x-timestamp": datetime.now().isoformat(),
        "x-ratelimit-remaining": "8",
        "x-ratelimit-limit": "10",
        "x-ratelimit-reset": str(int(time.time()) + 60),
        "x-jws-signature": get_str("x-jws-signature", ""),
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
        "X-XSS-Protection": "1; mode=block",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'"
    }

def send_traffic_update(
    endpoint_name: str, 
    method: str,
    req_json: Optional[dict], 
    resp_json: Optional[dict], 
    status: str,
    elapsed_ms: float,
    corr_id: str,
    msg_id: str,
    poll_count: int,
    headers: dict,
    resp_headers: dict
):
    global stats
    with stats_lock:
        current_total = stats["total"]
        current_processed = stats["processed"]
        current_errors = stats["errors"]

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Add to in-memory history
    record = {
        "timestamp": timestamp,
        "endpoint": endpoint_name,
        "method": method,
        "request": req_json,
        "response": resp_json,
        "status": status,
        "poll_number": poll_count,
        "elapsed_time": elapsed_ms
    }
    add_history_record(record)

    if _traffic_queue is not None:
        try:
            high_perf = config.Config.get("server", "high_perf", default=False)
            
            if high_perf:
                _traffic_queue.put_nowait({
                    "stats": {
                        "total": current_total,
                        "processed": current_processed,
                        "errors": current_errors
                    }
                })
            else:
                # Format a user-friendly inspector view
                req_view = (
                    f"--- REQUEST METADATA ---\n"
                    f"Timestamp: {timestamp}\n"
                    f"Endpoint:  {endpoint_name}\n"
                    f"Method:    {method}\n"
                    f"Headers:\n{json.dumps(headers, indent=2)}\n\n"
                    f"--- REQUEST PAYLOAD ---\n"
                    f"{json.dumps(req_json, indent=2) if req_json else 'N/A'}"
                )
                
                resp_view = (
                    f"--- RESPONSE METADATA ---\n"
                    f"Returned Status Code: {status}\n"
                    f"Elapsed Time:        {elapsed_ms:.2f} ms\n"
                    f"Poll Count:          {poll_count}\n"
                    f"Headers:\n{json.dumps(resp_headers, indent=2)}\n\n"
                    f"--- RESPONSE PAYLOAD ---\n"
                    f"{json.dumps(resp_json, indent=2) if resp_json else 'N/A'}"
                )

                _traffic_queue.put_nowait({
                    "input_queue": f"{method} {endpoint_name}",
                    "output_queue": f"HTTP {status}",
                    "request_xml": req_view,
                    "response_xml": resp_view,
                    "biz_msg_idr": corr_id,
                    "msg_id": msg_id,
                    "timestamp": timestamp,
                    "status": f"HTTP {status}",
                    "stats": {
                        "total": current_total,
                        "processed": current_processed,
                        "errors": current_errors
                    }
                })
        except Exception as e:
            logger.error(f"Failed to push to traffic queue: {e}")

# Override validation handler to return strict UAEIPP-style validation messages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    global stats
    with stats_lock:
        stats["total"] += 1
        stats["errors"] += 1
        current_total = stats["total"]

    start_time = time.perf_counter()
    errors = exc.errors()
    error_msg = "; ".join([f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors])
    
    transaction_type = "N/A"
    merchant_trx_id = "N/A"
    transaction_id = "N/A"
    
    try:
        body = await request.json()
        if isinstance(body, dict):
            transaction_type = body.get("transactionType", "N/A")
            merchant_trx_id = body.get("merchantTrxId", "N/A")
            transaction_id = body.get("transactionId", "N/A")
    except Exception:
        pass

    raw_headers = dict(request.headers)
    resp_body = {
        "outcome": "999",
        "errorMsg": f"Schema Validation Error - {error_msg}",
        "transactionType": transaction_type,
        "merchantTrxId": merchant_trx_id
    }
    
    resp_headers = make_response_headers(raw_headers)
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    # Report to logs and UI
    logger.error(f"[TRANS #{current_total}] Request schema validation failed: {error_msg}")
    send_traffic_update(
        endpoint_name=request.url.path,
        method=request.method,
        req_json={"validation_errors": errors},
        resp_json=resp_body,
        status="422",
        elapsed_ms=elapsed_ms,
        corr_id=raw_headers.get("x-idempotency-key", "N/A"),
        msg_id=transaction_id,
        poll_count=0,
        headers=raw_headers,
        resp_headers=resp_headers
    )
    
    return JSONResponse(status_code=422, content=resp_body, headers=resp_headers)


def select_random_response(endpoint: str) -> str:
    if endpoint == "POST":
        options = ["201", "202", "400", "401", "404", "409", "500", "Timeout", "No Response"]
        weights = [0.70,  0.15,  0.02,  0.02,  0.02,  0.02,  0.03,  0.02,      0.02]
        return random.choices(options, weights=weights, k=1)[0]
    elif endpoint == "GET":
        options = ["200", "202", "400", "404", "500", "Timeout", "No Response"]
        weights = [0.70,  0.15,  0.03,  0.03,  0.05,  0.02,      0.02]
        return random.choices(options, weights=weights, k=1)[0]
    else:  # DELETE
        options = ["200", "202", "400", "500", "Timeout", "No Response"]
        weights = [0.80,  0.05,  0.05,  0.05,  0.025,     0.025]
        return random.choices(options, weights=weights, k=1)[0]


async def handle_timeout_and_no_response(request: Request, delay_sec: float, timeout_mode: str, details_label: str):
    logger.info(f"Simulating {details_label} using mode: {timeout_mode}")
    if timeout_mode == "Sleep":
        # Mode 1: Sleep longer than configured delay (simulate sleep timeout)
        sleep_time = max(delay_sec + 5.0, 15.0)
        await asyncio.sleep(sleep_time)
        return JSONResponse(
            status_code=504, 
            content={"outcome": "999", "errorMsg": "Gateway Timeout Simulated", "transactionType": "N/A", "merchantTrxId": "N/A"}
        )
    elif timeout_mode == "Never Respond":
        # Mode 2: Never respond (infinite sleep)
        await asyncio.sleep(3600.0)
        return JSONResponse(
            status_code=504, 
            content={"outcome": "999", "errorMsg": "Infinite Timeout Simulated", "transactionType": "N/A", "merchantTrxId": "N/A"}
        )
    elif timeout_mode == "Close Connection":
        # Mode 3: Close connection immediately
        transport = request.scope.get("transport")
        if transport:
            transport.close()
        raise asyncio.CancelledError()


# Header Validation Dependency
async def validate_headers(
    request: Request,
    x_idempotency_key: str = Header(..., alias="x-idempotency-key"),
    x_request_id: str = Header(..., alias="x-request-id"),
    x_timestamp: str = Header(..., alias="x-timestamp"),
    client_id: str = Header(..., alias="client-id"),
    authorization: str = Header(..., alias="authorization"),
    x_jws_signature: Optional[str] = Header(None, alias="x-jws-signature"),
    buyerBankUserId: Optional[str] = Header(None, alias="buyerBankUserId")
):
    return {
        "x-idempotency-key": x_idempotency_key,
        "x-request-id": x_request_id,
        "x-timestamp": x_timestamp,
        "client-id": client_id,
        "authorization": authorization,
        "x-jws-signature": x_jws_signature,
        "buyerBankUserId": buyerBankUserId
    }


# ---------------------------------------------------------
# 1. POST Verify Reserve Buyer IBAN
# ---------------------------------------------------------
@app.post("/p2b/payments/verify-reserve-buyer-iban")
async def verify_reserve_buyer_iban(
    request: Request,
    payload: VerifyReserveRequest,
    headers: dict = Depends(validate_headers)
):
    global stats
    start_time = time.perf_counter()
    
    with stats_lock:
        stats["total"] += 1
        current_total = stats["total"]

    req_json = payload.dict(by_alias=True)
    transaction_id = payload.transactionId
    merchant_trx_id = payload.merchantTrxId
    trx_type = payload.transactionType

    # Read configuration values
    delay = float(config.Config.get("server", "response_delay_seconds", default=0.0))
    random_response = config.Config.get("server", "random_response_enabled", default=False)
    timeout_mode = config.Config.get("server", "timeout_mode", default="Sleep")
    logging_enabled = config.Config.get("server", "logging_enabled", default=True)

    # Determine POST Response Mode
    if random_response:
        response_mode = select_random_response("POST")
    else:
        response_mode = config.Config.get("server", "post_response_mode", default="201")

    # Apply Delay non-blockingly
    if delay > 0:
        await asyncio.sleep(delay)

    # Initialize headers
    resp_headers = make_response_headers(headers)

    # Log variables
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    thread_id = threading.get_ident()

    # Handle Timeouts
    if response_mode in ("Timeout", "No Response"):
        with stats_lock:
            stats["errors"] += 1
        send_traffic_update(
            "/p2b/payments/verify-reserve-buyer-iban", "POST", req_json, None, 
            "TIMEOUT", elapsed_ms, headers["x-idempotency-key"], transaction_id, 0, headers, resp_headers
        )
        return await handle_timeout_and_no_response(request, delay, timeout_mode, response_mode)

    # Handle Standard Status Codes
    status_code = int(response_mode)
    if status_code in (201, 202):
        resp_body = {
            "outcome": "000",
            "errorMsg": "",
            "transactionType": trx_type,
            "merchantTrxId": merchant_trx_id
        }
        with stats_lock:
            stats["processed"] += 1
        
        # Initialize polling counts for GET route
        with poll_counter_lock:
            # Auto-cleanup older records
            if len(poll_counter) > 5000:
                keys_to_del = list(poll_counter.keys())[:1000]
                for k in keys_to_del:
                    poll_counter.pop(k, None)
            poll_counter[transaction_id] = 0
            
    else:
        # Error responses
        err_info = ERROR_OUTCOMES.get(status_code, ("999", "Unknown Simulated Error"))
        resp_body = {
            "outcome": err_info[0],
            "errorMsg": err_info[1],
            "transactionType": trx_type,
            "merchantTrxId": merchant_trx_id
        }
        with stats_lock:
            stats["errors"] += 1

    # Log Transaction
    if logging_enabled:
        log_msg = (
            f"\n==================================================\n"
            f"VERIFY RESERVE POST [{datetime.now().isoformat()}]\n"
            f"--------------------------------------------------\n"
            f"Transaction ID:    {transaction_id}\n"
            f"Merchant Trx ID:   {merchant_trx_id}\n"
            f"Response Mode:     {response_mode}\n"
            f"Returned HTTP:     {status_code}\n"
            f"Elapsed Time:      {elapsed_ms:.2f} ms\n"
            f"Thread ID:         {thread_id}\n"
            f"Correlation ID:    {headers['x-idempotency-key']}\n"
            f"Payload:           {json.dumps(req_json, indent=2)}\n"
            f"Response:          {json.dumps(resp_body, indent=2)}\n"
            f"=================================================="
        )
        logger.info(log_msg)

    send_traffic_update(
        "/p2b/payments/verify-reserve-buyer-iban", "POST", req_json, resp_body, 
        str(status_code), elapsed_ms, headers["x-idempotency-key"], transaction_id, 0, headers, resp_headers
    )

    return JSONResponse(status_code=status_code, content=resp_body, headers=resp_headers)


# ---------------------------------------------------------
# 2. GET Poll Verify Reserve Buyer IBAN
# ---------------------------------------------------------
@app.get("/p2b/payments/verify-reserve-buyer-iban")
async def get_verify_reserve_buyer_iban(
    request: Request,
    transactionId: Optional[str] = None,
    merchantTrxId: Optional[str] = None
):
    global stats
    start_time = time.perf_counter()
    
    with stats_lock:
        stats["total"] += 1
        current_total = stats["total"]

    raw_headers = dict(request.headers)

    # Read configuration values
    delay = float(config.Config.get("server", "response_delay_seconds", default=0.0))
    random_response = config.Config.get("server", "random_response_enabled", default=False)
    timeout_mode = config.Config.get("server", "timeout_mode", default="Sleep")
    poll_success_count = int(config.Config.get("server", "poll_success_count", default=3))
    logging_enabled = config.Config.get("server", "logging_enabled", default=True)

    # Determine GET Response Mode
    if random_response:
        response_mode = select_random_response("GET")
    else:
        response_mode = config.Config.get("server", "get_response_mode", default="200")

    # Retrieve correlation keys
    corr_id = raw_headers.get("x-idempotency-key", "N/A")
    msg_id = transactionId if transactionId else "N/A"

    # Increment Polling Counter if transaction exists and mode is 200/dynamic polling
    current_poll = 0
    if transactionId:
        with poll_counter_lock:
            if transactionId in poll_counter:
                poll_counter[transactionId] += 1
                current_poll = poll_counter[transactionId]
            else:
                poll_counter[transactionId] = 1
                current_poll = 1

    # Apply Delay non-blockingly
    if delay > 0:
        await asyncio.sleep(delay)

    # Initialize headers
    resp_headers = make_response_headers(raw_headers)

    # Log variables
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    thread_id = threading.get_ident()

    # Handle Timeouts
    if response_mode in ("Timeout", "No Response"):
        with stats_lock:
            stats["errors"] += 1
        send_traffic_update(
            "/p2b/payments/verify-reserve-buyer-iban", "GET", {"transactionId": transactionId, "merchantTrxId": merchantTrxId}, None, 
            "TIMEOUT", elapsed_ms, corr_id, msg_id, current_poll, raw_headers, resp_headers
        )
        return await handle_timeout_and_no_response(request, delay, timeout_mode, response_mode)

    # Evaluate dynamic success counter if selected response mode is 200
    status_code = 200
    if response_mode == "200":
        if current_poll < poll_success_count:
            status_code = 202
        else:
            status_code = 200
    else:
        status_code = int(response_mode)

    if status_code in (200, 202):
        resp_body = {
            "outcome": "000",
            "errorMsg": "",
            "transactionType": "P613",
            "merchantTrxId": merchantTrxId if merchantTrxId else "N/A"
        }
        with stats_lock:
            stats["processed"] += 1
    else:
        err_info = ERROR_OUTCOMES.get(status_code, ("999", "Unknown Polling Error"))
        resp_body = {
            "outcome": err_info[0],
            "errorMsg": err_info[1],
            "transactionType": "P613",
            "merchantTrxId": merchantTrxId if merchantTrxId else "N/A"
        }
        with stats_lock:
            stats["errors"] += 1

    # Log Poll Transaction
    if logging_enabled:
        log_msg = (
            f"\n==================================================\n"
            f"VERIFY RESERVE GET POLL [{datetime.now().isoformat()}]\n"
            f"--------------------------------------------------\n"
            f"Transaction ID:    {transactionId}\n"
            f"Merchant Trx ID:   {merchantTrxId}\n"
            f"Poll Number:       {current_poll} / {poll_success_count}\n"
            f"Response Mode:     {response_mode} (Evaluated HTTP: {status_code})\n"
            f"Elapsed Time:      {elapsed_ms:.2f} ms\n"
            f"Thread ID:         {thread_id}\n"
            f"Correlation ID:    {corr_id}\n"
            f"Response:          {json.dumps(resp_body, indent=2)}\n"
            f"=================================================="
        )
        logger.info(log_msg)

    send_traffic_update(
        "/p2b/payments/verify-reserve-buyer-iban", "GET", {"transactionId": transactionId, "merchantTrxId": merchantTrxId}, resp_body, 
        str(status_code), elapsed_ms, corr_id, msg_id, current_poll, raw_headers, resp_headers
    )

    return JSONResponse(status_code=status_code, content=resp_body, headers=resp_headers)


# ---------------------------------------------------------
# 3. DELETE Reserve
# ---------------------------------------------------------
@app.delete("/payments/reserve/{transactionId}")
async def delete_reserve(
    request: Request,
    transactionId: str
):
    global stats
    start_time = time.perf_counter()
    
    with stats_lock:
        stats["total"] += 1
        current_total = stats["total"]

    raw_headers = dict(request.headers)

    # Read configuration values
    delay = float(config.Config.get("server", "response_delay_seconds", default=0.0))
    random_response = config.Config.get("server", "random_response_enabled", default=False)
    timeout_mode = config.Config.get("server", "timeout_mode", default="Sleep")
    logging_enabled = config.Config.get("server", "logging_enabled", default=True)

    # Determine DELETE Response Mode
    if random_response:
        response_mode = select_random_response("DELETE")
    else:
        response_mode = config.Config.get("server", "delete_response_mode", default="200")

    corr_id = raw_headers.get("x-idempotency-key", "N/A")
    msg_id = transactionId

    # Idempotent deletion: remove transaction count state from dict without throwing error if absent
    with poll_counter_lock:
        existed = transactionId in poll_counter
        poll_counter.pop(transactionId, None)

    # Apply Delay non-blockingly
    if delay > 0:
        await asyncio.sleep(delay)

    # Initialize headers
    resp_headers = make_response_headers(raw_headers)

    # Log variables
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    thread_id = threading.get_ident()

    # Handle Timeouts
    if response_mode in ("Timeout", "No Response"):
        with stats_lock:
            stats["errors"] += 1
        send_traffic_update(
            f"/payments/reserve/{transactionId}", "DELETE", None, None, 
            "TIMEOUT", elapsed_ms, corr_id, msg_id, 0, raw_headers, resp_headers
        )
        return await handle_timeout_and_no_response(request, delay, timeout_mode, response_mode)

    status_code = int(response_mode)
    if status_code in (200, 202):
        resp_body = {
            "outcome": "000",
            "errorMsg": "",
            "transactionId": transactionId
        }
        with stats_lock:
            stats["processed"] += 1
    else:
        err_info = ERROR_OUTCOMES.get(status_code, ("999", "Unknown Delete Error"))
        resp_body = {
            "outcome": err_info[0],
            "errorMsg": err_info[1],
            "transactionId": transactionId
        }
        with stats_lock:
            stats["errors"] += 1

    # Log Delete Transaction
    if logging_enabled:
        log_msg = (
            f"\n==================================================\n"
            f"VERIFY RESERVE DELETE [{datetime.now().isoformat()}]\n"
            f"--------------------------------------------------\n"
            f"Transaction ID:    {transactionId}\n"
            f"State Existed:     {existed}\n"
            f"Response Mode:     {response_mode}\n"
            f"Returned HTTP:     {status_code}\n"
            f"Elapsed Time:      {elapsed_ms:.2f} ms\n"
            f"Thread ID:         {thread_id}\n"
            f"Correlation ID:    {corr_id}\n"
            f"Response:          {json.dumps(resp_body, indent=2)}\n"
            f"=================================================="
        )
        logger.info(log_msg)

    send_traffic_update(
        f"/payments/reserve/{transactionId}", "DELETE", None, resp_body, 
        str(status_code), elapsed_ms, corr_id, msg_id, 0, raw_headers, resp_headers
    )

    return JSONResponse(status_code=status_code, content=resp_body, headers=resp_headers)


class FastAPIServerEngine:
    def __init__(self, host, port):
        self.host = host
        self.port = int(port)
        self.server = None
        self.thread = None

    def start(self):
        # Allow reusing address for quick restarts during testing
        config_obj = uvicorn.Config(app, host=self.host, port=self.port, log_level="warning", loop="asyncio")
        self.server = uvicorn.Server(config_obj)
        
        # Run the server in a separate thread
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        logger.info(f"FastAPI Server Engine started on {self.host}:{self.port}")

    def stop(self):
        if self.server:
            logger.info("FastAPI Server Engine stopping...")
            self.server.should_exit = True
            if self.thread and self.thread.is_alive():
                # Allow a brief moment for the thread to catch the exit signal
                time.sleep(0.5)
            logger.info("FastAPI Server Engine stopped.")
