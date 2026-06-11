import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/Providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI-GD-Pro | AI Group Discussion Simulator',
  description: 'Practice placement-level group discussions with AI-powered bots. Improve your communication, leadership, and teamwork skills.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased`}>
        <Providers>
          <div className="min-h-screen ambient-bg particles-bg">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  )
}
