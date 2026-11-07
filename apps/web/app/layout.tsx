import "./globals.css";
import type {Metadata} from "next";

import {Providers} from "@/components/providers";

export const metadata: Metadata = {
  title: "CineForge AI — Create cinematic images & videos",
  description: "An independent AI creative platform: generate images and video, direct camera movement, keep characters consistent, and manage your entire portfolio — credits and all.",
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950 font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
