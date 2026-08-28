import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PoolBerry Control",
  description: "PoolBerry controller management dashboard",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="nl">
      <body>{children}</body>
    </html>
  );
}
