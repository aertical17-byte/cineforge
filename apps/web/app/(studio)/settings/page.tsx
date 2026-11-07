import {useEffect} from "react";

/** /settings → /settings/profile */
export default function SettingsIndex() {
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.location.replace("/settings/profile");
    }
  }, []);
  return null;
}
