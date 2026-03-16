import "../styles/globals.css";
import type { Metadata } from "next";
import { TopNav } from "../components/TopNav";

export const metadata: Metadata = {
  title: "SketchWave",
  description: "Whiteboard explainers from PDFs or prompts",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <TopNav brandName="SketchWave" subtitle="PDF / Prompt → Whiteboard Video" />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-neutral-200 py-5 text-center text-xs text-neutral-500">
            <div className="mx-auto w-full max-w-6xl px-4">
              Built for rapid explainer generation · {new Date().getFullYear()}
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
