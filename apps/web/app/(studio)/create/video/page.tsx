import {Workspace} from "@/components/workspace";

export default function CreateVideo() {
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Video studio</h1>
      <p className="mb-6 text-sm text-ink-300">Text or first-frame → video, with the camera and film setup you dictate.</p>
      <Workspace type="video" />
    </div>
  );
}
