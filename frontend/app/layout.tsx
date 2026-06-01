import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Suton",
  description: "资料溯源复习工作台"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
