import { useState, type FormEvent } from 'react'
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
      <div className="signin-brand"><img className="signin-logo" src={vridhiLogo} alt="Vridhi logo" /><div><strong>Vridhi</strong><span>Constructions &amp; Designs</span></div></div>
      <h1>Login</h1>
      <form onSubmit={onSubmit}><input type="hidden" name="csrf" value={csrf} /><label>Username or email<input autoComplete="username" required value={identity} onChange={event => setIdentity(event.target.value)} placeholder="Username or email address" /></label><label>Password<div className="signin-password"><input type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="Password" /><button type="button" className="icon-button" title={showPassword ? 'Hide password' : 'Show password'} aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>{error && <div className="form-error" role="alert">{error.message}</div>}<button className="button-primary login-submit" disabled={pending}>{pending ? 'Signing in...' : 'Sign in'}<ArrowUpRight size={16} /></button></form>
      <div className="login-footnote"><ShieldCheck size={15} />Secure workspace access</div>
    </div></section>
  </main>
}

export function ProjectChooser({ data, loading, onSelect, onCreate }: { data?: Page<Project>; loading: boolean; onSelect: (id: string) => void; onCreate: () => void }) {
  const projects = data?.items || []
  const groups = [
    { status: 'Planning', icon: '◷' },
    { status: 'Active', icon: '↗' },
    { status: 'On Hold', icon: 'Ⅱ' },
    { status: 'Completed', icon: '✓' },
    { status: 'Cancelled', icon: '×' },
  ]
  return <><div className="page-heading"><div><h1>All Projects Dashboard</h1><p>Select a project to open its dashboard and operational modules.</p></div><button className="button-primary" onClick={onCreate}><span aria-hidden="true">＋</span>New project</button></div>{loading ? <div className="loading-line" /> : <><PortfolioKpis projects={projects} /><div className="project-sections">{groups.map(group => {
    const entries = projects.filter(project => project.status === group.status)
    return <section className="portfolio-section" key={group.status}><h2 className="portfolio-heading"><span className={`portfolio-status-glyph ${statusClass(group.status)}`}>{group.icon}</span>{group.status}<span className="portfolio-count">{entries.length} project{entries.length === 1 ? '' : 's'}</span></h2>{entries.length ? <div className="project-grid">{entries.map(project => <button className="project-card" key={project.id} onClick={() => onSelect(project.id)}><div className="project-card-top"><strong>{project.name}</strong><span className={`status-pill ${statusClass(project.status)}`}>{project.status}</span></div><p className="project-location">{project.location}{project.status === 'On Hold' && project.hold_reason ? ` · ${project.hold_reason}` : ''}</p><div className="project-card-metrics"><div><small>Contract</small><strong>{currency(project.contract_value, project.currency)}</strong></div><div><small>Actual cost</small><strong>{currency(project.actual_cost, project.currency)}</strong></div></div></button>)}</div> : <div className="portfolio-empty">No projects in this status.</div>}</section>
  })}</div></>}</>
}

function PortfolioKpis({ projects }: { projects: Project[] }) {
  const metrics = [
    { label: 'Total Projects', icon: BriefcaseBusiness, tone: 'blue', note: 'Across all statuses', count: projects.length },
    { label: 'Planning', icon: Clock3, tone: 'amber', note: 'Not yet active', count: projects.filter(project => project.status === 'Planning').length },
    { label: 'Active', icon: ArrowUpRight, tone: 'pine', note: 'Currently underway', count: projects.filter(project => project.status === 'Active').length },
    { label: 'On Hold', icon: Pause, tone: 'coral', note: 'Paused projects', count: projects.filter(project => project.status === 'On Hold').length },
    { label: 'Completed', icon: Check, tone: 'blue', note: 'Closed projects', count: projects.filter(project => project.status === 'Completed').length },
    { label: 'Cancelled', icon: CircleX, tone: 'rose', note: 'Cancelled projects', count: projects.filter(project => project.status === 'Cancelled').length },
  ]
  return <div className="portfolio-kpis portfolio-summary">{metrics.map((metric, index) => {
    const share = projects.length ? Math.round(metric.count / projects.length * 100) : 0
    return <article className={`portfolio-kpi summary-tile summary-${metric.tone}`} key={metric.label}><div className="portfolio-kpi-top"><span>{metric.label}</span><i className={`portfolio-kpi-icon ${metric.tone}`}><metric.icon size={18} strokeWidth={1.8} /></i></div><div className="summary-value"><strong>{metric.count}</strong><span>{index === 0 ? 'projects' : `${share}%`}</span></div><small>{metric.note}</small><div className="summary-track" aria-hidden="true"><span style={{ width: `${share}%` }} /></div></article>
  })}</div>
}
