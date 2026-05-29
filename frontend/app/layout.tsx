import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Suton v0.1.0",
  description: "资料溯源最小闭环"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
