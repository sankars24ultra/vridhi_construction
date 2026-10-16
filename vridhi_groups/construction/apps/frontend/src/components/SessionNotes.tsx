import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { NotebookPen, PanelRightClose, Trash2 } from 'lucide-react'
import { ModalFrame } from './ModalFrame'

const storageKey = (userId: string) => `vridhi-session-notes:${userId}`

export function clearSessionNotes(userId: string) {
  try { sessionStorage.removeItem(storageKey(userId)) } catch { return }
}

export function SessionNotes({ userId }: { userId: string }) {
  const [saved] = useState(() => {
    try {
      const value = JSON.parse(sessionStorage.getItem(storageKey(userId)) || '{}')
      return { text: typeof value.text === 'string' ? value.text : '', open: value.open === true, width: typeof value.width === 'number' && Number.isFinite(value.width) ? value.width : 280 }
    } catch { return { text: '', open: false, width: 280 } }
  })
  const [text, setText] = useState(saved.text)
  const [open, setOpen] = useState(saved.open)
  const [width, setWidth] = useState(saved.width)
  const [viewportWidth, setViewportWidth] = useState(window.innerWidth)
  const maximumWidth = viewportWidth <= 760 ? viewportWidth - 24 : Math.min(560, Math.floor(viewportWidth * 0.45))
  const minimumWidth = Math.min(240, maximumWidth)
  const panelWidth = Math.max(minimumWidth, Math.min(width, maximumWidth))
  const panel = useRef<HTMLElement>(null)
  const stopDragging = useRef<(() => void) | null>(null)
  useEffect(() => () => { stopDragging.current?.() }, [])
  const [confirmClear, setConfirmClear] = useState(false)
  const [storageError, setStorageError] = useState(false)
  const editor = useRef<HTMLTextAreaElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const persist = (nextText: string, nextOpen: boolean) => {
    try {
      sessionStorage.setItem(storageKey(userId), JSON.stringify({ text: nextText, open: nextOpen, width }))
      setStorageError(false)
    } catch { setStorageError(true) }
  }
  const resize = (nextWidth: number) => {
    const boundedWidth = Math.max(minimumWidth, Math.min(nextWidth, maximumWidth))
    setWidth(boundedWidth)
    try {
      sessionStorage.setItem(storageKey(userId), JSON.stringify({ text, open, width: boundedWidth }))
      setStorageError(false)
    } catch { setStorageError(true) }
  }
  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  useEffect(() => {
    const main = panel.current?.closest<HTMLElement>('.main-area')
    main?.style.setProperty('--session-notes-width', `${panelWidth}px`)
    return () => { main?.style.removeProperty('--session-notes-width') }
  }, [open, panelWidth])
  const toggle = (nextOpen: boolean) => {
    setOpen(nextOpen)
    persist(text, nextOpen)
  }
  const close = () => {
    toggle(false)
    trigger.current?.focus()
  }
  useEffect(() => {
    if (!open || confirmClear) return
    editor.current?.focus()
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !document.querySelector('[role="dialog"]')) {
        setOpen(false)
        try {
          const value = JSON.parse(sessionStorage.getItem(storageKey(userId)) || '{}')
          if (value.text) sessionStorage.setItem(storageKey(userId), JSON.stringify({ ...value, open: false }))
        } catch { return }
        trigger.current?.focus()
      }
    }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open, confirmClear, userId])
  return <>
    <span className="row-action-tooltip user-badge-tooltip" data-tooltip="Notes">
      <button ref={trigger} type="button" className="icon-button session-notes-trigger" aria-label="Notes" aria-expanded={open} aria-controls="session-notes-panel" onClick={() => toggle(!open)}>
        <NotebookPen size={17} />{text.trim() && <span className="session-notes-indicator" aria-label="Notes contain text" />}
      </button>
    </span>
    {open && <aside ref={panel} id="session-notes-panel" className="session-notes" aria-label="Personal notes" style={{ '--session-notes-width': `${panelWidth}px` } as CSSProperties}>
      <div className="session-notes-resize" role="separator" aria-label="Resize notes" aria-orientation="vertical" aria-valuemin={minimumWidth} aria-valuemax={maximumWidth} aria-valuenow={panelWidth} aria-valuetext={`${panelWidth} pixels wide`} aria-controls="session-notes-panel" tabIndex={0} title="Drag to resize notes"
        onPointerDown={event => {
          event.preventDefault()
          stopDragging.current?.()
          const pointerId = event.pointerId
          const move = (pointer: PointerEvent) => {
            if (pointer.pointerId === pointerId) resize(window.innerWidth - pointer.clientX)
          }
          const stop = () => {
            window.removeEventListener('pointermove', move)
            window.removeEventListener('pointerup', stop)
            window.removeEventListener('pointercancel', stop)
            stopDragging.current = null
          }
          stopDragging.current = stop
          window.addEventListener('pointermove', move)
          window.addEventListener('pointerup', stop)
          window.addEventListener('pointercancel', stop)
        }}
        onKeyDown={event => {
          if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
          event.preventDefault()
          resize(event.key === 'Home' ? minimumWidth : event.key === 'End' ? maximumWidth : panelWidth + (event.key === 'ArrowLeft' ? 20 : -20))
        }}
      />
      <div className="session-notes-heading"><h2>Notes</h2><div className="row-actions">
        <button type="button" className="icon-button" title="Clear notes" aria-label="Clear notes" disabled={!text} onClick={() => setConfirmClear(true)}><Trash2 size={16} /></button>
        <button type="button" className="icon-button" title="Collapse notes" aria-label="Collapse notes" onClick={close}><PanelRightClose size={17} /></button>
      </div></div>
      <textarea ref={editor} aria-label="Personal notes" placeholder="Write a note..." value={text} spellCheck onChange={event => { setText(event.target.value); persist(event.target.value, true) }} />
      {storageError && <p className="session-notes-error" role="status">Session storage is unavailable. Notes will not survive a page refresh.</p>}
    </aside>}
    {confirmClear && <ModalFrame title="Clear notes" onClose={() => setConfirmClear(false)}><div className="session-notes-confirm"><p>Delete all your current notes? This cannot be undone.</p><div className="row-actions"><button type="button" className="button-secondary" onClick={() => setConfirmClear(false)}>Cancel</button><button type="button" className="button-primary" onClick={() => { setText(''); persist('', open); setConfirmClear(false) }}>Clear notes</button></div></div></ModalFrame>}
  </>
}