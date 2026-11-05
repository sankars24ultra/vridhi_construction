import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import CompanyWebsite from './CompanyWebsite'

createRoot(document.getElementById('root')!).render(
  <StrictMode><CompanyWebsite /></StrictMode>,
)
