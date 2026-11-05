import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowRight, ArrowUpRight, Armchair, BriefcaseBusiness, Building2, Check, ClipboardList, Clock, Hammer, HardHat, House, Layers3, Lightbulb, Mail, MapPin, MessageSquare, Moon, Phone, Ruler, Sun, X, type LucideIcon } from 'lucide-react'
import './CompanyWebsite.css'

const serviceContent = [
  { title: 'Construction', icon: Building2, summary: 'Build a new home or business space, or thoughtfully improve an existing one.', detail: 'Explore construction support for new builds, renovations and extensions, with the work shaped around the agreed plans and the way you want your space to work.', areas: ['New residential and commercial spaces', 'Renovation and extension possibilities', 'Site preparation, construction and finishing'] },
  { title: 'Design & planning', icon: Layers3, summary: 'Shape the look and function of your space, inside and out.', detail: 'From early design guidance to considered plans, explore layouts, materials, interiors and practical details for a new space or one ready for change.', areas: ['Early ideas and design direction', 'Layouts, materials and interior design', 'Planning for new builds and existing spaces'] },
  { title: 'Project coordination', icon: HardHat, summary: 'Keep people, decisions and progress connected as your project takes shape.', detail: 'For a home, business space or another agreed project, clear coordination helps connect the plan with site activity and the conversations that move the work forward.', areas: ['Coordinating agreed project stages', 'Progress reviews and upcoming decisions', 'Clear communication about changes and next steps'] },
]
const steps = [
  { title: 'Your Aspirations', text: 'Every space starts with a conversation. Explore your ideas, priorities and the way you want to live or work.', image: 'A project conversation with inspiration boards, a site map and a planning notebook.', activities: ['Discuss your lifestyle, business needs and design inspiration.', 'Review available site information and practical constraints.', 'Explore your budget range, priorities and preferred timing.'], outcome: 'A shared project brief to guide the next discussion.', involvement: 'Bring your ideas, site details and the questions that matter to you.' },
  { title: 'Thoughtful Design', text: 'Give the vision a shape. Consider layouts, materials and practical details in a clear design direction.', image: 'An architectural floor plan with a ruler, material samples and a building sketch.', activities: ['Explore layouts and how people will move through the space.', 'Discuss materials, finishes and the balance of form and function.', 'Review the proposed scope and decisions before construction.'], outcome: 'An agreed design direction, with scope and next steps to be confirmed.', involvement: 'Review the options and share feedback on what feels right for your space.' },
  { title: 'Taking Shape', text: 'Bring the plan into the real world, with coordinated work and careful attention to each stage.', image: 'A building under construction with a tower crane, structural frame and site barriers.', activities: ['Coordinate site activities around the agreed construction plan.', 'Discuss progress, material choices and upcoming decisions.', 'Review proposed changes and their implications before agreement.'], outcome: 'A space taking shape through reviewed construction stages.', involvement: 'Stay involved in agreed reviews and discuss changes with the project team.' },
  { title: 'New Beginnings', text: 'Review the finishing touches and walk through the space, bringing the journey from idea to reality together.', image: 'A finished concept home with landscaping, an entrance path and a handover key.', activities: ['Walk through the completed scope and review finishing details.', 'Record outstanding items and agree how they will be addressed.', 'Discuss applicable handover information and care guidance.'], outcome: 'A reviewed handover, with any remaining actions clearly recorded.', involvement: 'Join the walkthrough and raise questions before completing handover.' },
]
const alternativeSteps = [
  { title: 'Your Aspirations', text: 'Before there is a plan, there is your story. Tell us what you imagine, what matters most and how you want your future space to feel.', activities: ['Share the everyday needs, ideas and inspirations behind your project.', 'Explore your site, budget priorities and preferred timing together.', 'Talk through your questions and identify what needs further review.'], outcome: 'A shared understanding of your priorities, ready to guide the design conversation.', involvement: 'Bring your wish list, any available site information and the ideas you are excited to explore.' },
  { title: 'Thoughtful Design', text: 'Your priorities become a design direction. Together, we explore how layout, light, materials and practical details can work for the way you live or do business.', activities: ['Consider layouts that connect your needs with the possibilities of the site.', 'Explore materials and finishes in the context of your budget and preferences.', 'Review the proposed design, scope and next steps before moving ahead.'], outcome: 'A considered design direction shaped by your feedback, with the scope and next steps to be agreed.', involvement: 'Tell us what feels right, ask questions and review the choices before decisions are finalised.' },
  { title: 'Taking Shape', text: 'Your plans take shape through coordinated work, thoughtful details and clear conversations at every stage.', activities: ['Coordinate teams and site activities around the agreed plans.', 'Review progress and discuss upcoming materials and finishing decisions.', 'Consider proposed changes and their cost or timing implications before agreement.'], outcome: 'Your space taking shape through reviewed stages, with changes discussed rather than assumed.', involvement: 'Take part in agreed progress reviews and share feedback as your space develops.' },
  { title: 'New Beginnings', text: 'The final walkthrough is more than a project milestone. It is a chance to see your ideas brought together and prepare for the life or work that comes next.', activities: ['Walk through the agreed completed scope and review the finishing details.', 'Record any outstanding items and agree the next actions together.', 'Discuss applicable handover documents and guidance for caring for your space.'], outcome: 'A reviewed handover and a clear record of any remaining actions, ready for your next chapter.', involvement: 'Explore the space with us, ask your final questions and review the handover information.' },
]
const projectInterests = [
  { title: 'A new home', icon: House, description: 'A space that fits your everyday life, with room for what comes next.', topics: ['Location and available plot details', 'Rooms, lifestyle and future needs', 'Preferred style and budget range', 'Target start date and any existing plans'] },
  { title: 'A business space', icon: BriefcaseBusiness, description: 'A practical environment shaped around your people, customers and work.', topics: ['Business use and location', 'Space, access and operational needs', 'Design priorities and budget range', 'Opening plans and target timeline'] },
  { title: 'A renovation or extension', icon: Hammer, description: 'Make an existing space work better, or explore how it might grow with your needs.', topics: ['What you would like to improve or add', 'Existing plans, photos or site measurements', 'How the space needs to work during the project', 'Budget priorities and preferred timing'] },
  { title: 'Interior design', icon: Armchair, description: 'Explore how layouts, materials, lighting and finishes can shape the way your space feels and functions.', topics: ['Rooms or areas you would like to focus on', 'Styles, colours or spaces that inspire you', 'Furniture, storage or lighting needs', 'Any existing plans, measurements or material preferences'] },
  { title: 'Design guidance', icon: Lightbulb, description: 'Bring your early ideas into focus before deciding the next step.', topics: ['Photos, sketches or inspiration', 'Site dimensions, if available', 'What works and what you want to change', 'Questions about layouts, materials or finishes'] },
  { title: 'Something else', icon: MessageSquare, description: 'Have a different project or an early question? Start with what you know, and we can identify what to explore next.', topics: ['The kind of space or project you have in mind', 'Where you are in the planning process', 'What you would most like help thinking through', 'Any questions or constraints you already know'] },
]
function ProjectGuide({ title, heading, intro, items, selected, onSelect, eyebrow, listHeading, note, noteText, nextStep, detailId }: { title: string; heading: ReactNode; intro: string; items: { title: string; icon: LucideIcon; description: string; topics: string[]; nextStep?: string }[]; selected: number; onSelect: (index: number) => void; eyebrow: string; listHeading: string; note: string; noteText: string; nextStep: string; detailId: string }) {
  const interest = items[selected]
  return (
    <section className="website-section website-project-alternative" id="project-discussion" aria-labelledby={`${detailId}-title`}>
      <div className="website-alternative-heading">
        <div><p className="website-eyebrow">{title}</p><h2 id={`${detailId}-title`}>{heading}</h2></div>
        <div><p>{intro}</p></div>
      </div>
      <div className="website-project-guide">
        <div className="website-project-paths" role="group" aria-label="Choose a project starting point">
          {items.map((item, index) => <button key={item.title} type="button" aria-pressed={selected === index} aria-controls={detailId} onMouseEnter={() => onSelect(index)} onFocus={() => onSelect(index)} onClick={() => onSelect(index)}><span className="website-project-path-icon"><item.icon size={19} aria-hidden="true" /></span><span>{item.title}</span><ArrowRight size={18} aria-hidden="true" /></button>)}
          <div className="website-project-guide-note"><MessageSquare size={20} aria-hidden="true" /><p><strong>{note}</strong><br />{noteText}</p></div>
        </div>
        <div className="website-project-guide-detail" id={detailId} aria-live="polite">
          <p className="website-eyebrow">{eyebrow}</p>
          <h3>{interest.title}</h3>
          <p className="website-project-guide-description">{interest.description}</p>
          <div className="website-project-guide-topics"><h4>{listHeading}</h4><ul>{interest.topics.map(topic => <li key={topic}><Check size={17} aria-hidden="true" />{topic}</li>)}</ul></div>
          <div className="website-project-guide-next"><span>YOUR NEXT STEP</span><p>{interest.nextStep ?? nextStep}</p><a href="#contact">Explore Contact <ArrowUpRight size={15} aria-hidden="true" /></a></div>
        </div>
      </div>
    </section>
  )
}

function ProjectStartingPoints() {
  const [selected, setSelected] = useState(0)
  return <ProjectGuide title="WHAT WE DO · PROJECT STARTING POINTS" heading={<>Every project starts somewhere.<br />Let&apos;s find your starting point.</>} intro="Every project starts somewhere different. Choose the path that feels closest to yours and see what could help shape an initial conversation." items={projectInterests} selected={selected} onSelect={setSelected} eyebrow="A GOOD PLACE TO BEGIN" listHeading="Bring these to the conversation" note="A conversation, not a commitment." noteText="Feasibility, pricing and timelines need a project-specific review." nextStep="When you’re ready, explore our contact details and decide how you’d like to connect." detailId="project-discussion-detail" />
}

function JourneyIllustration({ stage }: { stage: number }) {
  return (
    <svg viewBox="0 0 520 360" role="img" aria-label={steps[stage].image}>
      <rect width="520" height="360" rx="12" fill="#E4EEF9" />
      <path d="M0 60H520M0 120H520M0 180H520M0 240H520M0 300H520M65 0V360M130 0V360M195 0V360M260 0V360M325 0V360M390 0V360M455 0V360" stroke="#285A8E" opacity=".07" />
      <circle cx="430" cy="72" r="44" fill="#C4D5E7" />
      {stage === 0 && <g>
        <rect x="58" y="52" width="216" height="150" rx="8" fill="#fff" stroke="#91A9C3" />
        <rect x="74" y="69" width="86" height="80" fill="#C4D5E7" />
        <path d="M85 130L116 98L148 130M95 130V145H139V130" fill="none" stroke="#285A8E" strokeWidth="5" />
        <path d="M177 79H254M177 97H241M177 125H253M177 143H231M77 174H245" stroke="#91A9C3" strokeWidth="6" />
        <rect x="300" y="118" width="151" height="115" rx="8" fill="#fff" stroke="#91A9C3" />
        <path d="M321 141L348 130L376 143L425 132V205L391 218L355 205L321 214Z" fill="#C4D5E7" />
        <path d="M380 149C360 149 354 171 380 194C406 171 400 149 380 149Z" fill="#285A8E" /><circle cx="380" cy="166" r="6" fill="#fff" />
        <path d="M40 265H480" stroke="#243244" strokeWidth="13" strokeLinecap="round" />
        <path d="M81 271V322M439 271V322" stroke="#526579" strokeWidth="10" />
        <path d="M179 236L252 220L324 236L252 251Z" fill="#fff" stroke="#91A9C3" strokeWidth="2" />
        <circle cx="104" cy="223" r="20" fill="#91A9C3" /><path d="M104 214V233M95 223H113" stroke="#fff" strokeWidth="3" />
      </g>}
      {stage === 1 && <g>
        <path d="M67 65L369 49L391 277L89 293Z" fill="#fff" stroke="#91A9C3" strokeWidth="2" />
        <g fill="none" stroke="#285A8E" strokeWidth="6">
          <path d="M113 105H332V245H113ZM113 170H205V105M205 170V245M263 105V197H332" />
          <path d="M147 105H180M113 208V226M294 245H315" stroke="#C4D5E7" strokeWidth="9" />
        </g>
        <path d="M122 82H322M97 109V245" stroke="#91A9C3" strokeDasharray="4 5" />
        <path d="M82 309H370L82 248Z" fill="#91C5FF" stroke="#285A8E" strokeWidth="2" /><path d="M106 296H229L106 271Z" fill="#E4EEF9" />
        <rect x="395" y="158" width="66" height="55" rx="4" fill="#526579" /><rect x="385" y="200" width="66" height="55" rx="4" fill="#91A9C3" /><rect x="375" y="243" width="66" height="55" rx="4" fill="#C4D5E7" />
        <path d="M351 84L371 82L390 228L380 249L370 231Z" fill="#285A8E" />
      </g>}
      {stage === 2 && <g>
        <path d="M50 302H473" stroke="#91A9C3" strokeWidth="6" />
        <path d="M351 51V298M329 298L351 252L374 298M338 93H463L351 51L234 93H338" fill="none" stroke="#285A8E" strokeWidth="7" strokeLinejoin="round" />
        <path d="M271 94V152M260 152H282" stroke="#526579" strokeWidth="4" />
        <rect x="85" y="172" width="224" height="127" fill="#C4D5E7" />
        <path d="M85 169H309M85 220H309M85 267H309M94 172V298M161 172V298M230 172V298M300 172V298" stroke="#526579" strokeWidth="8" />
        <rect x="105" y="231" width="44" height="27" fill="#91A9C3" /><rect x="173" y="182" width="44" height="26" fill="#91A9C3" />
        <path d="M67 276H325" stroke="#fff" strokeWidth="12" /><path d="M73 276H107M138 276H172M203 276H237M268 276H302" stroke="#285A8E" strokeWidth="12" />
        <path d="M73 283V315M320 283V315" stroke="#526579" strokeWidth="6" />
        <path d="M399 296L416 250L432 296Z" fill="#285A8E" /><path d="M405 279H426" stroke="#fff" strokeWidth="5" />
      </g>}
      {stage === 3 && <g>
        <path d="M67 296H462" stroke="#91A9C3" strokeWidth="5" />
        <rect x="121" y="126" width="244" height="169" fill="#fff" />
        <path d="M103 130L241 60L382 130Z" fill="#285A8E" />
        <rect x="149" y="160" width="65" height="59" rx="3" fill="#91C5FF" /><path d="M181 160V219M149 188H214" stroke="#fff" strokeWidth="4" />
        <rect x="272" y="160" width="65" height="59" rx="3" fill="#91C5FF" /><path d="M304 160V219M272 188H337" stroke="#fff" strokeWidth="4" />
        <rect x="226" y="230" width="36" height="65" fill="#526579" /><circle cx="254" cy="264" r="3" fill="#fff" />
        <path d="M226 295L204 350H286L262 295" fill="#C4D5E7" />
        <path d="M85 294V218M405 294V218" stroke="#526579" strokeWidth="6" /><circle cx="85" cy="210" r="28" fill="#91A9C3" /><circle cx="405" cy="210" r="28" fill="#91A9C3" />
        <circle cx="422" cy="80" r="33" fill="#fff" stroke="#285A8E" strokeWidth="4" /><circle cx="413" cy="75" r="9" fill="none" stroke="#285A8E" strokeWidth="5" /><path d="M420 82L439 101M430 92L437 85" stroke="#285A8E" strokeWidth="5" />
      </g>}
    </svg>
  )
}

function WebsiteJourney() {
  const [selectedStage, setSelectedStage] = useState(0)
  const journeySteps = alternativeSteps
  const stage = journeySteps[selectedStage]
  const titleId = 'website-journey-title'
  const detailId = 'website-step-detail'
  return (
    <section className="website-approach" id="approach" aria-labelledby={titleId}>
      <div className="website-section">
        <div className="website-alternative-heading">
          <div><p className="website-eyebrow">THE JOURNEY</p><h2 id={titleId}>Your story.<br />Thoughtfully brought to life.</h2></div>
          <div><p>Your project is personal. From the first conversation to the final walkthrough, explore how your priorities guide each step of the journey.</p></div>
        </div>
        <div className="website-steps website-hover-steps" aria-label="Preview journey stages">
          {journeySteps.map((step, index) => <button key={step.title} type="button" aria-pressed={selectedStage === index} aria-controls={detailId} onMouseEnter={() => setSelectedStage(index)} onFocus={() => setSelectedStage(index)} onClick={() => setSelectedStage(index)}><span>0{index + 1}</span>{step.title}<ArrowRight size={18} /></button>)}
        </div>
        <div className="website-step-detail" id={detailId} aria-live="polite">
          <figure className="website-journey-visual"><JourneyIllustration stage={selectedStage} /></figure>
          <div className="website-journey-copy"><h3>{stage.title}</h3><p>{stage.text}</p>
            <h4>What we explore together</h4><ul>{stage.activities.map(activity => <li key={activity}><Check size={17} aria-hidden="true" />{activity}</li>)}</ul>
            <div className="website-journey-outcome"><h4>Intended outcome</h4><p>{stage.outcome}</p></div>
            <h4>Your part in the journey</h4><p>{stage.involvement}</p>
          </div>
        </div>
        <p className="website-journey-disclaimer">Illustrative process for discussion. Deliverables, reviews and responsibilities depend on the agreed project scope.</p>
      </div>
    </section>
  )
}

export default function CompanyWebsite() {
  const websiteRef = useRef<HTMLDivElement>(null)
  const legalDialogRef = useRef<HTMLDialogElement>(null)
  const [copyrightYear] = useState(() => new Date().getFullYear())
  const [legalNotice, setLegalNotice] = useState<'privacy' | 'terms'>('privacy')
  const openLegalNotice = (notice: 'privacy' | 'terms') => {
    setLegalNotice(notice)
    legalDialogRef.current?.showModal()
  }
  useEffect(() => {
    const target = document.getElementById(window.location.hash.slice(1))
    if (target && websiteRef.current?.contains(target)) target.scrollIntoView()
  }, [])
  useEffect(() => {
    const website = websiteRef.current
    if (!website || !('IntersectionObserver' in window)) return
    const sections = website.querySelectorAll<HTMLElement>('main > section:not(.website-hero)')
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('website-revealed')
        } else if (entry.boundingClientRect.top >= window.innerHeight && !entry.target.contains(document.activeElement)) {
          entry.target.classList.remove('website-revealed')
        }
      }
    }, { threshold: 0, rootMargin: '0px 0px -40px 0px' })
    for (const section of sections) {
      section.classList.add('website-scroll-reveal')
      observer.observe(section)
    }
    const revealFocusedSection = (event: FocusEvent) => {
      if (!(event.target instanceof Element)) return
      const section = event.target.closest('.website-scroll-reveal')
      if (section) {
        section.classList.add('website-revealed')
      }
    }
    const revealNavigationSection = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || !(event.target instanceof Element)) return
      const link = event.target.closest<HTMLAnchorElement>('.website-header a[href^="#"]')
      if (!link) return
      const section = document.getElementById(link.hash.slice(1))
      if (!section || !website.contains(section) || !section.classList.contains('website-scroll-reveal')) return
      const relatedSections = [section]
      if (section.id === 'about') {
        const clientSection = website.querySelector<HTMLElement>('.website-client-values')
        if (clientSection) relatedSections.push(clientSection)
      }
      for (const relatedSection of relatedSections) {
        relatedSection.classList.add('website-revealed')
        relatedSection.classList.remove('website-navigation-reveal')
      }
      void section.offsetWidth
      for (const relatedSection of relatedSections) relatedSection.classList.add('website-navigation-reveal')
    }
    website.addEventListener('focusin', revealFocusedSection)
    website.addEventListener('click', revealNavigationSection)
    return () => {
      observer.disconnect()
      website.removeEventListener('focusin', revealFocusedSection)
      website.removeEventListener('click', revealNavigationSection)
      for (const section of sections) section.classList.remove('website-scroll-reveal', 'website-revealed', 'website-navigation-reveal')
    }
  }, [])
  const [nightMode, setNightMode] = useState(() => {
    try { return localStorage.getItem('vridhi-website-color-mode') === 'dark' }
    catch (error) { console.warn('Unable to read the website theme preference.', error); return false }
  })
  useEffect(() => {
    try { localStorage.setItem('vridhi-website-color-mode', nightMode ? 'dark' : 'day') }
    catch (error) { console.warn('Unable to save the website theme preference.', error) }
  }, [nightMode])
  const [evening, setEvening] = useState(nightMode)
  return (
    <div className="company-website" data-theme={nightMode ? 'dark' : 'day'} ref={websiteRef}>
      <a className="website-skip" href="#website-main">Skip to content</a>
      <header className="website-header">
        <a className="website-brand" href="#home" aria-label="Vridhi home">
          <img src="/vridhi-logo.png" alt="" />
          <span><strong><span className="website-sr-only">VRIDHI</span></strong><small>CONSTRUCTIONS &amp; DESIGNS</small></span>
        </a>
        <nav aria-label="Company website">
          <a href="#home">Home</a>
          <a href="#about">About</a>
          <a href="#services">Services</a>
          <a href="#approach">Our approach</a>
          <a className="website-enquiry-link" href="#project-discussion">Plan your project</a>
          <a href="#contact">Contact</a>
          <button className="website-theme-toggle" type="button" role="switch" aria-label="Website night mode" aria-checked={nightMode} onClick={() => { setNightMode(!nightMode); setEvening(!nightMode) }}>
            {nightMode ? <Sun size={19} aria-hidden="true" /> : <Moon size={19} aria-hidden="true" />}
            <span className="website-theme-tooltip" aria-hidden="true">{nightMode ? 'Day mode' : 'Night mode'}</span>
          </button>
        </nav>
      </header>
      <main id="website-main">
        <section className="website-hero" id="home">
          <div className="website-hero-copy">
            <p className="website-eyebrow website-service-tagline"><span>ARCHITECTURE</span><span><Building2 size={16} aria-hidden="true" /> CONSTRUCTION</span><span><HardHat size={16} aria-hidden="true" /> INTERIOR DESIGN</span></p>
            <h1>Building <em>trust.</em><br />Creating <em>futures.</em></h1>
            <p>Thoughtful design. Purposeful construction. A clear vision for the spaces where life happens.</p>
            <div className="website-hero-actions"><a className="website-primary" href="#project-discussion">Let&apos;s shape your vision <ArrowUpRight size={17} /></a><a className="website-secondary" href="#services">Explore our services <ArrowDown size={17} /></a></div>
            <div className="website-hero-values"><span>Thoughtful design</span><span>Clear collaboration</span><span>Care in every detail</span></div>
          </div>
          <div className={`website-scene${evening ? ' is-evening' : ''}`}>
          <div className="website-architecture" role="img" aria-label={`Conceptual architecture in ${evening ? 'evening' : 'daylight'}, not an actual company project`}
            onPointerMove={event => {
              if (event.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
              const bounds = event.currentTarget.getBoundingClientRect()
              event.currentTarget.style.setProperty('--scene-x', `${((event.clientX - bounds.left) / bounds.width - .5) * 16}px`)
              event.currentTarget.style.setProperty('--scene-y', `${((event.clientY - bounds.top) / bounds.height - .5) * 12}px`)
            }}
            onPointerLeave={event => {
              event.currentTarget.style.removeProperty('--scene-x')
              event.currentTarget.style.removeProperty('--scene-y')
            }}>
            <div className="website-blueprint" />
            <div className="website-sun" />
            <div className="website-building website-building-back" />
            <div className="website-building website-building-front"><span /><span /><span /><span /><span /><span /></div>
            <div className="website-building website-building-side" />
            <div className="website-architecture-caption"><span>VISION INTO REALITY</span><strong>Designed with purpose.<br />Built with care.</strong><small>{evening ? 'Evening atmosphere' : 'Daylight & form'}</small></div>
          </div>
          <button className="website-scene-toggle" type="button" aria-pressed={evening} onClick={() => setEvening(!evening)}>{evening ? <Sun size={16} /> : <Moon size={16} />}{evening ? 'Show daylight' : 'See it at dusk'}</button>
          </div>
        </section>
        <section className="website-about website-section" id="about" aria-labelledby="website-about-title">
          <div><p className="website-eyebrow">ABOUT VRIDHI CONSTRUCTIONS &amp; DESIGNS</p><h2 id="website-about-title">Your vision.<br />Thoughtfully brought together.</h2></div>
          <div><p>A space should feel right for the people who use it. At Vridhi Constructions &amp; Designs, <strong>we bring architecture, structural construction and interior design together</strong> to shape spaces that are practical, personal and thoughtfully connected.</p><p>We begin with what matters to you: how you live or work, what you value and what you want your space to become. These priorities guide the conversation, from the layout and structural needs to the materials and finishing touches.</p><p>Our aim is to make the journey as considered as the design itself, through clear planning, collaborative decisions and care for the details. The result we work towards is simple: a space with purpose, character and lasting value.</p></div>
        </section>
        <section className="website-client-values website-section" aria-labelledby="website-client-values-title">
          <div className="website-client-heading"><div><p className="website-eyebrow">CLIENT FIRST</p><h2 id="website-client-values-title">Your Project.<br />Your Priorities.</h2></div><div className="website-client-copy"><p>Choosing to build a home or a commercial space is one of the most significant investments you will ever make. It comes with big dreams—and understandable questions.</p><p>We design our entire process around these conversations. By listening first, we ensure that your priorities drive every blueprint we draw and every brick we lay. Our goal isn’t just to hand over a beautiful space; it’s to give you complete peace of mind from the first day to the final walkthrough.</p></div></div>
          <div className="website-value-grid">
            <article><div className="website-value-top"><span className="website-value-icon"><Ruler size={22} aria-hidden="true" /></span><span className="website-value-number" aria-hidden="true">01</span></div><h3>Designed around you</h3><p>Start with how you want to use your space, not just how it should look. Bring your needs, inspiration and must-haves into the discussion.</p></article>
            <article><div className="website-value-top"><span className="website-value-icon"><ClipboardList size={22} aria-hidden="true" /></span><span className="website-value-number" aria-hidden="true">02</span></div><h3>Clarity before commitment</h3><p>Discuss the scope, material choices, budget assumptions and proposed stages before deciding how to move forward.</p></article>
            <article><div className="website-value-top"><span className="website-value-icon"><MessageSquare size={22} aria-hidden="true" /></span><span className="website-value-number" aria-hidden="true">03</span></div><h3>A shared understanding</h3><p>Agree how decisions, updates and changes should be communicated, so you know what to ask and what comes next.</p></article>
          </div>
          <p className="website-draft-note"><span className="website-draft-mark" aria-hidden="true">*</span> Proposed client approach · Service scope and commitments are subject to discussion and written agreement.</p>
        </section>
        <section className="website-section website-services-alternative" id="services" aria-labelledby="website-services-alternative-title">
          <div className="website-alternative-heading">
            <div><p className="website-eyebrow">WHAT WE DO</p><h2 id="website-services-alternative-title">One vision.<br />Thoughtfully connected.</h2></div>
            <div><p>Whether you’re planning a new home or business space, rethinking an existing one, exploring interiors or seeking early design guidance, we can discuss how our services may support your project.</p></div>
          </div>
          <div className="website-alternative-grid">
            {serviceContent.map(({ title, icon: Icon, summary, detail, areas }, index) => (
              <article className="website-alternative-card" key={title}>
                <div className="website-alternative-visual" aria-hidden="true"><Icon size={42} strokeWidth={1.4} /><span>0{index + 1}</span></div>
                <div className="website-alternative-body">
                  <p className="website-eyebrow">{title}</p>
                  <h3>{['Bring your plans to life.', 'Make room for your ideas.', 'Keep every stage connected.'][index]}</h3>
                  <p><strong>{summary}</strong></p>
                  <p>{detail}</p>
                  <div className="website-alternative-includes"><h4>{['Ways we can support', 'Design possibilities', 'Across your project'][index]}</h4><ul>{areas.map(item => <li key={item}><Check size={16} aria-hidden="true" />{item}</li>)}</ul></div>
                </div>
              </article>
            ))}
          </div>
          <p className="website-draft-note"><span className="website-draft-mark" aria-hidden="true">*</span> Proposed services. Specific scope, deliverables and responsibilities are discussed and agreed for each project.</p>
        </section>
        <ProjectStartingPoints />
        <WebsiteJourney />
        <section className="website-section website-contact" id="contact" aria-labelledby="website-contact-title">
          <div className="website-contact-copy">
            <p className="website-eyebrow">CONTACT US</p>
            <h2 id="website-contact-title">Great spaces start<br />with a conversation.</h2>
            <p>Tell us what you’re planning, what matters most and any questions you have. We can talk by phone, WhatsApp or email, or arrange an in-person meeting or project-site visit to suit your needs and the stage of your project.</p>
          </div>
            <dl className="website-contact-details">
              <div><Phone size={20} /><div><dt>Phone / WhatsApp</dt><dd>+91 XXXXX XXXXX <small>Sample number · Not active</small></dd></div></div>
              <div><Mail size={20} /><div><dt>Email</dt><dd>hello@vridhi.example <small>Example address · Not active</small></dd></div></div>
              <div><MapPin size={20} /><div><dt>Meetings &amp; site visits</dt><dd>Meet at an agreed location or your project site.<small>By prior arrangement · No walk-in office</small></dd></div></div>
              <div><Clock size={20} /><div><dt>Arrange a conversation</dt><dd>Get in touch to agree a convenient time.<small>Meeting and visit timings are confirmed together.</small></dd></div></div>
            </dl>
        </section>
      </main>
      <footer className="website-footer">
        <div className="website-footer-brand"><strong><span className="website-sr-only">VRIDHI</span></strong><span>Constructions &amp; Designs</span><p>Building trust. Creating futures.</p></div>
        <div className="website-footer-info">
          <nav aria-label="Footer"><button type="button" onClick={() => openLegalNotice('privacy')}>Privacy Policy</button><button type="button" onClick={() => openLegalNotice('terms')}>Terms of Use</button><a href="#contact">Contact</a></nav>
          <small>© {copyrightYear} Vridhi Constructions &amp; Designs.</small>
        </div>
      </footer>
      <dialog className="website-legal-dialog" ref={legalDialogRef} aria-labelledby="website-legal-title">
        <div className="website-legal-heading"><h2 id="website-legal-title">{legalNotice === 'privacy' ? 'Privacy Policy' : 'Terms of Use'}</h2><form method="dialog"><button type="submit" aria-label="Close policy" title="Close" autoFocus><X size={20} aria-hidden="true" /></button></form></div>
        <div className="website-legal-content" tabIndex={0} role="region" aria-labelledby="website-legal-title">
        {legalNotice === 'privacy' ? <>
          <p>This notice explains browser storage and information handling on the Vridhi Constructions &amp; Designs website.</p>
          <h3>Your choices on this website</h3>
          <p>The project planning guide lets you explore possible starting points. Your selections are not submitted or saved by the guide.</p>
          <h3>Theme preference and browser storage</h3>
          <p>This website uses your browser&apos;s local storage to remember your day or night theme. You can remove this preference by clearing the site&apos;s browser data. This preference is not an account setting.</p>
          <h3>Enquiries and contact information</h3>
          <p>The public website has no enquiry form. If you contact us by phone, WhatsApp or email, the information you share is handled through that channel, not submitted through this website. Please share only the details needed to discuss your project and avoid sending sensitive personal or financial information.</p>
          <h3>Communication service providers</h3>
          <p>If you contact us through WhatsApp, email or phone, the service provider&apos;s privacy policy also applies. These providers process information to deliver their services, such as messages, emails or call connection details. Their privacy policies explain how they handle that information.</p>
          <h3>Technical information</h3>
          <p>The website hosting provider may process technical request information, such as IP addresses, to deliver and protect the website. This public website does not include account sign-in or an ERP workspace.</p>
        </> : <>
          <h3>General information</h3>
          <p>This website introduces Vridhi Constructions &amp; Designs and possible services. Its content is for initial discussion, not a quotation, professional assessment or commitment to undertake a project.</p>
          <h3>Your project agreement</h3>
          <p>Feasibility, pricing, timelines, deliverables and responsibilities depend on a project-specific review and a separate agreement. Illustrations and the journey guide are indicative, not promises of a particular result.</p>
          <h3>Website content</h3>
          <p>Please respect the rights of the relevant content owners. Reuse must comply with applicable permissions, licences and law. Third-party materials remain subject to their own rights and licences.</p>
          <h3>Contact and meetings</h3>
          <p>The displayed phone number and email address are currently samples, not active business channels. There is no walk-in office; meetings and project-site visits are by prior arrangement.</p>
        </>}
        </div>
      </dialog>
    </div>
  )
}
