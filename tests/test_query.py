from app.config import get_settings
from app.db import SessionLocal
from app.models import Document, DocumentStatus
from app.services.rag import NO_CONTEXT_ANSWER, STILL_PROCESSING_ANSWER
from tests.helpers import auth_headers, upload

REFUND_TEXT = (
    "Refund policy: customers may request a full refund within 30 days of delivery. "
    "Refunds are issued to the original payment method within 5 business days."
)
SHIPPING_TEXT = (
    "Shipping information: furniture orders ship from regional warehouses. "
    "Large items are delivered by a two-person team that schedules a delivery window."
)


def test_answer_cites_the_relevant_page(client):
    headers = auth_headers(client)
    upload(client, headers, "policies.pdf", [SHIPPING_TEXT, REFUND_TEXT])

    resp = client.post(
        "/query", headers=headers, json={"question": "How many days do I have to get a refund?"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]
    top = body["citations"][0]
    assert top["filename"] == "policies.pdf"
    assert top["page"] == 2
    assert "30 days" in top["snippet"]
    assert top["cited"] is True


def test_query_can_be_scoped_to_documents(client):
    headers = auth_headers(client)
    refunds = upload(client, headers, "refunds.pdf", [REFUND_TEXT])
    shipping = upload(client, headers, "shipping.pdf", [SHIPPING_TEXT])

    resp = client.post(
        "/query",
        headers=headers,
        json={"question": "What is the refund policy?", "document_ids": [shipping["id"]]},
    )
    doc_ids = {c["document_id"] for c in resp.json()["citations"]}
    assert doc_ids == {shipping["id"]}
    assert refunds["id"] not in doc_ids


def test_no_documents_returns_fallback_without_citations(client):
    headers = auth_headers(client)
    resp = client.post("/query", headers=headers, json={"question": "Anything at all?"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": NO_CONTEXT_ANSWER, "citations": []}


def test_other_users_documents_are_never_retrieved(client):
    alice = auth_headers(client, "alice@example.com")
    bob = auth_headers(client, "bob@example.com")
    upload(client, alice, "refunds.pdf", [REFUND_TEXT])

    resp = client.post("/query", headers=bob, json={"question": "What is the refund policy?"})
    assert resp.json()["citations"] == []


def test_daily_quota_is_enforced(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "daily_query_limit", 2)
    headers = auth_headers(client)
    ask = {"question": "hello?"}
    for _ in range(2):
        assert client.post("/query", headers=headers, json=ask).status_code == 200
    assert client.post("/query", headers=headers, json=ask).status_code == 429


def test_history_is_paginated_newest_first(client):
    headers = auth_headers(client)
    for q in ["first question", "second question", "third question"]:
        client.post("/query", headers=headers, json={"question": q})

    page = client.get("/queries?limit=2", headers=headers).json()
    assert [h["question"] for h in page] == ["third question", "second question"]
    rest = client.get("/queries?limit=2&offset=2", headers=headers).json()
    assert [h["question"] for h in rest] == ["first question"]


def test_query_while_documents_are_processing_says_so(client):
    headers = auth_headers(client)
    user_id = client.get("/auth/me", headers=headers).json()["id"]

    async def add_pending_document():
        async with SessionLocal() as db:
            db.add(Document(owner_id=user_id, filename="big.pdf", status=DocumentStatus.PENDING))
            await db.commit()

    client.portal.call(add_pending_document)
    resp = client.post("/query", headers=headers, json={"question": "What is in big.pdf?"})
    assert resp.json() == {"answer": STILL_PROCESSING_ANSWER, "citations": []}
