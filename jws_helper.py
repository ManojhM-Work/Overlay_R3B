import base64
import json
import os
from typing import Union, Optional, Dict, Any
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

def base64url_encode(data: Union[bytes, str]) -> str:
    """
    Base64URL encode data (RFC 4648 §5) without padding '=' characters.
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data_str: str) -> bytes:
    """
    Decode Base64URL encoded string, handling missing padding.
    """
    rem = len(data_str) % 4
    if rem > 0:
        data_str += '=' * (4 - rem)
    return base64.urlsafe_b64decode(data_str.encode('utf-8'))

def load_private_key(key_input: Union[str, bytes], password: Optional[bytes] = None) -> rsa.RSAPrivateKey:
    """
    Load RSA private key from PEM bytes, PEM file path, or string.
    """
    if isinstance(key_input, str):
        if os.path.exists(key_input):
            with open(key_input, "rb") as f:
                key_bytes = f.read()
        else:
            key_bytes = key_input.encode('utf-8')
    else:
        key_bytes = key_input

    key = serialization.load_pem_private_key(key_bytes, password=password)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Provided key is not an RSA private key")
    return key

def load_public_key(cert_or_key_input: Union[str, bytes]) -> rsa.RSAPublicKey:
    """
    Load RSA public key from X.509 Certificate or RSA Public Key (PEM bytes, file path, or string).
    """
    if isinstance(cert_or_key_input, str):
        if os.path.exists(cert_or_key_input):
            with open(cert_or_key_input, "rb") as f:
                input_bytes = f.read()
        else:
            input_bytes = cert_or_key_input.encode('utf-8')
    else:
        input_bytes = cert_or_key_input

    # Try loading as X.509 certificate first
    try:
        cert = x509.load_pem_x509_certificate(input_bytes)
        pub_key = cert.public_key()
        if not isinstance(pub_key, rsa.RSAPublicKey):
            raise ValueError("Certificate public key is not an RSA public key")
        return pub_key
    except Exception:
        pass

    # Fallback to loading as public key
    pub_key = serialization.load_pem_public_key(input_bytes)
    if not isinstance(pub_key, rsa.RSAPublicKey):
        raise ValueError("Provided key is not an RSA public key")
    return pub_key

def get_cert_thumbprint(
    cert_input: Union[str, bytes, x509.Certificate],
    hash_alg: str = "sha256",
    fmt: str = "hex"
) -> str:
    """
    Compute thumbprint/fingerprint of X.509 certificate.
    fmt: 'hex' (uppercase hex without colons) or 'base64url'
    """
    if isinstance(cert_input, x509.Certificate):
        cert = cert_input
    else:
        if isinstance(cert_input, str):
            if os.path.exists(cert_input):
                with open(cert_input, "rb") as f:
                    cert_bytes = f.read()
            else:
                cert_bytes = cert_input.encode('utf-8')
        else:
            cert_bytes = cert_input
        cert = x509.load_pem_x509_certificate(cert_bytes)

    h_func = hashes.SHA256() if hash_alg.lower() == "sha256" else hashes.SHA1()
    digest = cert.fingerprint(h_func)

    if fmt.lower() == "base64url":
        return base64url_encode(digest)
    else:
        return digest.hex().upper()

def compose_detached_jws(
    payload: Union[Dict[str, Any], list, str, bytes],
    private_key_input: Union[str, bytes],
    kid: Optional[str] = None,
    cert_input: Optional[Union[str, bytes]] = None,
    password: Optional[bytes] = None,
    custom_header: Optional[Dict[str, str]] = None
) -> str:
    """
    Composes a Detachable Signature for x-jws-signature per UAEIPP Overlay API specification.

    Steps:
    1. Create JOSE header (alg: RS256, typ: JOSE, kid: Signing cert thumbprint)
    2. BASE64URL(UTF8(header))
    3. BASE64URL(payload)
    4. Concatenate: BASE64URL(UTF8(header)) + "." + BASE64URL(payload)
    5. RSA256 sign resulting string using private key -> BASE64URL(signature)
    6. Append signature: BASE64URL(UTF8(header)) + "." + BASE64URL(payload) + "." + BASE64URL(signature)
    7. Knock off payload part: BASE64URL(UTF8(header)) + ".." + BASE64URL(signature)
    """
    # Determine kid if not explicitly provided
    if not kid:
        if cert_input:
            kid = get_cert_thumbprint(cert_input, hash_alg="sha256", fmt="hex")
        else:
            kid = "default-kid"

    # Step 1: Create JOSE Header
    if custom_header:
        header_dict = custom_header
    else:
        header_dict = {
            "alg": "RS256",
            "typ": "JOSE",
            "kid": kid
        }
    header_json = json.dumps(header_dict, separators=(',', ':'))

    # Step 2: B64URL encode header
    b64_header = base64url_encode(header_json)

    # Step 3: Format and B64URL encode payload
    if isinstance(payload, (dict, list)):
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    elif isinstance(payload, str):
        payload_bytes = payload.encode('utf-8')
    elif isinstance(payload, bytes):
        payload_bytes = payload
    else:
        payload_bytes = str(payload).encode('utf-8')

    b64_payload = base64url_encode(payload_bytes)

    # Step 4: Concatenate strings, separated with a dot: BASE64URL(UTF8(header)) + "." + BASE64URL(payload)
    signing_input_str = f"{b64_header}.{b64_payload}"

    # Step 5: RSA256 sign string using private key
    private_key = load_private_key(private_key_input, password=password)
    raw_signature = private_key.sign(
        signing_input_str.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    b64_signature = base64url_encode(raw_signature)

    # Step 6 & 7: Knock off payload part of resulting string
    # BASE64URL(UTF8(header)) + ".." + BASE64URL(signature)
    detached_jws = f"{b64_header}..{b64_signature}"
    return detached_jws

def verify_detached_jws(
    jws_header_val: str,
    payload: Union[Dict[str, Any], list, str, bytes],
    public_key_or_cert_input: Union[str, bytes]
) -> bool:
    """
    Verifies a detached x-jws-signature against payload and matching public key/certificate.
    """
    if not jws_header_val:
        return False

    parts = jws_header_val.split('.')
    if len(parts) != 3:
        return False

    b64_header, empty_or_payload, b64_signature = parts

    # Format payload to base64url
    if isinstance(payload, (dict, list)):
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    elif isinstance(payload, str):
        payload_bytes = payload.encode('utf-8')
    elif isinstance(payload, bytes):
        payload_bytes = payload
    else:
        payload_bytes = str(payload).encode('utf-8')

    b64_payload = base64url_encode(payload_bytes)

    signing_input_str = f"{b64_header}.{b64_payload}"
    signature_bytes = base64url_decode(b64_signature)

    pub_key = load_public_key(public_key_or_cert_input)

    try:
        pub_key.verify(
            signature_bytes,
            signing_input_str.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False

def decode_jws_header(jws_header_val: str) -> dict:
    """
    Decodes the Base64URL encoded JOSE header from x-jws-signature string.
    """
    parts = jws_header_val.split('.')
    if not parts or not parts[0]:
        raise ValueError("Invalid JWS signature format")
    header_json_bytes = base64url_decode(parts[0])
    return json.loads(header_json_bytes.decode('utf-8'))
