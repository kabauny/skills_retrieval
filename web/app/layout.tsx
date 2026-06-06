import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Wiki LM",
  description: "Oncology knowledge base — query, capture, review",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
