import { useEffect, useRef, useState, type PointerEvent } from 'react'
import Clock from 'react-clock'
import 'react-clock/dist/Clock.css'
import { DayPicker, type DateRange } from 'react-day-picker'
import { ChevronLeft, ChevronRight, Clock3, X } from 'lucide-react'
import 'react-day-picker/style.css'

function localDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function CompactTime({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState(value)
  const [mode, setMode] = useState<'hours' | 'minutes'>('hours')
  const popup = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const [hour, minute] = draft.split(':').map(Number)
  const format = (time: string) => {
    const [hours, minutes] = time.split(':').map(Number)
    return `${String(hours % 12 || 12).padStart(2, '0')}:${String(minutes).padStart(2, '0')} ${hours >= 12 ? 'PM' : 'AM'}`
  }
  const close = () => { setOpen(false); trigger.current?.focus() }
  useEffect(() => {
    if (!open) return
    popup.current?.querySelector<HTMLElement>('[aria-label="Select hours"]')?.focus({ preventScroll: true })
  }, [open])
  const changeTime = (hours: number, minutes: number) => {
    setDraft(`${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`)
  }
  const select = (position: number) => {
    if (mode === 'hours') changeTime(position % 12 + (hour >= 12 ? 12 : 0), minute)
    else changeTime(hour, position % 60)
  }
  const selectPointer = (event: PointerEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect()
    const horizontal = event.clientX - bounds.left - bounds.width / 2
    const vertical = event.clientY - bounds.top - bounds.height / 2
    if (Math.hypot(horizontal, vertical) < 12) return
    const angle = (Math.atan2(horizontal, -vertical) * 180 / Math.PI + 360) % 360
    select(Math.round(angle / (mode === 'hours' ? 30 : 6)))
  }
  const clockValue = new Date(2000, 0, 1, hour, mode === 'hours' ? 0 : minute, 0)
  return <>
    <button ref={trigger} type="button" className="audit-time-trigger" aria-label={`Select ${label.toLowerCase()}`} aria-expanded={open} onClick={() => { setDraft(value); setMode('hours'); setOpen(true) }}><Clock3 size={14} />{format(value)}</button>
    {open && <div ref={popup} className="audit-time-popup audit-analog-popup" role="group" aria-label={`${label} selection`} onKeyDown={event => { if (event.key === 'Escape') { event.stopPropagation(); close() } }}>
      <div className="audit-filter-heading"><strong>{label}</strong><button type="button" className="icon-button" aria-label={`Close ${label.toLowerCase()}`} title="Close time selection" onClick={close}><X size={15} /></button></div>
      <div className="audit-analog-display">
        <button type="button" aria-label="Select hours" aria-pressed={mode === 'hours'} onClick={() => setMode('hours')}>{String(hour % 12 || 12).padStart(2, '0')}</button><span>:</span>
        <button type="button" aria-label="Select minutes" aria-pressed={mode === 'minutes'} onClick={() => setMode('minutes')}>{String(minute).padStart(2, '0')}</button>
        <div className="audit-analog-period">{['AM', 'PM'].map(period => <button type="button" key={period} aria-pressed={(hour >= 12) === (period === 'PM')} onClick={() => changeTime(hour % 12 + (period === 'PM' ? 12 : 0), minute)}>{period}</button>)}</div>
      </div>
      <div className={`audit-analog-dial ${mode}`} role="slider" tabIndex={0} aria-label={`${label} ${mode}`} aria-valuemin={mode === 'hours' ? 1 : 0} aria-valuemax={mode === 'hours' ? 12 : 59} aria-valuenow={mode === 'hours' ? hour % 12 || 12 : minute} aria-valuetext={format(draft)}
        onPointerDown={event => { event.preventDefault(); event.currentTarget.focus(); event.currentTarget.setPointerCapture(event.pointerId); selectPointer(event) }}
        onPointerMove={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) selectPointer(event) }}
        onPointerUp={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) { selectPointer(event); event.currentTarget.releasePointerCapture(event.pointerId); if (mode === 'hours') setMode('minutes') } }}
        onKeyDown={event => {
          if (!['ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft', 'Home', 'End', 'Enter'].includes(event.key)) return
          event.preventDefault()
          if (event.key === 'Enter') { setMode(mode === 'hours' ? 'minutes' : 'hours'); return }
          const maximum = mode === 'hours' ? 12 : 60
          const current = mode === 'hours' ? hour % 12 : minute
          select(event.key === 'Home' ? 0 : event.key === 'End' ? maximum - 1 : (current + (['ArrowUp', 'ArrowRight'].includes(event.key) ? 1 : -1) + maximum) % maximum)
        }}>
        <Clock value={clockValue} size={148} renderNumbers={false} renderSecondHand={false} hourHandWidth={3} minuteHandWidth={2} hourHandLength={76} minuteHandLength={76} hourHandOppositeLength={0} minuteHandOppositeLength={0} />
        {Array.from({ length: 12 }, (_, index) => {
          const position = index + 1
          const number = mode === 'hours' ? position : position * 5 % 60
          const angle = position * Math.PI / 6
          const selected = mode === 'hours' ? hour % 12 === position % 12 : minute === number
          return <span key={position} className={`audit-analog-number${selected ? ' selected' : ''}`} aria-hidden="true" style={{ left: `${50 + Math.sin(angle) * 38}%`, top: `${50 - Math.cos(angle) * 38}%` }}>{mode === 'minutes' ? String(number).padStart(2, '0') : number}</span>
        })}
        <span className="audit-analog-center" />
      </div>
      <div className="audit-range-footer"><button type="button" className="button-secondary" onClick={close}>Cancel</button><button type="button" className="button-primary" onClick={() => { onChange(draft); close() }}>OK</button></div>
    </div>}
  </>
}

export function AuditDateRange({ from, to, onApply, onClose }: { from: string; to: string; onApply: (from: string, to: string) => void; onClose: () => void }) {
  const [range, setRange] = useState<DateRange | undefined>(() => from || to ? { from: from ? new Date(from) : undefined, to: to ? new Date(to) : undefined } : undefined)
  const [month, setMonth] = useState(range?.from || new Date())
  const [startClock, setStartClock] = useState(from.split('T')[1]?.slice(0, 5) || '00:00')
  const [endClock, setEndClock] = useState(to.split('T')[1]?.slice(0, 5) || '23:59')
  const start = range?.from ? `${localDate(range.from)}T${startClock}` : ''
  const end = range?.to ? `${localDate(range.to)}T${endClock}:59.999` : ''
  const invalid = !start || !end || !startClock || !endClock || new Date(start).getTime() > new Date(end).getTime()
  const shortcut = (kind: string) => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const beginning = new Date(today)
    const ending = new Date(today)
    if (kind === 'Yesterday') { beginning.setDate(beginning.getDate() - 1); ending.setDate(ending.getDate() - 1) }
    if (kind === 'Last 7 days') beginning.setDate(beginning.getDate() - 6)
    if (kind === 'This month') beginning.setDate(1)
    setRange({ from: beginning, to: ending })
    setMonth(beginning)
    setStartClock('00:00')
    setEndClock('23:59')
  }
  return <>
    <div className="audit-filter-heading"><strong>Time range</strong><button type="button" className="icon-button" aria-label="Close time filter" title="Close time filter" onClick={onClose}><X size={15} /></button></div>
    <div className="audit-range-shortcuts">{['Today', 'Yesterday', 'Last 7 days', 'This month'].map(label => <button key={label} type="button" onClick={() => shortcut(label)}>{label}</button>)}</div>
    <DayPicker mode="range" selected={range} onSelect={setRange} month={month} onMonthChange={setMonth} numberOfMonths={1} showOutsideDays autoFocus components={{ Chevron: ({ orientation }) => orientation === 'left' ? <ChevronLeft size={18} /> : <ChevronRight size={18} /> }} />
    <div className="audit-range-times"><div className="audit-range-boundary"><strong>From date</strong><span>{range?.from?.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) || 'Not selected'}</span><CompactTime label="From time" value={startClock} onChange={setStartClock} /></div><div className="audit-range-boundary"><strong>To date</strong><span>{range?.to?.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) || 'Not selected'}</span><CompactTime label="To time" value={endClock} onChange={setEndClock} /></div></div>
    {start && end && invalid && <p className="form-error" role="alert">End time must not be before start time.</p>}
    <div className="audit-range-footer"><button type="button" className="button-secondary" onClick={() => { onApply('', ''); onClose() }}>Reset</button><button type="button" className="button-primary" disabled={invalid} onClick={() => { onApply(start, end); onClose() }}>Apply</button></div>
  </>
}