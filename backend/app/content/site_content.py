"""Canonical seed content for the public website.

Only copy that the brief states is present here verbatim. Anything the missing
`content-ar.md` / `content-en.md` files would have supplied is left null and
flagged `needs_review`, so the CMS shows the owner exactly what to approve
before launch. No number, statistic, company, service description or claim is
invented here.
"""

from __future__ import annotations

BRAND_AR = "شركة ستارت أب سفير القابضة ذ.م.م"
BRAND_EN = "START UP SPHERE HOLDING CO W.L.L"
BRAND_SHORT_AR = "ستارت أب سفير القابضة"
BRAND_SHORT_EN = "Start Up Sphere Holding"

CONTACT = {
    "country_ar": "مملكة البحرين",
    "country_en": "Kingdom of Bahrain",
    "email": "info@sup-edu.com",
    "phone": "+973 17626990",
}

# The holding's own commercial registration, stated in the brief's header. It is
# the data controller identifier the privacy policy must carry.
CR_NUMBER = "165704-1"

# --- Site settings (key -> (ar, en)) ---------------------------------------
SETTINGS: dict[str, tuple[str | None, str | None]] = {
    "brand_name": (BRAND_AR, BRAND_EN),
    "brand_short": (BRAND_SHORT_AR, BRAND_SHORT_EN),
    "country": (CONTACT["country_ar"], CONTACT["country_en"]),
    "contact_email": (CONTACT["email"], CONTACT["email"]),
    "contact_phone": (CONTACT["phone"], CONTACT["phone"]),
    # §9: the privacy policy names the data controller, the commercial
    # registration and the email. The register number is the one in the brief.
    "commercial_register": (CR_NUMBER, CR_NUMBER),
    # SEO title/description: brief-approved wording only.
    "seo_title": (f"{BRAND_AR} | {BRAND_SHORT_EN}", f"{BRAND_SHORT_EN} | {BRAND_SHORT_AR}"),
    "seo_description": (
        "شركة قابضة بحرينية تعمل على تطوير شركات المجموعة، وتنسيق خبراتها، وربط العملاء بالخدمات والفرص التجارية والاستثمارية.",
        "A Bahraini holding company that develops the group's companies, coordinates their expertise, and connects clients with services and commercial and investment opportunities.",
    ),
    # Mandatory legal notice for the opportunity form (brief §5.G).
    "opportunity_notice": (
        "إرسال المعلومات لا يعني قبولها أو الالتزام بتمويلها أو الدخول في شراكة.",
        "Submitting information does not mean it is accepted or that there is any obligation to fund it or enter into a partnership.",
    ),
}

# --- Hero slides (approved headlines, brief §5.B) --------------------------
SLIDES = [
    {
        "title_ar": "نربط الخبرات والفرص لبناء أعمال قابلة للنمو.",
        "title_en": "Connecting expertise and opportunity to build businesses that grow.",
        "body_ar": None,
        "body_en": None,
        # §9 Table 12: the hero's two buttons are «استكشف فرص الاستثمار»
        # (the opportunity form) and «اطلب حلولًا لأعمالك» (the service form).
        "cta_primary_label_ar": "استكشف فرص الاستثمار",
        "cta_primary_label_en": "Explore investment opportunities",
        "cta_primary_href": "/opportunities",
        "cta_secondary_label_ar": "اطلب حلولًا لأعمالك",
        "cta_secondary_label_en": "Request solutions for your business",
        "cta_secondary_href": "/service-request",
    },
    {
        "title_ar": "شركات متخصصة، تعمل ضمن رؤية مجموعة واحدة.",
        "title_en": "Specialised companies, working under one group vision.",
        "body_ar": None,
        "body_en": None,
        "cta_primary_label_ar": "شركات المجموعة",
        "cta_primary_label_en": "Group companies",
        "cta_primary_href": "/companies",
        "cta_secondary_label_ar": "عن القابضة",
        "cta_secondary_label_en": "About the holding",
        "cta_secondary_href": "/about",
    },
    {
        "title_ar": "حلول أعمال تبدأ من احتياجك وتمتد إلى فرص النمو.",
        "title_en": "Business solutions that start from your need and extend to growth.",
        "body_ar": None,
        "body_en": None,
        "cta_primary_label_ar": "منظومة الحلول",
        "cta_primary_label_en": "Solutions ecosystem",
        "cta_primary_href": "/solutions",
        "cta_secondary_label_ar": "تواصل معنا",
        "cta_secondary_label_en": "Contact us",
        "cta_secondary_href": "/contact",
    },
]

# --- Homepage sections (about copy is the approved description) ------------
SECTIONS = [
    {
        "key": "about",
        "title_ar": "من نحن",
        "title_en": "About us",
        "body_ar": (
            "شركة ستارت أب سفير القابضة ذ.م.م شركة قابضة بحرينية تعمل على تطوير "
            "شركات المجموعة، وتنسيق خبراتها، وربط العملاء بالخدمات والفرص التجارية "
            "والاستثمارية."
        ),
        "body_en": (
            "Start Up Sphere Holding Co W.L.L is a Bahraini holding company that "
            "develops the group's companies, coordinates their expertise, and "
            "connects clients with services and commercial and investment "
            "opportunities."
        ),
        "sort_order": 1,
        "needs_review": False,
    },
    {
        "key": "companies",
        "title_ar": "شركات المجموعة",
        "title_en": "Group companies",
        "body_ar": None,
        "body_en": None,
        "sort_order": 2,
        "needs_review": True,
    },
    {
        "key": "solutions",
        "title_ar": "منظومة الحلول",
        "title_en": "Solutions ecosystem",
        "body_ar": None,
        "body_en": None,
        "sort_order": 3,
        "needs_review": True,
    },
    {
        "key": "service_request",
        "title_ar": "طلب خدمة",
        "title_en": "Service request",
        "body_ar": None,
        "body_en": None,
        "sort_order": 4,
        "needs_review": True,
    },
    {
        "key": "opportunities",
        "title_ar": "الفرص التجارية والاستثمارية",
        "title_en": "Business and investment opportunities",
        "body_ar": None,
        "body_en": None,
        "sort_order": 5,
        "needs_review": True,
    },
    {
        "key": "careers",
        "title_ar": "هل ترغب في الانضمام إلى فريقنا؟",
        "title_en": "Would you like to join our team?",
        "body_ar": None,
        "body_en": None,
        "sort_order": 6,
        "needs_review": False,
    },
    {
        "key": "contact",
        "title_ar": "تواصل معنا",
        "title_en": "Contact us",
        "body_ar": None,
        "body_en": None,
        "sort_order": 7,
        "needs_review": False,
    },
]

# --- The six approved services (brief §5.E) --------------------------------
# Descriptions are deliberately null: the brief forbids inventing them and
# requires the owner to add and approve them from the CMS.
SERVICES = [
    ("business-setup", "تأسيس الأعمال والخدمات المرتبطة بها", "Business setup and related services"),
    ("studies", "الدراسات ودراسات الجدوى", "Studies and feasibility studies"),
    ("consulting", "الاستشارات", "Consulting"),
    ("marketing", "التسويق والإعلان", "Marketing and advertising"),
    ("supply", "التوريد والتوزيع", "Supply and distribution"),
    ("other", "خدمة أخرى", "Other service"),
]

# --- Navigation (header) ---------------------------------------------------
# §9: «القائمة العلوية: عن القابضة، شركات المجموعة، منظومة الحلول، الفرص
# التجارية، الوظائف، تواصل» — exactly these six links; the brand mark is the
# way back to the home page, so there is no «الرئيسية» entry.
HEADER_NAV = [
    ("عن القابضة", "About", "/about"),
    ("شركات المجموعة", "Companies", "/companies"),
    ("منظومة الحلول", "Solutions", "/solutions"),
    ("الفرص التجارية", "Opportunities", "/opportunities"),
    ("الوظائف", "Careers", "/careers"),
    ("تواصل", "Contact", "/contact"),
]

FOOTER_NAV = [
    ("سياسة الخصوصية", "Privacy policy", "/privacy"),
]

# Countries permitted for the opportunity form (brief §8).
OPPORTUNITY_COUNTRIES = ["البحرين", "السعودية", "الإمارات", "الكويت", "قطر", "عُمان", "الأردن"]
OPPORTUNITY_COUNTRIES_EN = [
    "Bahrain", "Saudi Arabia", "United Arab Emirates", "Kuwait", "Qatar", "Oman", "Jordan",
]

# Privacy policy — presented as text requiring legal review (brief §11).
# No unverified claim about storage, transfer or cookies is made here.
PRIVACY_INTRO_AR = (
    "توضّح هذه السياسة كيفية تعامل شركة ستارت أب سفير القابضة ذ.م.م مع البيانات "
    "التي تُرسل عبر هذا الموقع."
)
PRIVACY_INTRO_EN = (
    "This policy explains how Start Up Sphere Holding Co W.L.L handles data "
    "submitted through this website."
)
PRIVACY_REVIEW_NOTE_AR = (
    "هذا النص معروض للمراجعة القانونية، ويجب تأكيد إعدادات المعالجة الفعلية قبل "
    "الإطلاق النهائي."
)
PRIVACY_REVIEW_NOTE_EN = (
    "This text is presented for legal review; the actual processing settings must "
    "be confirmed before final launch."
)
