import {Suspense} from "react";

import {Workspace} from "@/components/workspace";

export default function CreateEdit() {
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Enhance & edit</h1>
      <p className="mb-6 text-sm text-ink-300">
        Upscale an image or re-shape a region of a video. Engines marked experimental surface their status honestly.
      </p>
      {/* Suspense: useSearchParams inside Workspace requires a boundary for static prerender */}
      <Suspense fallback={null}>
        <Workspace type="edit" />
      </Suspense>
    </div>
  );
}
