import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, Search, FilterX, CalendarRange } from 'lucide-react'
import { api, type ProjectAuditEntry } from '../../lib/api'
import { ExportHeader } from '../../components/ExportHeader'
import { EmptyState, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { userHistoryChanges } from './userHistory'
import { AuditDateRange } from '../../components/AuditDateRange'

export function AuditLog({ projectId, projectName, canExport }: { projectId: string; projectName?: string; canExport: boolean }) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [fromTime, setFromTime] = useState('')
  const [toTime, setToTime] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const filterContainer = useRef<HTMLDivElement>(null)
  const filterButton = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!filtersOpen) return
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !filterContainer.current?.contains(event.target)) setFiltersOpen(false)
    }
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setFiltersOpen(false); filterButton.current?.focus() }
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape) }
  }, [filtersOpen])
  const [printRows, setPrintRows] = useState<ProjectAuditEntry[] | null>(null)
  const startTime = fromTime && !Number.isNaN(new Date(fromTime).getTime()) ? new Date(fromTime).toISOString() : ''
  const endTime = toTime && !Number.isNaN(new Date(toTime).getTime()) ? new Date(toTime).toISOString() : ''
  const invalidRange = Boolean(startTime && endTime && startTime > endTime)
  const audit = useQuery({ queryKey: ['project', projectId, 'audit', page, pageSize, search, startTime, endTime], queryFn: () => api.projectAudit(projectId, page, pageSize, search, startTime, endTime), enabled: !invalidRange })
  const exportReport = useMutation({ mutationFn: async () => {
    await api.recordActivity(projectId, 'audit', 'export')
    const firstPage = await api.projectAudit(projectId, 1, 100, search, startTime, endTime)
    const rows = [...firstPage.items]
    for (let nextPage = 2; nextPage <= Math.ceil(firstPage.total / 100); nextPage += 1) {
      const result = await api.projectAudit(projectId, nextPage, 100, search, startTime, endTime)
      rows.push(...result.items)
    }
    setPrintRows(rows)
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
    await document.fonts.ready
    const originalTitle = document.title
    document.title = `${projectName || 'Project'} - Audit Log`
    const restore = () => { document.title = originalTitle; setPrintRows(null) }
    window.addEventListener('afterprint', restore, { once: true })
    try { window.print() } catch (error) { window.removeEventListener('afterprint', restore); restore(); throw error }
  }, onSuccess: () => { void audit.refetch() } })
  const total = audit.data?.total || 0
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return <div className="audit-log-view">
    <ExportHeader reportTitle="Project Audit Log" projectName={projectName} />
    <PageTitle eyebrow="PROJECT ACTIVITY" title="Audit Log" subtitle={projectName || ''} action={canExport && <div className="overview-actions"><button className="button-secondary export-report-action" disabled={exportReport.isPending || invalidRange} onClick={() => exportReport.mutate()}><Download size={15} />{exportReport.isPending ? 'Preparing report...' : 'Export report'}</button></div>} />
    <section className="panel table-panel"><PanelHeading title="Activity history" meta={`${printRows?.length ?? total} records · Newest first`} action={<div className="audit-time-filters">
        <div ref={filterContainer} className="audit-filter-control">
          <span className={`row-action-tooltip user-badge-tooltip${filtersOpen ? ' audit-filter-tooltip-hidden' : ''}`} data-tooltip={fromTime || toTime ? 'Time range filter active' : 'Filter by time range'}><button ref={filterButton} type="button" className={`icon-button audit-filter-trigger${fromTime || toTime ? ' active' : ''}`} aria-label="Filter by time range" aria-expanded={filtersOpen} aria-controls="audit-time-range" onClick={() => setFiltersOpen(previous => !previous)}><CalendarRange size={17} />{(fromTime || toTime) && <span className="audit-filter-indicator" />}</button></span>
          {filtersOpen && <div id="audit-time-range" className="audit-filter-popover" role="group" aria-label="Audit time range">
            <AuditDateRange from={fromTime} to={toTime} onApply={(from, to) => { setFromTime(from); setToTime(to); setPage(1) }} onClose={() => { setFiltersOpen(false); filterButton.current?.focus() }} />
          </div>}
        </div>
        <span className="row-action-tooltip user-badge-tooltip" data-tooltip="Clear audit filters"><button type="button" className="icon-button" aria-label="Clear audit filters" disabled={!fromTime && !toTime && !search} onClick={() => { setFromTime(''); setToTime(''); setSearch(''); setPage(1) }}><FilterX size={17} /></button></span>
        <div className="search-wrap"><Search size={15} /><input aria-label="Search audit log" placeholder="Search username or activity" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} /></div>
      </div>} />
      {invalidRange && <div className="form-error" role="alert">From date and time must be before To date and time.</div>}
      {printRows && <p className="audit-report-filters">Period: {fromTime ? new Date(fromTime).toLocaleString('en-IN') : 'Beginning'} to {toTime ? new Date(toTime).toLocaleString('en-IN') : 'Present'}{search && ` · Search: ${search}`}</p>}
      <div className="table-scroll"><table className="data-table"><thead><tr><th>Username</th><th>Date and time</th><th>User activity</th><th>Record</th><th>Details</th><th>Reference</th></tr></thead><tbody>
        {!printRows && audit.isLoading ? <tr><td colSpan={6}><div className="loading-line" /></td></tr> : (printRows || audit.data?.items || []).length ? (printRows || audit.data?.items || []).map(entry => <tr key={entry.id}><td><strong>{entry.username}</strong><div className="muted-cell">{entry.name}</div></td><td>{new Date(entry.occurred_at).toLocaleString('en-IN')}</td><td>{entry.activity}</td><td>{entry.record_type}</td><td>{entry.action.startsWith('visit_') ? 'Page opened' : entry.action.startsWith('export_') ? 'Export requested; browser save/print completion is not available.' : entry.details ? <details open={printRows !== null || undefined}><summary>View changes</summary><ul className="user-history-details">{userHistoryChanges(entry.action, entry.details).map((change, index) => <li key={index}>{change}</li>)}</ul></details> : 'Detailed changes were not recorded'}<div className="muted-cell">Audit ID: {entry.id}</div></td><td>{entry.record_id || 'None'}</td></tr>) : <tr><td colSpan={6}><EmptyState title="No matching activities" note="" /></td></tr>}
      </tbody></table></div>
      <QueryError error={audit.error || exportReport.error} onRetry={() => void audit.refetch()} />
      <div className="register-pagination"><label>Rows per page <select aria-label="Audit rows per page" value={pageSize} onChange={event => { setPageSize(Number(event.target.value)); setPage(1) }}>{[10, 20, 50, 100].map(size => <option key={size} value={size}>{size}</option>)}</select></label><span>Page {page} of {pages}</span><div className="row-actions"><button className="icon-button" title="Previous audit page" aria-label="Previous audit page" disabled={page <= 1 || audit.isFetching} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button><button className="icon-button" title="Next audit page" aria-label="Next audit page" disabled={page >= pages || audit.isFetching} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button></div></div>
    </section>
  </div>
}