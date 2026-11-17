import { notFound } from "next/navigation";

/** Any unknown path under a valid locale is a 404, rendered by not-found.tsx. */
export default function CatchAll() {
  notFound();
}
