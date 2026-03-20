import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Assistant - EV Power Energy',
  description: 'Internal AI Assistant & Knowledge Chatbot',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const themeInitScript = `
    (function() {
      try {
        var key = 'evp-ai-assistant-theme';
        var stored = localStorage.getItem(key);
        var theme = stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system';
        var isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
        document.documentElement.classList.toggle('dark', isDark);
      } catch (e) {}
    })();
  `

  return (
    <html lang="th" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={inter.className}>
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
