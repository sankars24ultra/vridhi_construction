import { useRef, useState, type ClipboardEvent, type DragEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownLeft, ArrowUpRight, CircleDollarSign, Clock3, Download, FileText, Plus, Settings2 } from 'lucide-react'
import { api, type Project, type PurchaseOrder } from '../../lib/api'
import { currency, statusClass, todayISO } from '../../lib/format'
import { EmptyState, FormActions, Kpi, MutationError, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { ModalFrame } from '../../components/ModalFrame'
import type { View } from '../../lib/types'
import { OrderTable } from '../procurement/Procurement'
import { CostBreakdownDonut } from './CostBreakdownDonut'
import { CompletionGauge } from './CompletionGauge'
import { ExportHeader } from '../../components/ExportHeader'

export function Overview({ project, projectId, canWrite = true, canQuickEntry = canWrite, canUploadPlan = canWrite, canUpdateStatus = canWrite, canExport = true, onNavigate, onNewPO, onRecordReceipt }: { project?: Project; projectId: string; canWrite?: boolean; canQuickEntry?: boolean; canUploadPlan?: boolean; canUpdateStatus?: boolean; canExport?: boolean; onNavigate: (view: View) => void; onNewPO: () => void; onRecordReceipt: () => void }) {
  const queryClient = useQueryClient()
  const [printOrders, setPrintOrders] = useState<PurchaseOrder[] | null>(null)
  const [editingStatus, setEditingStatus] = useState(false)
  const [uploadingPlan, setUploadingPlan] = useState(false)
  const canReadProcurement = project?.permissions?.procurement?.access === 'allow'
  const canReadCashFlow = project?.permissions?.cashflow?.access === 'allow'
  const receiptPermission = project?.permissions?.cashflow
  const canRecordReceipt = canReadCashFlow && (receiptPermission?.write.mode === 'all' || receiptPermission?.write.actions.record_receipt === true)
  const valueHistory = useQuery({ queryKey: ['project', projectId, 'value-history'], queryFn: () => api.valueHistory(projectId) })
  const documents = useQuery({ queryKey: ['project', projectId, 'documents'], queryFn: () => api.documents(projectId) })
  const dashboard = useQuery({ queryKey: ['project', projectId, 'dashboard'], queryFn: () => api.dashboard(projectId) })
  const cashFlow = useQuery({ queryKey: ['project', projectId, 'cash-flow'], queryFn: () => api.cashFlow(projectId), enabled: canReadCashFlow })
  const statuses = useQuery({ queryKey: ['project', projectId, 'status-history'], queryFn: () => api.statusHistory(projectId) })
  const orders = useQuery({ queryKey: ['project', projectId, 'purchase-orders', { page: 1, page_size: 4 }], queryFn: () => api.purchaseOrders(projectId, 1, 4), enabled: canReadProcurement })
  const exportQueries = [dashboard, documents, statuses, valueHistory, ...(canReadCashFlow ? [cashFlow] : []), ...(canReadProcurement ? [orders] : [])]
  const dash = dashboard.data
  const actual = Number(dash?.actual_cost || 0)
  const contractValue = Number(dash?.approved_contract_value || 0)
  const remainingValue = Math.max(0, contractValue - actual)
  const overrun = Math.max(0, actual - contractValue)
  const spentPercent = contractValue > 0 ? Math.min(100, actual / contractValue * 100) : actual > 0 ? 100 : 0
  const profitAmount = contractValue - actual
  const receivedAmount = canReadCashFlow ? Number(cashFlow.data?.cash_received || 0) : undefined
  const billedOutstanding = canReadCashFlow ? Number(cashFlow.data?.outstanding_invoices || 0) : undefined
  const exportReport = async () => {
    if (!dash) return
    try {
      const allOrders: PurchaseOrder[] = []
      if (canReadProcurement) {
        const firstPage = await api.purchaseOrders(projectId, 1, 200)
        allOrders.push(...firstPage.items)
        for (let page = 2; page <= Math.ceil(firstPage.total / 200); page += 1) {
          const nextPage = await api.purchaseOrders(projectId, page, 200)
          allOrders.push(...nextPage.items)
        }
      }
      setPrintOrders(allOrders)
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      await document.fonts.ready
      const originalTitle = document.title
      document.title = `${project?.name || 'Project'} - Overview Report`
      window.addEventListener('afterprint', () => { document.title = originalTitle; setPrintOrders(null) }, { once: true })
      await api.recordActivity(projectId, 'overview', 'export')
      window.print()
    } catch {
      setPrintOrders(null)
      if (canReadProcurement) await orders.refetch()
    }
  }
  return <div className="overview-sections">
    <PageTitle eyebrow="PROJECT OVERVIEW" title={project?.name || 'Project overview'} subtitle={`${project?.location || ''} · Updated ${dash?.as_of ? new Date(dash.as_of).toLocaleDateString('en-IN') : 'today'}`} action={<div className="overview-actions">{canUpdateStatus && <button className="button-secondary project-status-action" onClick={() => setEditingStatus(true)} disabled={!project?.eligible_statuses?.length}><Settings2 size={14} />Project status</button>}{canExport && <button className="button-secondary export-report-action" onClick={exportReport} disabled={!dash || exportQueries.some(query => query.isFetching || query.isError)}><Download size={14} />Export report</button>}{canQuickEntry && canReadProcurement && <button className="button-primary quick-entry-action" onClick={onNewPO}><Plus size={15} />Quick entry</button>}</div>} />
    <ExportHeader reportTitle="Project Overview Report" projectName={project?.name} projectLocation={project?.location} asOf={dash?.as_of} />
    <div className="kpi-grid five"><Kpi label="Contract value" value={currency(dash?.approved_contract_value, dash?.currency)} note="Original and approved changes" icon={<FileText size={17} />} loading={dashboard.isLoading} /><Kpi label="Cash received" value={canReadCashFlow ? currency(receivedAmount, dash?.currency) : ''} note={canReadCashFlow ? cashFlow.isError ? 'Receipt data unavailable' : `${currency(billedOutstanding, dash?.currency)} billed outstanding` : ''} icon={<CircleDollarSign size={17} />} loading={canReadCashFlow && cashFlow.isLoading} /><Kpi label="Actual cost" value={currency(dash?.actual_cost, dash?.currency)} note={`Labor ${currency(dash?.cost_breakdown.find(item => item.category === 'Labor')?.amount || '0', dash?.currency)} (contract ${currency(dash?.labor_cost_breakdown?.contract_claims || '0', dash?.currency)} · direct ${currency(dash?.labor_cost_breakdown?.direct_workers || '0', dash?.currency)}) · ${contractValue ? Math.round(actual / contractValue * 100) : 0}% of contract`} icon={<ArrowDownLeft size={17} />} loading={dashboard.isLoading} /><Kpi label="Open commitments" value={currency(dash?.open_commitments, dash?.currency)} note="Outstanding procurement" icon={<Clock3 size={17} />} loading={dashboard.isLoading} /><Kpi label="Projected margin" value={`${dash?.margin_percent || '0'}%`} note="Based on current records" icon={<ArrowUpRight size={17} />} loading={dashboard.isLoading} /></div>
    <QueryError error={dashboard.error} onRetry={() => void dashboard.refetch()} />
    <div className="overview-grid">
      <section className="panel financial-position-panel"><PanelHeading title="Project financial position" meta="Approved contract value, recorded costs, and client billing" action={canRecordReceipt && <button className="text-action" onClick={onRecordReceipt}>Record client receipt</button>} /><div className="financial-position-content"><div className="financial-position-total"><div><span>Total project amount</span><small>Approved contract value</small></div><strong>{currency(contractValue, dash?.currency)}</strong></div><div className="financial-position-track" role="img" aria-label={`${currency(actual, dash?.currency)} spent of ${currency(contractValue, dash?.currency)} approved contract value`}><span className="financial-position-spent" style={{ width: `${spentPercent}%` }} /><span className="financial-position-remaining" style={{ width: `${Math.max(0, 100 - spentPercent)}%` }} /></div><div className="financial-position-legend"><span><i className="financial-spent-key" />Recorded spend<strong>{currency(actual, dash?.currency)}</strong></span><span><i className="financial-remaining-key" />Contract remaining after spend<strong>{currency(remainingValue, dash?.currency)}</strong></span></div>{overrun > 0 && <div className="financial-position-overrun" role="status">Recorded cost exceeds contract value by <strong>{currency(overrun, dash?.currency)}</strong>.</div>}<div className="financial-position-metrics"><div className="financial-position-metric receipts"><span>Received from client</span><strong>{canReadCashFlow ? cashFlow.isLoading ? 'Loading…' : currency(receivedAmount, dash?.currency) : ''}</strong><small>{canReadCashFlow ? cashFlow.isError ? 'Receipt data unavailable' : `${currency(billedOutstanding, dash?.currency)} billed outstanding` : ''}</small></div><div className="financial-position-metric"><span>Projected profit</span><strong style={{ color: profitAmount >= 0 ? '#287454' : '#bd6245' }}>{dashboard.isLoading ? 'Loading…' : currency(profitAmount, dash?.currency)}</strong><small>{dash?.margin_percent || '0'}% margin · contract less recorded spend</small></div></div><div className="financial-position-commitments"><div><span>Open purchase-order commitments</span><small>Shown separately; not added again to recorded spend</small></div><strong>{currency(dash?.open_commitments, dash?.currency)}</strong></div><QueryError error={canReadCashFlow ? cashFlow.error : null} onRetry={() => void cashFlow.refetch()} /></div></section>
      <section className="panel completion-panel"><PanelHeading title="Completion" meta="Project progress based on actual spend vs approved contract" /><CompletionGauge value={Math.round(spentPercent)} /></section>
      <section className="panel cost-breakdown-panel"><PanelHeading title="Cost breakdown" meta="Actual costs only · unrecorded categories are not estimated" /><CostBreakdownDonut dash={dash} /></section>
    </div>
    <section className="panel table-panel"><PanelHeading title={printOrders ? 'Purchase order register' : 'Recent purchase orders'} meta={printOrders ? `${printOrders.length} purchase orders · order date, newest first` : 'Latest procurement activity for this project'} action={canReadProcurement && !printOrders && <button className="button-secondary" onClick={() => onNavigate('procurement')}>View all <ArrowUpRight size={14} /></button>} /><OrderTable orders={canReadProcurement ? printOrders || orders.data?.items || [] : []} loading={canReadProcurement && !printOrders && orders.isLoading} compact /><QueryError error={canReadProcurement && !printOrders ? orders.error : null} onRetry={() => void orders.refetch()} /></section>
    <section className="panel table-panel"><PanelHeading title="Plan documents" meta="Approval documents and updated plans · newest first" action={canUploadPlan && project && ['Planning', 'Active', 'On Hold'].includes(project.status) && <button className="button-primary" onClick={() => setUploadingPlan(true)}><Plus size={15} />Upload plan document</button>} /><div className="table-scroll"><table className="data-table"><thead><tr><th>Document</th><th>Uploaded</th><th>Uploaded by</th><th className="numeric">Current value (₹)</th><th className="numeric">New estimate (₹)</th><th>Comment</th><th>File</th></tr></thead><tbody>{documents.isLoading ? <tr><td colSpan={7}><div className="loading-line" /></td></tr> : documents.data?.items.length ? documents.data.items.map(file => <tr key={file.id}><td><strong>{file.filename}</strong><div className="muted-cell">{file.content_type}</div></td><td>{new Date(file.uploaded_at).toLocaleString('en-IN')}</td><td>{file.uploaded_by}</td><td className="numeric">{file.current_value != null ? currency(file.current_value, project?.currency) : 'Not recorded'}</td><td className="numeric">{file.new_estimate != null ? currency(file.new_estimate, project?.currency) : 'Not recorded'}</td><td className="overview-comment">{file.comment || 'No comment'}</td><td><span className="row-action-tooltip" data-tooltip="Download"><a className="icon-button" href={`/api/v1/projects/${projectId}/documents/${file.id}/file`} download title="Download" aria-label={`Download ${file.filename}`}><Download size={15} /></a></span></td></tr>) : <tr><td colSpan={7}><EmptyState title="No plan documents have been uploaded" note="" /></td></tr>}</tbody></table></div><QueryError error={documents.error} onRetry={() => void documents.refetch()} /></section>
    <section className="panel table-panel"><PanelHeading title="Project value history" meta="Estimate changes from uploaded plans · newest first" /><div className="table-scroll"><table className="data-table"><thead><tr><th>Change date</th><th>Existing value</th><th>New estimate</th><th>Changed by</th><th>Plan document / comment</th></tr></thead><tbody>{valueHistory.data?.items.length ? valueHistory.data.items.map(entry => <tr key={entry.id}><td>{new Date(entry.changed_at).toLocaleString('en-IN')}</td><td>{currency(entry.previous_value, dash?.currency)}</td><td>{currency(entry.new_value, dash?.currency)}</td><td>{entry.changed_by}</td><td><strong>{entry.filename}</strong><div className="overview-comment">{entry.comment}</div></td></tr>) : <tr><td colSpan={5}><EmptyState title={valueHistory.isLoading ? 'Loading value history...' : 'No plan-based estimate changes recorded'} note="" /></td></tr>}</tbody></table></div><QueryError error={valueHistory.error} onRetry={() => void valueHistory.refetch()} /></section>
    <section className="panel table-panel overview-status"><PanelHeading title="Project status" meta="Status changes and user comments · newest first" action={canUpdateStatus && <button className="button-secondary" onClick={() => setEditingStatus(true)} disabled={!project?.eligible_statuses?.length}><Settings2 size={14} />Update status</button>} /><div className="overview-status-body"><div className="overview-current-status"><span className={`status-dot ${statusClass(project?.status || 'Planning')}`} /><span>Current status: <strong>{project?.status}</strong></span></div></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Current status</th><th>Status before</th><th>Date it changed</th><th>Who updated</th><th>Comments</th></tr></thead><tbody>{statuses.isLoading ? <tr><td colSpan={5}><div className="loading-line" /></td></tr> : statuses.data?.items.length ? statuses.data.items.map(entry => <tr key={entry.id}><td><span className={`status-pill ${statusClass(entry.new_status)}`}>{entry.new_status}</span></td><td>{entry.previous_status || 'Not recorded'}</td><td>{new Date(entry.occurred_at).toLocaleString('en-IN')}</td><td>{entry.actor.name}</td><td className="overview-comment">{entry.comment || 'No comment'}</td></tr>) : <tr><td colSpan={5}><EmptyState title="No status comments recorded yet" note="" /></td></tr>}</tbody></table></div><QueryError error={statuses.error} onRetry={() => void statuses.refetch()} /></section>
    {editingStatus && project && <ModalFrame title="Update project status" onClose={() => setEditingStatus(false)}><ProjectStatusForm key={project.id} project={project} onCancel={() => setEditingStatus(false)} onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ['projects'] }); await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'status-history'] }); setEditingStatus(false) }} /></ModalFrame>}
    {uploadingPlan && dash && <ModalFrame title="Upload plan document" dismissOnBackdrop={false} onClose={() => setUploadingPlan(false)}><PlanUploadForm key={projectId} projectId={projectId} currentValue={dash.approved_contract_value} onCancel={() => setUploadingPlan(false)} onSaved={async () => { await queryClient.invalidateQueries({ queryKey: ['project', projectId] }); await queryClient.invalidateQueries({ queryKey: ['projects'] }); setUploadingPlan(false) }} /></ModalFrame>}
  </div>
}

export function ProjectStatusForm({ project, onCancel, onSaved }: { project: Project; onCancel: () => void; onSaved: () => void }) {
  const eligibleStatuses = project.eligible_statuses || []
  const [status, setStatus] = useState(eligibleStatuses[0] || '')
  const [comment, setComment] = useState('')
  const [holdReason, setHoldReason] = useState('')
  const [confirmComplete, setConfirmComplete] = useState(false)
  const mutation = useMutation({ mutationFn: () => api.updateProjectStatus(project, { status, comment, hold_reason: holdReason, confirm_complete: confirmComplete }), onSuccess: onSaved })
  return <form className="form-grid" onSubmit={event => { event.preventDefault(); if (eligibleStatuses.includes(status)) mutation.mutate() }}><div className="full overview-current-status">Current status: <strong>{project.status}</strong></div><label className="field full">Project status<select required value={status} onChange={event => setStatus(event.target.value)}>{eligibleStatuses.map(value => <option key={value}>{value}</option>)}</select></label><label className="field full">Comment<textarea required value={comment} onChange={event => setComment(event.target.value)} /></label>{status === 'On Hold' && <label className="field full">Hold reason<input required value={holdReason} onChange={event => setHoldReason(event.target.value)} /></label>}{status === 'Completed' && <label className="full overview-confirm"><input required type="checkbox" checked={confirmComplete} onChange={event => setConfirmComplete(event.target.checked)} />Confirm project completion</label>}<MutationError error={mutation.error} /><FormActions onCancel={onCancel} busy={mutation.isPending || !eligibleStatuses.length} submit="Update status" /></form>
}

export function PlanUploadForm({ projectId, currentValue, onCancel, onSaved }: { projectId: string; currentValue: string; onCancel: () => void; onSaved: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [newEstimate, setNewEstimate] = useState('')
  const [comment, setComment] = useState('')
  const [fileError, setFileError] = useState('')
  const mutation = useMutation({ mutationFn: () => api.uploadPlan(projectId, file!, comment, currentValue, newEstimate), onSuccess: onSaved })
  const acceptFile = (candidate?: File) => {
    if (!candidate) return
    if (!/\.(pdf|png|jpe?g|docx)$/i.test(candidate.name)) { setFileError('Choose a PDF, PNG, JPG, or DOCX file.'); return }
    if (!candidate.size || candidate.size > 10 * 1024 * 1024) { setFileError('Choose a non-empty file no larger than 10 MB.'); return }
    setFileError('')
    setFile(candidate)
  }
  return <form className="form-grid" onSubmit={event => { event.preventDefault(); if (!file) { setFileError('Choose a plan document.'); return } mutation.mutate() }}>
    <label className="field">Current project value (₹)<input disabled value={new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(Number(currentValue))} /></label>
    <label className="field">New estimated value (₹)<input required type="number" min="0" step="0.01" value={newEstimate} disabled={mutation.isPending} onChange={event => setNewEstimate(event.target.value)} placeholder="Enter revised estimate" /></label>
    <label className="field full">Plan approval or updated plan<div className="native-file-row" tabIndex={0} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); acceptFile(event.dataTransfer.files[0]) }} onPaste={event => { const image = Array.from(event.clipboardData.items).find(item => item.type.startsWith('image/'))?.getAsFile(); if (image) { event.preventDefault(); acceptFile(new File([image], `pasted-plan-${Date.now()}.${image.type === 'image/jpeg' ? 'jpg' : 'png'}`, { type: image.type })) } }}><input type="file" accept=".pdf,.png,.jpg,.jpeg,.docx" disabled={mutation.isPending} onChange={event => acceptFile(event.target.files?.[0])} /></div>{file && <small className="field-hint">{file.name}</small>}<small className="field-hint">PDF, PNG, JPG, or DOCX · max 10 MB</small></label>
    <label className="field full">Comment (optional)<textarea maxLength={500} value={comment} disabled={mutation.isPending} onChange={event => setComment(event.target.value)} placeholder="Describe this approval or plan update" /></label>
    {fileError && <div className="form-error full" role="alert">{fileError}</div>}
    <MutationError error={mutation.error} /><FormActions onCancel={onCancel} busy={mutation.isPending} submit="Upload document" />
  </form>
}

export function ProjectForm({ csrf, onSaved, onCancel }: { csrf: string; onSaved: (project: Project) => void; onCancel: () => void }) {
  const [form, setForm] = useState({ name: '', location: '', baseline_budget: '', contract_value: '', start_date: todayISO, status: 'Planning' as 'Planning' | 'Active', plan_comment: '' })
  const [planDocument, setPlanDocument] = useState<File | null>(null)
  const [fileError, setFileError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const mutation = useMutation({ mutationFn: () => api.createProject({ ...form, plan_document: planDocument }, csrf), onSuccess: onSaved })
  const acceptFile = (file?: File) => {
    if (!file) return
    const allowed = /\.(pdf|png|jpe?g|docx)$/i.test(file.name)
    if (!allowed) { setFileError('Choose a PDF, PNG, JPG, or DOCX file.'); return }
    if (file.size > 10 * 1024 * 1024) { setFileError('The plan file must be 10 MB or smaller.'); return }
    setFileError('')
    setPlanDocument(file)
  }
  const handlePaste = (event: ClipboardEvent<HTMLDivElement>) => {
    const image = Array.from(event.clipboardData.items).find(item => item.type.startsWith('image/'))
    const blob = image?.getAsFile()
    if (!blob) return
    event.preventDefault()
    const extension = blob.type === 'image/jpeg' ? 'jpg' : blob.type.split('/')[1] || 'png'
    acceptFile(new File([blob], `pasted-plan-${Date.now()}.${extension}`, { type: blob.type }))
  }
  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    acceptFile(event.dataTransfer.files[0])
  }
  return <form className="form-grid" onSubmit={event => { event.preventDefault(); mutation.mutate() }}>
    <label className="field full">Project name<input required maxLength={160} value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="e.g. Riverside Medical Center" /></label>
    <label className="field full">Location<input required value={form.location} onChange={event => setForm({ ...form, location: event.target.value })} placeholder="City, state or region" /></label>
    <label className="field">Approved budget (₹)<input required type="number" min="0" step="0.01" value={form.baseline_budget} onChange={event => setForm({ ...form, baseline_budget: event.target.value })} /></label>
    <label className="field">Contract value (₹)<input required type="number" min="0" step="0.01" value={form.contract_value} onChange={event => setForm({ ...form, contract_value: event.target.value })} /></label>
    <label className="field">Start date<input required type="date" value={form.start_date} onChange={event => setForm({ ...form, start_date: event.target.value })} /></label>
    <label className="field">Project status<select value={form.status} onChange={event => setForm({ ...form, status: event.target.value as 'Planning' | 'Active' })}><option value="Planning">Planning</option><option value="Active">Active</option></select></label>
    <label className="field full">Initial plan approval document (optional)<div className="native-file-row" tabIndex={0} onPaste={handlePaste} onDragOver={event => event.preventDefault()} onDrop={handleDrop} aria-label="Choose, paste, or drop an initial plan document"><input ref={fileInput} type="file" accept=".pdf,.png,.jpg,.jpeg,.docx" onChange={event => acceptFile(event.target.files?.[0])} />{planDocument && <span className="selected-file-name">{planDocument.name} · {(planDocument.size / (1024 * 1024)).toFixed(2)} MB</span>}</div><small className="field-hint">PDF, PNG, JPG, or DOCX · max 10 MB · paste an image or drop a file here</small></label>
    {fileError && <div className="form-error full">{fileError}</div>}
    <label className="field full">Document comment<textarea maxLength={500} value={form.plan_comment} onChange={event => setForm({ ...form, plan_comment: event.target.value })} placeholder="Add a note about this approval document (optional)" /></label>
    <MutationError error={mutation.error} /><FormActions onCancel={onCancel} busy={mutation.isPending} submit="Create project" />
  </form>
}
