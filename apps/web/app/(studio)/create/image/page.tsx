import {Suspense} from "react";

import {Workspace} from "@/components/workspace";

export default function CreateImage() {
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Image studio</h1>
      <p className="mb-6 text-sm text-ink-300">Text→image with style controls. Reference images enter the flow below.</p>
      {/* Suspense: useSearchParams inside Workspace requires a boundary for static prerender */}
      <Suspense fallback={null}>
        <Workspace type="image" />
      </Suspense>
    </div>
  );
}
