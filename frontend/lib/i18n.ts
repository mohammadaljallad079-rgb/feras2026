/**
 * Bilingual dictionary. Arabic is the primary language; English is a full
 * translation of every key, not a partial one.
 */

export type Locale = "ar" | "en";

export const LOCALES: Locale[] = ["ar", "en"];
export const DEFAULT_LOCALE: Locale = "ar";

export const dir = (locale: Locale) => (locale === "ar" ? "rtl" : "ltr");

export const dict = {
  // Brand name exactly as printed in the design reference (page 1 title and the
  // sidebar of every screen): «ستارت أب سفير القابضة» / "Start Up Sphere Holding".
  app: { ar: "ستارت أب سفير القابضة", en: "Start Up Sphere Holding" },
  nav: {
    dashboard: { ar: "لوحة التحكم", en: "Dashboard" },
    companies: { ar: "الشركات", en: "Companies" },
    reports: { ar: "التقارير الشهرية", en: "Monthly reports" },
    accounting: { ar: "محاسبة القابضة", en: "Holding accounting" },
    serviceRequests: { ar: "طلبات الخدمات", en: "Service requests" },
    leads: { ar: "العملاء المحتملون", en: "Leads" },
    opportunities: { ar: "الفرص", en: "Opportunities" },
    directives: { ar: "التوجيهات", en: "Directives" },
    hr: { ar: "الموظفون والموارد البشرية", en: "Employees & HR" },
    website: { ar: "إدارة الموقع", en: "Website management" },
    advisor: { ar: "المستشار الخارجي", en: "External advisor" },
    assistant: { ar: "المساعد الذكي", en: "AI assistant" },
    formBuilder: { ar: "منشئ النماذج", en: "Form builder" },
    users: { ar: "المستخدمون والأدوار", en: "Users & roles" },
    audit: { ar: "سجل النشاط", en: "Audit log" },
  },
  common: {
    login: { ar: "تسجيل الدخول", en: "Sign in" },
    logout: { ar: "تسجيل الخروج", en: "Sign out" },
    email: { ar: "البريد الإلكتروني", en: "Email" },
    password: { ar: "كلمة المرور", en: "Password" },
    save: { ar: "حفظ", en: "Save" },
    cancel: { ar: "إلغاء", en: "Cancel" },
    create: { ar: "إنشاء", en: "Create" },
    edit: { ar: "تعديل", en: "Edit" },
    close: { ar: "إغلاق", en: "Close" },
    activate: { ar: "تفعيل", en: "Activate" },
    refresh: { ar: "تحديث القائمة", en: "Refresh listing" },
    submit: { ar: "إرسال", en: "Submit" },
    approve: { ar: "اعتماد", en: "Approve" },
    return: { ar: "إعادة", en: "Return" },
    forward: { ar: "إرسال للإدارة", en: "Send to management" },
    search: { ar: "بحث", en: "Search" },
    export: { ar: "تصدير Excel", en: "Export Excel" },
    loading: { ar: "جارٍ التحميل…", en: "Loading…" },
    empty: { ar: "لا توجد بيانات لعرضها.", en: "No data to display." },
    error: { ar: "تعذّر تحميل البيانات.", en: "Could not load data." },
    forbidden: { ar: "لا تملك صلاحية هذا الإجراء.", en: "You are not permitted to do this." },
    dark: { ar: "الوضع الداكن", en: "Dark mode" },
    language: { ar: "اللغة", en: "Language" },
    menu: { ar: "القائمة", en: "Menu" },
    actions: { ar: "إجراءات", en: "Actions" },
    status: { ar: "الحالة", en: "Status" },
    reason: { ar: "السبب", en: "Reason" },
    notes: { ar: "ملاحظات", en: "Notes" },
    company: { ar: "الشركة", en: "Company" },
    currency: { ar: "العملة", en: "Currency" },
    amount: { ar: "المبلغ", en: "Amount" },
    date: { ar: "التاريخ", en: "Date" },
    restrictedAttachment: { ar: "مرفق مقيد", en: "Restricted attachment" },
    download: { ar: "تنزيل", en: "Download" },
  },
  login: {
    title: { ar: "تسجيل الدخول إلى المنصة", en: "Sign in to the platform" },
    failed: { ar: "بيانات الدخول غير صحيحة.", en: "Invalid credentials." },
    forgot: { ar: "نسيت كلمة المرور؟", en: "Forgot your password?" },
  },
  passwordReset: {
    requestTitle: { ar: "استعادة كلمة المرور", en: "Reset your password" },
    requestHint: {
      ar: "أدخل بريدك الإلكتروني وسنُصدر رابطًا لمرة واحدة صالحًا لمدة محدودة.",
      en: "Enter your email and we will issue a single-use link that expires shortly.",
    },
    issued: {
      ar: "إذا كان الحساب موجودًا فقد صدر رابط إعادة التعيين. الرابط صالح لمرة واحدة ولمدة محدودة.",
      en: "If the account exists, a reset link has been issued. It is single-use and expires.",
    },
    devToken: { ar: "رمز إعادة التعيين (بيئة التطوير)", en: "Reset token (development)" },
    devTokenHint: {
      ar: "لا يوجد ناقل بريد في هذه البيئة، لذا يُعرض الرمز هنا. في الإنتاج يُرسل خارج المنصة ولا يُعرض.",
      en: "No mail transport is configured here, so the token is shown. In production it is delivered out-of-band and never displayed.",
    },
    useToken: { ar: "متابعة إلى تعيين كلمة المرور", en: "Continue to set a new password" },
    confirmTitle: { ar: "تعيين كلمة مرور جديدة", en: "Set a new password" },
    token: { ar: "رمز إعادة التعيين", en: "Reset token" },
    newPassword: { ar: "كلمة المرور الجديدة", en: "New password" },
    confirmPassword: { ar: "تأكيد كلمة المرور", en: "Confirm password" },
    submit: { ar: "تعيين كلمة المرور", en: "Set password" },
    done: { ar: "تم تعيين كلمة المرور. يمكنك تسجيل الدخول الآن.", en: "Password set. You can sign in now." },
    mismatch: { ar: "كلمتا المرور غير متطابقتين.", en: "The passwords do not match." },
    tooShort: { ar: "يجب أن تكون كلمة المرور 8 أحرف على الأقل.", en: "The password must be at least 8 characters." },
    invalidToken: { ar: "الرمز غير صالح أو منتهٍ أو مستعمل سابقًا.", en: "The token is invalid, expired, or already used." },
    backToLogin: { ar: "العودة إلى تسجيل الدخول", en: "Back to sign in" },
    send: { ar: "إرسال رابط الاستعادة", en: "Send reset link" },
  },
  companies: {
    title: { ar: "إدارة الشركات", en: "Companies management" },
    code: { ar: "رمز الشركة", en: "Company code" },
    nameAr: { ar: "الاسم بالعربية", en: "Arabic name" },
    nameEn: { ar: "الاسم بالإنجليزية", en: "English name" },
    country: { ar: "الدولة", en: "Country" },
    sector: { ar: "القطاع", en: "Sector" },
    manager: { ar: "مدير الشركة", en: "Company manager" },
    ownership: { ar: "نسبة الملكية", en: "Ownership percentage" },
    logo: { ar: "شعار الشركة", en: "Company logo" },
    closed: { ar: "الشركات المغلقة", en: "Closed companies" },
    newCompany: { ar: "شركة جديدة", en: "New company" },
    wizard: {
      title: { ar: "إنشاء شركة (أربع خطوات)", en: "Create company (four steps)" },
      step1: { ar: "البيانات الأساسية", en: "Basic data" },
      step2: { ar: "بيانات التواصل", en: "Contact details" },
      step3: { ar: "الملكية والعملة", en: "Ownership and currency" },
      step4: { ar: "المراجعة", en: "Review" },
      saveDraft: { ar: "حفظ كمسودة", en: "Save draft" },
      next: { ar: "التالي", en: "Next" },
      back: { ar: "السابق", en: "Back" },
    },
  },
  reports: {
    title: { ar: "التقارير الشهرية", en: "Monthly reports" },
    period: { ar: "فترة التقرير", en: "Reporting period" },
    commentary: { ar: "التعليق الإداري", en: "Administrative commentary" },
    bankStatement: { ar: "كشف الحساب البنكي", en: "Bank statement" },
    submitToAccounting: { ar: "إرسال إلى المحاسبة", en: "Submit to accounting" },
    history: { ar: "سجل التقرير", en: "Report history" },
    statusDraft: { ar: "مسودة", en: "Draft" },
    statusSubmitted: { ar: "مُرسل", en: "Submitted" },
    statusReturned: { ar: "مُعاد", en: "Returned" },
    statusApproved: { ar: "معتمد", en: "Approved" },
    statusForwarded: { ar: "مُرسل للإدارة", en: "Sent to management" },
    locked: { ar: "التقرير معتمد ومقفل.", en: "The report is approved and locked." },
    currencyNote: {
      ar: "تُعرض المبالغ بعملة الشركة ولا تُجمع عملات مختلفة في إجمالي واحد.",
      en: "Amounts are shown in the company currency; different currencies are never summed into one total.",
    },
  },
  opportunities: {
    title: { ar: "الفرص", en: "Opportunities" },
    decision: { ar: "قرار المالك", en: "Owner decision" },
    underReview: { ar: "قيد المراجعة", en: "Under review" },
    deferred: { ar: "مؤجّل", en: "Deferred" },
  },
  directives: {
    title: { ar: "التوجيهات التنفيذية", en: "Executive directives" },
    followUp: { ar: "تاريخ المتابعة", en: "Follow-up date" },
    overdue: { ar: "متأخر", en: "Overdue" },
    received: { ar: "مستلَم", en: "Received" },
    completed: { ar: "منجز", en: "Completed" },
    acknowledge: { ar: "إقرار الاستلام", en: "Acknowledge receipt" },
    complete: { ar: "إنجاز", en: "Complete" },
  },
  assistant: {
    title: { ar: "المساعد الذكي", en: "AI assistant" },
    ask: { ar: "اسأل المساعد", en: "Ask the assistant" },
    sources: { ar: "المصادر", en: "Sources" },
    confidence: { ar: "درجة الثقة", en: "Confidence" },
    unconfigured: {
      ar: "المساعد غير مهيأ: مفتاح مزوّد الذكاء الاصطناعي غير مُعد على الخادم.",
      en: "The assistant is not configured: no AI provider key is set on the server.",
    },
    noData: {
      ar: "لا توجد سجلات مصرّح بها للإجابة. لم يتم اختلاق أي بيانات.",
      en: "There are no permitted records to answer from. No data was invented.",
    },
  },
  audit: {
    title: { ar: "سجل النشاط", en: "Activity log" },
    timestamp: { ar: "الوقت", en: "Timestamp" },
    user: { ar: "المستخدم", en: "User" },
    role: { ar: "الدور", en: "Role" },
    action: { ar: "الإجراء", en: "Action" },
    target: { ar: "السجل المستهدف", en: "Target record" },
  },
  users: {
    title: { ar: "المستخدمون والصلاحيات", en: "Users and roles" },
    invite: { ar: "دعوة مستخدم", en: "Invite user" },
    roles: { ar: "الأدوار", en: "Roles" },
    permissions: { ar: "الصلاحيات", en: "Permissions" },
    setupLink: { ar: "رابط إعداد كلمة المرور", en: "Password setup link" },
    newUser: { ar: "مستخدم جديد", en: "New user" },
  },
} as const;

export const appName = (locale: Locale) => dict.app[locale];

export function t(section: string, key: string, locale: Locale): string {
  const entries = (dict as unknown as Record<string, Record<string, Record<Locale, string>>>)[section];
  const entry = entries?.[key];
  return entry ? entry[locale] : key;
}

/** Pick the right field from a bilingual record. */
export function bilingual(row: Record<string, unknown>, base: string, locale: Locale): string {
  const key = locale === "ar" ? `${base}_ar` : `${base}_en`;
  return String(row[key] ?? "");
}
