import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Check, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, CircleDollarSign, ClipboardList, Clock3, Download, ExternalLink, FileText, Package, Plus, Search, Settings2 } from 'lucide-react'
import { api, type Project, type PurchaseOrder } from '../../lib/api'
import { currency, dateLabel, todayISO } from '../../lib/format'
import { EmptyState, FormActions, InlineError, Kpi, MutationError, PageTitle, PanelHeading, QueryError } from '../../components/ui'
import { ExportHeader } from '../../components/ExportHeader'

export function Procurement({ project, projectId, canWrite = true, canNew = canWrite, canEdit = canWrite, canPay = canWrite, canExport = true, search, setSearch, onNew, onEdit, onPayment, onHistory }: { project?: Project; projectId: string; canWrite?: boolean; canNew?: boolean; canEdit?: boolean; canPay?: boolean; canExport?: boolean; search: string; setSearch: (value: string) => void; onNew: () => void; onEdit: (order: PurchaseOrder) => void; onPayment: (order: PurchaseOrder) => void; onHistory: (order: PurchaseOrder) => void }) {
  const [paymentStatus, setPaymentStatus] = useState('')
  const [pagination, setPagination] = useState<{ projectId: string; search: string; paymentStatus?: string; page: number; size: number }>({ projectId, search, paymentStatus, page: 1, size: 10 })
  const [printOrders, setPrintOrders] = useState<PurchaseOrder[] | null>(null)
  const page = pagination.projectId === projectId && pagination.search === search && pagination.paymentStatus === paymentStatus ? pagination.page : 1
  const pageSize = pagination.size
  const summary = useQuery({ queryKey: ['project', projectId, 'procurement-summary'], queryFn: () => api.procurementSummary(projectId) })
  const orders = useQuery({ queryKey: ['project', projectId, 'purchase-orders', { search, paymentStatus, page, pageSize }], queryFn: () => api.purchaseOrders(projectId, page, pageSize, search, paymentStatus) })
  const visibleOrders = (orders.data?.items || []).filter(order => !paymentStatus || order.payment_status === paymentStatus)
  const total = orders.data?.total || 0
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const changePage = (next: number) => setPagination({ projectId, search, paymentStatus, page: next, size: pageSize })
  const totals = summary.data
  const exportReport = async () => {
    try {
      const firstPage = await api.purchaseOrders(projectId, 1, 200)
      const allOrders = [...firstPage.items]
      for (let pageNumber = 2; pageNumber <= Math.ceil(firstPage.total / 200); pageNumber += 1) {
        const pageResult = await api.purchaseOrders(projectId, pageNumber, 200)
        allOrders.push(...pageResult.items)
      }
      setPrintOrders(allOrders)
      await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      await document.fonts.ready
      const previousTitle = document.title
      document.title = `${project?.name || 'Project'} - Procurement Register`
      window.addEventListener('afterprint', () => { document.title = previousTitle; setPrintOrders(null) }, { once: true })
      await api.recordActivity(projectId, 'procurement', 'export')
      window.print()
    } catch {
      setPrintOrders(null)
    }
  }
  return <><PageTitle eyebrow="PURCHASING" title="Procurement" subtitle="Purchase orders and vendor commitments" action={<div className="overview-actions">{canExport && <button className="button-secondary export-report-action" onClick={exportReport} disabled={summary.isFetching || summary.isError || orders.isFetching || orders.isError}><Download size={14} />Export report</button>}{canNew && <button className="button-primary" onClick={onNew}><Plus size={16} />New purchase order</button>}</div>} />
    <ExportHeader reportTitle="Procurement &amp; Purchase Order Register" projectName={project?.name} projectLocation={project?.location} />
    <div className="kpi-grid four"><Kpi label="Purchase orders" value={String(totals?.order_count ?? '—')} note="For this project" icon={<ClipboardList size={17} />} loading={summary.isLoading} /><Kpi label="Total ordered" value={currency(totals?.total_ordered, totals?.currency)} note="Purchase order value" icon={<Package size={17} />} loading={summary.isLoading} /><Kpi label="Total paid" value={currency(totals?.total_paid, totals?.currency)} note="Payment ledger" icon={<Check size={17} />} loading={summary.isLoading} /><Kpi label="Outstanding balance" value={currency(totals?.outstanding_balance, totals?.currency)} note="Vendor payments due" icon={<CircleDollarSign size={17} />} loading={summary.isLoading} /></div>{summary.error && <InlineError error={summary.error} onRetry={() => void summary.refetch()} />}<section className="panel table-panel procurement-register"><PanelHeading title={printOrders ? 'Purchase order register' : 'Purchase order register'} meta={printOrders ? `${printOrders.length} purchase orders · order date, newest first` : 'Order date, newest first · payment state does not affect order'} action={!printOrders && <div className="register-tools"><div className="register-status-filter" role="group" aria-label="Filter purchase orders by payment status"><span className="register-filter-hint">Status</span><button type="button" className={`register-status-option${paymentStatus === '' ? ' selected' : ''}`} aria-pressed={paymentStatus === ''} onClick={() => { setPaymentStatus(''); setPagination({ projectId, search, paymentStatus: '', page: 1, size: pageSize }) }}>All</button>{(['Paid', 'Partially paid', 'Pending'] as const).map(status => <button key={status} type="button" className={`register-status-option${paymentStatus === status ? ' selected' : ''}`} aria-label={`Filter ${status} purchase orders`} aria-pressed={paymentStatus === status} onClick={() => { setPaymentStatus(status); setPagination({ projectId, search, paymentStatus: status, page: 1, size: pageSize }) }}><StatusMark status={status} /><span>{status}</span></button>)}</div><div className="search-wrap"><Search size={16} /><input placeholder="Search vendor, item or PO" value={search} onChange={event => { setSearch(event.target.value); setPagination({ projectId, search: event.target.value, paymentStatus, page: 1, size: pageSize }) }} /></div></div>} /><OrderTable orders={printOrders || visibleOrders} loading={!printOrders && orders.isLoading} onEdit={canEdit && !printOrders ? onEdit : undefined} onPayment={canPay && !printOrders ? onPayment : undefined} onHistory={printOrders ? undefined : onHistory} /><div className="register-pagination"><label>Rows per page<select aria-label="Purchase orders per page" value={pageSize} onChange={event => setPagination({ projectId, search, paymentStatus, page: 1, size: Number(event.target.value) })}>{[10, 20, 50, 100, 200].map(size => <option key={size}>{size}</option>)}</select></label><span aria-live="polite">{orders.isFetching ? 'Loading...' : `${total ? (page - 1) * pageSize + 1 : 0}–${total ? (page - 1) * pageSize + (orders.data?.items.length || 0) : 0} of ${total}`}</span><div className="register-page-controls"><button className="icon-button" title="First page" aria-label="First page" disabled={page <= 1 || orders.isFetching} onClick={() => changePage(1)}><ChevronsLeft size={16} /></button><button className="icon-button" title="Previous page" aria-label="Previous page" disabled={page <= 1 || orders.isFetching} onClick={() => changePage(page - 1)}><ChevronLeft size={16} /></button><span>Page {page} of {pages}</span><button className="icon-button" title="Next page" aria-label="Next page" disabled={page >= pages || orders.isFetching || !!orders.error} onClick={() => changePage(page + 1)}><ChevronRight size={16} /></button><button className="icon-button" title="Last page" aria-label="Last page" disabled={page >= pages || orders.isFetching || !!orders.error} onClick={() => changePage(pages)}><ChevronsRight size={16} /></button></div></div><QueryError error={orders.error} onRetry={() => void orders.refetch()} /></section></>
}

export function OrderTable({ orders, loading, compact = false, onEdit, onPayment, onHistory }: { orders: PurchaseOrder[]; loading: boolean; compact?: boolean; onEdit?: (order: PurchaseOrder) => void; onPayment?: (order: PurchaseOrder) => void; onHistory?: (order: PurchaseOrder) => void }) {
  return <div className="table-scroll"><table className="data-table">
    <thead><tr><th>PO number</th><th>Vendor</th><th>Item</th><th>Order date</th><th className="numeric">Total</th><th className="numeric">Paid</th><th className="numeric">Balance</th>{!compact && <th>Actions</th>}</tr></thead>
    <tbody>{loading ? <tr><td colSpan={compact ? 7 : 8}><div className="loading-line" /></td></tr> : orders.length ? orders.map(order => {
      const editEnabled = Boolean(onEdit) && order.can_edit
      const paymentEnabled = Boolean(onPayment) && order.can_add_payment
      const editLabel = !onEdit ? 'Edit purchase order permission required' : order.can_edit ? 'Edit purchase order' : 'Fully paid; editing is disabled'
      const paymentLabel = !onPayment ? 'Add payment permission required' : order.can_add_payment ? 'Add payment' : 'Fully paid; no balance remains'
      return <tr key={order.id}>
        <td><span className="po-number">{order.number}</span><StatusMark status={order.payment_status} /></td><td>{order.vendor.name}</td><td><span className="item-cell">{order.item_names.join(', ') || '—'}</span></td><td>{dateLabel(order.order_date)}</td>
        <td className="numeric">{currency(order.total, order.currency)}</td><td className="numeric">{currency(order.paid_to_date, order.currency)}</td><td className={`numeric ${order.balance === '0.00' ? 'settled-text' : 'balance-text'}`}>{currency(order.balance, order.currency)}</td>
        {!compact && <td><div className="row-actions">
          <span className="row-action-tooltip" data-tooltip={editLabel}><button className="icon-button" title={editLabel} aria-label={editLabel} disabled={!editEnabled} onClick={() => onEdit?.(order)}><Settings2 size={15} /></button></span>
          <span className="row-action-tooltip" data-tooltip={paymentLabel}><button className="icon-button" title={paymentLabel} aria-label={paymentLabel} disabled={!paymentEnabled} onClick={() => onPayment?.(order)}><Plus size={16} /></button></span>
          <span className="row-action-tooltip" data-tooltip={`Payment history for ${order.number}`}><button className="icon-button" title={`Payment history for ${order.number}`} aria-label={`Payment history for ${order.number}`} onClick={() => onHistory?.(order)}><Clock3 size={15} /></button></span>
        </div></td>}
      </tr>
    }) : <tr><td colSpan={compact ? 7 : 8}><EmptyState title="No purchase orders" note="Create an order to start tracking vendor commitments." /></td></tr>}</tbody>
  </table></div>
}

export function StatusMark({ status }: { status: string }) { const cls = status === 'Paid' ? 'paid' : status === 'Partially paid' ? 'partial' : 'unpaid'; return <span className={`payment-mark ${cls}`} title={status} aria-label={status}>{status === 'Paid' ? '✓' : status === 'Partially paid' ? '◐' : '!'}</span> }

export function PaymentHistory({ projectId, order }: { projectId: string; order: PurchaseOrder }) {
  const [page, setPage] = useState(1)
  const pageSize = 5
  const detail = useQuery({ queryKey: ['project', projectId, 'po', order.id, 'detail'], queryFn: () => api.purchaseOrder(projectId, order.id) })
  const payments = useQuery({ queryKey: ['project', projectId, 'po', order.id, 'payments', page, pageSize], queryFn: () => api.payments(projectId, order.id, page, pageSize) })
  const total = payments.data?.total || 0
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const receiptImage = detail.data?.image || order.image
  return <div className="payment-history-dialog">
    <div className="payment-summary history-summary">
      <div className="history-order-identity">
        <span>Purchase order</span>
        <strong>{order.number}</strong>
        <small>{order.vendor.name}</small>
      </div>
      <div className="history-total">
        <span>Total</span>
        <strong>{currency(order.total, order.currency)}</strong>
      </div>
      <div className="history-paid">
        <span>Paid</span>
        <strong>{currency(order.paid_to_date, order.currency)}</strong>
      </div>
      <div className="history-balance">
        <span>Balance</span>
        <strong>{currency(order.balance, order.currency)}</strong>
      </div>
    </div>
    {receiptImage?.available && (
      <div className="history-receipt-banner">
        <div className="history-receipt-preview">
          <a href={receiptImage.url} target="_blank" rel="noreferrer" title="Click to view full receipt image" aria-label={`View uploaded receipt image ${receiptImage.filename}`}>
            <img src={receiptImage.url} alt={`Receipt proof for ${order.number}`} className="history-receipt-thumb" />
          </a>
        </div>
        <div className="history-receipt-info">
          <span className="history-receipt-label">
            <FileText size={14} /> Uploaded purchase receipt proof
          </span>
          <strong className="history-receipt-filename" title={receiptImage.filename}>{receiptImage.filename}</strong>
          <span className="history-receipt-note">Original invoice / payment proof attached during purchase order creation</span>
        </div>
        <div className="history-receipt-action">
          <a href={receiptImage.url} target="_blank" rel="noreferrer" className="button-secondary history-receipt-link">
            <ExternalLink size={13} /> Open receipt
          </a>
        </div>
      </div>
    )}
    <div className="table-scroll">
      <table className="data-table payment-history-table">
        <thead>
          <tr>
            <th>Payment date</th>
            <th className="numeric">Amount</th>
            <th>Mode</th>
            <th>Reference</th>
            <th>Comment</th>
            <th>Recorded by</th>
          </tr>
        </thead>
        <tbody>
          {payments.isLoading ? (
            <tr><td colSpan={6}><div className="loading-line" /></td></tr>
          ) : payments.data?.items.length ? (
            payments.data.items.map(payment => (
              <tr key={payment.id}>
                <td>{dateLabel(payment.payment_date)}</td>
                <td className="numeric">{currency(payment.amount, order.currency)}</td>
                <td>{payment.payment_mode || 'Other'}</td>
                <td>{payment.reference || '—'}</td>
                <td className="overview-comment">{payment.comment || '—'}</td>
                <td>{payment.recorded_by.name}</td>
              </tr>
            ))
          ) : (
            <tr><td colSpan={6}><EmptyState title="No payments recorded" note="Installments will appear here after they are saved." /></td></tr>
          )}
        </tbody>
      </table>
    </div>
    {total > pageSize && (
      <div className="register-pagination">
        <span>{(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}</span>
        <div className="register-page-controls">
          <button className="icon-button" title="Previous payments" aria-label="Previous payments" disabled={page <= 1 || payments.isFetching} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /></button>
          <span>Page {page} of {pages}</span>
          <button className="icon-button" title="Next payments" aria-label="Next payments" disabled={page >= pages || payments.isFetching} onClick={() => setPage(page + 1)}><ChevronRight size={16} /></button>
        </div>
      </div>
    )}
    <QueryError error={payments.error} onRetry={() => void payments.refetch()} />
  </div>
}

export function POForm({ projectId, csrf, order, onSaved, onCancel }: { projectId: string; csrf: string; order: PurchaseOrder | null; onSaved: () => void; onCancel: () => void }) {
  const vendors = useQuery({ queryKey: ['reference', 'vendors'], queryFn: api.vendors })
  const materials = useQuery({ queryKey: ['reference', 'items'], queryFn: api.inventoryItems })
  const detail = useQuery({ queryKey: ['project', projectId, 'po', order?.id], queryFn: () => api.purchaseOrder(projectId, order!.id), enabled: !!order })
  const [vendor, setVendor] = useState('')
  const [item, setItem] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [price, setPrice] = useState('')
  const [orderDate, setOrderDate] = useState(todayISO)
  const [paid, setPaid] = useState('0')
  const [paymentMode, setPaymentMode] = useState<'Gpay' | 'Bank transfer' | 'Cash' | 'Other'>('Cash')
  const [paymentComment, setPaymentComment] = useState('')
  const [orderImage, setOrderImage] = useState<File | null>(null)
  const [imageError, setImageError] = useState('')
  const matchName = (input: string, choices: { name: string }[] = []) => choices.find(choice => choice.name.toLocaleLowerCase() === input.trim().toLocaleLowerCase())?.name || input
  const vendorSuggestions = vendor.trim() ? (vendors.data?.items || []).filter(value => value.name.toLocaleLowerCase().includes(vendor.trim().toLocaleLowerCase())) : []
  const materialSuggestions = item.trim() ? (materials.data?.items || []).filter(value => value.name.toLocaleLowerCase().includes(item.trim().toLocaleLowerCase())) : []
  useEffect(() => { if (detail.data) { setVendor(detail.data.vendor.name); setItem(detail.data.lines[0]?.item.name || ''); setQuantity(detail.data.lines[0]?.quantity || '1'); setPrice(detail.data.lines[0]?.unit_price || ''); setOrderDate(detail.data.order_date) } }, [detail.data])
  const total = Math.round(Number(quantity || 0) * Number(price || 0) * 100) / 100
  const paidAmount = order ? Number(detail.data?.paid_to_date || order.paid_to_date) : Number(paid || 0)
  const balance = total - paidAmount
  const paymentInvalid = !Number.isFinite(total) || !Number.isFinite(paidAmount) || paidAmount < 0 || paidAmount > total
  const mutation = useMutation({ mutationFn: () => {
    const vendorName = matchName(vendor, vendors.data?.items)
    const materialName = matchName(item, materials.data?.items)
    return api.savePurchaseOrder(projectId, {
      vendor_name: vendorName.trim(), order_date: orderDate,
      lines: [{ item_name: materialName.trim(), category: 'Material', description: materialName.trim(), quantity, unit_price: price }],
      ...(!order ? { paid_amount: paid || '0', payment_mode: paymentMode, payment_comment: paymentComment } : {}),
    }, csrf, order ? { id: order.id, version: detail.data?.version ?? order.version } : undefined, orderImage)
  }, onSuccess: onSaved })
  return <form className="form-grid" onSubmit={event => { event.preventDefault(); if (!paymentInvalid) mutation.mutate() }}>
    <label className="field full">Vendor<input required maxLength={160} list="purchase-order-vendor-suggestions" value={vendor} onChange={event => setVendor(matchName(event.target.value, vendors.data?.items))} onBlur={() => setVendor(matchName(vendor, vendors.data?.items))} placeholder="Enter vendor name" /><datalist id="purchase-order-vendor-suggestions">{vendorSuggestions.map(value => <option key={value.id} value={value.name} />)}</datalist></label>
    <label className="field full">Material<input required maxLength={180} list="purchase-order-material-suggestions" value={item} onChange={event => setItem(matchName(event.target.value, materials.data?.items))} onBlur={() => setItem(matchName(item, materials.data?.items))} placeholder="Enter material or service" /><datalist id="purchase-order-material-suggestions">{materialSuggestions.map(value => <option key={value.id} value={value.name} />)}</datalist></label>
    {order && detail.data?.image?.available && <div className="field full"><span>Attached image</span><a href={detail.data.image.url} target="_blank" rel="noreferrer">{detail.data.image.filename}</a></div>}
    {!order && <label className="field full">Receipt (Optional)<input type="file" accept="image/png,image/jpeg,image/webp" onChange={event => { const file = event.target.files?.[0]; if (!file) { setOrderImage(null); setImageError(''); return } if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) { setOrderImage(null); setImageError('Choose a PNG, JPG, or WEBP image.'); return } if (!file.size || file.size > 10 * 1024 * 1024) { setOrderImage(null); setImageError('Choose a non-empty image no larger than 10 MB.'); return } setOrderImage(file); setImageError('') }} />{orderImage && <small className="field-hint">{orderImage.name} · {(orderImage.size / (1024 * 1024)).toFixed(2)} MB</small>}{imageError && <span className="form-error" role="alert">{imageError}</span>}</label>}
    <label className="field">Quantity<input required type="number" min="0.01" step="0.01" value={quantity} onChange={event => setQuantity(event.target.value)} /></label>
    <label className="field">Unit price (₹)<input required type="number" min="0" step="0.01" value={price} onChange={event => setPrice(event.target.value)} /></label>
    <label className="field full">Total purchase price (₹)<input readOnly value={Number.isFinite(total) ? total.toFixed(2) : '0.00'} /></label>
    <label className="field">Paid (₹)<input type="number" min="0" max={total} step="0.01" readOnly={!!order} aria-invalid={paymentInvalid} aria-describedby={paymentInvalid ? 'po-payment-error' : undefined} value={order ? paidAmount.toFixed(2) : paid} onChange={event => setPaid(event.target.value)} />{paymentInvalid && <span id="po-payment-error" className="form-error" role="alert">{paidAmount > total ? 'Paid amount cannot exceed the total purchase price.' : 'Enter a valid nonnegative paid amount.'}</span>}</label>
    <label className="field">Balance (₹)<input readOnly value={Number.isFinite(balance) ? balance.toFixed(2) : '0.00'} /></label>
    <label className="field">Order date<input required type="date" value={orderDate} onChange={event => setOrderDate(event.target.value)} /></label>
    {!order && <><label className="field">Payment mode<select value={paymentMode} onChange={event => setPaymentMode(event.target.value as typeof paymentMode)}><option>Gpay</option><option>Bank transfer</option><option>Cash</option><option>Other</option></select></label><label className="field full">Payment reference / comment<textarea maxLength={500} value={paymentComment} onChange={event => setPaymentComment(event.target.value)} placeholder="Transaction reference number or payment feedback" /></label></>}
    <MutationError error={vendors.error || materials.error || detail.error || mutation.error} /><FormActions onCancel={onCancel} busy={mutation.isPending || detail.isLoading || vendors.isLoading || materials.isLoading} disabled={paymentInvalid || !vendor.trim() || !item.trim() || !!imageError} submit={order ? 'Save changes' : 'Create purchase order'} />
  </form>
}

export function PaymentForm({ projectId, csrf, order, onSaved, onCancel }: { projectId: string; csrf: string; order: PurchaseOrder; onSaved: () => void; onCancel: () => void }) { const detail = useQuery({ queryKey: ['project', projectId, 'po', order.id, 'detail'], queryFn: () => api.purchaseOrder(projectId, order.id) }); const [amount, setAmount] = useState(''); const [paymentDate, setPaymentDate] = useState(todayISO); const [paymentMode, setPaymentMode] = useState<'Gpay' | 'Bank transfer' | 'Cash' | 'Other'>('Cash'); const [reference, setReference] = useState(''); const [comment, setComment] = useState(''); const [idempotencyKey] = useState(() => crypto.randomUUID()); const currentBalance = Number(detail.data?.balance ?? order.balance); const enteredAmount = Number(amount || 0); const balanceAfterPayment = currentBalance - enteredAmount; const paymentInvalid = !amount || enteredAmount <= 0 || enteredAmount > currentBalance; const mutation = useMutation({ mutationFn: (token: string) => api.addPayment(projectId, order.id, { amount, payment_date: paymentDate, payment_mode: paymentMode, reference, comment }, token, idempotencyKey), onSuccess: onSaved }); return <form className="form-grid" onSubmit={event => { event.preventDefault(); if (!paymentInvalid) mutation.mutate(csrf) }}><div className="payment-summary full"><span>{order.number} · {order.vendor.name}</span><strong>Current balance {currency(currentBalance, order.currency)}</strong></div><label className="field">Payment amount (₹)<input autoFocus required type="number" min="0.01" max={currentBalance} step="0.01" value={amount} aria-invalid={paymentInvalid && !!amount} onChange={event => setAmount(event.target.value)} /></label><label className="field">Balance after payment (₹)<input readOnly value={currency(Math.max(0, balanceAfterPayment), order.currency)} /></label>{paymentInvalid && !!amount && <div className="form-error full" role="alert">Payment amount cannot exceed the current balance.</div>}<label className="field">Payment date<input required type="date" value={paymentDate} onChange={event => setPaymentDate(event.target.value)} /></label><label className="field">Mode of payment<select value={paymentMode} onChange={event => setPaymentMode(event.target.value as typeof paymentMode)}><option>Gpay</option><option>Bank transfer</option><option>Cash</option><option>Other</option></select></label><label className="field full">Reference<input maxLength={100} value={reference} onChange={event => setReference(event.target.value)} placeholder="Payment reference number" /></label><label className="field full">Comment<textarea maxLength={500} value={comment} onChange={event => setComment(event.target.value)} placeholder="Optional payment feedback" /></label><MutationError error={detail.error || mutation.error} /><FormActions onCancel={onCancel} busy={mutation.isPending || detail.isLoading} disabled={paymentInvalid} submit="Record payment" /></form> }
