import type { Metadata } from "next";
import { setting, getSite, type Locale } from "@/lib/site";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  return { title: locale === "ar" ? "سياسة الخصوصية" : "Privacy policy" };
}

/**
 * Privacy policy. The intro is brief-approved wording; the processing sections
 * are presented as requiring legal review, and no unverified claim about
 * storage, transfer or retention is made here.
 */
export default async function PrivacyPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale: raw } = await params;
  const locale = raw as Locale;
  const ar = locale === "ar";
  const site = await getSite();
  const email = setting(site, "contact_email", locale);

  const intro = ar
    ? "توضّح هذه السياسة كيفية تعامل شركة ستارت أب سفير القابضة ذ.م.م مع البيانات التي تُرسل عبر هذا الموقع."
    : "This policy explains how Start Up Sphere Holding Co W.L.L handles data submitted through this website.";

  const reviewNote = ar
    ? "هذا النص معروض للمراجعة القانونية، ويجب تأكيد إعدادات المعالجة الفعلية قبل الإطلاق النهائي."
    : "This text is presented for legal review; the actual processing settings must be confirmed before final launch.";

  const sections = ar
    ? [
        { h: "البيانات التي نجمعها", p: "نستلم البيانات التي تُدخلها في النماذج: الاسم، والبريد الإلكتروني، ورقم التواصل، وتفاصيل الطلب أو الفرصة، والمرفقات التي تختار إرسالها." },
        { h: "الغرض من المعالجة", p: "تُستخدم البيانات للرد على طلبك، ودراسة الفرصة أو الطلب، وإدارة العلاقة معك." },
        { h: "الأمان", p: "تُخزّن المرفقات في تخزين خاص غير متاح للعموم، ويُقيَّد الوصول إليها وفق صلاحيات المستخدم." },
        { h: "حقوقك", p: "يمكنك طلب الوصول إلى بياناتك أو تصحيحها أو حذفها بالتواصل معنا." },
      ]
    : [
        { h: "Data we collect", p: "We receive the data you enter in the forms: name, email, contact number, request or opportunity details, and any attachments you choose to send." },
        { h: "Purpose of processing", p: "The data is used to respond to your request, to review the opportunity or request, and to manage our relationship with you." },
        { h: "Security", p: "Attachments are held in private storage that is not publicly reachable, and access is limited by user permissions." },
        { h: "Your rights", p: "You can ask to access, correct or delete your data by contacting us." },
      ];

  return (
    <section className="site-section">
      <div className="site-container max-w-[820px]">
        <span className="site-eyebrow">{ar ? "قانوني" : "Legal"}</span>
        <h1 className="site-h2">{ar ? "سياسة الخصوصية" : "Privacy policy"}</h1>
        <p className="site-lead">{intro}</p>

        <p className="mt-6 rounded-lg border border-[#ede2cc] border-s-4 border-s-brand-sand bg-[#fbf7ef] p-5 text-[14px] text-[#6a5731]">
          {reviewNote}
        </p>

        <div className="mt-9 grid gap-6">
          {sections.map((s) => (
            <div key={s.h}>
              <h2 className="text-[18px] font-bold">{s.h}</h2>
              <p className="mt-2 text-[15px] text-brand-slate">{s.p}</p>
            </div>
          ))}
        </div>

        {email && (
          <p className="mt-9 text-[15px]">
            {ar ? "للتواصل: " : "Contact: "}
            <a className="text-brand-deep underline" href={`mailto:${email}`}>{email}</a>
          </p>
        )}
      </div>
    </section>
  );
}
