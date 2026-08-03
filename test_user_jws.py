import json
import jws_helper

sig = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpPU0UiLCJraWQiOiIzRDY1MjdCREYyOEQ5QTJEMjg1NkM2ODk0OUFERTVGNzQzMkEwRTMzQkRBODQxMkI5QzUyODlFNDY5QUQ1NEE5In0..TgAT6INgPcULk5Gze2L1h2nGyWORbN8GeU2YYpzUuksdS-EQFf1zNU8x4CxkPHSEcwPGUhatvImSuxI_2U0CyW35TkWGOl9xyi8UVS3smwtbpyI1MUlru4VJ1pqEubza6FTxCdDukgB78uTrdjNgfXdIRThtCfTvEffasa1OIZVA0sL4zM44Lk3J4QX9Cbr_0-0bya8KxyqgFHc-xcKKs-e0Y9VPJ0smCPlf0_JFF01GhHJdlBRcXiIA_SDFG-iitg0TGWtFc027KRs7aabBhle228iOEpAj4b6TfFWxZ7mia5q5tmD-Kmf3llgMXUaFsQk3yJq0BB3lh4g4B5JrOg"

body = '{"outcome":"000","errorMsg":"","authorizationID":"authId8564484661","debtorAccount":{"iban":"AE2900078115245785609","accountIdentifier":null}}'

header = jws_helper.decode_jws_header(sig)
cert_thumbprint = jws_helper.get_cert_thumbprint("certs/server.crt")
is_valid = jws_helper.verify_detached_jws(sig, body, "certs/server.crt")

print("--- JWS Verification Results ---")
print("1. JOSE Header:", json.dumps(header, indent=2))
print("2. Certificate Thumbprint (kid):", cert_thumbprint)
print("3. kid Match:", header.get("kid") == cert_thumbprint)
print("4. Signature Verification Result:", is_valid)
