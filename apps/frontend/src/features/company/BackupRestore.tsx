import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CalendarClock, DatabaseBackup, Download, FileCheck2, History, Info, RotateCcw, ShieldCheck, X } from 'lucide-react'
import { api, type BackupJob, type RestorePreview } from '../../lib/api'
import { PageTitle, PanelHeading } from '../../components/ui'
import { ModalFrame } from '../../components/ModalFrame'
import { CompactTime } from '../../components/AuditDateRange'

type SaveMethod = 'save_dialog' | 'download'
type SavePicker = (options: { suggestedName: string; types: { description: string; accept: Record<string, string[]> }[] }) => Promise<{ createWritable: () => Promise<WritableStream> }>

export const sizeLabel = (bytes = 0) => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
export const dateTimeLabel = (value?: string | null) => value ? new Date(value).toLocaleString('en-IN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'Never'

/** Lets the user choose where to save (Chrome / Edge). Other browsers fall back to a normal download. Returns null when cancelled. */
export async function saveBackupFile(url: string, fileName: string): Promise<SaveMethod | null> {
  const picker = (window as unknown as { showSaveFilePicker?: SavePicker }).showSaveFilePicker
  if (picker) {
    let handle
    try {
      handle = await picker({ suggestedName: fileName, types: [{ description: 'Vridhi backup', accept: { 'application/octet-stream': ['.vbak'] } }] })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return null
      throw error
    }
    const response = await fetch(`/api/v1${url}`, { credentials: 'include' })
    if (!response.ok || !response.body) throw new Error('The backup file could not be downloaded. Try again.')
    await response.body.pipeTo(await handle.createWritable())
    return 'save_dialog'
  }
  const link = document.createElement('a')
  link.href = `/api/v1${url}`
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  return 'download'
}

export function PendingBackupBanner({ csrf }: { csrf: string }) {
  const queryClient = useQueryClient()
  const status = useQuery({ queryKey: ['backup-status'], queryFn: api.backupStatus, refetchInterval: 5 * 60 * 1000 })
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem('vridhi-backup-later') || '')
  const [awaitingDownload, setAwaitingDownload] = useState(false)
  const pending = status.data?.pending
  const save = useMutation({
    mutationFn: async () => {
      const method = await saveBackupFile('/backup/pending/download', pending!.file)
      if (method === 'save_dialog') await api.confirmPendingSaved(method, csrf)
      if (method === 'download') setAwaitingDownload(true)
      return method
    },
    onSuccess: method => { if (method === 'save_dialog') void queryClient.invalidateQueries({ queryKey: ['backup-status'] }) },
  })
  const confirm = useMutation({ mutationFn: () => api.confirmPendingSaved('download', csrf), onSuccess: () => { setAwaitingDownload(false); void queryClient.invalidateQueries({ queryKey: ['backup-status'] }) } })
  if (!pending || dismissed === pending.id) return null
  return <div className="backup-pending-banner" role="status">
    <DatabaseBackup size={17} aria-hidden="true" />
    <span><strong>Daily backup ready.</strong> {dateTimeLabel(pending.created_at)} · {sizeLabel(pending.file_bytes)}. Save it, then upload it to Google Drive or another safe place.</span>
    {save.error && <span className="form-error">{save.error.message}</span>}
    {awaitingDownload
      ? <button className="button-primary" disabled={confirm.isPending} onClick={() => confirm.mutate()}>I've saved it</button>
      : <button className="button-primary" disabled={save.isPending} onClick={() => save.mutate()}><Download size={15} />{save.isPending ? 'Saving…' : 'Save backup'}</button>}
    <button type="button" className="text-action" onClick={() => { sessionStorage.setItem('vridhi-backup-later', pending.id); setDismissed(pending.id) }}>Later</button>
  </div>
}

export function BackupRestore({ csrf }: { csrf: string }) {
  const queryClient = useQueryClient()
  const status = useQuery({ queryKey: ['backup-status'], queryFn: api.backupStatus })
  const [helpOpen, setHelpOpen] = useState(false)
  const data = status.data
  return <div className="backup-restore">
    <PageTitle eyebrow="COMPANY DATA" title="Backup & Restore" subtitle="Save one encrypted file with all projects, finances, users, audit history and documents. Keep it off this computer." action={<span className="row-action-tooltip" data-tooltip="How backups work"><button type="button" className="icon-button" aria-label="How backups work" aria-haspopup="dialog" onClick={() => setHelpOpen(true)}><Info size={17} aria-hidden="true" /></button></span>} />
    {data && <div className={`backup-health${data.stale || !data.last_saved_at ? ' stale' : ''}`} role="status">
      {data.stale || !data.last_saved_at ? <AlertTriangle size={17} aria-hidden="true" /> : <ShieldCheck size={17} aria-hidden="true" />}
      <span><strong>Last saved backup:</strong> {dateTimeLabel(data.last_saved_at)}</span>
      <span className="backup-health-divider">·</span>
      <span><strong>Daily backup:</strong> {data.schedule.enabled ? `On at ${data.schedule.time}` : 'Off'}</span>
      <span className="backup-health-divider">·</span>
      <span><strong>Last restore:</strong> {data.last_restore ? `${dateTimeLabel(data.last_restore.performed_at)} by ${data.last_restore.performed_by}` : 'Never'}</span>
      {!data.last_saved_at && <span className="backup-health-warning">Create a backup and keep it off this computer.</span>}
      {data.stale && <span className="backup-health-warning">No backup has been saved in the last 2 days.</span>}
      {data.schedule.last_error && <span className="backup-health-warning">Last daily backup failed: {data.schedule.last_error}</span>}
    </div>}
    {data?.pending && <PendingBackupBanner csrf={csrf} />}
    <div className="backup-sections">
      <CreateBackup csrf={csrf} activeJob={data?.active_job || null} busy={!!data?.busy} onChanged={() => void queryClient.invalidateQueries({ queryKey: ['backup-status'] })} />
      {data?.can_restore && <DailySchedule csrf={csrf} schedule={data.schedule} onChanged={() => void queryClient.invalidateQueries({ queryKey: ['backup-status'] })} />}
      {data?.can_restore && <RestoreBackup csrf={csrf} />}
    </div>
    {helpOpen && <ModalFrame title="How backups work" className="backup-help-modal" onClose={() => setHelpOpen(false)}><div className="backup-help">
      <p><strong>What is included:</strong> every project, purchase order, inventory, labour, cash flow, Company Cashbook entry, user account, permission, audit history and uploaded document.</p>
      <p><strong>Passphrase:</strong> the file is encrypted. Without the passphrase nobody can open it, including us. Store the passphrase separately from the file.</p>
      <p><strong>Keep it safe:</strong> Save the file, then upload it to Google Drive or email it to yourself. The app does not keep copies on this computer.</p>
      <p><strong>Daily backup:</strong> prepared at the set time (or when the app next starts, if this computer was off). You will see a “Daily backup ready” prompt to save it.</p>
      <p><strong>Restore:</strong> Global access only. It replaces <em>all</em> current data with the backup and signs everyone out. A safety copy of the current data is made first.</p>
    </div></ModalFrame>}
  </div>
}

function PassphraseFields({ passphrase, confirm, setPassphrase, setConfirm, idPrefix }: { passphrase: string; confirm: string; setPassphrase: (value: string) => void; setConfirm: (value: string) => void; idPrefix: string }) {
  return <>
    <label className="field">Passphrase<input id={`${idPrefix}-passphrase`} type="password" autoComplete="new-password" minLength={8} required value={passphrase} onChange={event => setPassphrase(event.target.value)} /></label>
    <label className="field">Confirm passphrase<input id={`${idPrefix}-confirm`} type="password" autoComplete="new-password" minLength={8} required value={confirm} onChange={event => setConfirm(event.target.value)} /></label>
  </>
}

function CreateBackup({ csrf, activeJob, busy, onChanged }: { csrf: string; activeJob: BackupJob | null; busy: boolean; onChanged: () => void }) {
  const [passphrase, setPassphrase] = useState('')
  const [confirm, setConfirm] = useState('')
  const [job, setJob] = useState<BackupJob | null>(activeJob)
  const [awaitingDownload, setAwaitingDownload] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  useEffect(() => { if (activeJob && !job) setJob(activeJob) }, [activeJob, job])
  useEffect(() => {
    if (job?.status !== 'running') return
    const timer = window.setInterval(() => { void api.backupJob(job.id).then(setJob).catch(reason => setError(reason instanceof Error ? reason.message : 'Backup status is unavailable')) }, 1500)
    return () => window.clearInterval(timer)
  }, [job?.id, job?.status])
  const start = useMutation({ mutationFn: () => api.startBackup(passphrase, csrf), onSuccess: result => { setJob(result); setPassphrase(''); setConfirm(''); setMessage(''); setError('') }, onError: reason => setError(reason.message) })
  const finish = async (method: SaveMethod) => {
    if (!job) return
    await api.confirmBackupSaved(job.id, method, csrf)
    setJob(null); setAwaitingDownload(false); setMessage(`Backup saved (${job.file_name}). Now upload it to Google Drive or another safe place.`); onChanged()
  }
  const save = useMutation({
    mutationFn: async () => {
      if (!job?.file_name) return
      const method = await saveBackupFile(`/backup/jobs/${job.id}/download`, job.file_name)
      if (method === 'save_dialog') await finish(method)
      if (method === 'download') setAwaitingDownload(true)
    },
    onError: reason => setError(reason.message),
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    setError('')
    if (passphrase.length < 8) { setError('Use at least 8 characters for the passphrase.'); return }
    if (passphrase !== confirm) { setError('Passphrases do not match.'); return }
    start.mutate()
  }
  return <section className="panel backup-panel">
    <PanelHeading title="Create backup" meta="Full copy of all company data and documents" />
    {message && <p className="backup-success" role="status"><FileCheck2 size={16} aria-hidden="true" />{message}</p>}
    {job?.status === 'running' && <div className="backup-progress" role="status"><span className="backup-spinner" aria-hidden="true" /><span>{job.step || 'Working'}…</span></div>}
    {job?.status === 'ready' && <div className="backup-ready">
      <div><strong>{job.file_name}</strong><span>{sizeLabel(job.file_bytes)} · Ready to save</span></div>
      <div className="backup-ready-actions">
        {awaitingDownload
          ? <button className="button-primary" onClick={() => void finish('download').catch(reason => setError(reason.message))}>I've saved it</button>
          : <button className="button-primary" disabled={save.isPending} onClick={() => save.mutate()}><Download size={15} />{save.isPending ? 'Saving…' : 'Save to…'}</button>}
        <button className="button-secondary" onClick={() => void api.discardBackup(job.id, csrf).then(() => { setJob(null); setAwaitingDownload(false); onChanged() })}>Discard</button>
      </div>
      {awaitingDownload && <p className="field-hint">Your browser downloaded the file. Move it to a safe place, then select “I've saved it”.</p>}
    </div>}
    {job?.status === 'failed' && <p className="form-error" role="alert">{job.error || 'Backup failed.'}</p>}
    {(!job || job.status === 'failed') && <form className="backup-form" onSubmit={submit}>
      <PassphraseFields idPrefix="backup" passphrase={passphrase} confirm={confirm} setPassphrase={setPassphrase} setConfirm={setConfirm} />
      <p className="field-hint full">At least 8 characters. You need this passphrase to restore. It cannot be recovered.</p>
      <div className="full backup-form-actions"><button className="button-primary" disabled={start.isPending || busy}><DatabaseBackup size={15} />{busy ? 'Another backup is running…' : 'Create backup'}</button></div>
    </form>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>
}

function DailySchedule({ csrf, schedule, onChanged }: { csrf: string; schedule: { enabled: boolean; time: string; passphrase_set: boolean; last_run_at: string | null }; onChanged: () => void }) {
  const [enabled, setEnabled] = useState(schedule.enabled || !schedule.passphrase_set)
  const [time, setTime] = useState(schedule.time)
  const [changePassphrase, setChangePassphrase] = useState(!schedule.passphrase_set)
  const [passphrase, setPassphrase] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const update = useMutation({
    mutationFn: () => api.updateBackupSchedule({ enabled, time, ...(changePassphrase && passphrase ? { passphrase } : {}) }, csrf),
    onSuccess: () => { setSaved(true); setPassphrase(''); setConfirm(''); setChangePassphrase(false); onChanged() },
    onError: reason => setError(reason.message),
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    setError(''); setSaved(false)
    if (changePassphrase && (passphrase || enabled)) {
      if (passphrase.length < 8) { setError('Use at least 8 characters for the passphrase.'); return }
      if (passphrase !== confirm) { setError('Passphrases do not match.'); return }
    }
    update.mutate()
  }
  return <section className="panel backup-panel">
    <PanelHeading title="Daily backup" meta={schedule.last_run_at ? `Last prepared ${dateTimeLabel(schedule.last_run_at)}` : 'Prepared automatically, saved by you'} />
    <form className="backup-form" onSubmit={submit}>
      <label className="backup-toggle full"><input type="checkbox" checked={enabled} onChange={event => setEnabled(event.target.checked)} /><CalendarClock size={15} aria-hidden="true" />Prepare a backup every day</label>
      <div className="field backup-time-picker"><span>Time</span><CompactTime label="Daily backup time" value={time} onChange={setTime} /></div>
      <p className="field-hint backup-time-hint">If this computer is off at that time, the backup is prepared the next time the app starts.</p>
      {changePassphrase
        ? <PassphraseFields idPrefix="schedule" passphrase={passphrase} confirm={confirm} setPassphrase={setPassphrase} setConfirm={setConfirm} />
        : <p className="full backup-passphrase-set"><ShieldCheck size={15} aria-hidden="true" />Daily backup passphrase is set. <button type="button" className="text-action" onClick={() => setChangePassphrase(true)}>Change passphrase</button></p>}
      <div className="full backup-form-actions"><button className="button-primary" disabled={update.isPending}>{update.isPending ? 'Saving…' : 'Save settings'}</button>{saved && <span className="backup-saved-note">Saved</span>}</div>
    </form>
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>
}

function RestoreBackup({ csrf }: { csrf: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [passphrase, setPassphrase] = useState('')
  const [preview, setPreview] = useState<RestorePreview | null>(null)
  const [confirmText, setConfirmText] = useState('')
  const [job, setJob] = useState<BackupJob | null>(null)
  const [error, setError] = useState('')
  const [inputKey, setInputKey] = useState(0)
  const check = useMutation({ mutationFn: () => api.uploadRestoreFile(file!, passphrase, csrf), onSuccess: result => { setPreview(result); setPassphrase(''); setError('') }, onError: reason => setError(reason.message) })
  const apply = useMutation({ mutationFn: () => api.applyRestore(preview!.upload_id, csrf), onSuccess: result => { setJob(result); setPreview(null) }, onError: reason => setError(reason.message) })
  useEffect(() => {
    if (job?.status !== 'running' || !job.token) return
    const token = job.token
    const timer = window.setInterval(() => { void api.restoreJob(job.id, token).then(next => setJob({ ...next, token })).catch(() => undefined) }, 1500)
    return () => window.clearInterval(timer)
  }, [job?.id, job?.status, job?.token])
  const reset = () => { if (preview) void api.cancelRestore(preview.upload_id, csrf).catch(() => undefined); setPreview(null); setFile(null); setConfirmText(''); setPassphrase(''); setError(''); setInputKey(key => key + 1) }
  return <section className="panel backup-panel backup-restore-panel">
    <PanelHeading title="Restore from backup" meta="Global access only · Replaces all current data" />
    {job ? <div className="backup-restore-status">
      {job.status === 'running' && <div className="backup-progress" role="status"><span className="backup-spinner" aria-hidden="true" /><span>{job.step || 'Restoring'}… Do not close this page.</span></div>}
      {job.status === 'done' && <div className="backup-success" role="status"><FileCheck2 size={16} aria-hidden="true" /><span>Restore complete. Everyone has been signed out. Sign in again with the accounts from the backup.</span><button className="button-primary" onClick={() => window.location.reload()}>Go to sign in</button></div>}
      {job.status === 'failed' && <div><p className="form-error" role="alert">{job.error || 'Restore failed.'} Your current data was not changed.</p><button className="button-secondary" onClick={() => { setJob(null); reset() }}>Try again</button></div>}
    </div> : preview ? <div className="backup-preview">
      <dl className="backup-preview-details">
        <div><dt>File</dt><dd>{preview.file}</dd></div>
        <div><dt>Backup made</dt><dd>{dateTimeLabel(preview.preview.created_at)}</dd></div>
        <div><dt>Made by</dt><dd>{preview.preview.created_by}</dd></div>
        <div><dt>Documents</dt><dd>{preview.preview.uploads} ({sizeLabel(preview.preview.upload_bytes)})</dd></div>
        {preview.preview.highlights.map(item => <div key={item.label}><dt>{item.label}</dt><dd>{item.count}</dd></div>)}
      </dl>
      {preview.preview.needs_upgrade && <p className="field-hint">This backup is from an earlier version. It will be upgraded automatically during restore.</p>}
      <div className="backup-restore-warning" role="alert"><AlertTriangle size={17} aria-hidden="true" /><div><strong>All current data will be replaced with this backup.</strong><span>Anything recorded after {dateTimeLabel(preview.preview.created_at)} will be lost. Everyone is signed out. A safety copy of the current data is made first.</span></div></div>
      <form className="backup-form" onSubmit={event => { event.preventDefault(); if (confirmText === 'RESTORE') apply.mutate() }}>
        <label className="field full">Type RESTORE to confirm<input autoComplete="off" value={confirmText} onChange={event => setConfirmText(event.target.value)} /></label>
        <div className="full backup-form-actions"><button type="button" className="button-secondary" onClick={reset}><X size={15} />Cancel</button><button className="button-danger" disabled={confirmText !== 'RESTORE' || apply.isPending}><RotateCcw size={15} />{apply.isPending ? 'Starting…' : 'Restore all data'}</button></div>
      </form>
    </div> : <form className="backup-form" onSubmit={event => { event.preventDefault(); if (!file) { setError('Choose a .vbak backup file.'); return } check.mutate() }}>
      <label className="field">Backup file (.vbak)<input key={inputKey} type="file" accept=".vbak" required onChange={event => { setFile(event.target.files?.[0] || null); setError('') }} /></label>
      <label className="field">Passphrase<input type="password" autoComplete="off" required value={passphrase} onChange={event => setPassphrase(event.target.value)} /></label>
      <div className="full backup-form-actions"><button className="button-secondary" disabled={check.isPending || !file || !passphrase}><History size={15} />{check.isPending ? 'Checking file…' : 'Check backup'}</button></div>
      <p className="field-hint full">The file is checked first. Nothing changes until you confirm.</p>
    </form>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>
}
