import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import './App.css'
import App from './App.tsx'
import CompanyWebsite from './CompanyWebsite'
import { initializeClientLogging } from './lib/logging'

initializeClientLogging()

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true, staleTime: 15_000 } } })
let pathname = window.location.pathname.replace(/\/+$/, '')
const websiteUrl = new URL(window.location.href)
if (pathname === '/website-preview' || pathname === '/login-icon-preview' || (pathname === '' && websiteUrl.searchParams.get('readability') === 'preview')) {
  websiteUrl.pathname = '/'
  websiteUrl.searchParams.delete('readability')
  window.history.replaceState(null, '', `${websiteUrl.pathname}${websiteUrl.search}${websiteUrl.hash}`)
  pathname = ''
}
const isCompanyWebsite = pathname === ''
document.title = isCompanyWebsite ? 'Vridhi Constructions & Designs' : 'Vridhi | Project Workspace'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>{isCompanyWebsite ? <CompanyWebsite /> : <App />}</QueryClientProvider>
  </StrictMode>,
)
