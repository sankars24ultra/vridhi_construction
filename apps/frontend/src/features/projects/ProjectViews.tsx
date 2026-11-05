import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { QueryError } from '../../components/ui'
import { ArrowUpRight, BriefcaseBusiness, Check, CircleX, Clock3, Pause, ShieldCheck } from 'lucide-react'
import { Eye, EyeOff } from 'lucide-react'
import { lazy, Suspense } from 'react'
import type { Page, Project } from '../../lib/api'
import { currency, statusClass } from '../../lib/format'
import vridhiLogo from '../../../../../images/logo-transparent.png'
const LoginCity = lazy(() => import('../../LoginCity'))

export function Login({ darkMode, identity, password, setIdentity, setPassword, csrf, error, pending, onSubmit }: { darkMode: boolean; identity: string; password: string; setIdentity: (value: string) => void; setPassword: (value: string) => void; csrf: string; error: Error | null; pending: boolean; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  const [showPassword, setShowPassword] = useState(false)
  return <main data-theme={darkMode ? 'dark' : 'day'} className="login-layout reference-login">
    <div className="login-photo login-city-panel"><Suspense fallback={null}><LoginCity darkMode={darkMode} /></Suspense></div>
    <section className="login-panel"><div className="login-form-wrap">
      <div className="signin-brand"><img className="signin-logo" src={vridhiLogo} alt="Vridhi logo" /><div><strong className="app-wordmark" role="img" aria-label="VRIDHI" /><span>Constructions &amp; Designs</span></div></div>
      <h1>Login</h1>
      <form onSubmit={onSubmit}><input type="hidden" name="csrf" value={csrf} /><label>Username or email<input autoComplete="username" required value={identity} onChange={event => setIdentity(event.target.value)} placeholder="Username or email address" /></label><label>Password<div className="signin-password"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="Password" /><button type="button" className="icon-button" title={showPassword ? 'Hide password' : 'Show password'} aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>{error && <div className="form-error" role="alert">{error.message}</div>}<button className="button-primary login-submit" disabled={pending}>{pending ? 'Signing in...' : 'Sign in'}<ArrowUpRight size={16} /></button></form>
      <div className="login-footnote"><ShieldCheck size={15} />Secure workspace access</div>
    </div></section>
  </main>
}

export function ProjectChooser({ data, loading, onSelect, onCreate, canCreate }: { data?: Page<Project>; loading: boolean; onSelect: (id: string) => void; onCreate: () => void; canCreate: boolean }) {
  const [scope, setScope] = useState<'current' | 'archived'>('current')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [search, setSearch] = useState('')
  const listing = useQuery({ queryKey: ['projects', 'directory', scope, page, pageSize, search], queryFn: () => api.projectPage(scope, page, pageSize, search) })
  const projects = listing.data?.items || []
  const total = listing.data?.total || 0
  const count = (archived: boolean) => data?.items.filter(project => Boolean(project.archived_at) === archived).length || 0
  const groups = [
    { status: 'Planning', icon: '◷' },
    { status: 'Active', icon: '↗' },
    { status: 'On Hold', icon: 'Ⅱ' },
    { status: 'Completed', icon: '✓' },
    { status: 'Cancelled', icon: '×' },
  ].filter(group => scope === 'current' || ARCHIVABLE_STATUSES.includes(group.status))
  return <><div className="page-heading"><div><h1>Projects Dashboard</h1><p>Select a project to open its dashboard and operational modules.</p></div>{scope === 'current' && <button className="button-primary" disabled={!canCreate} title={!canCreate ? 'Dashboard New Project permission is required' : undefined} onClick={onCreate}><span aria-hidden="true">＋</span>New project</button>}</div>
    <div className="cashbook-tabs project-directory-tabs" role="tablist" aria-label="Project archive scope">{(['current', 'archived'] as const).map(value => <button key={value} type="button" role="tab" aria-selected={scope === value} className={scope === value ? 'selected' : ''} onClick={() => { setScope(value); setPage(1) }}>{value === 'current' ? 'Current Projects' : 'Archived Projects'} ({count(value === 'archived')})</button>)}</div>
    <div className="project-directory-tools">
      <p className="project-directory-hint">{scope === 'archived' ? 'Archived projects are read-only. Their approved profit / loss remains in Company Cashbook.' : 'All non-archived projects, including On Hold, Completed and Cancelled.'}</p>
      <input aria-label="Search projects" placeholder="Search project name" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} />
    </div>
    <QueryError error={listing.error} onRetry={() => void listing.refetch()} />
    {loading || listing.isLoading ? <div className="loading-line" /> : <><PortfolioKpis projects={projects} counts={listing.data?.status_counts} archived={scope === 'archived'} /><div className="project-sections" role="tabpanel">{groups.map(group => {
    const entries = projects.filter(project => project.status === group.status)
    return <section className="portfolio-section" key={group.status}><h2 className="portfolio-heading"><span className={`portfolio-status-glyph ${statusClass(group.status)}`}>{group.icon}</span>{group.status}<span className="portfolio-count">{entries.length} project{entries.length === 1 ? '' : 's'} on this page</span></h2>{entries.length ? <div className="project-grid">{entries.map(project => <button className="project-card" key={project.id} onClick={() => onSelect(project.id)}><div className="project-card-top"><strong>{project.name}</strong><span className={`status-pill ${statusClass(project.status)}`}>{project.status}</span></div><p className="project-location">{project.location}{project.status === 'On Hold' && project.hold_reason ? ` · ${project.hold_reason}` : ''}</p><div className="project-card-metrics"><div><small>Contract</small><strong>{currency(project.contract_value, project.currency)}</strong></div><div><small>Actual cost</small><strong>{currency(project.actual_cost, project.currency)}</strong></div></div>{project.archived_at && <p className="project-archived-label">Archived · Read-only</p>}</button>)}</div> : <div className="portfolio-empty">No matching projects in this status on this page.</div>}</section>
  })}</div><div className="register-pagination"><label>Rows <select aria-label="Projects per page" value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(1) }}>{[10, 25, 50, 100].map(size => <option key={size}>{size}</option>)}</select></label><span>{total} projects · Page {page} of {Math.max(1, Math.ceil(total / pageSize))}</span><div><button className="button-secondary" disabled={page === 1 || listing.isFetching} onClick={() => setPage(page - 1)}>Previous</button><button className="button-secondary" disabled={page * pageSize >= total || listing.isFetching} onClick={() => setPage(page + 1)}>Next</button></div></div></>}</>
}

const ARCHIVABLE_STATUSES = ['Completed', 'Cancelled']

function PortfolioKpis({ projects, counts, archived = false }: { projects: Project[]; counts?: Record<string, number>; archived?: boolean }) {
  const total = counts ? Object.values(counts).reduce((sum, count) => sum + count, 0) : projects.length
  const statusCount = (status: string) => counts ? counts[status] || 0 : projects.filter(project => project.status === status).length
  const metrics = [
    { label: 'Total Projects', icon: BriefcaseBusiness, tone: 'blue', note: 'Selected tab and search, all pages', count: total },
    { label: 'Planning', icon: Clock3, tone: 'amber', note: 'Not yet active', count: statusCount('Planning') },
    { label: 'Active', icon: ArrowUpRight, tone: 'pine', note: 'Currently underway', count: statusCount('Active') },
    { label: 'On Hold', icon: Pause, tone: 'coral', note: 'Paused projects', count: statusCount('On Hold') },
    { label: 'Completed', icon: Check, tone: 'success', note: 'Closed projects', count: statusCount('Completed') },
    { label: 'Cancelled', icon: CircleX, tone: 'rose', note: 'Cancelled projects', count: statusCount('Cancelled') },
  ].filter(metric => !archived || metric.label === 'Total Projects' || ARCHIVABLE_STATUSES.includes(metric.label))
  return <div className={`portfolio-kpis portfolio-summary${archived ? ' archived-summary' : ''}`}>{metrics.map((metric, index) => {
    const share = total ? Math.round(metric.count / total * 100) : 0
    return <article className={`portfolio-kpi summary-tile summary-${metric.tone}`} key={metric.label}><div className="portfolio-kpi-top"><span>{metric.label}</span><i className={`portfolio-kpi-icon ${metric.tone}`}><metric.icon size={18} strokeWidth={1.8} /></i></div><div className="summary-value"><strong>{metric.count}</strong><span>{index === 0 ? 'projects' : `${share}%`}</span></div><small>{metric.note}</small><div className="summary-track" aria-hidden="true"><span style={{ width: `${share}%` }} /></div></article>
  })}</div>
}
