import os
from pathlib import Path
from typing import Any, Final

from fastapi import FastAPI, HTTPException

from ingestion_pipeline.clients.llamastack import (
    LlamaStackVectorStoreClient,
    VectorStoreFileContentSummary,
    VectorStoreFileSummary,
    VectorStoreSummary,
)
from ingestion_pipeline.clients.minio import MinioDocumentClient

LLAMASTACK_HOST = os.environ.get("LLAMASTACK_HOST", "llamastack")
LLAMASTACK_PORT = int(os.environ.get("LLAMASTACK_PORT", "8321"))
VECTOR_STORE_NAME: Final[str] = os.environ.get("VECTOR_STORE_NAME", "")
RUNBOOKS_DIR: Final[Path] = Path(os.environ.get("RUNBOOKS_DIR", "/app/runbooks"))
MINIO_ENDPOINT: Final[str] = os.environ.get("MINIO_ENDPOINT", "")
MINIO_ACCESS_KEY: Final[str] = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY: Final[str] = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_BUCKET: Final[str] = os.environ.get("MINIO_BUCKET", "")
MINIO_SECURE: Final[bool] = os.environ.get("MINIO_SECURE", "false").lower() == "true"
MINIO_RUNBOOK_PREFIX: Final[str] = os.environ.get("MINIO_RUNBOOK_PREFIX", "runbooks/")

app = FastAPI(
    title="Ingestion Pipeline",
    description="Syncs packaged runbooks to MinIO and ingests them into a Llama Stack vector store",
    version="0.1.0",
)


def _get_client() -> LlamaStackVectorStoreClient:
    return LlamaStackVectorStoreClient(
        base_url=f"http://{LLAMASTACK_HOST}:{LLAMASTACK_PORT}",
        vector_store_name=VECTOR_STORE_NAME,
    )


def _get_minio_client() -> MinioDocumentClient:
    if not MINIO_ENDPOINT or not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY or not MINIO_BUCKET:
        raise HTTPException(status_code=400, detail="MinIO is not fully configured")
    return MinioDocumentClient(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        bucket=MINIO_BUCKET,
        secure=MINIO_SECURE,
    )


def _runbook_object_name(filename: str) -> str:
    prefix = MINIO_RUNBOOK_PREFIX.strip("/")
    if not prefix:
        return filename
    return f"{prefix}/{filename}"


def _sync_packaged_runbooks_to_minio(minio_client: MinioDocumentClient) -> dict[str, Any]:
    minio_client.ensure_bucket()
    uploaded: list[str] = []
    skipped: list[str] = []
    if RUNBOOKS_DIR.exists():
        for runbook_path in sorted(RUNBOOKS_DIR.glob("*.md")):
            object_name = _runbook_object_name(runbook_path.name)
            was_uploaded = minio_client.put_text_object_if_missing(
                object_name,
                runbook_path.read_text(encoding="utf-8"),
            )
            if was_uploaded:
                uploaded.append(object_name)
            else:
                skipped.append(object_name)

    return {
        "bucket": MINIO_BUCKET,
        "prefix": MINIO_RUNBOOK_PREFIX,
        "uploaded_count": len(uploaded),
        "skipped_count": len(skipped),
        "uploaded_objects": uploaded,
        "skipped_objects": skipped,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
def models() -> dict[str, Any]:
    client = _get_client()
    return {"models": client.list_models()}


@app.get("/vector-store")
def vector_store() -> dict[str, Any]:
    client = _get_client()
    summary: VectorStoreSummary = client.ensure_vector_store()
    return {
        "id": summary.id,
        "name": summary.name,
        "status": summary.status,
        "file_counts": summary.file_counts,
    }


@app.post("/runbooks/sync")
def sync_runbooks() -> dict[str, Any]:
    minio_client = _get_minio_client()
    return _sync_packaged_runbooks_to_minio(minio_client)


@app.post("/runbooks/ingest")
def ingest_runbooks() -> dict[str, Any]:
    minio_client = _get_minio_client()
    vector_client = _get_client()
    objects = minio_client.load_prefix_text_objects(MINIO_RUNBOOK_PREFIX)
    ingested = []

    for obj in objects:
        summary: VectorStoreFileSummary = vector_client.ingest_text(
            filename=Path(obj.object_name).name,
            content=obj.content,
            attributes={"source_type": "runbook", "source_name": obj.object_name},
        )
        ingested.append(
            {
                "id": summary.id,
                "vector_store_id": summary.vector_store_id,
                "status": summary.status,
                "attributes": summary.attributes,
            }
        )

    return {
        "bucket": MINIO_BUCKET,
        "prefix": MINIO_RUNBOOK_PREFIX,
        "ingested_count": len(ingested),
        "objects": ingested,
    }


@app.get("/vector-store/files/{file_id}/content")
def vector_store_file_content(file_id: str) -> dict[str, Any]:
    client = _get_client()
    summary: VectorStoreFileContentSummary = client.get_file_content(file_id=file_id)
    return {
        "id": summary.id,
        "vector_store_id": summary.vector_store_id,
        "status": summary.status,
        "data": [
            {
                "text": item.text,
                "metadata": item.metadata,
                "embedding": item.embedding,
            }
            for item in summary.data
        ],
    }


