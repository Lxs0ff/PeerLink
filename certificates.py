import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from aioquic.quic.configuration import QuicConfiguration
import ssl
import hmac

def makeCert():
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "p2p")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert, key

def fingerprint(cert):
    return cert.fingerprint(hashes.SHA256()).hex()

def peer_matches(client, expected_hex):
    cert = getattr(client._quic.tls, "_peer_certificate", None)
    if cert is None:
        return False
    actual = cert.fingerprint(hashes.SHA256()).hex()
    return hmac.compare_digest(actual, expected_hex.lower())

def createHostConfig(code):
    cert, key = makeCert()
    config = QuicConfiguration(is_client=False,alpn_protocols=[code.strip(),"cutout-mesh-protocol"])
    config.max_datagram_frame_size = 1200
    config.certificate = cert
    config.private_key = key
    fp = fingerprint(cert)
    return config, cert, key,  fp

def createConfig(code):
    config = QuicConfiguration(is_client=True,alpn_protocols=[code.strip(),"cutout-mesh-protocol"])
    config.max_datagram_frame_size = 1200
    config.verify_mode = ssl.CERT_NONE
    return config
