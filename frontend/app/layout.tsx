import "../styles/globals.css";
import type { Metadata } from "next";
import { TopNav } from "../components/TopNav";

export const metadata: Metadata = {
  title: "TeachYou — AI Video Generator",
  description: "Turn any idea into a video. BYOK, self-host, no watermark.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <TopNav />
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
