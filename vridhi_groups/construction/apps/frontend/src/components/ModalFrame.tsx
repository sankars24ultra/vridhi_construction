import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

export function ModalFrame({ title, onClose, children, className = '' }: { title: string; onClose: () => void; children: React.ReactNode; dismissOnBackdrop?: boolean; className?: string }) {
  const dialog = useRef<HTMLElement>(null)
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || document.querySelectorAll('[role="dialog"]').item(document.querySelectorAll('[role="dialog"]').length - 1) !== dialog.current) return
      event.preventDefault()
      onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])
  return <div className="modal-backdrop"><section ref={dialog} className={`modal ${className}`} role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div className="modal-heading"><div><span className="eyebrow">VRIDHI WORKSPACE</span><h2 id="dialog-title">{title}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={18} /></button></div>{children}</section></div>
}
