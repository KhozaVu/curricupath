import { PersonalIntention,ContinuationCard } from "./PersonalSpace";
import { contextKey } from "../academicWorkspace.mjs";
import { safeLocal } from "../storageModel.mjs";
import React, { useRef } from "react";
import { historySummary } from "../experienceModel.mjs";
import { useInView } from "../useExperience";
import { useMediaQuery } from "../interaction";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  Route,
  MessageSquareText,
  Compass,
} from "lucide-react";

import { nextAction } from "../planModel.mjs";
import { AsyncPanel,readJson } from "./shared";
import { AtlasArtwork, ChapterKicker } from "./AtlasArtwork";
import { InterestStudio, VisitFeedback } from "./InterestStudio";
const programmeName = (code) =>
  ({ EFA03: "Electrical Engineering", EFA04: "Information Engineering" })[
    code
  ] || "Your degree, your direction";
export function HomePage({
  profile,
  continuation,onResume,onDismissContinuation,onPrivacy,
  modules,
  ready,
  evidenceViewed,
  onNavigate,
  loading,
  error,
  onRetry,
  motion = "subtle",
  visible = true,
}) {
  const heroRef = useRef(null);
  const heroVisible = useInView(heroRef);
  const pointer = useMediaQuery("(hover: hover) and (pointer: fine)");
  const history = historySummary(profile);
  const drift = event => {
    if (!pointer || motion !== 'expressive') return;
    const bounds = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty('--depth-x', `${((event.clientX-bounds.left)/bounds.width-.5)*8}px`);
    event.currentTarget.style.setProperty('--depth-y', `${((event.clientY-bounds.top)/bounds.height-.5)*6}px`);
  };
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const completed = modules.filter((m) =>
    profile.completed.includes(m.course_code),
  ).length;
  const action = nextAction(profile, ready);
  const year = profile.stage?.match(/year_(\d)/)?.[1] || "1";
  const scenarioCount=readJson('curricupath-scenarios-v1',[]).length;
  const answerCount=readJson('curricupath-saved-answers-v1',[]).length;
  const milestones = [
    [
      "Your starting point",
      "A degree profile to make guidance personal",
      ready,
    ],
    [
      "Finding your direction",
      "Your first evidence-led recommendation",
      safeLocal.getItem("curricupath-first-recommendation") === "true",
    ],
    [
      "Seeing the whole picture",
      "Explore the sources behind your choices",
      evidenceViewed,
    ],
    ['A possibility to revisit','Create a separate hypothetical draft',scenarioCount>0],
    ['An answer worth keeping','Save guidance with its declared context',answerCount>0],

  ];
  return (
    <div className="home-page page-content atlas-home">
      <section ref={heroRef} className="campus-hero" aria-label="Welcome to CurricuPath" onPointerMove={drift} onPointerLeave={event=>{event.currentTarget.style.setProperty("--depth-x","0px");event.currentTarget.style.setProperty("--depth-y","0px");}}>
        <div className="campus-hero-photo" aria-hidden="true" />
        <div className={`campus-light-trails hero-light-trails ${!heroVisible || !visible ? "is-paused" : ""}`} aria-hidden="true"><span className="campus-light-trail trail-amber" /><span className="campus-light-trail trail-blue" /><span className="campus-light-trail trail-pearl" /></div>
        <div className="home-heading">
          <div className="eyebrow">
            <span className="live-dot" /> Your journey, in focus
          </div>
          <h1>
            <span className="hero-greeting">{greeting}{profile.name ? `, ${profile.name}` : ""}.</span>
            <em>Let’s find your next step.</em>
          </h1>
          <p>
            {programmeName(profile.programme)}
            {ready && (
              <>
                {" "}
                <span>·</span> Year {year} <span>·</span> University of the
                Witwatersrand
              </>
            )}
          </p>
          <div className="hero-next-step"><span className="eyebrow">Your next step</span><p>{action.text}</p><button className="primary-button" onClick={()=>onNavigate(action.destination,action)}>{action.label}<ArrowRight size={17} aria-hidden="true" /></button><button className="hero-interest-link" onClick={()=>{const heading=document.getElementById('studio-heading');heading?.focus();heading?.scrollIntoView({block:'start',behavior:motion==='off'?'instant':'smooth'});}}>Or follow an interest <ArrowUpRight size={16} aria-hidden="true" /></button></div>
        </div>
        <div className="campus-window" aria-hidden="true"><span className="window-registration" /><span className="window-registration" /></div>
        <div className="campus-caption">
          <span className="campus-caption-line" />
          <span>
            Wits ARM Building<span>University of the Witwatersrand</span>
          </span>
        </div>
      </section>
      <section className="campus-journey" aria-label="From campus to your next step" data-no-reveal>
        <div className="journey-scene" aria-hidden="true">
          <div className="journey-scene-photo" />
          <div className="journey-scene-caption"><span>WITS / YOUR JOURNEY</span><strong>A place to begin.<br />A direction to discover.</strong></div>
        </div>
        <div className="journey-chapters">
          <article className="journey-chapter">
            <span className="eyebrow">01 / Your foundation</span>
            <h2>Your place.<br /><em>Your possibilities.</em></h2>
            <p>{programmeName(profile.programme)}. Start with your actual academic history, not assumptions.</p>
            <button className="text-button" onClick={()=>onNavigate('profile')}>Review your profile <ArrowUpRight size={16} aria-hidden="true" /></button>
          </article>
          <article className="journey-chapter">
            <span className="eyebrow">02 / Your pathway</span>
            <h2>See what<br /><em>connects.</em></h2>
            <p>{history.text}</p>
            <div className="journey-records">
              <span><strong>{loading || error || (!profile.historyConfirmed && !profile.completed.length) ? '—' : completed}</strong>Declared complete</span>
              <span><strong>{!profile.historyConfirmed && !profile.current.length ? '—' : profile.current.length}</strong>Declared current</span>
              <span><strong>{profile.planned.length}</strong>Declared planned</span>
            </div>
            <button className="text-button" onClick={()=>onNavigate('plan')}>Open your curriculum <ArrowUpRight size={16} aria-hidden="true" /></button>
          </article>
          <article className="journey-chapter">
            <span className="eyebrow">03 / Your next step</span>
            <h2>Move forward.<br /><em>With context.</em></h2>
            <p>{action.text}</p>
            <button className="primary-button" onClick={()=>onNavigate(action.destination,action)}>{action.label}<ArrowRight size={17} aria-hidden="true" /></button>
          </article>
        </div>
      </section>
      <ContinuationCard record={continuation} profileKey={contextKey(profile)} onResume={onResume} onDismiss={onDismissContinuation}/>
      <PersonalIntention />
      <div className="home-focus-grid">
        <section className="history-context" aria-labelledby="history-context-heading">
          <span className="eyebrow">Your starting point</span><h2 id="history-context-heading">{history.label}</h2><p>{history.text}</p><span className={`status-pill ${history.tone}`}>{profile.historyConfirmed ? 'Confirmed declaration' : 'More context may be needed'}</span>
          <button className="text-button" onClick={()=>onNavigate('profile')}>Edit degree profile <ArrowUpRight size={16} aria-hidden="true" /></button>
        </section>
        <section className="progress-summary">
          <div className="eyebrow">Your module history</div>
          <div className="record-total">
            <strong>{loading || error || (!profile.historyConfirmed && !profile.completed.length) ? "—" : completed}</strong>
            <span>modules declared complete</span>
          </div>
          <p>
            Your declared history, not a degree completion percentage. Elective
            options are included in the catalogue.
          </p>
          {(loading || error) && (
            <AsyncPanel
              loading={loading}
              title={
                error
                  ? "Module history is unavailable"
                  : "Checking your module history…"
              }
              error={error}
              onRetry={onRetry}
            />
          )}
          <div className="progress-counts">
            <div>
              <strong>{!profile.historyConfirmed && !profile.current.length ? "—" : profile.current.length}</strong>
              <span>Declared current</span>
            </div>
            <div>
              <strong>{profile.planned.length}</strong>
              <span>Declared planned</span>
            </div>
          </div>
        </section>
      </div>
      {(profile.planned.length > 0) && <section className="continuation-space" aria-labelledby="continuation-heading">
        <div className="section-label"><div><span className="eyebrow">Remembered on this device</span><h2 id="continuation-heading">Pick up where you left off.</h2></div></div>
        <div className="continuation-grid">
          {profile.planned.length > 0 && <section><h3>Your study horizon</h3>{profile.planned.slice(0,3).map(code=><button key={code} className="collection-row" onClick={()=>onNavigate('plan',{module:code})}><span className="module-code">{code}</span><strong>{modules.find(m=>m.course_code===code)?.course_name || 'Declared planned module'}</strong><ArrowUpRight size={16} aria-hidden="true" /></button>)}</section>}
        </div>
      </section>}
      <InterestStudio onNavigate={onNavigate} />
      <section className="atlas-wayfinding" aria-labelledby="wayfinding-heading">
      <div className="section-label"><h2 id="wayfinding-heading">Three ways forward.</h2><span>Your next chapter</span></div>
      <div className="home-shortcuts">
        {[
          [
            MessageSquareText,
            "Ask advisor",
            "A question is a good place to start.",
            "advisor",
          ],
          [
            Route,
            "Review plan",
            "See the connections. Choose your next move.",
            "plan",
          ],
          [
            Compass,
            "Explore Wits modules",
            "Follow an interest a little further.",
            "explore",
          ],
        ].map(([Icon, title, text, destination]) => (
          <button key={title} className={`atlas-destination destination-${destination}`} onClick={() => onNavigate(destination)}>
            <span className="destination-top"><ChapterKicker index={{plan:"01",advisor:"02",explore:"03"}[destination]}>{destination === "advisor" ? "Clarity" : destination === "plan" ? "Direction" : "Discovery"}</ChapterKicker><Icon size={18} aria-hidden="true" /></span>
            <AtlasArtwork variant={{plan:"path",advisor:"dialogue",explore:"orbit"}[destination]} />
            <span>
              <strong>{title}</strong>
              <small>{text}</small>
            </span>
            <ArrowUpRight size={19} />
          </button>
        ))}
      </div>
      </section>
      <p className="helper-text">Next useful task: {milestones.find(([, ,done])=>!done)?.[1] || 'Revisit your saved work when it is useful.'}. Milestones record actions, not time spent.</p>
      <details className="milestones milestone-disclosure"><summary>Small steps. Real momentum.<span>{milestones.filter(([, , done])=>done).length} of {milestones.length} reached</span></summary>
        <div className="section-label">
          <h2>Small steps. Real momentum.</h2>
          <span>YOUR MILESTONES</span>
        </div>
        <p className="milestone-context">{milestones.filter(([, , done]) => done).length} of {milestones.length} exploration milestones reached. Take them at your own pace.</p>
        {milestones.map(([title, text, done], i) => (
          <div className="milestone-row" key={title}>
            <span className={`milestone-number ${done ? "done" : ""}`}>
              {done ? <Check size={16} /> : `0${i + 1}`}
            </span>
            <div className="milestone-copy">
              <strong>{title}</strong>
              <p>{text}</p>
              <button className="text-button" onClick={() => onNavigate(["profile", "advisor", "evidence"][i])}>{["Review your profile", "Ask a question", "Open the sources"][i]} <ArrowUpRight size={14} aria-hidden="true" /></button>
            </div>
            <span className="milestone-state">
              {done ? "Reached" : "Still ahead"}
            </span>
          </div>
        ))}
      </details>
      <VisitFeedback />
      <button className="text-button" onClick={onPrivacy}>Privacy & local records</button>
    </div>
  );
}
