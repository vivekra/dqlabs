import type { Metadata } from 'next';
import './globals.css';

export const viewport = {
  themeColor: '#7c3aed',
};

export const metadata: Metadata = {
  title: 'DigitalQ Labs — AI-Native Kubernetes Learning Platform',
  description:
    'Launch isolated Kubernetes workspaces, practise DevOps and infrastructure engineering in a high-density cloud sandbox, powered by an integrated AI diagnostic assistant.',
  keywords: ['kubernetes', 'devops', 'learning', 'workspace', 'AI', 'k3s', 'cloud', 'xterm'],
  authors: [{ name: 'DigitalQ Labs' }],
  openGraph: {
    title: 'DigitalQ Labs',
    description: 'AI-Native Kubernetes & DevOps learning cloud',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
