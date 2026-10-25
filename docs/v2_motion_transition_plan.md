# CurricuPath V2: Campus to Curriculum Motion Plan

Date: 2026-10-14
Status: motion implementation delivered using the progressive-enhancement scope below. V2 has a three-chapter campus/pathway/next-step section, a desktop sticky photograph, Expressive-mode hero arrival and progressive scroll depth, and cancellable incoming workspace transitions. Compact layouts use static stacked chapters. Scroll reveals are restricted to selected home panels.

### Finishing work delivered

- New chat DOM entries receive a 160 ms reveal; existing transcript entries and streaming text updates do not replay it.
- Only the first four new course results receive a bounded 40 ms stagger. Course IDs already seen within the workspace do not replay when filtered back in.
- Effect cleanup cancels active animations; hidden tabs do not start content animations. Off mode skips them and Subtle mode uses opacity only.
- Retained the existing accessible drawer/inspector entrance and exit as the explicitly allowed fallback instead of shared-element morphing. Subtle drawer motion now fades. The existing focus trap and Escape behaviour remain authoritative.
- Removed overlapping legacy page entrances. No academic logic, response formulation, source data or evaluation cases changed.

### Verification record

- V2 production build passed (existing shader directive and large-chunk warnings remain).
- `node --test frontend_v2/src/contentMotion.test.mjs`: 5 passed. Covers transcript non-replay, bounded/deduplicated course effects, Off/hidden behaviour, cleanup and Subtle mode.
- Browser checks: Home/Plan navigation; course drawer focus entry; Escape dismissal; focus restoration to the course card; return Home; compact viewport has no horizontal overflow. Earlier desktop/mobile checks verified the sticky/static layout split.
- Follow-up regression: full Python suite completed with 440 passed, 3 skipped and 30 warnings. Warnings include learned-ranker fallback/catalogue-fingerprint conditions and provider-unavailable test paths; this is not proof of live provider availability.
- Motion unit coverage expanded to 9 passing tests across `contentMotion.test.mjs` and `workspaceMotion.test.mjs`, including reverse navigation, cancellation, fixed-shell exclusion and hidden-tab suppression.
- Light-theme tablet check at 768 px found no horizontal overflow; dark theme and original viewport restored. Final browser error log was empty.
- The browser reported system reduced motion; effective motion was Off and the hero animation was `none`, as intended. Do not bypass that preference to demonstrate effects.
- Not yet verified: full cross-browser matrix, formal contrast audit, performance profiling on target hardware, screen-reader testing and live Gemini response animation. These remain QA tasks, not claims of completed validation.

## Direction

Make CurricuPath feel like one continuous academic journey, not separate dashboard pages. Borrow TimeFrame's visual continuity and staged storytelling, not its entire marketing-site interaction model.

Reference inspected: https://timeframe-app.webflow.io/

Observed reference patterns: a layered image composition, oversized typography, a central phone presentation carried through successive scroll sections, changing surrounding colours and descriptions, and persistent navigation. These observations describe the visible experience, not a verified account of its animation library.

CurricuPath keeps its Wits campus photograph, blue/white identity, warm photographic highlights, existing typography, and all academic functionality. Do not copy the reference's photographs or brand assets.

## Current Implementation

- `frontend_v2/src/App.jsx` already coordinates Home, Plan, Advisor and Explore, with route history and persistent profile state.
- `useScrollReveal.js` already provides CSS scroll-timeline reveals with an IntersectionObserver fallback. It currently targets many sections/articles and can replay reveals on each pass.
- `experienceModel.mjs` already defines Off, Subtle and Expressive modes and respects system reduced-motion preferences.
- `styles/tokens.css` already defines motion duration/easing tokens.
- `styles/campus.css` owns the home photograph composition; `styles/shell.css` owns the persistent background.
- The package already includes heavy graphics dependencies. This proposal does not require more shaders, WebGL scenes, a new model, API keys, or backend changes.

## Signature Experience

### 1. Arrival: your place at Wits

Show the supplied evening campus photograph as the dominant opening visual. Reveal the greeting, programme context and next-step button in a short sequence. In Expressive mode only, let the photo settle from scale 1.025 to 1 over approximately 700 ms. Text remains on a stable contrast layer.

Never gate access behind an intro, splash screen, or loading animation. Returning users can go directly to any workspace.

### 2. Home scroll: from campus to your pathway

On wide screens, use one short sticky composition, approximately 160-180 viewport heights including the initial screen, with three chapters:

1. **Your foundation:** the campus image and current degree context.
2. **Your pathway:** a compact preview of the student's real year/module selections moves into focus as the campus image recedes.
3. **Your next step:** the preview settles into a stable card beside the existing action to review history, plan modules or ask the advisor.

Keep one visual anchor rather than animating every card independently. The degree preview must use real profile data; unknown history stays visibly unknown. No decorative fake eligibility decisions or invented progress.

Scrolling is native and reversible. No wheel interception, forced snapping, horizontal scroll traps, or mandatory tour. A visible action lets users bypass the sequence at all times.

### 3. Workspace transitions: continuity without delay

Keep navigation and the background mounted. Change only the main content with a restrained 220-320 ms fade and 12-20 px directional movement. Home -> Plan should feel like entering the pathway shown in the preview. Back navigation reverses the directional cue and restores scroll/focus.

Do not animate filter changes as full route changes. Preserve chat, unsent messages, selections, API requests and academic state. Rapid navigation cancels obsolete animation instead of queueing it.

### 4. Module cards: expand into evidence

Selecting a module carries its title/code visually into the existing detail panel, then reveals scope, lecturer, requirements and evidence. Use a shared-element-style transition only where stable module IDs permit it; otherwise slide/fade the existing drawer in 180-240 ms.

Focus moves into the dialog and returns to the originating card on close. Escape remains available. Repeated cards need unique transition names or a single selected anchor. No duplicate accessible copies during animation.

### 5. Advisor: calm, readable answers

The chat composer stays stationary. New answer cards may fade in with at most 8 px movement over 120-180 ms. Do not typewrite decisions, delay reasons, bounce messages, or replay the whole transcript. Announce answers once to assistive technology. Keep clarification and manual-review states visually distinct without suggesting certainty from animation.

### 6. Explore: orderly discovery

Use a one-time 40 ms stagger for the first few visible results, capped at 160 ms total. Open course details through the same panel transition used for modules. Filtering shows a stable loading state, then the result list; it must not flash stale results or animate a full catalogue on every keystroke.

## Motion Architecture

Prefer the existing React/CSS stack. Use CSS transforms and opacity for ordinary transitions, IntersectionObserver for discrete reveals and progressive CSS scroll timelines for the optional Home sequence. Unsupported browsers receive static sections, not missing content.

Introduce a small motion coordinator only if necessary for route exit/entry timing. Native View Transitions are an optional enhancement after capability testing, never a requirement. Do not add GSAP or another motion library in the first iteration; reconsider only if a specific choreography cannot be maintained cleanly with current tools.

Scope `useScrollReveal` to explicitly opted-in presentation blocks. Exclude chat messages, rules, forms, errors, live results and eligibility explanations. Content should be visible by default if animation setup fails. Avoid competing transforms on an element controlled by both route and scroll animation.

Suggested ownership: `styles/motion.css` for shared tokens/transitions; `HomePage.jsx` and `styles/campus.css` for the signature sequence; `App.jsx` and route-history integration for page changes; the existing Drawer/ModuleInspector components for detail continuity. Keep academic models and backend endpoints untouched.

## Mobile, Accessibility and Performance

- Below the existing compact breakpoint, use stacked sections, no sticky cinematic timeline, and no parallax; retain the photograph and short fades.
- Off mode and `prefers-reduced-motion` disable decorative transforms, scroll scrubbing and stagger. All content and navigation remain usable immediately.
- Subtle mode uses short fades; Expressive adds the Home choreography. Retain the user's saved setting; do not silently enable Expressive.
- Preserve keyboard navigation, focus visibility, dialog focus trapping and route announcements. Do not let an overlay intercept interaction after its animation ends.
- Keep text contrast at WCAG AA targets in both themes. Darken behind text rather than dimming the whole photograph.
- Pause decorative work in hidden tabs. Avoid continuous animation, large animated blurs and layout-property animation.
- Profile on an ordinary laptop and mobile viewport, targeting smooth 60 Hz interaction without new animation-attributable long tasks over 50 ms. Record actual measurements rather than claiming performance from CSS alone.

## Implementation Order

1. **Foundation:** document current routes/state; scope existing reveals; centralise motion settings; add cancellation and reduced-motion tests.
2. **Hero prototype:** implement the three-chapter Home sequence behind a presentation flag. Verify desktop and static mobile before expanding scope.
3. **Workspace continuity:** add page and detail-panel transitions without remounting persistent state.
4. **Finishing:** restrained result/message reveals, light-theme checks, contrast, keyboard and performance verification.

Deliver Phase 2 first for visual approval. If time is limited, ship the improved hero and simple page fade; defer sticky choreography and shared elements rather than compromising advising reliability.

## Acceptance Checks

- Home, Plan, Advisor, Explore, direct hash links and browser Back/Forward work during and after animation.
- Completed/current/planned/repeating selections, history confirmation, chat and ranking mode survive navigation unchanged.
- Test existing module eligibility, missing-fact clarification, manual review, module information and course recommendation scenarios; responses must remain unchanged.
- Test rapid repeated navigation, open/close detail panels, slow network, failed requests and empty data.
- Verify layouts at 390, 768 and 1440 px widths in light/dark themes and all motion modes.
- Verify reduced motion, keyboard-only operation, no invisible focus targets, no horizontal overflow and no layout shift from the campus image.
- Build V2 and run existing UI/model tests. Capture before/after screenshots and a short interaction recording where available; report any untested browsers.
- V1, frozen evaluation inputs and academic decision logic remain untouched.

## Boundaries

This is a presentation improvement, not evidence of better advising or usability. It does not change evaluation results. TimeFrame is design inspiration; its marketing-site pacing should not be imposed on students who need a quick factual answer.
