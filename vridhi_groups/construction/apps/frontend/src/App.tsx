import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Banknote, BriefcaseBusiness, CalendarDays, Check, ChevronDown, ClipboardList, HardHat, LayoutDashboard, LogOut, Package, Users, Wallet } from 'lucide-react'
import { api, type AuditModule, type PurchaseOrder } from './lib/api'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { Sun, Moon } from 'lucide-react'
import { statusClass } from './lib/format'
import { Login, ProjectChooser } from './features/projects/ProjectViews'
import { Overview, ProjectForm } from './features/projects/Overview'
import { Procurement, PaymentHistory, POForm, PaymentForm } from './features/procurement/Procurement'
import { Inventory } from './features/inventory/Inventory'
import { Billing, BillingForm } from './features/billing/Billing'
import { CashFlow, CashReceiptForm } from './features/billing/CashFlow'
import { LaborWages } from './features/labor/LaborWages'
import { UserDetails, UsersView } from './features/admin/UsersView'
import { AuditLog } from './features/admin/AuditLog'
import { ModalFrame } from './components/ModalFrame'
import { clearSessionNotes, SessionNotes } from './components/SessionNotes'
import type { View, Modal } from './lib/types'
import vridhiLogo from '../../../images/logo-transparent.png'

const workspaceLocationKey = 'vridhi-workspace-location'
const validViews: View[] = ['projects', 'dashboard', 'procurement', 'inventory', 'cash-flow', 'labor-wages', 'users', 'audit']

function readWorkspaceLocation(): { projectId: string; view: View } {
  try {
    const saved = JSON.parse(sessionStorage.getItem(workspaceLocationKey) || '{}') as { projectId?: unknown; view?: unknown }
    const projectId = typeof saved.projectId === 'string' ? saved.projectId : ''
    const view = validViews.includes(saved.view as View) ? saved.view as View : 'projects'
    return { projectId, view: view !== 'projects' && view !== 'users' && !projectId ? 'projects' : view }
  } catch {
    return { projectId: '', view: 'projects' }
  }
}

export default function App() {
  const queryClient = useQueryClient()
  const [loginCsrf, setLoginCsrf] = useState('')
  const [identity, setIdentity] = useState('')
  const [password, setPassword] = useState('')
  const [initialLocation] = useState(readWorkspaceLocation)
  const [selectedProjectId, setSelectedProjectId] = useState(initialLocation.projectId)
  const [view, setView] = useState<View>(initialLocation.view)
  const [projectMenuOpen, setProjectMenuOpen] = useState(false)
  const [myDetailsOpen, setMyDetailsOpen] = useState(false)
  const [currentTime, setCurrentTime] = useState(() => new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [darkMode, setDarkMode] = useState(() => {
    try { return localStorage.getItem('vridhi-color-mode') === 'dark' } catch { return false }
  })
  useEffect(() => {
    try { localStorage.setItem('vridhi-color-mode', darkMode ? 'dark' : 'day') } catch { return }
  }, [darkMode])
  useEffect(() => {
    try { sessionStorage.setItem(workspaceLocationKey, JSON.stringify({ projectId: selectedProjectId, view })) } catch { return }
  }, [selectedProjectId, view])
  const [menuTooltip, setMenuTooltip] = useState<{ label: string; left: number; top: number } | null>(null)
  const showMenuTooltip = (target: EventTarget | null) => {
    const button = target instanceof Element ? target.closest<HTMLButtonElement>('.nav-item') : null
    if (!sidebarCollapsed || !button) { setMenuTooltip(null); return }
    const bounds = button.getBoundingClientRect()
    const mobile = window.innerWidth <= 760
    setMenuTooltip({ label: button.getAttribute('aria-label') || '', left: mobile ? Math.max(8, Math.min(bounds.left, window.innerWidth - 150)) : bounds.right + 10, top: mobile ? bounds.bottom + 8 : bounds.top + bounds.height / 2 })
  }
  useEffect(() => {
    if (!projectMenuOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setProjectMenuOpen(false)
    }
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Element && !event.target.closest('.workspace-project-picker')) setProjectMenuOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    document.addEventListener('pointerdown', closeOutside)
    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      document.removeEventListener('pointerdown', closeOutside)
    }
  }, [projectMenuOpen])
  const [modal, setModal] = useState<Modal>(null)
  const [selectedOrder, setSelectedOrder] = useState<PurchaseOrder | null>(null)
  const [historyOrder, setHistoryOrder] = useState<PurchaseOrder | null>(null)
  const [search, setSearch] = useState('')
  const [toast, setToast] = useState('')
  const bootstrap = useQuery({ queryKey: ['bootstrap'], queryFn: api.bootstrap, retry: false })
  const csrf = loginCsrf || bootstrap.data?.csrf_token || ''
  const me = useQuery({ queryKey: ['me'], queryFn: api.me, enabled: bootstrap.data?.authenticated === true, retry: false })
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects, enabled: !!me.data })
  const projectId = selectedProjectId
  const selectedProject = projects.data?.items.find(project => project.id === projectId)
  const canAccessUsers = me.data?.permissions?.users.read === true
  const canAccessAudit = me.data?.permissions?.audit?.read === true
  const lastActivity = useRef('')
  const canRead = (resource: string) => Boolean(selectedProject?.permissions?.[resource as keyof NonNullable<typeof selectedProject.permissions>]?.access === 'allow' || !projectId && me.data?.global_access && me.data.global_permissions?.[resource as keyof NonNullable<typeof me.data.global_permissions>]?.access === 'allow')
  const projectCanRead = canRead
  const projectCanWrite = (resource: string, action?: string) => {
    const permission = selectedProject?.permissions?.[resource as keyof NonNullable<typeof selectedProject.permissions>]
    if (permission?.access !== 'allow') return false
    return permission.write.mode === 'all' || !action || permission.write.actions[action] === true
  }
  const firstPermittedView: View = canRead('overview') ? 'dashboard' : canRead('procurement') ? 'procurement' : canRead('inventory') ? 'inventory' : canRead('cashflow') ? 'cash-flow' : canRead('labor') ? 'labor-wages' : 'projects'
  useEffect(() => {
    const modules: Partial<Record<View, AuditModule>> = { dashboard: 'overview', procurement: 'procurement', inventory: 'inventory', 'cash-flow': 'cashflow', 'labor-wages': 'labor', audit: 'audit' }
    const module = modules[view]
    if (!me.data || !projectId || !selectedProject || !module || !(module === 'audit' ? canAccessAudit : selectedProject.permissions?.[module]?.access === 'allow')) {
      lastActivity.current = ''
      return
    }
    const key = `${me.data.id}:${projectId}:${module}`
    if (lastActivity.current === key) return
    lastActivity.current = key
    void api.recordActivity(projectId, module, 'visit').catch(() => { if (lastActivity.current === key) lastActivity.current = '' })
  }, [view, projectId, selectedProject, me.data, canAccessAudit])
  useEffect(() => {
    if (view === 'dashboard' && !canRead('overview') || view === 'procurement' && !canRead('procurement') || view === 'inventory' && !canRead('inventory') || view === 'cash-flow' && !canRead('cashflow') || view === 'labor-wages' && !canRead('labor') || view === 'users' && projects.isSuccess && !canAccessUsers) setView(firstPermittedView)
  }, [view, me.data, firstPermittedView, projectId, selectedProject?.permissions, canAccessUsers, projects.isSuccess])
  const login = useMutation({ mutationFn: () => api.login(identity, password, csrf), onSuccess: async result => { setLoginCsrf(result.csrf_token); setPassword(''); queryClient.setQueryData(['me'], await api.me()); await queryClient.invalidateQueries({ queryKey: ['projects'] }) } })
  const logout = useMutation({ mutationFn: () => api.logout(csrf), onSuccess: async () => { if (me.data) clearSessionNotes(me.data.id); setLoginCsrf(''); setMyDetailsOpen(false); queryClient.clear(); setSelectedProjectId(''); setView('projects'); try { sessionStorage.removeItem(workspaceLocationKey) } catch { /* Storage can be unavailable in private contexts. */ } await queryClient.invalidateQueries({ queryKey: ['bootstrap'] }) } })
  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(''), 3200); return () => window.clearTimeout(timer) }, [toast])
  if (bootstrap.isLoading || (bootstrap.data?.authenticated && me.isLoading)) return <div className="boot-screen"><div className="brand-mark"><HardHat size={22} /></div><span>Opening Vridhi workspace</span></div>
  if (bootstrap.error && !csrf) return <div className="boot-screen"><div className="brand-mark"><HardHat size={22} /></div><strong>Local API is unavailable</strong><span>Start FastAPI and PostgreSQL, then reload this page.</span><button className="button-secondary" onClick={() => void bootstrap.refetch()}>Retry connection</button></div>
  if (!me.data) return <Login darkMode={darkMode} identity={identity} password={password} setIdentity={setIdentity} setPassword={setPassword} csrf={csrf} error={login.error} pending={login.isPending} onSubmit={event => { event.preventDefault(); login.mutate() }} />
  const nav: { id: View; label: string; icon: typeof LayoutDashboard }[] = [{ id: 'projects', label: 'Projects', icon: BriefcaseBusiness }]
  if (projectId && projectCanRead('overview')) nav.push({ id: 'dashboard', label: 'Overview', icon: LayoutDashboard })
  if (projectId && projectCanRead('procurement')) nav.push({ id: 'procurement', label: 'Procurement', icon: ClipboardList })
  if (projectId && projectCanRead('inventory')) nav.push({ id: 'inventory', label: 'Inventory', icon: Package })
  if (projectId && projectCanRead('cashflow')) nav.push({ id: 'cash-flow', label: 'Cash flow', icon: Banknote })
  if (projectId && projectCanRead('labor')) nav.push({ id: 'labor-wages', label: 'Labor and Wages', icon: Wallet })
  if (canAccessUsers) nav.push({ id: 'users', label: 'Users', icon: Users })
  if (projectId && canAccessAudit) nav.push({ id: 'audit', label: 'Audit Log', icon: ClipboardList })
  return <div data-theme={darkMode ? 'dark' : 'day'} className={`app-shell${sidebarCollapsed ? ' sidebar-collapsed' : ''}`} onMouseOver={event => showMenuTooltip(event.target)} onMouseOut={() => setMenuTooltip(null)} onFocus={event => showMenuTooltip(event.target)} onBlur={() => setMenuTooltip(null)} onClick={() => setMenuTooltip(null)}>
    {myDetailsOpen && <ModalFrame title="My Details" className="payment-history-modal user-details-modal" onClose={() => setMyDetailsOpen(false)}><UserDetails user={{ ...me.data, users_permissions: { access: me.data.permissions?.users.read ? 'allow' : 'block', read: { export_report: me.data.permissions?.users.export_report === true }, write: { mode: 'partial', actions: { add_user: me.data.permissions?.users.write === true, reset_password: me.data.permissions?.users.reset_password === true, activate_deactivate: me.data.permissions?.users.activate_deactivate === true, delete_user: me.data.permissions?.users.delete_user === true, history: me.data.permissions?.users.history === true } } }, assigned_project_ids: projects.data?.items.map(project => project.id), project_permissions: Object.fromEntries((projects.data?.items || []).map(project => [project.id, project.permissions || null])) }} projectNames={Object.fromEntries((projects.data?.items || []).map(project => [project.id, project.name]))} /></ModalFrame>}
    {sidebarCollapsed && menuTooltip && <div className="collapsed-menu-tooltip" role="tooltip" style={{ left: menuTooltip.left, top: menuTooltip.top }}>{menuTooltip.label}</div>}
    <button className="icon-button sidebar-toggle" title={sidebarCollapsed ? 'Expand left menu' : 'Collapse left menu'} aria-label={sidebarCollapsed ? 'Expand left menu' : 'Collapse left menu'} aria-expanded={!sidebarCollapsed} aria-controls="workspace-sidebar" onClick={() => setSidebarCollapsed(!sidebarCollapsed)}>{sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</button>
    <aside id="workspace-sidebar" className="sidebar"><a className="brand brand-with-logo" href="#projects" onClick={event => { event.preventDefault(); setView('projects') }}><img className="sidebar-logo" src={vridhiLogo} alt="Vridhi Constructions & Designs" /></a>{!!projects.data?.items.length && <><div className="sidebar-label">WORKSPACE</div><div className="workspace-project-picker"><button type="button" className="project-switcher" aria-label="Select project" aria-haspopup="listbox" aria-expanded={projectMenuOpen} onClick={() => setProjectMenuOpen(open => !open)}><BriefcaseBusiness size={16} /><span className="project-switcher-name">{selectedProject?.name || 'All projects'}</span><ChevronDown size={14} /></button>{projectMenuOpen && <div className="workspace-project-menu" role="listbox" aria-label="Available projects"><button type="button" role="option" aria-selected={!projectId} className={`workspace-project-option${!projectId ? ' selected' : ''}`} onClick={() => { setSelectedProjectId(''); setView('projects'); setProjectMenuOpen(false) }}><span className="workspace-project-name">All projects</span></button>{projects.data?.items.map(project => <button type="button" role="option" aria-selected={project.id === projectId} className={`workspace-project-option${project.id === projectId ? ' selected' : ''}`} key={project.id} onClick={() => { setSelectedProjectId(project.id); setView('dashboard'); setProjectMenuOpen(false) }}><span className="workspace-project-name">{project.name}</span><span className={`status-pill ${statusClass(project.status)}`}>{project.status}</span></button>)}</div>}</div>{selectedProject && <div className="active-project"><span className={`status-dot ${statusClass(selectedProject.status)}`} /> <span>{selectedProject.name}</span></div>}</>}<nav className="main-nav" aria-label="Workspace navigation">{projectId && <div className="sidebar-label">PROJECT</div>}{nav.map(item => <button key={item.id} title={item.label} aria-label={item.label} className={`nav-item ${view === item.id ? 'selected' : ''}`} onClick={() => setView(item.id)}><item.icon size={17} strokeWidth={1.8} /><span>{item.label}</span>{view === item.id && <span className="nav-indicator" />}</button>)}</nav><div className="sidebar-bottom"><div className="local-badge"><span /> LOCAL WORKSPACE</div><div className="profile"><span className="avatar">{me.data.name.split(' ').map(part => part[0]).join('').slice(0, 2)}</span><span className="profile-copy"><strong>{me.data.name}</strong></span></div></div></aside>
    <main className="main-area"><header className="topbar"><div className="breadcrumbs"><span>{view === 'users' ? 'Account' : 'Projects'}</span><span className="crumb-divider">/</span><strong>{view === 'users' ? 'Users' : view === 'projects' ? 'All projects' : selectedProject?.name || 'Workspace'}</strong></div><div className="topbar-right"><button className="theme-toggle" type="button" role="switch" aria-label="Dark mode" aria-checked={darkMode} title={darkMode ? 'Switch to day mode' : 'Switch to dark mode'} onClick={() => setDarkMode(!darkMode)}><Sun size={14} aria-hidden="true" /><Moon size={14} aria-hidden="true" /><span className="theme-toggle-thumb" /></button><span className="today"><CalendarDays size={15} />{currentTime.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}</span><time className="workspace-clock" dateTime={currentTime.toISOString()} title="Local time">{currentTime.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</time><span className="top-divider" /><SessionNotes key={me.data.id} userId={me.data.id} /><span className="row-action-tooltip user-badge-tooltip" data-tooltip="My Details"><button type="button" className="top-avatar my-details-trigger" aria-label="My Details" aria-haspopup="dialog" onClick={() => { setProjectMenuOpen(false); setMyDetailsOpen(true) }}>{me.data.name.split(' ').map(part => part[0]).join('').slice(0, 2)}</button></span><button className="button-secondary top-logout" onClick={() => logout.mutate()} disabled={logout.isPending}><LogOut size={15} />Sign out</button></div></header><div className="page-content">{view === 'projects' || (!projectId && view !== 'users') ? <ProjectChooser data={projects.data} loading={projects.isLoading} onSelect={id => { setSelectedProjectId(id); setView(firstPermittedView) }} onCreate={() => setModal('project')} /> : <>
      {view !== 'users' && selectedProject && <div className="project-context"><span className={`status-dot ${statusClass(selectedProject.status)}`} /><span>{selectedProject.location}</span><span className="context-divider">·</span><span>{selectedProject.status}</span></div>}
      {view === 'dashboard' && projectId && projectCanRead('overview') && <Overview project={selectedProject} projectId={projectId} canWrite={projectCanWrite('overview')} canQuickEntry={projectCanWrite('overview', 'quick_entry')} canUploadPlan={projectCanWrite('overview', 'upload_plan_document')} canUpdateStatus={projectCanWrite('overview', 'update_status')} canExport={selectedProject?.permissions?.overview?.read.export_report ?? true} onNavigate={setView} onNewPO={() => setModal('po')} onRecordReceipt={() => setModal('cash-receipt')} />}
      {view === 'procurement' && projectId && projectCanRead('procurement') && <Procurement project={selectedProject} projectId={projectId} canWrite={projectCanWrite('procurement')} canNew={projectCanWrite('procurement', 'new_purchase_order')} canEdit={projectCanWrite('procurement', 'new_purchase_order')} canPay={projectCanWrite('procurement', 'add_payment')} canExport={selectedProject?.permissions?.procurement?.read.export_report ?? true} search={search} setSearch={setSearch} onNew={() => { setSelectedOrder(null); setModal('po') }} onEdit={order => { setSelectedOrder(order); setModal('po') }} onPayment={order => { setSelectedOrder(order); setModal('payment') }} onHistory={order => setHistoryOrder(order)} />}
      {view === 'inventory' && projectId && projectCanRead('inventory') && <Inventory project={selectedProject} projectId={projectId} canWrite={projectCanWrite('inventory')} canReceive={projectCanWrite('inventory', 'receive_stock')} canUse={projectCanWrite('inventory', 'use_stock')} canExport={selectedProject?.permissions?.inventory?.read.export_report ?? true} search={search} setSearch={setSearch} csrf={csrf} />}
      {view === 'billing' && projectId && canRead('cashflow') && <Billing project={selectedProject} projectId={projectId} onNew={() => setModal('billing')} />}
      {view === 'cash-flow' && projectId && projectCanRead('cashflow') && <CashFlow project={selectedProject} projectId={projectId} canWrite={projectCanWrite('cashflow')} canRecordReceipt={projectCanWrite('cashflow', 'record_receipt')} canCreateApplication={projectCanWrite('cashflow', 'new_application')} canExport={selectedProject?.permissions?.cashflow?.read.export_report ?? true} onRecordReceipt={() => setModal('cash-receipt')} onNewApplication={() => setModal('billing')} />}
      {view === 'labor-wages' && projectId && projectCanRead('labor') && <LaborWages project={selectedProject} projectId={projectId} csrf={csrf} canWrite={projectCanWrite('labor')} projectPermissions={selectedProject?.permissions?.labor} />}
      {view === 'users' && canAccessUsers && <UsersView currentUser={me.data} projectId={projectId} csrf={csrf} />}
      {view === 'audit' && projectId && canAccessAudit && <AuditLog key={projectId} projectId={projectId} projectName={selectedProject?.name} canExport={me.data.permissions?.audit?.export_report === true} />}
    </>}</div></main>
    {modal && <ModalFrame title={{ project: 'Create project', po: selectedOrder ? `Edit ${selectedOrder.number}` : 'New purchase order', payment: 'Record vendor payment', billing: 'New billing application', 'cash-receipt': 'Record client receipt' }[modal]} dismissOnBackdrop={modal !== 'project'} onClose={() => setModal(null)}>
      {modal === 'project' && <ProjectForm csrf={csrf} onSaved={async project => { await queryClient.invalidateQueries({ queryKey: ['projects'] }); setSelectedProjectId(project.id); setView(firstPermittedView); setModal(null); setToast('Project created.') }} onCancel={() => setModal(null)} />}
      {modal === 'po' && projectId && <POForm projectId={projectId} csrf={csrf} order={selectedOrder} onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ['project', projectId] }); setModal(null); setToast('Purchase order saved.') }} onCancel={() => setModal(null)} />}
      {modal === 'payment' && projectId && selectedOrder && <PaymentForm projectId={projectId} csrf={csrf} order={selectedOrder} onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ['project', projectId] }); setModal(null); setToast('Payment recorded.') }} onCancel={() => setModal(null)} />}
      {modal === 'billing' && projectId && <BillingForm projectId={projectId} csrf={csrf} onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ['project', projectId] }); await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'cash-flow'] }); setModal(null); setToast('Billing application submitted.') }} onCancel={() => setModal(null)} />}
      {modal === 'cash-receipt' && projectId && <CashReceiptForm projectId={projectId} csrf={csrf} onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'cash-flow'] }); await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'billing-summary'] }); setModal(null); setToast('Client receipt recorded.') }} onCancel={() => setModal(null)} />}
    </ModalFrame>}{toast && <div className="toast"><Check size={17} />{toast}</div>}
    {historyOrder && <ModalFrame title={`${historyOrder.number} · Payment history`} className="payment-history-modal" onClose={() => setHistoryOrder(null)}><PaymentHistory projectId={projectId} order={historyOrder} /></ModalFrame>}
  </div>
}
