import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import ipaddress

from cryptography.hazmat.primitives.serialization import pkcs12

def generate_self_signed_certs(output_dir="certs"):
    os.makedirs(output_dir, exist_ok=True)
    
    server_key_path = os.path.join(output_dir, "server.key")
    server_crt_path = os.path.join(output_dir, "server.crt")
    client_key_path = os.path.join(output_dir, "client.key")
    client_crt_path = os.path.join(output_dir, "client_ca.crt")
    client_p12_path = os.path.join(output_dir, "client.p12")

    # 1. Generate Server Private Key & Certificate
    if not (os.path.exists(server_key_path) and os.path.exists(server_crt_path)):
        print("Generating Server Key and Certificate...")
        server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Expleo Simulator"),
        ])
        server_cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
                critical=False,
            )
            .sign(server_key, hashes.SHA256())
        )

        with open(server_key_path, "wb") as f:
            f.write(server_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(server_crt_path, "wb") as f:
            f.write(server_cert.public_bytes(serialization.Encoding.PEM))
        print(f"Created: {server_crt_path}, {server_key_path}")

    # 2. Generate Client Key & Certificate (Client CA)
    if not (os.path.exists(client_key_path) and os.path.exists(client_crt_path)):
        print("Generating Client Key and Certificate (Client CA)...")
        client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        client_subject = client_issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "UAEIPP Client Participant"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Client Bank"),
        ])
        client_cert = (
            x509.CertificateBuilder()
            .subject_name(client_subject)
            .issuer_name(client_issuer)
            .public_key(client_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
            .sign(client_key, hashes.SHA256())
        )

        with open(client_key_path, "wb") as f:
            f.write(client_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(client_crt_path, "wb") as f:
            f.write(client_cert.public_bytes(serialization.Encoding.PEM))
        print(f"Created: {client_crt_path}, {client_key_path}")

    # 3. Generate PKCS12 (.p12) KeyStore for JMeter
    if os.path.exists(client_key_path) and os.path.exists(client_crt_path) and not os.path.exists(client_p12_path):
        print("Generating Client PKCS12 Keystore (client.p12) for JMeter...")
        with open(client_key_path, "rb") as f:
            c_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(client_crt_path, "rb") as f:
            c_cert = x509.load_pem_x509_certificate(f.read())

        p12_data = pkcs12.serialize_key_and_certificates(
            name=b"jmeter-client",
            key=c_key,
            cert=c_cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b"password123")
        )
        with open(client_p12_path, "wb") as f:
            f.write(p12_data)
        print(f"Created: {client_p12_path} (password: password123)")

if __name__ == "__main__":
    generate_self_signed_certs()

