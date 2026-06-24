/**
 * src/app/layout.tsx — Root layout for Brain OS Dashboard
 */
import type { Metadata } from 'next';
import '@/styles/globals.css';

export const metadata: Metadata = {
  title: 'Brain OS Dashboard',
  description: 'Real-time robot brain visualization and human-in-the-loop control',
  icons: { icon: '/icons/favicon.ico' },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className="h-screen w-screen overflow-hidden">
        {children}
      </body>
    </html>
  );
}
