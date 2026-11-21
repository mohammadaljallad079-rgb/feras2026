"""Canonical seed content for the public website.

Every string below is copied verbatim from `content-ar.md` / `content-en.md`
(repository root), the approved copy deck. Do not paraphrase, translate loosely
or "improve" a string here: the website must read exactly as the deck says. If a
string is missing from the deck it stays null rather than being invented.
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
    # SEO title/description — verbatim from the deck (§1).
    "seo_title": (
        "ستارت أب سفير القابضة | نربط الخبرات والفرص لبناء أعمال قابلة للنمو",
        "Start Up Sphere Holding | Connecting expertise and opportunity to build businesses that can grow",
    ),
    "seo_description": (
        "شركة قابضة بحرينية تطوّر شركات المجموعة وتربط العملاء بالخدمات والفرص التجارية والاستثمارية المناسبة.",
        "A Bahraini holding company developing its group companies and connecting clients with suitable services and commercial and investment opportunities.",
    ),
    # Mandatory legal notice for the opportunity form (§8).
    "opportunity_notice": (
        "إرسال المعلومات لا يعني قبولها أو الالتزام بتمويلها أو الدخول في شراكة.",
        "Submitting information does not mean it is accepted, that we commit to fund it, or that we will enter a partnership.",
    ),
    # Top bar (§2) and the footer tagline (§11).
    "top_bar": (
        "مملكة البحرين · ستارت أب سفير القابضة ذ.م.م",
        "Kingdom of Bahrain · Start Up Sphere Holding W.L.L",
    ),
    "footer_tagline": (
        "شركة قابضة بحرينية تعمل على تطوير شركات المجموعة وربط الخبرات بفرص الأعمال والنمو.",
        "A Bahraini holding company developing its portfolio and connecting expertise with business and growth opportunities.",
    ),
}

# --- Hero slides (§3 of the deck, three slides) ----------------------------
SLIDES = [
    {
        "eyebrow_ar": "ستارت أب سفير القابضة · البحرين",
        "eyebrow_en": "Start Up Sphere Holding · Bahrain",
        "title_ar": "نربط الخبرات والفرص لبناء أعمال قابلة للنمو",
        "title_en": "Connecting expertise and opportunity to build businesses that can grow",
        "body_ar": "من البحرين، نعمل على تطوير شركات المجموعة وربط العملاء بالخدمات والفرص المناسبة.",
        "body_en": "From Bahrain, we develop the group’s companies and connect clients with relevant services and opportunities.",
        # §3 slide 3 names the hero buttons; they point at the opportunity and
        # service-request forms respectively.
        "cta_primary_label_ar": "استكشف فرص الاستثمار",
        "cta_primary_label_en": "Explore opportunities",
        "cta_primary_href": "/opportunities",
        "cta_secondary_label_ar": "اطلب حلولًا لأعمالك",
        "cta_secondary_label_en": "Request business solutions",
        "cta_secondary_href": "/service-request",
    },
    {
        "eyebrow_ar": "شركات المجموعة",
        "eyebrow_en": "Our portfolio",
        "title_ar": "شركات متخصصة، تعمل ضمن رؤية مجموعة واحدة",
        "title_en": "Specialist companies, connected by one group vision",
        "body_ar": "تجمع القابضة بين خبرات شركات المجموعة وتوجهها نحو فرص النمو في الأسواق التي تعمل بها.",
        "body_en": "The holding connects the expertise of its companies and focuses them on growth opportunities in their markets.",
        "cta_primary_label_ar": "شركات المجموعة",
        "cta_primary_label_en": "Group companies",
        "cta_primary_href": "/companies",
        "cta_secondary_label_ar": "عن القابضة",
        "cta_secondary_label_en": "About",
        "cta_secondary_href": "/about",
    },
    {
        "eyebrow_ar": "منظومة الحلول",
        "eyebrow_en": "Our solutions",
        "title_ar": "حلول أعمال تبدأ من احتياجك وتمتد إلى فرص النمو",
        "title_en": "Business solutions shaped around your needs and growth opportunities",
        "body_ar": "اختر الخدمة المناسبة لمشروعك، وسيصل طلبك إلى الجهة المختصة داخل المجموعة.",
        "body_en": "Choose the service your project needs, and your request will reach the relevant team within the group.",
        "cta_primary_label_ar": "منظومة الحلول",
        "cta_primary_label_en": "Solutions",
        "cta_primary_href": "/solutions",
        "cta_secondary_label_ar": "تواصل معنا",
        "cta_secondary_label_en": "Contact",
        "cta_secondary_href": "/contact",
    },
]

# --- Homepage sections (§4–§10 of the deck) --------------------------------
SECTIONS = [
    {
        "key": "about",
        "title_ar": "من نحن",
        "title_en": "About",
        "body_ar": (
            "ستارت أب سفير القابضة ذ.م.م · مملكة البحرين\n\n"
            "قابضة تجمع الخبرة وتحوّلها إلى فرص نمو.\n\n"
            "تعمل ستارت أب سفير القابضة على إدارة وتطوير شركات المجموعة، وتنسيق "
            "خبراتها، وفتح مسارات عملية للأعمال والفرص الاستثمارية. تتولى كل شركة "
            "أعمالها ضمن نشاطها، بينما تعمل القابضة على تعزيز التكامل بينها وتوجيه "
            "المجموعة نحو نمو مدروس."
        ),
        "body_en": (
            "Start Up Sphere Holding W.L.L · Kingdom of Bahrain\n\n"
            "A holding company that connects expertise with growth opportunities.\n\n"
            "Start Up Sphere Holding manages and develops its group companies, aligns "
            "their expertise, and opens practical paths for business and investment "
            "opportunities. Each company operates in its field while the holding "
            "strengthens collaboration and guides the group toward considered growth."
        ),
        "sort_order": 1,
        "needs_review": False,
    },
    {
        "key": "companies",
        "title_ar": "محفظة المجموعة",
        "title_en": "Our portfolio",
        "body_ar": "شركات متخصصة تعمل في قطاعات وأسواق مختلفة ضمن محفظة واحدة.",
        "body_en": "Specialist companies across different sectors and markets, within one portfolio.",
        "sort_order": 2,
        "needs_review": False,
    },
    {
        "key": "solutions",
        "title_ar": "منظومة الحلول",
        "title_en": "Solutions",
        "body_ar": "خدمات مترابطة لاحتياجات الأعمال.",
        "body_en": "Connected services for business needs.",
        "sort_order": 3,
        "needs_review": False,
    },
    {
        "key": "service_request",
        "title_ar": "اطلب خدمة",
        "title_en": "Request a service",
        "body_ar": "نافذة واحدة لاحتياجات الأعمال",
        "body_en": "One point of contact for business needs",
        "sort_order": 4,
        "needs_review": False,
    },
    {
        "key": "opportunities",
        "title_ar": "الفرص التجارية والاستثمارية",
        "title_en": "Business and investment opportunities",
        "body_ar": "هل لديك مشروع أو فرصة للنمو؟",
        "body_en": "Do you have a project or growth opportunity?",
        "sort_order": 5,
        "needs_review": False,
    },
    {
        "key": "careers",
        "title_ar": "العمل معنا",
        "title_en": "Careers",
        "body_ar": "هل ترغب في الانضمام إلى فريقنا؟",
        "body_en": "Would you like to join our team?",
        "sort_order": 6,
        "needs_review": False,
    },
    {
        "key": "contact",
        "title_ar": "تواصل معنا",
        "title_en": "Get in touch",
        "body_ar": "ابدأ محادثة حول احتياج أعمالك.",
        "body_en": "Start a conversation about your business needs.",
        "sort_order": 7,
        "needs_review": False,
    },
]

# --- The six approved services (§6 of the deck) ----------------------------
# Descriptions stay null: the deck says they are not approved yet and the owner
# adds them from the CMS before launch.
SERVICES = [
    ("business-setup", "تأسيس الأعمال والخدمات المرتبطة بها", "Business setup and related services"),
    ("studies", "الدراسات ودراسات الجدوى", "Studies and feasibility studies"),
    ("consulting", "الاستشارات", "Consulting"),
    ("marketing", "التسويق والإعلان", "Marketing and advertising"),
    ("supply", "التوريد والتوزيع", "Supply and distribution"),
    ("other", "خدمة أخرى", "Other service"),
]

# --- Navigation (§2 header links, §11 footer links) ------------------------
# The deck names exactly these six header links; the brand mark is the way home,
# so there is no «الرئيسية» entry.
HEADER_NAV = [
    ("عن القابضة", "About the holding", "/about"),
    ("شركات المجموعة", "Group companies", "/companies"),
    ("منظومة الحلول", "Solutions", "/solutions"),
    ("الفرص التجارية", "Business opportunities", "/opportunities"),
    ("الوظائف", "Careers", "/careers"),
    ("تواصل", "Contact", "/contact"),
]

FOOTER_NAV = [
    ("سياسة الخصوصية", "Privacy policy", "/privacy"),
]

# Countries permitted for the opportunity form (§12 of the deck).
OPPORTUNITY_COUNTRIES = ["البحرين", "السعودية", "الإمارات", "الكويت", "قطر", "عُمان", "الأردن"]
OPPORTUNITY_COUNTRIES_EN = [
    "Bahrain", "Saudi Arabia", "United Arab Emirates", "Kuwait", "Qatar", "Oman", "Jordan",
]

# Privacy policy (§13). The nine numbered headings and their bodies are verbatim
# from the deck; the deck itself marks the text as awaiting legal review.
PRIVACY_INTRO_AR = (
    "توضح هذه السياسة كيفية جمع شركة ستارت أب سفير القابضة ذ.م.م واستخدامها وحماية "
    "البيانات الشخصية التي تقدمها عند استخدام موقعنا أو إرسال طلب أو فرصة أو سيرة "
    "ذاتية. الشركة مسجلة في مملكة البحرين، رقم السجل التجاري 165704-1. للتواصل بشأن "
    "الخصوصية: info@sup-edu.com."
)
PRIVACY_INTRO_EN = (
    "This policy explains how Start Up Sphere Holding W.L.L collects, uses and "
    "protects the personal data you provide when you use our website or submit a "
    "request, an opportunity or a CV. The company is registered in the Kingdom of "
    "Bahrain, commercial registration no. 165704-1. For privacy enquiries: "
    "info@sup-edu.com."
)
PRIVACY_REVIEW_NOTE_AR = (
    "هذا النص معروض للمراجعة القانونية، ويجب تأكيد إعدادات المعالجة الفعلية قبل "
    "الإطلاق النهائي."
)
PRIVACY_REVIEW_NOTE_EN = (
    "This text is presented for legal review; the actual processing settings must "
    "be confirmed before final launch."
)

# The eight remaining numbered sections of §13, in order.
PRIVACY_SECTIONS = [
    (
        "البيانات التي نجمعها",
        "Data we collect",
        "نجمع البيانات التي تقدمها لنا عبر نماذج الموقع، وقد تشمل: الاسم والبريد "
        "الإلكتروني ورقم التواصل؛ نوع الخدمة المطلوبة ووصف الطلب؛ الدولة التي يوجد "
        "فيها المشروع عند تقديم فرصة؛ المعلومات والملفات التي يرفقها مقدم الفرصة؛ "
        "المعلومات الواردة في السيرة الذاتية وطلب التوظيف؛ والبيانات اللازمة لتشغيل "
        "الموقع وحمايته، إذا كانت أدوات تقنية لهذا الغرض مفعّلة.",
        "We collect the data you provide through our website forms, which may "
        "include: your name, email and contact number; the type of service requested "
        "and the request description; the project country when you submit an "
        "opportunity; the information and files you attach; the information "
        "contained in a CV or job application; and the data needed to operate and "
        "protect the website, if technical tools are enabled for that purpose.",
    ),
    (
        "أغراض استخدام البيانات",
        "How we use data",
        "نستخدم البيانات لاستلام طلب الخدمة والرد عليه، وتوجيهه إلى الجهة المناسبة "
        "داخل المجموعة، ومراجعة الفرص التجارية والاستثمارية، والنظر في طلبات "
        "التوظيف، والتواصل بشأن الطلب، وحماية الموقع والامتثال للالتزامات القانونية. "
        "لا نستخدم بياناتك لإرسال رسائل تسويقية مباشرة إلا وفق المتطلبات القانونية، "
        "مع إتاحة الاعتراض على هذا الاستخدام.",
        "We use data to receive and respond to your request, route it to the "
        "appropriate party within the group, review commercial and investment "
        "opportunities, consider job applications, communicate about your "
        "submission, protect the website and comply with legal obligations. We do "
        "not use your data to send direct marketing messages except as legally "
        "required, and you may object to such use.",
    ),
    (
        "مشاركة البيانات",
        "Sharing data",
        "قد نشارك القدر اللازم من بيانات طلب الخدمة مع الشركة التابعة المختصة "
        "بمعالجته. وقد يطّلع عليها موظفون مخولون أو مزودو خدمات تقنية يعملون لمصلحة "
        "القابضة، أو جهات رسمية عندما يوجب القانون ذلك. لا نبيع بياناتك الشخصية.",
        "We may share the data necessary to handle a service request with the "
        "relevant group company. Authorized staff, technical service providers "
        "acting for the holding, or official bodies where the law requires may also "
        "access it. We do not sell your personal data.",
    ),
    (
        "الاحتفاظ بالبيانات",
        "Retention",
        "نحتفظ بالبيانات للمدة اللازمة لمعالجة الطلب أو الفرصة أو التوظيف، ولأي مدة "
        "أخرى يوجبها القانون أو تلزم لحفظ الحقوق. بعد انتهاء الغرض، تُحذف البيانات أو "
        "تُحجب أو تُزال منها معلومات التعريف، بحسب ما يسمح به القانون.",
        "We keep data for as long as needed to handle the request, opportunity or "
        "application, and for any other period required by law or needed to protect "
        "rights. Once the purpose ends, data is deleted, blocked or de-identified, as "
        "the law permits.",
    ),
    (
        "حماية البيانات ونقلها",
        "Data protection and transfers",
        "نتخذ تدابير مناسبة لحماية البيانات من الوصول أو الاستخدام أو الإفصاح غير "
        "المصرح به. وإذا استعنا بمزود خدمة أو استضافة خارج مملكة البحرين، فسيكون نقل "
        "البيانات خاضعًا للمتطلبات القانونية البحرينية المطبقة.",
        "We take appropriate measures to protect data against unauthorized access, "
        "use or disclosure. If we use a service provider or hosting outside the "
        "Kingdom of Bahrain, any transfer of data will be subject to the applicable "
        "Bahraini legal requirements.",
    ),
    (
        "حقوق صاحب البيانات",
        "Your rights",
        "يجوز لك، وفقًا للقانون والحالة، طلب معرفة البيانات التي نعالجها، أو تصحيح "
        "بيانات غير دقيقة، أو الاعتراض على بعض أوجه المعالجة، أو طلب حجب البيانات أو "
        "محوها عند توافر شروط ذلك. لتقديم طلب، تواصل معنا عبر info@sup-edu.com، وقد "
        "نطلب ما يثبت هويتك لحماية بياناتك.",
        "Subject to the law and the circumstances, you may ask to know what data we "
        "process, request correction of inaccurate data, object to certain "
        "processing, or request blocking or erasure where the conditions are met. To "
        "make a request, contact us at info@sup-edu.com; we may ask for proof of "
        "identity to protect your data.",
    ),
    (
        "ملفات تعريف الارتباط",
        "Cookies",
        "إذا استخدم الموقع ملفات تعريف ارتباط أو أدوات تحليل، فسنوضح أنواعها "
        "وأغراضها في إعدادات الارتباط بالموقع، وسنطلب الموافقة حيث تكون مطلوبة.",
        "If the website uses cookies or analytics tools, we will explain their types "
        "and purposes in the website’s cookie settings and will ask for consent "
        "where it is required.",
    ),
    (
        "تعديلات السياسة والتواصل",
        "Changes and contact",
        "قد نحدّث هذه السياسة عند تغيير الموقع أو طريقة معالجة البيانات. ستُنشر "
        "النسخة المحدثة في هذه الصفحة مع تاريخ تحديثها. للاستفسارات أو طلبات "
        "الخصوصية، تواصل معنا عبر info@sup-edu.com.",
        "We may update this policy when the website or the way we process data "
        "changes. The updated version will be published on this page with its update "
        "date. For enquiries or privacy requests, contact us at info@sup-edu.com.",
    ),
]
