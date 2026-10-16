import type { ReactNode } from 'react'
import { ArrowUpRight } from 'lucide-react'

export function PageTitle({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>
}

export function Kpi({ label, value, note, icon, loading }: { label: string; value: string; note: string; icon: ReactNode; loading?: boolean }) {
  return <article className="kpi-card module-summary" aria-busy={loading || false}><div className="kpi-card-top"><span>{label}</span><i>{icon}</i></div><strong className={loading ? 'value-loading' : ''}>{loading ? ' ' : value}</strong><small>{note}</small><div className="module-summary-accent" aria-hidden="true" /></article>
}

export function PanelHeading({ title, meta, action }: { title: string; meta?: string; action?: ReactNode }) {
  return <div className="panel-heading"><div><h2>{title}</h2>{meta && <span>{meta}</span>}</div>{action}</div>
}

export function EmptyState({ title, note }: { title: string; note: string }) {
  return <div className="empty-state"><span>{title}</span><small>{note}</small></div>
}

export function FormActions({ onCancel, busy, disabled = false, submit }: { onCancel: () => void; busy: boolean; disabled?: boolean; submit: string }) {
  return <div className="form-actions full"><button type="button" className="button-secondary" onClick={onCancel}>Cancel</button><button type="submit" className="button-primary" disabled={busy || disabled}>{busy ? 'Saving…' : submit}<ArrowUpRight size={15} /></button></div>
}

export function MutationError({ error }: { error: Error | null }) {
  return error ? <div className="form-error full">{error.message}</div> : null
}

export function QueryError({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  return error ? <div className="query-error"><span>{error.message}</span><button className="text-action" onClick={onRetry}>Retry</button></div> : null
}

export function InlineError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return <div className="inline-error"><span>{error.message}</span><button onClick={onRetry}>Retry</button></div>
}
