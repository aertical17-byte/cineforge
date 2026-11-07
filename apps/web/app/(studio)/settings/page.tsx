import {redirect} from "next/navigation";

/** /settings → /settings/profile (server-side redirect, no client JS). */
export default function SettingsIndex() {
  redirect("/settings/profile");
}
