import type { Metadata } from 'next';
import { Chakra_Petch, Roboto } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { AthleteProvider } from '@/lib/contexts/AthleteContext';
import { AppChrome } from '@/components/AppChrome';
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister';

const chakra = Chakra_Petch({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-chakra',
  display: 'swap',
});

const roboto = Roboto({
  subsets: ['latin'],
  weight: ['400', '500', '700'],
  variable: '--font-roboto',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'BSAMS - Boxing Science Athlete Management System',
  description: 'High-performance athlete management and CMJ analysis',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${chakra.variable} ${roboto.variable}`}>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#090A3D" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="icon" href="/favicon.ico" sizes="32x32" />
        <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" />
      </head>
      <body className="min-h-screen font-body">
        <ServiceWorkerRegister />
        <AuthProvider>
          <AthleteProvider>
            <AppChrome>{children}</AppChrome>
          </AthleteProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
