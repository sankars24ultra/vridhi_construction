import vridhiLogo from '../../../../images/logo-transparent.png'

interface ExportHeaderProps {
  reportTitle: string
  projectName?: string
  projectLocation?: string
  asOf?: string
}

export function ExportHeader({ reportTitle, projectName, projectLocation, asOf }: ExportHeaderProps) {
  const printDate = asOf
    ? new Date(asOf).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })

  return (
    <div className="export-company-header" aria-hidden="true">
      <div className="export-header-left">
        <img src={vridhiLogo} alt="Vridhi Constructions & Designs" className="export-company-logo" />
        <div className="export-company-details">
          <strong className="export-company-name">VRIDHI CONSTRUCTIONS &amp; DESIGNS</strong>
          <span className="export-company-tagline">Building trust · Creating futures</span>
          <span className="export-company-sub">Company Address</span>
        </div>
      </div>
      <div className="export-header-right">
        <div className="export-report-title">{reportTitle}</div>
        {projectName && <div className="export-project-name">{projectName}</div>}
        {projectLocation && <div className="export-project-location">{projectLocation}</div>}
        <div className="export-report-date">Exported on {printDate}</div>
      </div>
    </div>
  )
}
