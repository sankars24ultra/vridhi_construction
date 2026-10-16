import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowUpRight, Clock3, CircleDollarSign, Download, FileText, Plus } from 'lucide-react'
import { api, type Project } from '../../lib/api'
import { currency, dateLabel, todayISO } from '../../lib/format'
import { EmptyState, FormActions, Kpi, MutationError, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { ExportHeader } from '../../components/ExportHeader'

export function Billing({ project, projectId, onNew }: { project?: Project; projectId: string; onNew: () => void }) {
  const summary = useQuery({ queryKey: ['project', projectId, 'billing-summary'], queryFn: () => api.billingSummary(projectId) })
  const billings = useQuery({ queryKey: ['project', projectId, 'billings'], queryFn: () => api.billings(projectId) })
  const data = summary.data
  const exportReport = async () => {
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
    await document.fonts.ready
    const originalTitle = document.title
    document.title = `${project?.name || 'Project'} - Progress Billing Summary`
    window.addEventListener('afterprint', () => { document.title = originalTitle }, { once: true })
    window.print()
  }
  return <><PageTitle eyebrow="CLIENT REVENUE" title="Progress billing" subtitle="Applications, contract and client collections" action={<div className="overview-actions"><button className="button-secondary export-report-action" onClick={exportReport} disabled={summary.isFetching || summary.isError || billings.isFetching || billings.isError}><Download size={14} />Export report</button><button className="button-primary" onClick={onNew}><Plus size={16} />New application</button></div>} />
    <ExportHeader reportTitle="Progress Billing Summary" projectName={project?.name} projectLocation={project?.location} />
    <div className="kpi-grid four"><Kpi label="Approved contract" value={currency(data?.approved_contract_value, data?.currency)} note="Original plus approved changes" icon={<FileText size={17} />} loading={summary.isLoading} /><Kpi label="Billed to date" value={currency(data?.billed_work, data?.currency)} note="Submitted applications" icon={<ArrowUpRight size={17} />} loading={summary.isLoading} /><Kpi label="Retainage held" value={currency(data?.retainage_held, data?.currency)} note="Based on approved billings" icon={<Clock3 size={17} />} loading={summary.isLoading} /><Kpi label="Awaiting payment" value={currency(data?.outstanding_invoices, data?.currency)} note="Outstanding invoices" icon={<CircleDollarSign size={17} />} loading={summary.isLoading} /></div><section className="panel table-panel"><PanelHeading title="Billing applications" meta="Client-side applications and current due" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Application</th><th>Work completed</th><th>Submitted</th><th className="numeric">Current due</th><th>Status</th></tr></thead><tbody>{billings.isLoading ? <tr><td colSpan={5}><div className="loading-line" /></td></tr> : billings.data?.items.length ? billings.data.items.map(row => <tr key={row.id}><td className="strong-cell">{row.application_number}</td><td>{row.description}</td><td>{dateLabel(row.period_start)}</td><td className="numeric">{currency(row.net_billable, row.currency)}</td><td><span className="status-pill planning">{row.status}</span></td></tr>) : <tr><td colSpan={5}><EmptyState title="No billing applications" note="Submitted applications will appear here." /></td></tr>}</tbody></table></div><QueryError error={billings.error} onRetry={() => void billings.refetch()} /></section></>
}

export function BillingForm({ projectId, csrf, onSaved, onCancel }: { projectId: string; csrf: string; onSaved: () => void; onCancel: () => void }) { const [form, setForm] = useState({ description: '', submitted_date: todayISO, amount: '' }); const mutation = useMutation({ mutationFn: () => api.createBilling(projectId, form, csrf), onSuccess: onSaved }); return <form className="form-grid" onSubmit={event => { event.preventDefault(); mutation.mutate() }}><label className="field full">Work completed<input required value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} placeholder="Description of this application" /></label><label className="field">Submitted date<input required type="date" value={form.submitted_date} onChange={event => setForm({ ...form, submitted_date: event.target.value })} /></label><label className="field">Current due (₹)<input required type="number" min="0.01" step="0.01" value={form.amount} onChange={event => setForm({ ...form, amount: event.target.value })} /></label><div className="form-note full">This records a submitted application. Invoice issuance and approvals are separate planned workflows.</div><MutationError error={mutation.error} /><FormActions onCancel={onCancel} busy={mutation.isPending} submit="Submit application" /></form> }
