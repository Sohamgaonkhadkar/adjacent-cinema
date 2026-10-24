import type { Metadata } from "next";
import "./globals.css";
import NightfallNavigation from "@/components/NightfallNavigation";

export const metadata: Metadata = {
  title: "Adjacent — Cultural Intelligence for Independent Cinema",
  description:
    "Audience-development decision support for programmed cultural venues. Powered by Qloo cultural intelligence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <NightfallNavigation />
        {children}
      </body>
    </html>
  );
}