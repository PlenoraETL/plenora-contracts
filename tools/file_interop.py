"""File Interchange 1.0: verify resolved bytes before consumer invocation."""

import hashlib


def evaluate(document):
    """Evaluate a structurally validated vector without opening its reference.

    The suite supplies the bytes returned by its authorized resolver. Reference
    strings are never filesystem instructions to the repository validator.
    """
    file = document["file"]
    consumer = document["consumer"]
    resolved = document["resolved"]
    payload = bytes.fromhex(resolved["bytes_hex"])
    cause = None
    if file["format_family"] not in consumer["format_families"]:
        cause = "undeclared_format_family"
    elif (file["content_type"] not in consumer["content_types"]
          or file["content_type"] != resolved["content_type"]):
        cause = "content_type_mismatch"
    elif len(payload) < file["size_bytes"]:
        cause = "truncated_payload"
    elif len(payload) > file["size_bytes"]:
        cause = "size_mismatch"
    elif hashlib.sha256(payload).hexdigest() != file["sha256"]:
        cause = "digest_mismatch"
    if cause is None:
        return {"outcome": "accepted"}
    return {
        "outcome": "error", "cause": cause, "category": "schema",
        "phase": "validate", "remote_effect": "none", "retry": "never",
        "message": "File handoff rejected.",
    }


def composition_errors(document, operations):
    """Check envelope identities separately from declared artifact forms."""
    errors = []
    for edge in document["edges"]:
        for side, direction in (("from", "output"), ("to", "input")):
            declaration = edge[side]
            endpoint = declaration["operation"]
            key = tuple(endpoint[k] for k in ("component", "operation", "version"))
            operation = operations.get(key)
            if operation is None:
                errors.append("FILE-006: unknown operation.")
            elif (declaration["envelope_contract"] != operation[direction]["contract"]
                  or edge["surface"] not in operation["surfaces"]):
                errors.append("FILE-006: incompatible envelope or surface.")
    return errors


def vector_errors(document, edges):
    """Cross-check the descriptor, declared edge and computed expectation."""
    edge = document["edge"]
    file = document["file"]
    errors = []
    if edge not in edges:
        errors.append("FILE-006: undeclared file edge.")
    if (file["producer"] != edge["from"]["operation"]
            or file["reference"]["surface"] != edge["surface"]
            or file["format_family"] != edge["format_family"]
            or file["content_type"] != edge["content_type"]):
        errors.append("FILE-006: descriptor differs from the file edge.")
    if evaluate(document) != document["expect"]:
        errors.append("FILE-007: unexpected file handoff outcome.")
    return errors
