import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Finn Bil-Analyse | Finn de beste bilkuppene",
  description: "Maskinlæring som analyserer tusenvis av bruktbilsannonser på Finn.no for å finne de best priset bilene.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="no">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
