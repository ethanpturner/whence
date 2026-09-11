"""Verify the recorded OMS bundles cryptographically and extract the signing identity.

Runs outside `whence`'s environment, because sigstore-python and cryptography are not dependencies
of the tool (DEC-021 defers verification; this measures what verification would find). Set up:

    uv venv .venv-sig && uv pip install --python .venv-sig/bin/python model-signing==1.1.1
    .venv-sig/bin/python docs/eval/signatures/tools/verify_bundles.py \
        docs/eval/signatures/dataset/signed_models.json docs/eval/signatures/recorded \
        docs/eval/signatures/verification.json

Bundle-only verification: the certificate chain against the public Sigstore trust root, the Rekor
inclusion proof carried in the bundle, and the DSSE signature over the in-toto statement. It does
not check that the signed digests match any files -- that needs the model's files, which this tool
does not download. The identity policy is `UnsafeNoOp`, on purpose: the point is to read who signed,
not to accept a signer. Network is used once, to fetch the Sigstore trust root through TUF.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.x509.oid import ExtensionOID, ObjectIdentifier
from sigstore.errors import VerificationError
from sigstore.models import Bundle, InvalidBundle
from sigstore.verify import Verifier, policy

ISSUER_V1 = ObjectIdentifier("1.3.6.1.4.1.57264.1.1")
ISSUER_V2 = ObjectIdentifier("1.3.6.1.4.1.57264.1.8")


def _identity(cert: x509.Certificate) -> tuple[list[str], str | None]:
    sans: list[str] = []
    try:
        san = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
        sans = [str(name.value) for name in san]
    except x509.ExtensionNotFound:
        pass
    for oid in (ISSUER_V2, ISSUER_V1):
        try:
            raw = cert.extensions.get_extension_for_oid(oid).value.value
        except x509.ExtensionNotFound:
            continue
        if oid == ISSUER_V2 and raw[:1] == b"\x0c":  # DER UTF8String
            raw = raw[2:] if raw[1] < 0x80 else raw[2 + (raw[1] & 0x7F) :]
        return sans, raw.decode("utf-8", "replace")
    return sans, None


def _bundle_path(recorded: Path, model: str) -> Path | None:
    flat = model.replace("/", "-")
    for candidate in (recorded / f"bundle-{flat}.json", recorded / f"cached-bundle-{flat}.json"):
        if candidate.exists():
            with candidate.open() as handle:
                body = json.load(handle)
            if isinstance(body, dict) and "dsseEnvelope" in body:
                return candidate
    return None


def main(argv: list[str]) -> int:
    dataset, recorded, out = Path(argv[1]), Path(argv[2]), Path(argv[3])
    with dataset.open() as handle:
        models = [str(entry["id"]) for entry in json.load(handle)["signed"]]
    verifier = Verifier.production()
    results: dict[str, dict[str, Any]] = {}
    for model in models:
        path = _bundle_path(recorded, model)
        record: dict[str, Any] = {"parses": False}
        if path is None:
            record["error"] = "no recorded bundle"
            results[model] = record
            continue
        raw = json.loads(path.read_text())
        material = raw.get("verificationMaterial") or {}
        tlog = material.get("tlogEntries") or []
        record["material"] = sorted(material.keys())
        try:
            bundle = Bundle.from_json(path.read_bytes())
        except (InvalidBundle, ValueError) as error:
            record["error"] = f"{type(error).__name__}: {error}"[:300]
            results[model] = record
            continue
        record["parses"] = True
        cert = bundle.signing_certificate
        sans, issuer = _identity(cert)
        record.update(
            {
                "san": sans,
                "issuer": issuer,
                "not_before": cert.not_valid_before_utc.isoformat(),
                "log_index": tlog[0].get("logIndex") if tlog else None,
            }
        )
        try:
            payload_type, payload = verifier.verify_dsse(bundle, policy.UnsafeNoOp())
        except VerificationError as error:
            record.update({"verifies": False, "error": f"{type(error).__name__}: {error}"[:300]})
        else:
            statement = json.loads(payload)
            record.update(
                {
                    "verifies": True,
                    "payload_type": payload_type,
                    "predicate_type": statement.get("predicateType"),
                    "n_subjects": len(statement.get("subject") or []),
                    "n_resources": len((statement.get("predicate") or {}).get("resources") or []),
                }
            )
        results[model] = record
        print(model, record.get("verifies"), record.get("san"), record.get("issuer"))
    out.write_text(json.dumps(results, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
