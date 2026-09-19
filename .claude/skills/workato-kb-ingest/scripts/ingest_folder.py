#!/usr/bin/env python3
"""ingest_folder.py — checkpointed, resumable, thread-pooled bulk upload of a
local folder of files into a Workato Knowledge Base via the ingest recipe
that init_kb_ingest.py provisions.

Read references/gotchas.md before running this at any real scale — in
particular, `enterprise_context.upsert_documents` auto-detects each
document's content type from its raw body when `content_type` is left
blank, and that auto-detection has real false positives on plain text (a
verified example: a document's text starting with "P1" gets misread as a
NetPBM image and rejected outright). This script always sets `content_type`
explicitly per file (via CONTENT_TYPE_BY_EXTENSION below) specifically to
avoid that — do not remove it "to simplify" without re-reading why it's there.

Usage:
    DEV_API_TOKEN=wrkaus-... WORKATO_DC=us python3 ingest_folder.py \\
        --manifest kb_manifest.json \\
        --folder /path/to/local/files \\
        --kb-name docs \\
        --checkpoint ingest_progress.jsonl \\
        --parallelism 5

If kb_manifest.json has more than one Knowledge Base, run this once per KB
with the matching --kb-name and --folder (point each KB at its own
subfolder), reusing the same --checkpoint file across runs is fine — it's
keyed by absolute file path, so runs against different folders never collide.
"""
import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from workato_client import WorkatoClient, resolve_effective_dc  # noqa: E402

BATCH_SIZE = 100  # the ingest recipe's declared limit: "Up to 100 documents per run"
_checkpoint_lock = threading.Lock()

# Extension -> explicit content_type, so upsert_documents never has to guess.
# This list matches the connector's own "Supported types" error enumeration
# (verified live) minus the binary formats (pdf/docx/xlsx/pptx/odt/epub) —
# this script only reads files as UTF-8 text, so it only maps text-native
# extensions. If your folder has binary office/PDF files, this script isn't
# the right tool as-is: you'd need to read+encode them per the connector's
# expectations for those types, which this reference build never exercised
# live and so does not attempt to guess at.
CONTENT_TYPE_BY_EXTENSION = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".rst": "text/x-rst",
    ".adoc": "text/asciidoc",
    ".asciidoc": "text/asciidoc",
    ".rtf": "text/rtf",
}
DEFAULT_CONTENT_TYPE = "text/plain"  # fallback for unrecognized text-like extensions


def list_folder_files(folder: str) -> list[str]:
    return [str(p) for p in sorted(Path(folder).rglob("*"))
            if p.is_file() and p.suffix.lower() in CONTENT_TYPE_BY_EXTENSION]


def load_checkpoint(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    done = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("status") == "done":
                done.add(row["path"])
    return done


def append_checkpoint(path: str, file_path: str, status: str) -> None:
    # Multiple worker threads append concurrently under --parallelism; the
    # lock keeps each JSONL line atomic so writes never interleave mid-line.
    line = json.dumps({"path": file_path, "status": status}) + "\n"
    with _checkpoint_lock:
        with open(path, "a") as f:
            f.write(line)


def document_id_for(file_path: str, folder_root: str) -> str:
    """Derive a stable document_id from the file's path relative to the
    ingest root, so re-running this script against an edited file UPDATES
    the same Knowledge Base document (upsert_documents matches by
    document_id) instead of creating a duplicate under a new ID."""
    rel = os.path.relpath(file_path, folder_root)
    return rel.replace(os.sep, "__")


def read_document(file_path: str, folder_root: str) -> dict:
    content_type = CONTENT_TYPE_BY_EXTENSION.get(
        Path(file_path).suffix.lower(), DEFAULT_CONTENT_TYPE)
    with open(file_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    return {
        "document_id": document_id_for(file_path, folder_root),
        "title": Path(file_path).stem,
        "content": content,
        "content_type": content_type,
    }


def batches(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def upload_batch(client: WorkatoClient, ingest_endpoint_url: str, ingest_api_token: str,
                   kb_id: str, documents: list[dict]) -> dict:
    """POST one batch (<=100 documents) to the ingest recipe's API endpoint.

    Returns {"total_count": int, "failed_documents": [{"document_id", "title"}, ...]}.
    Auth is a static `api-token` header (Auth Token access profile) — NOT
    `Authorization: Bearer`, which is what `auth_type: "token"` access
    profiles actually require (verified live against Workato's own docs
    after an initial 401 assuming Bearer auth).
    """
    status, body = client.call("POST", "", {
        "knowledge_base_id": kb_id, "documents": documents,
    }, base=ingest_endpoint_url, extra_headers={"api-token": ingest_api_token})
    return client.must(status, body, f"ingest batch of {len(documents)} documents into KB {kb_id}")


def _process_batch(client: WorkatoClient, ingest_endpoint_url: str, ingest_api_token: str,
                     checkpoint_path: str, kb_id: str, folder_root: str,
                     file_batch: list[str], max_retries: int) -> dict:
    """Upload one batch with retry, checkpointing each file done/failed. Safe
    to call from multiple worker threads concurrently — the only shared
    mutable state is the checkpoint file, guarded by `_checkpoint_lock`."""
    documents = [read_document(fp, folder_root) for fp in file_batch]
    doc_id_to_path = {doc["document_id"]: fp for doc, fp in zip(documents, file_batch)}
    counts = {"succeeded": 0, "failed": 0}

    attempt = 0
    while True:
        try:
            result = upload_batch(client, ingest_endpoint_url, ingest_api_token, kb_id, documents)
            failed_ids = {fd["document_id"] for fd in result.get("failed_documents", [])}
            for doc_id, fp in doc_id_to_path.items():
                if doc_id in failed_ids:
                    append_checkpoint(checkpoint_path, fp, "failed")
                    counts["failed"] += 1
                else:
                    append_checkpoint(checkpoint_path, fp, "done")
                    counts["succeeded"] += 1
            return counts
        except RuntimeError as e:
            attempt += 1
            if attempt >= max_retries:
                for fp in doc_id_to_path.values():
                    append_checkpoint(checkpoint_path, fp, "failed")
                    counts["failed"] += 1
                print(f"    ✗ batch permanently failed ({len(file_batch)} files): {e}",
                      file=sys.stderr)
                return counts
            time.sleep(1.0 * attempt)


def ingest_all(client: WorkatoClient, folder: str, kb_id: str, checkpoint_path: str,
                ingest_endpoint_url: str, ingest_api_token: str,
                max_retries: int = 3, batch_size: int = BATCH_SIZE, parallelism: int = 1) -> dict:
    already_done = load_checkpoint(checkpoint_path)
    counts = {"succeeded": 0, "failed": 0, "skipped": 0}

    all_files = list_folder_files(folder)
    pending_files = [fp for fp in all_files if fp not in already_done]
    counts["skipped"] = len(all_files) - len(pending_files)
    all_batches = list(batches(pending_files, batch_size))

    if parallelism <= 1:
        for file_batch in all_batches:
            result = _process_batch(client, ingest_endpoint_url, ingest_api_token,
                                       checkpoint_path, kb_id, folder, file_batch, max_retries)
            counts["succeeded"] += result["succeeded"]
            counts["failed"] += result["failed"]
        return counts

    # WorkatoClient.call uses a fresh requests.request(...) per call (no
    # shared session), so concurrent calls across threads are safe without
    # additional client-side locking beyond the checkpoint-file lock above.
    with ThreadPoolExecutor(max_workers=parallelism) as pool:
        futures = [
            pool.submit(_process_batch, client, ingest_endpoint_url, ingest_api_token,
                         checkpoint_path, kb_id, folder, file_batch, max_retries)
            for file_batch in all_batches
        ]
        for future in as_completed(futures):
            result = future.result()
            counts["succeeded"] += result["succeeded"]
            counts["failed"] += result["failed"]
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="kb_manifest.json")
    parser.add_argument("--folder", required=True, help="local folder to ingest, recursively")
    parser.add_argument("--kb-name", required=True,
                         help="which Knowledge Base (by name, as passed to init_kb_ingest.py's "
                              "--kb-names) to upsert into")
    parser.add_argument("--checkpoint", default="ingest_progress.jsonl")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--parallelism", type=int, default=1,
                         help="number of batches to upload concurrently (default: 1, sequential)")
    args = parser.parse_args()

    token = os.environ.get("DEV_API_TOKEN")
    if not token:
        sys.exit("error: DEV_API_TOKEN env var is required")

    with open(args.manifest) as f:
        manifest = json.load(f)
    kb_id = manifest["knowledge_bases"].get(args.kb_name)
    if not kb_id:
        sys.exit(f"error: KB {args.kb_name!r} not found in {args.manifest} "
                  f"(available: {list(manifest['knowledge_bases'])})")

    dc = resolve_effective_dc(manifest)
    client = WorkatoClient(token=token, dc=dc)

    print(f"Ingesting {args.folder!r} into KB {args.kb_name!r} ({kb_id}) "
          f"(batches of {args.batch_size}, parallelism={args.parallelism})")
    print(f"Checkpoint file: {args.checkpoint}")

    result = ingest_all(client, args.folder, kb_id, args.checkpoint,
                        manifest["ingest_endpoint_url"], manifest["ingest_api_token"],
                        batch_size=args.batch_size, parallelism=args.parallelism)
    print(f"\nDone: {result['succeeded']} succeeded, {result['failed']} failed, "
          f"{result['skipped']} skipped (already done)")
    if result["failed"]:
        print(f"\n{result['failed']} file(s) failed — see references/gotchas.md's content_type "
              f"section before assuming it's a data problem; re-run the same command to retry "
              f"(only failed/pending files are re-attempted).")


if __name__ == "__main__":
    main()
