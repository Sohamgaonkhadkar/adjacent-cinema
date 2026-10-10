import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adjacent — Cultural Intelligence for Independent Cinema",
  description:
    "Audience-development decision support for programmed cultural venues. Powered by Qloo cultural intelligence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}