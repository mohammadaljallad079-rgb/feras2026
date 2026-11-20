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
  // §9: the policy names the data controller, the commercial registration and
  // the email, and says the text is a draft subject to legal review.
  const cr = setting(site, "commercial_register", locale);

  const intro = ar
    ? "توضح هذه السياسة كيفية جمع شركة ستارت أب سفير القابضة ذ.م.م واستخدامها وحماية البيانات الشخصية التي تقدمها عند استخدام موقعنا أو إرسال طلب أو فرصة أو سيرة ذاتية. الشركة مسجلة في مملكة البحرين، رقم السجل التجاري 165704-1. للتواصل بشأن الخصوصية: info@sup-edu.com."
    : "This policy explains how START UP SPHERE HOLDING CO W.L.L collects, uses and protects the personal data you provide when you use our website or submit a request, an opportunity or a CV. The company is registered in the Kingdom of Bahrain under commercial registration 165704-1. For privacy enquiries: info@sup-edu.com.";

  const reviewNote = ar
    ? "هذا النص معروض للمراجعة القانونية، ويجب تأكيد إعدادات المعالجة الفعلية (الاستضافة، والمزودون، والتخزين، والكوكيز) قبل الإطلاق النهائي."
    : "This text is presented for legal review; the actual processing settings (hosting, providers, storage, cookies) must be confirmed before final launch.";

  const sections = ar
    ? [
        { h: "البيانات التي نجمعها", p: "نجمع البيانات التي تقدمها لنا عبر نماذج الموقع، وقد تشمل: الاسم والبريد الإلكتروني ورقم التواصل؛ نوع الخدمة المطلوبة ووصف الطلب؛ الدولة التي يوجد فيها المشروع عند تقديم فرصة؛ المعلومات والملفات التي يرفقها مقدم الفرصة؛ المعلومات الواردة في السيرة الذاتية وطلب التوظيف؛ والبيانات اللازمة لتشغيل الموقع وحمايته، إذا كانت أدوات تقنية لهذا الغرض مفعّلة." },
        { h: "أغراض استخدام البيانات", p: "نستخدم البيانات لاستلام طلب الخدمة والرد عليه، وتوجيهه إلى الجهة المناسبة داخل المجموعة، ومراجعة الفرص التجارية والاستثمارية، والنظر في طلبات التوظيف، والتواصل بشأن الطلب، وحماية الموقع والامتثال للالتزامات القانونية. لا نستخدم بياناتك لإرسال رسائل تسويقية مباشرة إلا وفق المتطلبات القانونية، مع إتاحة الاعتراض على هذا الاستخدام." },
        { h: "مشاركة البيانات", p: "قد نشارك القدر اللازم من بيانات طلب الخدمة مع الشركة التابعة المختصة بمعالجته. وقد يطّلع عليها موظفون مخولون أو مزودو خدمات تقنية يعملون لمصلحة القابضة، أو جهات رسمية عندما يوجب القانون ذلك. لا نبيع بياناتك الشخصية." },
        { h: "الاحتفاظ بالبيانات", p: "نحتفظ بالبيانات للمدة اللازمة لمعالجة الطلب أو الفرصة أو التوظيف، ولأي مدة أخرى يوجبها القانون أو تلزم لحفظ الحقوق. بعد انتهاء الغرض، تُحذف البيانات أو تُحجب أو تُزال منها معلومات التعريف، بحسب ما يسمح به القانون." },
        { h: "حماية البيانات ونقلها", p: "نتخذ تدابير مناسبة لحماية البيانات من الوصول أو الاستخدام أو الإفصاح غير المصرح به. وإذا استعنا بمزود خدمة أو استضافة خارج مملكة البحرين، فسيكون نقل البيانات خاضعًا للمتطلبات القانونية البحرينية المطبقة." },
        { h: "حقوق صاحب البيانات", p: "يجوز لك، وفقًا للقانون والحالة، طلب معرفة البيانات التي نعالجها، أو تصحيح بيانات غير دقيقة، أو الاعتراض على بعض أوجه المعالجة، أو طلب حجب البيانات أو محوها عند توافر شروط ذلك. لتقديم طلب، تواصل معنا عبر البريد الإلكتروني أدناه، وقد نطلب ما يثبت هويتك لحماية بياناتك." },
        { h: "ملفات تعريف الارتباط", p: "إذا استخدم الموقع ملفات تعريف ارتباط أو أدوات تحليل، فسنوضح أنواعها وأغراضها في إعدادات الارتباط بالموقع، وسنطلب الموافقة حيث تكون مطلوبة." },
        { h: "تعديلات السياسة والتواصل", p: "قد نحدّث هذه السياسة عند تغيير الموقع أو طريقة معالجة البيانات. ستُنشر النسخة المحدثة في هذه الصفحة مع تاريخ تحديثها. للاستفسارات أو طلبات الخصوصية، تواصل معنا عبر البريد الإلكتروني أدناه." },
      ]
    : [
        { h: "Data we collect", p: "We collect the data you provide through the website forms, which may include: your name, email address and contact number; the service type requested and a description of the request; the country in which a project is located when an opportunity is submitted; the information and files an opportunity submitter attaches; the information contained in a CV and job application; and the data needed to operate and protect the website, where technical tools for that purpose are enabled." },
        { h: "Purposes of use", p: "We use the data to receive and respond to service requests, to route them to the appropriate entity within the group, to review commercial and investment opportunities, to consider job applications, to communicate about the request, and to protect the website and comply with legal obligations. We do not use your data for direct marketing except in accordance with legal requirements, and you may object to such use." },
        { h: "Sharing data", p: "We may share the necessary portion of service-request data with the group company responsible for handling it. It may also be accessed by authorised employees or technical service providers working for the holding company, or by official bodies where the law requires it. We do not sell your personal data." },
        { h: "Retention", p: "We retain the data for the period needed to process the request, opportunity or application, and for any other period required by law or necessary to preserve rights. Once the purpose has ended, the data is deleted, blocked, or de-identified, as the law permits." },
        { h: "Protection and transfer", p: "We take appropriate measures to protect the data from unauthorised access, use or disclosure. If we use a service provider or hosting located outside the Kingdom of Bahrain, the transfer will be subject to the applicable Bahraini legal requirements." },
        { h: "Your rights", p: "Subject to the law and the circumstances, you may ask to know what data we process, to correct inaccurate data, to object to certain aspects of processing, or to request that the data be blocked or erased where the conditions are met. To make a request, contact us at the email below; we may ask for proof of identity to protect your data." },
        { h: "Cookies", p: "If the website uses cookies or analytics tools, we will explain their types and purposes in the website's cookie settings, and we will request consent where required." },
        { h: "Changes and contact", p: "We may update this policy when the website or the way data is processed changes. The updated version will be published on this page with its update date. For enquiries or privacy requests, contact us at the email below." },
      ];

  return (
    <section className="site-section">
      <div className="site-container max-w-[820px]">
        <span className="site-eyebrow">{ar ? "قانوني" : "Legal"}</span>
        <h1 className="site-h2">{ar ? "سياسة الخصوصية" : "Privacy policy"}</h1>
        <p className="site-lead">{intro}</p>

        <dl className="mt-6 grid gap-2 rounded-lg border border-brand-line bg-brand-mist p-5 text-[14px] sm:grid-cols-2">
          <div>
            <dt className="text-brand-slate">{ar ? "مسؤول معالجة البيانات" : "Data controller"}</dt>
            <dd className="font-semibold">{ar ? "شركة ستارت أب سفير القابضة ذ.م.م" : "START UP SPHERE HOLDING CO W.L.L"}</dd>
          </div>
          {cr && (
            <div>
              <dt className="text-brand-slate">{ar ? "السجل التجاري" : "Commercial registration"}</dt>
              <dd className="font-semibold" dir="ltr">{cr}</dd>
            </div>
          )}
          {email && (
            <div>
              <dt className="text-brand-slate">{ar ? "البريد الإلكتروني" : "Email"}</dt>
              <dd className="font-semibold" dir="ltr">{email}</dd>
            </div>
          )}
        </dl>

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
