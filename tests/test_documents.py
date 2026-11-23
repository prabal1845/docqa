from tests.helpers import auth_headers, make_pdf, upload


def test_upload_is_ingested_into_chunks(client):
    headers = auth_headers(client)
    doc = upload(client, headers, "handbook.pdf", ["Page one text " * 50, "Page two text " * 50])
    assert doc["filename"] == "handbook.pdf"

    # Inline mode runs the background task before the test client returns
    resp = client.get(f"/documents/{doc['id']}", headers=headers)
    body = resp.json()
    assert body["status"] == "ready", body
    assert body["page_count"] == 2
    assert body["chunk_count"] >= 2


def test_non_pdf_is_rejected(client):
    headers = auth_headers(client)
    resp = client.post(
        "/documents",
        headers=headers,
        files={"file": ("notes.pdf", b"just some text pretending", "application/pdf")},
    )
    assert resp.status_code == 415


def test_pdf_without_text_is_marked_failed(client):
    headers = auth_headers(client)
    doc = upload(client, headers, "scan.pdf", [""])
    body = client.get(f"/documents/{doc['id']}", headers=headers).json()
    assert body["status"] == "failed"
    assert "No extractable text" in body["error"]


def test_documents_are_private_to_their_owner(client):
    alice = auth_headers(client, "alice@example.com")
    bob = auth_headers(client, "bob@example.com")
    doc = upload(client, alice, "secret.pdf", ["Alice's private notes"])

    assert client.get(f"/documents/{doc['id']}", headers=bob).status_code == 404
    assert client.delete(f"/documents/{doc['id']}", headers=bob).status_code == 404
    assert client.get("/documents", headers=bob).json() == []
    assert len(client.get("/documents", headers=alice).json()) == 1


def test_delete_document(client):
    headers = auth_headers(client)
    doc = upload(client, headers, "temp.pdf", ["Temporary content"])
    assert client.delete(f"/documents/{doc['id']}", headers=headers).status_code == 204
    assert client.get(f"/documents/{doc['id']}", headers=headers).status_code == 404


def test_upload_requires_auth(client):
    resp = client.post("/documents", files={"file": ("a.pdf", make_pdf(["hi"]), "application/pdf")})
    assert resp.status_code == 401
