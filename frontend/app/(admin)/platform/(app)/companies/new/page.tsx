"use client";

import { useRouter } from "next/navigation";
import { CompanyWizard } from "@/components/CompanyWizard";

/**
 * Direct link to the §6.2 wizard. The normal entry point is the «إضافة شركة»
 * button on the companies screen, which opens the same wizard as a window over
 * that screen; this route keeps deep links and the capture scripts working.
 */
export default function NewCompanyPage() {
  const router = useRouter();
  return (
    <CompanyWizard
      onClose={() => router.push("/platform/companies")}
      onSaved={(id) => router.push(`/platform/companies/${id}`)}
    />
  );
}
