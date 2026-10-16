import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDownLeft, BadgeCheck, ChevronLeft, ChevronRight, Clock3, Download, History, MinusCircle, Package, Plus, Search, Truck } from 'lucide-react'
import { api, type InventoryRow, type Project } from '../../lib/api'
import { dateLabel, todayISO } from '../../lib/format'
import { EmptyState, FormActions, Kpi, MutationError, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { ExportHeader } from '../../components/ExportHeader'
import { ModalFrame } from '../../components/ModalFrame'

interface InventoryProps {
  project?: Project
  projectId: string
  canWrite: boolean
  canReceive?: boolean
  canUse?: boolean
  canExport?: boolean
  search: string
  setSearch: (value: string) => void
  csrf?: string
}

export function Inventory({ project, projectId, canWrite, canReceive = canWrite, canUse = canWrite, canExport = true, search, setSearch, csrf = '' }: InventoryProps) {
  const queryClient = useQueryClient()
  const [selectedMaterial, setSelectedMaterial] = useState<string>('All')
  const [receiveModalItem, setReceiveModalItem] = useState<InventoryRow['item'] | null>(null)
  const [issueModalItem, setIssueModalItem] = useState<InventoryRow | null>(null)
  const [historyTarget, setHistoryTarget] = useState<InventoryRow['item'] | null | 'ALL'>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [page, setPage] = useState<number>(1)
  const [pageSize, setPageSize] = useState<number>(20)

  const stock = useQuery({
    queryKey: ['project', projectId, 'inventory', { search }],
    queryFn: () => api.inventory(projectId)
  })
  const summary = useQuery({
    queryKey: ['project', projectId, 'inventory-summary'],
    queryFn: () => api.inventorySummary(projectId)
  })

  const allItems = stock.data?.items || []

  // Extract unique materials
  const materialsList = ['All', ...Array.from(new Set(allItems.map(row => row.item.name).filter(Boolean))).sort()]

  // Filter items by material and search
  const filteredRows = allItems.filter(row => {
    const matchesMaterial = selectedMaterial === 'All' || row.item.name === selectedMaterial
    const query = search.trim().toLowerCase()
    const matchesSearch = !query || `${row.item.name} ${row.item.sku} ${row.vendor_name || ''}`.toLowerCase().includes(query)
    return matchesMaterial && matchesSearch
  })

  const totalFiltered = filteredRows.length
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize))
  const currentPage = Math.min(page, totalPages)
  const paginatedRows = filteredRows.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  const exportReport = async () => {
    await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
    await document.fonts.ready
    const originalTitle = document.title
    document.title = `${project?.name || 'Project'} - Inventory Stock Register`
    window.addEventListener('afterprint', () => { document.title = originalTitle }, { once: true })
    await api.recordActivity(projectId, 'inventory', 'export')
    window.print()
  }

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3500)
  }

  const refreshInventory = async () => {
    await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'inventory'] })
    await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'inventory-summary'] })
    await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'inventory-transactions'] })
    await queryClient.invalidateQueries({ queryKey: ['project', projectId, 'dashboard'] })
  }

  // Calculate totals
  const totalReceived = allItems.reduce((acc, row) => acc + Number(row.received_quantity || 0), 0)
  const totalConsumed = allItems.reduce((acc, row) => acc + Number(row.consumed_quantity || 0), 0)
  const totalAvailable = allItems.reduce((acc, row) => acc + Number(row.available_quantity || 0), 0)
  const totalOpenOrder = allItems.reduce((acc, row) => acc + Number(row.open_order_quantity || 0), 0)

  return (
    <>
      <PageTitle
        eyebrow="MATERIALS &amp; ASSETS"
        title="Site inventory"
        subtitle="Procured materials, stock inward receipts, and daily site consumption"
        action={
          <div className="overview-actions">
            {canExport && <button className="button-secondary export-report-action" onClick={exportReport} disabled={stock.isFetching || stock.isError}>
              <Download size={14} />Export report
            </button>}
            <button className="button-secondary inventory-stock-ledger-action" onClick={() => setHistoryTarget('ALL')}>
              <History size={14} />Stock ledger
            </button>
            {canReceive && <button className="button-primary inventory-receive-action" onClick={() => setReceiveModalItem(allItems[0]?.item || null)} disabled={!allItems.length}>
              <Plus size={15} />Receive stock
            </button>}
          </div>
        }
      />

      <ExportHeader
        reportTitle="Site Inventory &amp; Stock Register"
        projectName={project?.name}
        projectLocation={project?.location}
      />

      {/* 5-Column Key Performance Indicator Cards in a Single Row */}
      <div className="kpi-grid five">
        <Kpi
          label="Catalog materials"
          value={String(summary.data?.catalog_item_count ?? allItems.length)}
          note="Linked from procurement"
          icon={<Package size={17} />}
          loading={summary.isLoading}
        />
        <Kpi
          label="Yet to receive"
          value={Math.round(totalOpenOrder).toLocaleString('en-IN')}
          note="Ordered via POs · pending delivery"
          icon={<Clock3 size={17} />}
          loading={stock.isLoading}
        />
        <Kpi
          label="Received at site"
          value={summary.data?.total_received_units ? Math.round(Number(summary.data.total_received_units)).toLocaleString('en-IN') : Math.round(totalReceived).toLocaleString('en-IN')}
          note="Total inward deliveries"
          icon={<Truck size={17} />}
          loading={summary.isLoading}
        />
        <Kpi
          label="Consumed on site"
          value={summary.data?.total_consumed_units ? Math.round(Number(summary.data.total_consumed_units)).toLocaleString('en-IN') : Math.round(totalConsumed).toLocaleString('en-IN')}
          note="Total logged daily usage"
          icon={<ArrowDownLeft size={17} />}
          loading={summary.isLoading}
        />
        <Kpi
          label="Remaining in stock"
          value={summary.data?.total_available_units ? Math.round(Number(summary.data.total_available_units)).toLocaleString('en-IN') : Math.round(totalAvailable).toLocaleString('en-IN')}
          note="Available on hand"
          icon={<BadgeCheck size={17} />}
          loading={summary.isLoading}
        />
      </div>

      <QueryError error={stock.error} onRetry={() => void stock.refetch()} />

      <section className="panel table-panel">
        <PanelHeading
          title="Project material register"
          meta={`${totalFiltered} material${totalFiltered === 1 ? '' : 's'} · ${allItems.length} total`}
          action={
            <div className="register-tools">
              {/* Material Filter Dropdown */}
              <div className="register-category-select-wrap">
                <label htmlFor="inventory-material-select" className="register-filter-hint">Material</label>
                <select
                  id="inventory-material-select"
                  className="register-category-select"
                  value={selectedMaterial}
                  onChange={event => setSelectedMaterial(event.target.value)}
                  aria-label="Filter materials by item name"
                >
                  <option value="All">All materials ({allItems.length})</option>
                  {materialsList.filter(m => m !== 'All').map(mat => {
                    const count = allItems.filter(r => r.item.name === mat).length
                    return (
                      <option key={mat} value={mat}>
                        {mat} ({count})
                      </option>
                    )
                  })}
                </select>
              </div>

              {/* Search Box */}
              <div className="search-wrap">
                <Search size={15} />
                <input
                  placeholder="Search material, SKU, vendor..."
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                />
              </div>
            </div>
          }
        />

        <div className="table-scroll">
          <table className="data-table inventory-register-table">
            <thead>
              <tr>
                <th>Material &amp; SKU</th>
                <th>Vendor</th>
                <th className="numeric">Ordered (PO)</th>
                <th className="numeric">Received (Inward)</th>
                <th className="numeric">Used (Outward)</th>
                <th className="numeric highlight-head">Remaining (On Hand)</th>
                <th>Stock Level</th>
                <th className="table-action-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {stock.isLoading ? (
                <tr>
                  <td colSpan={8}><div className="loading-line" /></td>
                </tr>
              ) : paginatedRows.length ? (
                paginatedRows.map(row => {
                  const ordered = Number(row.ordered_quantity || 0)
                  const received = Number(row.received_quantity || 0)
                  const consumed = Number(row.consumed_quantity || 0)
                  const available = Number(row.available_quantity || 0)

                  // Percentage of received stock still remaining
                  const pct = received > 0 ? Math.min(100, Math.max(0, Math.round((available / received) * 100))) : 0

                  let badgeCls = 'in-stock'
                  let badgeText = 'In stock'
                  const isFullyConsumed = available === 0 && received > 0

                  // Low stock logic: Remaining (On Hand) is <= 10% of Ordered (PO)
                  const isLowStock = available > 0 && ordered > 0 && available <= ordered * 0.1

                  if (received === 0 && ordered > 0) {
                    badgeCls = 'awaiting'
                    badgeText = 'Awaiting delivery'
                  } else if (isFullyConsumed) {
                    badgeCls = 'out-stock'
                    badgeText = 'Fully consumed'
                  } else if (isLowStock) {
                    badgeCls = 'low-stock'
                    badgeText = 'Low stock'
                  }

                  return (
                    <tr key={row.item.id}>
                      <td>
                        <div className="material-item-cell">
                          <strong className="material-name">{row.item.name}</strong>
                          <span className="material-sku">{row.item.sku}</span>
                        </div>
                      </td>
                      <td>
                        <span className="vendor-item-cell" title={row.vendor_name || '—'}>
                          {row.vendor_name || '—'}
                        </span>
                      </td>
                      <td className="numeric">{ordered.toLocaleString('en-IN')}</td>
                      <td className="numeric strong-received">{received.toLocaleString('en-IN')}</td>
                      <td className="numeric strong-consumed">{consumed.toLocaleString('en-IN')}</td>
                      <td className="numeric remaining-stock-cell">
                        <strong>{available.toLocaleString('en-IN')}</strong>
                        <small>{row.item.unit_of_measure}</small>
                      </td>
                      <td>
                        <div className="stock-level-cell">
                          <div className="stock-track" title={`${pct}% remaining`}>
                            <span
                              className={`stock-fill ${badgeCls}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className={`stock-badge ${badgeCls}`}>
                            {badgeText}
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="inventory-row-actions">
                          {canReceive && <button
                            type="button"
                            className="inventory-action-btn receive"
                            title={isFullyConsumed ? 'Item is fully consumed; create a new purchase order to order more' : 'Receive inward delivery for this item'}
                            disabled={isFullyConsumed}
                            onClick={() => setReceiveModalItem(row.item)}
                          >
                            <Truck size={12} />
                            Receive
                          </button>}
                          {canUse && <button
                            type="button"
                            className="inventory-action-btn use"
                            title={available <= 0 ? 'No stock available to consume' : 'Log material usage/consumption'}
                            disabled={available <= 0}
                            onClick={() => setIssueModalItem(row)}
                          >
                            <MinusCircle size={12} />
                            Use
                          </button>}
                          <button
                            type="button"
                            className="inventory-action-btn history"
                            title="View chronological stock movements"
                            onClick={() => setHistoryTarget(row.item)}
                          >
                            <History size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan={8}>
                    <EmptyState
                      title="No inventory materials found"
                      note="Items added to purchase orders in procurement automatically appear here in inventory."
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination controls: default 20, options 20, 50, 100, 200 */}
        <div className="register-pagination">
          <label>
            Rows per page
            <select
              aria-label="Materials per page"
              value={pageSize}
              onChange={event => {
                setPageSize(Number(event.target.value))
                setPage(1)
              }}
            >
              {[20, 50, 100, 200].map(size => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
          <span>
            {totalFiltered ? `${(currentPage - 1) * pageSize + 1}–${Math.min(currentPage * pageSize, totalFiltered)} of ${totalFiltered}` : '0 of 0'}
          </span>
          <div className="register-page-controls">
            <button
              className="icon-button"
              title="Previous page"
              aria-label="Previous page"
              disabled={currentPage <= 1}
              onClick={() => setPage(prev => Math.max(1, prev - 1))}
            >
              <ChevronLeft size={16} />
            </button>
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <button
              className="icon-button"
              title="Next page"
              aria-label="Next page"
              disabled={currentPage >= totalPages}
              onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </section>

      {/* MODAL 1: Receive Stock Inward */}
      {canReceive && receiveModalItem && (
        <ModalFrame
          title={`Receive material: ${receiveModalItem.name}`}
          onClose={() => setReceiveModalItem(null)}
        >
          <ReceiveStockForm
            projectId={projectId}
            csrf={csrf}
            targetItem={receiveModalItem}
            onCancel={() => setReceiveModalItem(null)}
            onSaved={async itemTitle => {
              await refreshInventory()
              setReceiveModalItem(null)
              showToast(`Stock inward recorded for ${itemTitle}.`)
            }}
          />
        </ModalFrame>
      )}

      {/* MODAL 2: Log Daily Usage */}
      {canUse && issueModalItem && (
        <ModalFrame
          title={`Log Material Usage: ${issueModalItem.item.name}`}
          onClose={() => setIssueModalItem(null)}
        >
          <LogUsageForm
            projectId={projectId}
            csrf={csrf}
            itemRow={issueModalItem}
            onCancel={() => setIssueModalItem(null)}
            onSaved={async qty => {
              await refreshInventory()
              setIssueModalItem(null)
              showToast(`Usage of ${qty} ${issueModalItem.item.unit_of_measure} logged.`)
            }}
          />
        </ModalFrame>
      )}

      {/* MODAL 3: Stock Movement Ledger History */}
      {historyTarget && (
        <ModalFrame
          title={historyTarget === 'ALL' ? 'Complete Site Inventory Ledger' : `${historyTarget.name} · Stock Movements`}
          className="inventory-ledger-modal"
          onClose={() => setHistoryTarget(null)}
        >
          <InventoryLedgerHistory
            projectId={projectId}
            targetItem={historyTarget === 'ALL' ? undefined : historyTarget}
          />
        </ModalFrame>
      )}

      {toastMessage && (
        <div className="toast" role="status">
          <BadgeCheck size={18} />
          {toastMessage}
        </div>
      )}
    </>
  )
}

/* =========================================================================
   Receive Stock Form Component
   ========================================================================= */
function ReceiveStockForm({
  projectId,
  csrf,
  targetItem,
  onCancel,
  onSaved
}: {
  projectId: string
  csrf: string
  targetItem: InventoryRow['item']
  onCancel: () => void
  onSaved: (itemName: string) => void
}) {
  const [quantity, setQuantity] = useState<string>('')
  const [txDate, setTxDate] = useState<string>(todayISO)
  const [reference, setReference] = useState<string>('')
  const [notes, setNotes] = useState<string>('')

  const mutation = useMutation({
    mutationFn: () =>
      api.recordInventoryTransaction(
        projectId,
        {
          item_id: targetItem.id,
          transaction_type: 'receipt',
          quantity,
          transaction_date: txDate,
          reference: reference.trim() || undefined,
          notes: notes.trim() || undefined
        },
        csrf
      ),
    onSuccess: () => onSaved(targetItem.name)
  })

  return (
    <form
      className="form-grid"
      onSubmit={event => {
        event.preventDefault()
        mutation.mutate()
      }}
    >
      <label className="field full">
        Material item
        <input
          type="text"
          disabled
          readOnly
          value={`${targetItem.name} (${targetItem.sku})`}
        />
      </label>

      <label className="field">
        Quantity received ({targetItem.unit_of_measure})
        <input
          required
          type="number"
          min="0.01"
          step="0.01"
          value={quantity}
          onChange={event => setQuantity(event.target.value)}
          placeholder="e.g. 50"
          autoFocus
        />
      </label>

      <label className="field">
        Received date
        <input
          required
          type="date"
          value={txDate}
          onChange={event => setTxDate(event.target.value)}
        />
      </label>

      <label className="field full">
        Delivery challan / Invoice ref (optional)
        <input
          maxLength={100}
          value={reference}
          onChange={event => setReference(event.target.value)}
          placeholder="e.g. DC-98421 / Vendor Inv (optional)"
        />
      </label>

      <label className="field full">
        Storage location &amp; notes (optional)
        <textarea
          maxLength={500}
          value={notes}
          onChange={event => setNotes(event.target.value)}
          placeholder="e.g. Received 50 bags, stored in Block B warehouse"
        />
      </label>

      <MutationError error={mutation.error} />
      <FormActions onCancel={onCancel} busy={mutation.isPending} submit="Confirm inward receipt" />
    </form>
  )
}

/* =========================================================================
   Log Usage Form Component
   ========================================================================= */
function LogUsageForm({
  projectId,
  csrf,
  itemRow,
  onCancel,
  onSaved
}: {
  projectId: string
  csrf: string
  itemRow: InventoryRow
  onCancel: () => void
  onSaved: (qty: string) => void
}) {
  const [quantity, setQuantity] = useState<string>('')
  const [txDate, setTxDate] = useState<string>(todayISO)
  const [reference, setReference] = useState<string>('')
  const [notes, setNotes] = useState<string>('')

  const available = Number(itemRow.available_quantity || 0)
  const enteredQty = Number(quantity || 0)
  const remainingAfter = Math.max(0, available - enteredQty)

  const mutation = useMutation({
    mutationFn: () =>
      api.recordInventoryTransaction(
        projectId,
        {
          item_id: itemRow.item.id,
          transaction_type: 'issue',
          quantity,
          transaction_date: txDate,
          reference: reference.trim() || undefined,
          notes: notes.trim() || undefined
        },
        csrf
      ),
    onSuccess: () => onSaved(quantity)
  })

  return (
    <form
      className="form-grid"
      onSubmit={event => {
        event.preventDefault()
        if (enteredQty <= 0) return
        mutation.mutate()
      }}
    >
      <label className="field">
        Material item
        <input
          type="text"
          disabled
          readOnly
          value={`${itemRow.item.name} (${itemRow.item.sku})`}
        />
      </label>

      <div className="field stock-inline-field">
        <span>Current available stock on site</span>
        <div className="stock-inline-box">
          <strong>
            {available.toLocaleString('en-IN')} {itemRow.item.unit_of_measure}
          </strong>
          {enteredQty > 0 && (
            <span className={`remaining-note ${remainingAfter < 0 ? 'over-limit' : 'normal'}`}>
              ({remainingAfter.toLocaleString('en-IN')} left after)
            </span>
          )}
        </div>
      </div>

      <label className="field">
        Quantity used ({itemRow.item.unit_of_measure})
        <input
          required
          type="number"
          min="0.01"
          max={available}
          step="0.01"
          value={quantity}
          onChange={event => setQuantity(event.target.value)}
          placeholder={`Max ${available}`}
          autoFocus
        />
      </label>

      {enteredQty > available && (
        <div className="form-error full" role="alert">
          Entered quantity ({enteredQty} {itemRow.item.unit_of_measure}) exceeds current available stock ({available} {itemRow.item.unit_of_measure}).
        </div>
      )}

      <label className="field">
        Usage date
        <input
          required
          type="date"
          value={txDate}
          onChange={event => setTxDate(event.target.value)}
        />
      </label>

      <label className="field">
        Work area / Construction task
        <input
          maxLength={100}
          value={reference}
          onChange={event => setReference(event.target.value)}
          placeholder="e.g. 2nd Floor Slab Casting, Block A"
          required
        />
      </label>

      <label className="field">
        Cost code or batch note
        <input
          maxLength={100}
          value={notes}
          onChange={event => setNotes(event.target.value)}
          placeholder="e.g. Concrete mix batch #1"
        />
      </label>

      <MutationError error={mutation.error} />
      <FormActions
        onCancel={onCancel}
        busy={mutation.isPending}
        disabled={available <= 0 || enteredQty > available}
        submit="Record usage"
      />
    </form>
  )
}

/* =========================================================================
   Inventory Ledger History Component
   ========================================================================= */
function InventoryLedgerHistory({
  projectId,
  targetItem
}: {
  projectId: string
  targetItem?: InventoryRow['item']
}) {
  const query = useQuery({
    queryKey: ['project', projectId, 'inventory-transactions', targetItem?.id],
    queryFn: () => api.inventoryTransactions(projectId, targetItem?.id)
  })

  const transactions = query.data?.items || []

  return (
    <div className="inventory-history-content">
      {targetItem && (
        <div className="inventory-history-header">
          <div>
            <h3>{targetItem.name}</h3>
            <span className="sku-badge">{targetItem.sku}</span>
          </div>
          <span className="unit-label">Unit of measure: {targetItem.unit_of_measure}</span>
        </div>
      )}

      <QueryError error={query.error} onRetry={() => void query.refetch()} />

      <div className="inventory-history-table-wrap">
        <table className="data-table inventory-history-table">
          <thead>
            <tr>
              <th className="th-date">Date</th>
              {!targetItem && <th className="th-material">Material</th>}
              <th className="th-movement">Movement Type</th>
              <th className="numeric th-quantity">Quantity</th>
              <th className="th-reference">Reference / Task</th>
              <th className="th-recorded">Recorded by</th>
              <th className="th-notes">Notes</th>
            </tr>
          </thead>
          <tbody>
            {query.isLoading ? (
              <tr>
                <td colSpan={targetItem ? 6 : 7}><div className="loading-line" /></td>
              </tr>
            ) : transactions.length ? (
              transactions.map(tx => {
                const isReceipt = tx.transaction_type === 'receipt'
                return (
                  <tr key={tx.id}>
                    <td>{dateLabel(tx.occurred_at.slice(0, 10))}</td>
                    {!targetItem && (
                      <td>
                        <strong>{tx.item_name}</strong>
                        <div className="muted-cell">{tx.sku}</div>
                      </td>
                    )}
                    <td>
                      <span className={`movement-pill ${isReceipt ? 'inward' : 'outward'}`}>
                        {isReceipt ? '+ Received (Inward)' : '− Used (Consumption)'}
                      </span>
                    </td>
                    <td className={`numeric font-bold ${isReceipt ? 'text-green' : 'text-amber'}`}>
                      {isReceipt ? '+' : '−'}
                      {Number(tx.quantity).toLocaleString('en-IN')} {tx.unit_of_measure}
                    </td>
                    <td>{tx.reference || (tx.po_number ? `PO ${tx.po_number}` : '—')}</td>
                    <td>{tx.recorded_by}</td>
                    <td className="history-notes-cell">{tx.notes || '—'}</td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={targetItem ? 6 : 7}>
                  <EmptyState
                    title="No stock movements recorded yet"
                    note="Use 'Receive Stock' to record deliveries or 'Log Usage' to track daily consumption."
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

