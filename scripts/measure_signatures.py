"""What the 64 published `model.sig` bundles bind, and to whom.

DEC-021 detects an OMS bundle and never calls it `valid`, because presence establishes that
somebody signed something -- not that the signature verifies, that it covers the files in front of
you, or that the identity it binds is the publisher's. This script measures each of those three
gaps on every signed model in the 45,000 most downloaded (swept 2026-09-10).

    uv run python scripts/measure_signatures.py            # replay the recording, offline
    uv run python scripts/measure_signatures.py --live     # capture a fresh recording

Cryptographic verification -- certificate chain, Rekor inclusion proof, DSSE signature -- is done
by `docs/eval/signatures/tools/verify_bundles.py` in its own environment (sigstore-python and
cryptography are not dependencies of this tool), and its output is committed as
`docs/eval/signatures/verification.json`. This script reads that file and joins it with what the
registry serves: the model's file listing, the bundle's own statement, and the publishing
namespace. Everything it computes from the bundle is a stdlib read of recorded JSON.

Identity-match rule, stated so it can be disagreed with: the signing certificate's SAN e-mail
domain is reduced to its second-level label (`ibm.com` -> `ibm`); the publishing namespace is
lower-cased and split on `-`, `_`, and `.`; the bundle `matches` if the label is one of the
namespace's tokens, `does-not-match` if a SAN is present and it is not, and is `undeterminable`
when no SAN e-mail was verified. The rule is deliberately literal. It would call a bundle signed
by `example.com` and published under `example-labs` a match, and that is the weakest claim it makes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from whence.domain import ArtifactRef
from whence.registry import LiveRegistry, RecordedRegistry, Registry, Response
from whence.signing import detect, signature_path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "docs" / "eval" / "signatures"
DATASET = EVAL / "dataset" / "signed_models.json"
RECORDED = EVAL / "recorded"
VERIFICATION = EVAL / "verification.json"

MODEL_FIELDS = ("id", "author", "sha", "gated", "private")
ORG_FIELDS = ("name", "fullname", "isVerified", "plan", "numModels", "error")


def _project(path: str, response: Response) -> Response:
    body = response.body
    if body is None:
        return response
    if path.startswith("/api/models/") and isinstance(body, dict):
        kept: dict[str, Any] = {k: body[k] for k in MODEL_FIELDS if k in body}
        kept["siblings"] = [
            {"rfilename": s["rfilename"]}
            for s in body.get("siblings") or []
            if isinstance(s, dict) and "rfilename" in s
        ]
        return Response(status=response.status, body=kept, location=response.location)
    if path.startswith(("/api/organizations/", "/api/users/")) and isinstance(body, dict):
        return Response(
            status=response.status,
            body={k: body[k] for k in ORG_FIELDS if k in body},
            location=response.location,
        )
    return response


class _Recording:
    def __init__(self, inner: LiveRegistry) -> None:
        self._inner = inner
        self.seen: dict[str, Response] = {}
        self.order: list[str] = []

    def get(self, path: str) -> Response:
        import time

        if path in self.seen:
            return self.seen[path]
        for attempt in range(8):
            time.sleep(1.2)
            response = self._inner.get(path)
            if response.status == 429 or response.status == 0:
                print(
                    f"{response.status} on {path}; waiting (attempt {attempt + 1})", file=sys.stderr
                )
                time.sleep(90)
                continue
            response = _project(path, response)
            self.seen[path] = response
            self.order.append(path)
            return response
        raise SystemExit(f"{path} stayed unreachable; recording stopped (DEC-014)")

    def write(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Captured registry interactions, replayed offline (DEC-009). Written by",
            "# scripts/measure_signatures.py. Model listings are projected to",
            "# id/author/sha/gated/private and the sibling file names; overviews to",
            "# name/fullname/isVerified/plan/numModels. Bundles are recorded whole. Every status,",
            "# redirect and kept value is what the registry returned.",
            f"captured_at: {datetime.now(tz=UTC).date().isoformat()}",
            "host: huggingface.co",
            "interactions:",
        ]
        for path in self.order:
            response = self.seen[path]
            lines.append(f"  - request: GET {path}")
            lines.append(f"    status: {response.status}")
            if response.location:
                lines.append(f"    location: {response.location}")
            if response.body is None:
                lines.append("    body: null")
            else:
                name = _filename(path) + ".json"
                (directory / name).write_text(json.dumps(response.body))
                lines.append(f"    body: {name}")
        (directory / "manifest.yaml").write_text("\n".join(lines) + "\n")


def _filename(path: str) -> str:
    trimmed = path.lstrip("/")
    if trimmed.startswith("api/models/"):
        return "model-" + trimmed[len("api/models/") :].replace("/", "-")
    if trimmed.startswith("api/organizations/"):
        return "org-" + trimmed[len("api/organizations/") :].replace("/overview", "")
    if trimmed.startswith("api/users/"):
        return "user-" + trimmed[len("api/users/") :].replace("/overview", "")
    if "/resolve/main/model.sig" in trimmed:
        return "bundle-" + trimmed.split("/resolve/")[0].replace("/", "-")
    if trimmed.startswith("api/resolve-cache/models/"):
        rest = trimmed[len("api/resolve-cache/models/") :]
        return "cached-bundle-" + "/".join(rest.split("/")[:2]).replace("/", "-")
    return trimmed.replace("/", "-").replace("?", "-").replace("&", "-")[:120]


def _ref(slug: str, revision: str | None) -> ArtifactRef:
    namespace, name = slug.split("/", 1)
    return ArtifactRef(
        host="huggingface.co",
        namespace=namespace,
        name=name,
        revision=revision,
        pinned=revision is not None,
    )


def _bundle(registry: Registry, ref: ArtifactRef) -> dict[str, Any] | None:
    response = registry.get(signature_path(ref))
    hops = 0
    while response.redirected and hops < 3:
        response = registry.get(str(response.location))
        hops += 1
    return response.body if response.status == 200 and isinstance(response.body, dict) else None


def _statement(bundle: dict[str, Any]) -> dict[str, Any] | None:
    envelope = bundle.get("dsseEnvelope") or {}
    payload = envelope.get("payload")
    if not isinstance(payload, str):
        return None
    try:
        decoded = json.loads(base64.b64decode(payload))
    except ValueError, json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _locate(name: str, present: set[str], subjects: list[str]) -> str | None:
    """The present file a signed resource name refers to, or None.

    A resource name is relative to the signed subject. When the subject is the repository root the
    two coincide; when it is a directory inside the repository (`openai/privacy-filter` signs
    `original/`), the file the bundle covers is `<subject>/<name>`, and a comparison that ignored
    the subject would report every signed file absent and every present file unsigned.
    """
    if name in present:
        return name
    for subject in subjects:
        if f"{subject}/{name}" in present:
            return f"{subject}/{name}"
    return None


def _identity_match(namespace: str, sans: list[str]) -> tuple[str, str | None]:
    emails = [s for s in sans if "@" in s]
    if not emails:
        return "undeterminable", None
    domain = emails[0].rsplit("@", 1)[1].lower()
    label = domain.split(".")[-2] if domain.count(".") >= 1 else domain
    tokens = [t for t in re.split(r"[-_.]", namespace.lower()) if t]
    return ("matches" if label in tokens else "does-not-match"), domain


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="capture a fresh recording")
    parser.add_argument("--json", dest="as_json", type=Path, default=None)
    args = parser.parse_args()

    dataset = json.loads(DATASET.read_text())
    signed: list[dict[str, Any]] = dataset["signed"]
    verification: dict[str, Any] = (
        json.loads(VERIFICATION.read_text()) if VERIFICATION.exists() else {}
    )

    registry: Registry
    recorder: _Recording | None = None
    if args.live:
        recorder = _Recording(LiveRegistry())
        registry = recorder
    else:
        registry = RecordedRegistry(RECORDED)

    rows: list[dict[str, Any]] = []
    payload_owners: dict[str, list[str]] = {}
    namespaces: dict[str, dict[str, Any]] = {}
    for entry in signed:
        slug = str(entry["id"])
        listing = registry.get(f"/api/models/{slug}")
        body = listing.body if isinstance(listing.body, dict) else {}
        revision = str(body["sha"]) if body.get("sha") else None
        ref = _ref(slug, revision)
        siblings = sorted(
            str(s["rfilename"]) for s in body.get("siblings") or [] if isinstance(s, dict)
        )
        state, note = detect(registry, ref)
        bundle = _bundle(registry, ref)
        namespace = ref.namespace
        if namespace not in namespaces:
            overview = registry.get(f"/api/organizations/{namespace}/overview")
            if overview.status == 404:
                overview = registry.get(f"/api/users/{namespace}/overview")
            namespaces[namespace] = {
                "status": overview.status,
                **(
                    {k: v for k, v in overview.body.items()}
                    if isinstance(overview.body, dict)
                    else {}
                ),
            }

        row: dict[str, Any] = {
            "model": slug,
            "revision": revision,
            "listing_status": listing.status,
            "signature_state": state.value,
            "detection_note": note.split(":")[0],
            "files": len(siblings),
        }
        if bundle is not None:
            material = bundle.get("verificationMaterial") or {}
            tlog = material.get("tlogEntries") or []
            statement = _statement(bundle)
            payload_digest = hashlib.sha256(
                str((bundle.get("dsseEnvelope") or {}).get("payload", "")).encode()
            ).hexdigest()
            payload_owners.setdefault(payload_digest, []).append(slug)
            row.update(
                {
                    "media_type": bundle.get("mediaType"),
                    "verification_material": sorted(
                        k
                        for k in ("certificate", "x509CertificateChain", "publicKey")
                        if k in material
                    ),
                    "tlog_entries": len(tlog),
                    "log_index": (tlog[0].get("logIndex") if tlog else None),
                    "payload_sha256": payload_digest,
                }
            )
            if statement is not None:
                resources = (statement.get("predicate") or {}).get("resources") or []
                signed_names = sorted(
                    str(r["name"]) for r in resources if isinstance(r, dict) and "name" in r
                )
                # `model.sig` cannot sign itself, and `model_signing` skips git paths by default
                # (`--ignore-git-paths`), so neither counts as a file the bundle left out.
                present = set(siblings) - {"model.sig", ".gitattributes", ".gitignore"}
                subjects = [str(s.get("name")) for s in statement.get("subject") or []]

                located = {name: _locate(name, present, subjects) for name in signed_names}
                covered = {path for path in located.values() if path is not None}
                row.update(
                    {
                        "predicate_type": statement.get("predicateType"),
                        "subject_names": subjects,
                        "signed_files": len(signed_names),
                        "signed_and_present": len(covered),
                        "signed_but_absent": sorted(n for n, p in located.items() if p is None),
                        "present_but_unsigned": sorted(present - covered),
                    }
                )
        verified = verification.get(slug) or {}
        sans = [str(s) for s in verified.get("san") or []]
        match, domain = _identity_match(namespace, sans if verified.get("verifies") else [])
        row.update(
            {
                "verifies": verified.get("verifies"),
                "verification_error": verified.get("error"),
                "signer": sans,
                "issuer": verified.get("issuer"),
                "signer_domain": domain,
                "identity": match,
            }
        )
        rows.append(row)

    if recorder is not None:
        recorder.write(RECORDED)
        print(f"captured {len(recorder.order)} interactions into {RECORDED}")

    for row in rows:
        owners = payload_owners.get(str(row.get("payload_sha256")), [])
        row["bundle_shared_with"] = sorted(o for o in owners if o != row["model"])

    def _count(key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = row.get(key)
            label = json.dumps(value) if isinstance(value, list) else str(value)
            counts[label] = counts.get(label, 0) + 1
        return dict(sorted(counts.items()))

    summary: dict[str, Any] = {
        "swept": dataset["swept"],
        "swept_models": dataset["n_models"],
        "signed_models": len(rows),
        "detection": _count("signature_state"),
        "verifies": _count("verifies"),
        "verification_material": _count("verification_material"),
        "identity": _count("identity"),
        "signer_domain": _count("signer_domain"),
        "namespaces": {
            ns: {"models": sum(1 for r in rows if r["model"].startswith(ns + "/")), **info}
            for ns, info in sorted(namespaces.items())
        },
        "bundles_shared_across_models": sum(1 for r in rows if r["bundle_shared_with"]),
        "models_with_unsigned_present_files": sum(1 for r in rows if r.get("present_but_unsigned")),
        "models_with_signed_absent_files": sum(1 for r in rows if r.get("signed_but_absent")),
        "rows": rows,
    }
    if args.as_json:
        args.as_json.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"\n{len(rows)} signed models of {dataset['n_models']} swept ({dataset['swept']})")
    for key in ("detection", "verifies", "verification_material", "identity", "signer_domain"):
        print(f"{key:<22} " + "  ".join(f"{k}={v}" for k, v in summary[key].items()))
    print(
        f"bundles shared across models: {summary['bundles_shared_across_models']}; "
        f"models with present-but-unsigned files: {summary['models_with_unsigned_present_files']}; "
        f"with signed-but-absent files: {summary['models_with_signed_absent_files']}"
    )
    for row in rows:
        if row["identity"] == "does-not-match" or row["bundle_shared_with"]:
            print(
                f"  {row['model']}: identity={row['identity']} signer={row['signer_domain']} "
                f"shared_with={row['bundle_shared_with']} unsigned_present={len(row.get('present_but_unsigned') or [])}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
