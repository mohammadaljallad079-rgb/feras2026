"""Public website CMS: settings, sections, slides, services, navigation.

The public site reads its copy from these tables, so an edit made in the admin
console has to reach ``/api/v1/public/site`` unchanged, and a role without
``site:manage`` must not be able to write any of them.
"""

from __future__ import annotations

from app.content import site_content as content
from app.models.site import SiteNavLink, SiteSection, SiteService, SiteSetting, SiteSlide


def _seed(db) -> None:
    """Populate the CMS the same way scripts/seed_site.py does."""
    for key, (ar, en) in content.SETTINGS.items():
        db.add(SiteSetting(key=key, value_ar=ar, value_en=en))
    for i, spec in enumerate(content.SLIDES):
        db.add(SiteSlide(sort_order=i, **spec))
    for spec in content.SECTIONS:
        db.add(SiteSection(**spec))
    for i, (slug, ar, en) in enumerate(content.SERVICES):
        db.add(SiteService(slug=slug, name_ar=ar, name_en=en, sort_order=i))
    for location, links in (("header", content.HEADER_NAV), ("footer", content.FOOTER_NAV)):
        for i, (ar, en, href) in enumerate(links):
            db.add(SiteNavLink(location=location, label_ar=ar, label_en=en, href=href, sort_order=i))
    db.commit()


def test_public_site_serves_seeded_content(client, db):
    _seed(db)
    body = client.get("/api/v1/public/site").json()
    assert body["settings"]["brand_name"]["ar"] == content.SETTINGS["brand_name"][0]
    assert len(body["sections"]) == len(content.SECTIONS)
    assert len(body["slides"]) == len(content.SLIDES)
    assert len(body["services"]) == len(content.SERVICES)
    assert len(body["header_nav"]) == len(content.HEADER_NAV)
    assert body["opportunity_countries"], "the opportunity form needs its country list"


def test_public_site_lists_only_published_companies(client, make_user, login, db):
    _seed(db)
    make_user("cms_owner@safir-platform.com", ["owner"])
    h = login("cms_owner@safir-platform.com")
    cid = client.post(
        "/api/v1/companies",
        headers=h,
        json={
            "code": "CMS-1",
            "name_ar": "شركة",
            "name_en": "Company",
            "sector": "services",
            "country": "BH",
            "ownership_percent": "60",
            "currency": "BHD",
        },
    ).json()["id"]

    # A company is not public until it is both activated and published.
    assert client.get("/api/v1/public/companies").json() == []

    activated = client.post(f"/api/v1/companies/{cid}/activate", headers=h)
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"
    # Activation alone is not enough; publishing is a separate decision.
    assert client.get("/api/v1/public/companies").json() == []

    client.patch(f"/api/v1/website/companies/{cid}/visibility", headers=h, json={"public_visible": True})
    listed = client.get("/api/v1/public/companies").json()
    assert [c["code"] for c in listed] == ["CMS-1"]

    # Unpublishing removes it again.
    client.patch(f"/api/v1/website/companies/{cid}/visibility", headers=h, json={"public_visible": False})
    assert client.get("/api/v1/public/companies").json() == []


def test_setting_edit_reaches_the_public_endpoint(client, make_user, login, db):
    _seed(db)
    make_user("cms_owner2@safir-platform.com", ["owner"])
    h = login("cms_owner2@safir-platform.com")

    listed = client.get("/api/v1/website/settings", headers=h)
    assert listed.status_code == 200, listed.text
    assert {s["key"] for s in listed.json()} >= {"brand_name", "seo_title"}

    patched = client.patch(
        "/api/v1/website/settings/brand_short",
        headers=h,
        json={"value_ar": "قابضة", "value_en": "Holding"},
    )
    assert patched.status_code == 200, patched.text
    assert client.get("/api/v1/public/site").json()["settings"]["brand_short"] == {
        "ar": "قابضة",
        "en": "Holding",
    }


def test_section_and_slide_and_service_and_nav_edits_persist(client, make_user, login, db):
    _seed(db)
    make_user("cms_owner3@safir-platform.com", ["owner"])
    h = login("cms_owner3@safir-platform.com")

    section = client.get("/api/v1/website/sections", headers=h).json()[0]
    r = client.patch(
        f"/api/v1/website/sections/{section['id']}",
        headers=h,
        json={"title_ar": "عنوان جديد", "is_visible": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["title_ar"] == "عنوان جديد"
    assert r.json()["is_visible"] is False

    slide = client.get("/api/v1/website/slides", headers=h).json()[0]
    r = client.patch(f"/api/v1/website/slides/{slide['id']}", headers=h, json={"title_en": "New hero"})
    assert r.status_code == 200, r.text
    assert r.json()["title_en"] == "New hero"

    service = client.get("/api/v1/website/services", headers=h).json()[0]
    r = client.patch(f"/api/v1/website/services/{service['id']}", headers=h, json={"needs_review": True})
    assert r.status_code == 200, r.text
    assert r.json()["needs_review"] is True

    nav = client.get("/api/v1/website/nav", headers=h).json()[0]
    r = client.patch(f"/api/v1/website/nav/{nav['id']}", headers=h, json={"label_en": "New label"})
    assert r.status_code == 200, r.text
    assert r.json()["label_en"] == "New label"


def test_hidden_section_is_not_published(client, make_user, login, db):
    _seed(db)
    make_user("cms_owner4@safir-platform.com", ["owner"])
    h = login("cms_owner4@safir-platform.com")

    section = client.get("/api/v1/website/sections", headers=h).json()[0]
    client.patch(f"/api/v1/website/sections/{section['id']}", headers=h, json={"is_visible": False})
    keys = {s["key"] for s in client.get("/api/v1/public/site").json()["sections"]}
    assert section["key"] not in keys


def test_site_management_requires_the_permission(client, make_user, login, db):
    _seed(db)
    make_user("cms_marketer@safir-platform.com", ["marketer"])
    h = login("cms_marketer@safir-platform.com")

    for path in ("/api/v1/website/settings", "/api/v1/website/sections", "/api/v1/website/nav"):
        assert client.get(path, headers=h).status_code == 403, path

    assert (
        client.patch(
            "/api/v1/website/settings/brand_short", headers=h, json={"value_en": "nope"}
        ).status_code
        == 403
    )
    # Anonymous callers never reach the CMS either.
    assert client.get("/api/v1/website/settings").status_code == 401


def test_cms_writes_are_audited(client, make_user, login, db):
    _seed(db)
    make_user("cms_owner5@safir-platform.com", ["owner"])
    h = login("cms_owner5@safir-platform.com")

    client.patch("/api/v1/website/settings/brand_short", headers=h, json={"value_en": "Audited"})
    actions = {e["action"] for e in client.get("/api/v1/audit", headers=h).json()}
    assert any(a.startswith("site.") for a in actions), actions


def test_published_company_logo_is_served_publicly_but_only_when_published(client, make_user, login, db):
    """§9: the portfolio card and the preview modal carry the company logo.

    The API pointed ``logo_url`` at the authenticated file endpoint, which the
    public site cannot call. A published company's logo must be reachable
    anonymously, and a company that is not published must not expose one.
    """
    _seed(db)
    make_user("logo_owner@safir-platform.com", ["owner"])
    h = login("logo_owner@safir-platform.com")
    cid = client.post(
        "/api/v1/companies",
        headers=h,
        json={
            "code": "PUB-LOGO",
            "name_ar": "شركة",
            "name_en": "Public Logo Co",
            "sector": "services",
            "country": "BH",
            "ownership_percent": "60",
            "currency": "BHD",
        },
    ).json()["id"]

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    file_id = client.post(
        "/api/v1/files",
        headers=h,
        files={"file": ("logo.png", png, "image/png")},
        data={"company_id": str(cid)},
    ).json()["id"]
    client.patch(f"/api/v1/companies/{cid}", headers=h, json={"logo_file_id": file_id})
    client.post(f"/api/v1/companies/{cid}/activate", headers=h)

    # Unpublished: the company is not listed and its logo is not reachable.
    assert client.get("/api/v1/public/companies").json() == []
    assert client.get("/api/v1/public/companies/PUB-LOGO/logo").status_code == 404

    client.patch(f"/api/v1/website/companies/{cid}/visibility", headers=h, json={"public_visible": True})
    listed = client.get("/api/v1/public/companies").json()
    assert [c["code"] for c in listed] == ["PUB-LOGO"]
    assert listed[0]["logo_url"] == "/api/v1/public/companies/PUB-LOGO/logo"

    # Anonymous download returns the image. No Content-Disposition filename is
    # sent, so a browser renders it inline rather than downloading it.
    logo = client.get("/api/v1/public/companies/PUB-LOGO/logo")
    assert logo.status_code == 200, logo.text
    assert logo.headers["content-type"].startswith("image/")
    assert "attachment" not in logo.headers.get("content-disposition", "")
    assert logo.content == png

    # Unpublishing withdraws the logo again.
    client.patch(f"/api/v1/website/companies/{cid}/visibility", headers=h, json={"public_visible": False})
    assert client.get("/api/v1/public/companies/PUB-LOGO/logo").status_code == 404

