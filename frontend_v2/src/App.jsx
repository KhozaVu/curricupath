import { safeLocal, safeSession } from "./storageModel.mjs";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Home, Route, MessageSquareText, Compass, CheckCircle2 } from "lucide-react";
import { Atmosphere, LiquidGlassFilter } from "./Atmosphere";
import { ModuleInspector } from "./Spatial";
import {
  AdvisorPage,
  ProfilePage,
  EvidencePage,
  ModuleDetail,
  INITIAL_MESSAGES,
  getJson,
  readJson,
  usePersistentState,
  usePersistentString,
} from "./views/DomainViews";
import {
  NavigationRail,
  TopBar,
  HomePage,
  PlanPage,
  ExplorePage,
  Drawer,
  GlobalSearch,
  SourceTrail,
} from "./views/Interface";
const PAGES = [
  ["home", Home, "Home"],
  ["plan", Route, "Plan"],
  ["advisor", MessageSquareText, "Advisor"],
  ["explore", Compass, "Explore"],
];
import {
  readRoute as route,
  readPlanOptions,
  planOptionsHash,
} from "./planModel.mjs";
import { PrivacyPanel } from "./views/PersonalSpace";
import { AsyncPanel, useStorageFailure } from "./views/shared";
import { useMediaQuery } from "./interaction";
import {
  readPlanList,
  planListHash,
} from "./workspaceModel.mjs";
import {
  DEFAULT_DISCOVERY,
  readDiscovery,
  discoveryHash,
} from "./exploreModel.mjs";
import { rememberView, destinationHash } from "./navigationModel.mjs";
import { SpaceHelp } from "./views/SpaceHelp";
import { MOTION_LEVELS, motionLevel, effectiveMotion } from "./experienceModel.mjs";
import { useRouteHistory } from "./useRouteHistory";
import { contextKey } from "./academicWorkspace.mjs";
import { usePageVisibility } from "./useExperience";
import { useScrollReveal } from "./useScrollReveal";
import { useWorkspaceMotion } from "./useWorkspaceMotion";
import { useContentMotion } from "./useContentMotion";
export function App() {
  const routeHistory = useRouteHistory();
  const storageFailure=useStorageFailure();
  const [graphicsLost,setGraphicsLost]=useState(false);
  useEffect(()=>{const lost=e=>{e.preventDefault();setGraphicsLost(true);};window.addEventListener("webglcontextlost",lost,true);return ()=>window.removeEventListener("webglcontextlost",lost,true);},[]);
  const [continuation,setContinuation]=usePersistentState("curricupath-continuation-v1",{});
  const overlayTrail = useRef([]);
  const overlayReturn = useRef(null);
  const compact = useMediaQuery("(max-width: 700px)");
  const initial = route(window.location.hash);
  const [profile, setProfile, profilePersistence] = usePersistentState("curricupath-profile", {
    stage: "year_4_semester_1",
    programme: safeLocal.getItem("curricupath-programme") || "",
    stream: "general",
    completed: readJson("curricupath-completed", []),
    current: [],
    planned: [],
    repeating: [],
    historyConfirmed: false,
    reviewNote: "",
    interests: [],
    careers: [],
    workload: "",
    format: "",
  });
  const [savedProgramme, setSavedProgramme] = usePersistentString(
    "curricupath-curriculum-ready",
  );
  const ready = Boolean(
    profile.programme && savedProgramme === profile.programme,
  );
  const [sidebarCollapsed, setSidebarCollapsed] = usePersistentState("curricupath-sidebar-collapsed", false);
  const [theme, setTheme] = usePersistentString("curricupath-theme", "dark");
  const [rankingMode, setRankingMode] = usePersistentString(
    "curricupath-ranking-mode",
    "prototype",
  );
  const [system, setSystem] = usePersistentString(
    "curricupath-advisor-system-v2",
    "curricupath",
  );
  const [sessionId, setSessionId] = useState(() =>
    safeSession.getItem("curricupath-session"),
  );
  const [messages, setMessages] = usePersistentState("curricupath-wits-conversation-v2", INITIAL_MESSAGES);
  const priorProfileContext = useRef(contextKey(profile));
  useEffect(()=>{
    const next=contextKey(profile);
    if(next!==priorProfileContext.current){
      setSessionId(null);safeSession.removeItem('curricupath-session');setHighlight([]);
      priorProfileContext.current=next;
    }
  },[contextKey(profile)]);
  const [advisorDraft, setAdvisorDraft] = useState("");
  const [advisorContext, setAdvisorContext] = useState(null);
  const viewMemory = useRef({});
  const [page, setPage] = useState(initial.page);
  const [planTab, setPlanTab] = useState(initial.planTab);
  const [planOptions, setPlanOptions] = useState(() =>
    readPlanOptions(window.location.hash),
  );
  const [planList, setPlanList] = useState(() =>
    readPlanList(window.location.hash),
  );
  const [motion, setMotion] = usePersistentString("curricupath-motion", "subtle");
  const systemReduced = useMediaQuery("(prefers-reduced-motion: reduce)");
  const motionPreference = motionLevel(motion);
  const motionMode = graphicsLost?"off":effectiveMotion(motion, systemReduced);
  const visible = usePageVisibility();
  const [exploreTab, setExploreTab] = useState(initial.exploreTab);
  const [discovery, setDiscovery] = useState(() =>
    readDiscovery(window.location.hash),
  );
  const [drawer, setDrawer] = useState(initial.drawer);
  const [searchOpen, setSearchOpen] = useState(false);
  const [summary, setSummary] = useState(null);
  const [modules, setModules] = useState([]);
  const [evidence, setEvidence] = useState(null);
  const [loading, setLoading] = useState({});
  const [loadErrors, setLoadErrors] = useState({});
  const retries = useRef({});
  const generations = useRef({});
  const detailRequest = useRef(0);
  const retryAction = useRef(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);
  const [inspect, setInspect] = useState(null);
  const [selectedModule, setSelectedModule] = useState(initial.module);
  const [highlight, setHighlight] = useState([]);
  const [busy, setBusy] = useState(false);
  useEffect(()=>{if(page==='home' || (['plan','advisor'].includes(page) && !ready))return;const hash=page==='plan'?`#plan${selectedModule?`?module=${selectedModule}`:''}`:page==='explore'?discoveryHash('#explore',discovery):'#advisor';setContinuation({hash,label:page==='plan'?selectedModule?`Inspect ${selectedModule}`:'Your curriculum workspace':page==='explore'?'Your Wits module search':'Your Advisor workspace',academic:page!=='explore',contextKey:contextKey(profile),at:new Date().toISOString()});},[page,selectedModule,discovery]);

  const [evidenceViewed, setEvidenceViewed] = useState(
    () => safeLocal.getItem("curricupath-evidence-viewed") === "true",
  );
  const request = useRef(0);
  const load = useCallback(async (key, url, setter) => {
    const generation = (generations.current[key] || 0) + 1;
    generations.current[key] = generation;
    retries.current[key] = () => load(key, url, setter);
    setLoadErrors((current) => ({ ...current, [key]: "" }));
    setLoading((v) => ({ ...v, [key]: true }));
    try {
      const data = await getJson(url);
      if (generations.current[key] === generation) {
        setter(data);
        if (key === "summary") setError("");
      }
    } catch (e) {
      if (generations.current[key] === generation)
        setLoadErrors((current) => ({
          ...current,
          [key]: `Could not load ${key}. ${e.message}`,
        }));
      if (key === "summary" && generations.current[key] === generation) {
        retryAction.current = retries.current[key];
        setError(`Could not load the catalogue summary. ${e.message}`);
      }
    } finally {
      if (generations.current[key] === generation)
        setLoading((v) => ({ ...v, [key]: false }));
    }
  }, []);
  useEffect(() => {
    load("summary", "/catalogue/summary", (data) => {
      setSummary(data);
    });
  }, []);
  useEffect(() => {
    safeLocal.setItem("curricupath-programme", profile.programme);
    safeLocal.setItem(
      "curricupath-completed",
      JSON.stringify(profile.completed),
    );
    setModules([]);
    setLoadErrors((current) => ({ ...current, modules: "" }));
    if (!profile.programme) {
      generations.current.modules = (generations.current.modules || 0) + 1;
      setLoading((current) => ({ ...current, modules: false }));
      return;
    }
    let alive = true;
    load("modules", `/programmes/${profile.programme}/modules`, (data) => {
      if (alive) setModules(data);
    });
    return () => {
      alive = false;
    };
  }, [profile.programme, load]);
  useEffect(() => {
    document.documentElement.style.colorScheme = theme;
    document.documentElement.style.backgroundColor = theme === "dark" ? "#0c111b" : "#f1f3f7";
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#0c111b" : "#f1f3f7");
  }, [theme]);
  useEffect(() => {
    const onKey = (event) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k" &&
        !drawer
      ) {
        event.preventDefault();
        setSearchOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);
  useEffect(() => {
    if (drawer !== "evidence") return;
    setEvidenceViewed(true);
    safeLocal.setItem("curricupath-evidence-viewed", "true");
    load("evidence", "/evidence", setEvidence);
  }, [drawer, load]);
  useEffect(() => {
    const handle = () => {
      if (window.location.hash === "#main-content") return;
      routeHistory.arrived();
      overlayTrail.current=[];
      setSearchOpen(false);
      const next = route(window.location.hash);
      detailRequest.current++;
      request.current++;
      setPage(next.page);
      setPlanTab(next.planTab);
      setPlanOptions(readPlanOptions(window.location.hash));
      setPlanList(readPlanList(window.location.hash));
      setExploreTab(next.exploreTab);
      setDiscovery(readDiscovery(window.location.hash));
      setDrawer(next.drawer);
      setInspect(null);
      setSelectedModule(next.module);
      setDetail(null);
      if (next.module) openModule(next.module, false);
      requestAnimationFrame(()=>{
        routeHistory.restore();
        if (!next.drawer && !course && !next.module) document.querySelector('main h1')?.focus({preventScroll:true});
      });
    };
    window.addEventListener("hashchange", handle);
    window.addEventListener("popstate", handle);
    return () => {
      window.removeEventListener("hashchange", handle);
      window.removeEventListener("popstate", handle);
    };
  }, []);
  useEffect(()=>{
    const frame=requestAnimationFrame(()=>routeHistory.restore((!profile.programme || loading.modules === false)));
    return ()=>cancelAnimationFrame(frame);
  },[page,modules,loading.modules]);
  useEffect(()=>{
    const heading=document.querySelector('main h1');
    if(heading)heading.tabIndex=-1;
  },[page]);
  useEffect(()=>{
    if(!overlayReturn.current)return;
    const frame=requestAnimationFrame(()=>{
      const previous=overlayReturn.current;
      const content=document.querySelector('.drawer-content');
      if(content)content.scrollTop=previous.scroll;
      document.querySelectorAll('.drawer button, .drawer input, .drawer a')[previous.focus]?.focus({preventScroll:true});
      overlayReturn.current=null;
    });
    return ()=>cancelAnimationFrame(frame);
  },[drawer]);
  const openOverlay = (destination, data=detail) => {
    if (drawer && drawer !== destination) overlayTrail.current.push({drawer,detail,scroll:document.querySelector('.drawer-content')?.scrollTop || 0,focus:[...document.querySelectorAll('.drawer button, .drawer input, .drawer a')].indexOf(document.activeElement)});
    setDetail(data);
    setDrawer(destination);
  };
  const navigate = (destination, options = {}) => {
    if (["profile", "evidence"].includes(destination)) {
      setDrawer(destination);
      return;
    }
    overlayTrail.current=[];
    viewMemory.current = rememberView(window.location.hash, viewMemory.current);
    const hash = destinationHash(destination, viewMemory.current, options);
    const next = route(hash);
    request.current++;
    detailRequest.current++;
    setDrawer(null);
    setInspect(null);
    setSelectedModule(null);
    setDetail(null);
    setPage(destination);
    if (destination === "advisor" && options.prompt) setAdvisorDraft(options.prompt);
    if (destination === "plan") {
      setPlanTab(next.planTab);
      setPlanOptions(readPlanOptions(hash));
      setPlanList(readPlanList(hash));
    }
    if (destination === "explore") {
      setExploreTab(next.exploreTab);
      setDiscovery(readDiscovery(hash));
    }
    routeHistory.push(hash);
    if (next.module) openModule(next.module, false);
    window.scrollTo({ top: 0, behavior: "instant" });
    if (!next.module)
      requestAnimationFrame(() =>
        (document.querySelector("main h1") || document.getElementById("main-content"))?.focus({ preventScroll: true }),
      );
  };
  const closeDrawer = useCallback(() => {
    detailRequest.current++;
    const previous=overlayTrail.current.pop();
    if(previous) {
      overlayReturn.current=previous;
      setDrawer(previous.drawer);
      setDetail(previous.detail);
    } else {
      setDrawer(null);
      setDetail(null);
    }
    if (["#profile", "#evidence"].includes(window.location.hash))
      window.history.replaceState(window.history.state, "", `#${page}`);
    const [path, search = ""] = window.location.hash.split("?");
    const params = new URLSearchParams(search);
    if (params.has("course") && previous?.drawer !== "course") {
      params.delete("course");
      window.history.replaceState(
        window.history.state,
        "",
        path + (params.size ? `?${params}` : ""),
      );
    }
  }, [page]);
  const closeInspector = useCallback(() => {
    request.current++;
    setInspect(null);
    const [path, search = ""] = window.location.hash.split("?");
    const params = new URLSearchParams(search);
    if (params.get("focus") !== "chain") params.delete("module");
    window.history.replaceState(
      window.history.state,
      "",
      path + (params.size ? `?${params}` : ""),
    );
  }, []);
  const openModule = async (code, syncUrl = true) => {
    setSelectedModule(code);
    if (syncUrl) {
      const [path, search = ""] = window.location.hash.split("?");
      const params = new URLSearchParams(search);
      params.set("module", code);
      routeHistory.push(`${path || "#plan"}?${params}`);
    }
    const id = ++request.current;
    setInspect({ code, loading: true, data: null });
    try {
      const data = await getJson(`/modules/${code}`);
      if (id === request.current) setInspect({ code, loading: false, data });
    } catch (e) {
      if (id === request.current) {
        setInspect({
          code,
          loading: false,
          data: null,
          error: `Could not open ${code}. ${e.message}`,
        });
      }
    }
  };
  const addToPlan = (code) => {
    setNotice(
      `${code} ${profile.planned.includes(code) ? "removed from" : "added to"} your study plan.`,
    );
    setProfile((p) => ({
      ...p,
      repeating: (p.repeating || []).filter((c) => c !== code),
      planned: p.planned.includes(code)
        ? p.planned.filter((c) => c !== code)
        : [...p.planned, code],
    }));
  };
  useEffect(() => {
    if (initial.module) openModule(initial.module, false);
  }, []);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 5000);
    return () => clearTimeout(timer);
  }, [notice]);
  const updateTab = (destination, tab, setter) => {
    setter(tab);
    const params = new URLSearchParams(
      window.location.hash.split("?")[1] || "",
    );
    params.set("tab", tab);
    routeHistory.push(`#${destination}?${params}`);
  };
  const updatePlanOptions = (patch) => {
    const next = { ...planOptions, ...patch };
    setPlanOptions(next);
    let hash = planOptionsHash(window.location.hash, next);
    if (next.focus && selectedModule) {
      const params = new URLSearchParams(hash.split("?")[1] || "");
      params.set("module", selectedModule);
      hash = `#plan?${params}`;
    }
    routeHistory.push(hash);
  };
  const updateDiscovery = (patch, replace = false) => {
    const next = { ...discovery, ...patch };
    setDiscovery(next);
    routeHistory.push(discoveryHash(window.location.hash, next),replace);
  };
  const updatePlanList = (patch, replace = false) => {
    const next = { ...planList, ...patch };
    setPlanList(next);
    routeHistory.push(planListHash(window.location.hash, next),replace);
  };

  const showInPlan = (codes, navigateNow) => {
    setHighlight(codes || []);
    if (navigateNow) {
      navigate("plan", { tab: "map" });
      setPlanTab("map");
    }
  };
  useScrollReveal(page, motionMode, systemReduced);
  useWorkspaceMotion(page, motionMode);
  useContentMotion(page, motionMode);
  return (
    <div
      className="app-shell"
      data-theme={theme}
      data-page={page}
      data-motion={motionMode === "off" ? "reduced" : "auto"}
      data-motion-level={motionMode}
      data-visibility={visible ? "visible" : "hidden"}
      data-sidebar={sidebarCollapsed ? "collapsed" : "expanded"}
    >
      <Atmosphere
        theme={theme}
        mood={page}
        motionLevel={motionMode}
        reducedMotion={motionMode === "off"}
      />
      <LiquidGlassFilter />
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          const main = document.getElementById("main-content");
          main?.focus({ preventScroll: true });
          main?.scrollIntoView({ behavior: "instant", block: "start" });
        }}
      >
        Skip to content
      </a>
      <NavigationRail
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(value => !value)}
        pages={PAGES}
        page={page}
        onNavigate={navigate}
        onProfile={() => setDrawer("profile")}
        profile={profile}
        ready={ready}
        busy={busy}
        reducedMotion={motionMode !== "expressive"}
        inert={Boolean(drawer || searchOpen || (compact && inspect))}
      />
      <main
        className="main-content"
        id="main-content"
        tabIndex={-1}
        inert={Boolean(drawer || searchOpen || (compact && inspect))}
      >
        <TopBar
          page={page}
          theme={theme}
          onTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
          onSearch={() => setSearchOpen(true)}
          onProfile={() => setDrawer("profile")}
          onDisplay={() => setDrawer("display")}
          onHelp={() => setDrawer("help")}
          profile={profile}
        />
        {error && (
          <div className="error-notice" role="alert">
            {error}
            <button
              onClick={() => {
                setError("");
                retryAction.current?.();
              }}
            >
              Try again
            </button>
            <button onClick={() => setError("")} aria-label="Dismiss error">
              ×
            </button>
          </div>
        )}
        {graphicsLost && <p className="workspace-warning" role="status">Graphics context was lost. Decorative effects are stopped; the reading view and recorded requirements remain available. <button className="text-button" onClick={()=>setGraphicsLost(false)}>Try graphics again</button></p>}
        {storageFailure && <p className="workspace-warning" role="status">Browser storage is unavailable or failed. You can keep using the interface, but changes may last only for this visit. <button className="text-button" onClick={()=>openOverlay("privacy")}>Review or export personal records</button></p>}
        {page === "home" && (
          <HomePage
            profile={profile}
            continuation={continuation?.hash?.startsWith("#explore") ? {...continuation,label:"Your Wits module search"} : continuation}
            onDismissContinuation={()=>setContinuation({})}
            onResume={hash=>{location.hash=hash;}}
            onPrivacy={()=>openOverlay("privacy")}
            modules={modules}
            ready={ready}
            evidenceViewed={evidenceViewed}
            onNavigate={navigate}
            loading={loading.modules}
            error={loadErrors.modules}
            onRetry={() => retries.current.modules?.()}
            motion={motionMode}
            visible={visible}
          />
        )}
        {page === "plan" && (
          <PlanPage
            capabilities={summary}
            profile={profile}
            modules={modules}
            loading={loading.modules}
            error={loadErrors.modules}
            onRetry={() => retries.current.modules?.()}
            tab={planTab}
            options={planOptions}
            listOptions={planList}
            onListOptions={updatePlanList}
            graphicsUnavailable={graphicsLost}
            reducedMotion={motionMode === "off"}
            onOptions={updatePlanOptions}
            setTab={(tab) => updateTab("plan", tab, setPlanTab)}
            selected={selectedModule}
            highlight={highlight}
            onOpenModule={openModule}
            onProfile={() => setDrawer("profile")}
            onSources={data=>openOverlay("sources",{type:"sources",data})}
          />
        )}
        {page === "advisor" &&
          (ready ? (
            <AdvisorPage
              draft={advisorDraft}
              onDraft={setAdvisorDraft}
              context={advisorContext}
              processing={busy}
              onHighlight={showInPlan}
              onBusy={setBusy}
              profile={profile}
              rankingMode={rankingMode}
              setRankingMode={setRankingMode}
              system={system}
              setSystem={setSystem}
              handbookRagDemoEnabled={Boolean(
                summary?.handbook_rag_demo_enabled,
              )}
              sessionId={sessionId}
              setSessionId={setSessionId}
              messages={messages}
              setMessages={setMessages}
              onEditProfile={() => setDrawer("profile")}
              onOpenModule={openModule}
              onSources={(data) => {
                openOverlay('sources',{type:'sources',data});
              }}
            />
          ) : (
            <div className="setup-empty">
              <MessageSquareText size={32} />
              <h1>Advice starts with you.</h1>
              <p>
                Add your programme and module history so every answer has the
                right context.
              </p>
              <button
                className="primary-button"
                onClick={() => setDrawer("profile")}
              >
                Set up your degree profile
              </button>
            </div>
          ))}
        {page === "explore" && <ExplorePage modules={modules} profile={profile} loading={loading.modules} error={loadErrors.modules} onRetry={()=>retries.current.modules?.()} onOpenModule={openModule} onProfile={()=>setDrawer('profile')} onAsk={prompt=>navigate('advisor',{prompt})}/>}
        <footer>
          <span>Built for your next step.</span>
          <button onClick={() => setDrawer("evidence")}>
            Evidence & sources
          </button>
          <span>CurricuPath · Wits EIE prototype</span>
        </footer>
      </main>
      <span className="visually-hidden" role="status" aria-live="polite">
        {page[0].toUpperCase() + page.slice(1)} view
      </span>
      <div
        className={`plan-notice ${notice ? "visible" : ""}`}
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {notice && <CheckCircle2 size={18} aria-hidden="true" />}
        <span>{notice}</span>
      </div>
      {inspect && (
        <ModuleInspector
          modal={compact}
          module={inspect.data}
          requestedCode={inspect.code}
          loading={inspect.loading}
          error={inspect.error}
          inert={Boolean(drawer || searchOpen)}
          onRetry={() => openModule(inspect.code, false)}
          profile={profile}
          onClose={closeInspector}
          onPlan={addToPlan}
          onMore={() => {
            openOverlay('module',{type:'module',data:inspect.data});
          }}
          onAsk={() => {
            setAdvisorContext({
              code: inspect.data.course_code,
              name: inspect.data.course_name,
            });
            setAdvisorDraft(`Can I take ${inspect.data.course_code}?`);
            navigate("advisor");
          }}
          onViewEvidence={() => {
            openOverlay('sources',{type:'sources',data:inspect.data});
          }}
        />
      )}
      {drawer && (
        <Drawer
          key={drawer}
          title={
            drawer === "privacy" ? "Privacy & local records" : drawer === "help" ? "How CurricuPath works" : drawer === "profile"
              ? "Your degree profile"
              : drawer === "evidence"
                ? "Evidence & sources"
                : drawer === "sources"
                  ? "Why this?"
                  : drawer === "display"
                    ? "Appearance & accessibility"
                    : detail?.data?.title ||
                      detail?.data?.course_name ||
                      "Details"
          }
          onClose={closeDrawer}
          backLabel={overlayTrail.current.length ? `Back to ${overlayTrail.current.at(-1).drawer === "sources" ? "source trail" : overlayTrail.current.at(-1).drawer}` : undefined}
          wide={drawer === "profile" || drawer === "evidence"}
        >
          {drawer === "display" && (
            <section className="display-settings">
              <p className="modal-lead">
                Choose the reading experience that feels right for you.
              </p>
              <div className="setting-card">
                <h3>Colour theme</h3>
                <div className="segmented">
                  {["dark", "light"].map((value) => (
                    <button
                      key={value}
                      className={theme === value ? "active" : ""}
                      aria-pressed={theme === value}
                      onClick={() => setTheme(value)}
                    >
                      {value === "dark" ? "Dusk" : "Daylight"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="setting-card">
                <fieldset><legend>Motion</legend><div className="motion-choices">{MOTION_LEVELS.map(level=><label key={level.id} className="motion-choice"><input type="radio" name="motion-level" value={level.id} checked={motionPreference===level.id} onChange={()=>setMotion(level.id)} /><span><strong>{level.label}</strong><small>{level.text}</small></span></label>)}</div></fieldset>
                <p className="motion-system-note">{systemReduced ? 'Your device requests reduced motion, so the interface stays still. Your selected level is remembered for when that preference changes.' : 'Your device’s reduced-motion setting always takes priority. Motion pauses when the campus is out of view or this tab is hidden.'}</p>
              </div>
              <div className="setting-card">
                <h3>Keyboard</h3>
                <p>
                  <kbd>Ctrl</kbd> / <kbd>⌘</kbd> + <kbd>K</kbd> opens search.{" "}
                  <kbd>Esc</kbd> returns from details. In search, use <kbd>↑</kbd> / <kbd>↓</kbd> to choose a result and <kbd>Enter</kbd> to open it. <kbd>Tab</kbd> moves between controls; buttons also work with <kbd>Enter</kbd> or <kbd>Space</kbd>.
                </p>
              </div>
              <div className="setting-card"><h3>Your space</h3><p>Preferences and saved choices are remembered in this browser. There is no cross-device backup.</p><button className="secondary-button" onClick={()=>openOverlay('help')}>How CurricuPath works</button></div>
            </section>
          )}
          {drawer === "display" && <button className="secondary-button" onClick={()=>openOverlay("privacy")}>Privacy & local records</button>}
          {drawer === "privacy" && <PrivacyPanel />}
          {drawer === "help" && <SpaceHelp onNavigate={destination=>{if(['profile','evidence'].includes(destination))openOverlay(destination);else navigate(destination);}} />}
          {drawer === "profile" && (
            <ProfilePage
              profile={profile}
              setProfile={setProfile}
              persistence={profilePersistence}
              modules={modules}
              loading={loading.modules}
              error={loadErrors.modules}
              onRetry={() => retries.current.modules?.()}
              onSave={() => {
                setSavedProgramme(profile.programme);
                closeDrawer();
                navigate("home");
              }}
            />
          )}
          {drawer === "evidence" && (
            <EvidencePage
              onInspect={async code=>{const token=++detailRequest.current;openOverlay("module",{type:"module",loading:true,id:code});try{const data=await getJson(`/modules/${code}`);if(token===detailRequest.current)setDetail({type:"module",data});}catch(e){if(token===detailRequest.current)setDetail({type:"module",error:e.message});}}}
              evidence={evidence}
              loading={loading.evidence}
              error={loadErrors.evidence}
              onRetry={() => retries.current.evidence?.()}
            />
          )}
          {detail && drawer === "module" && (detail.data?<ModuleDetail item={detail.data} />:<AsyncPanel loading={detail.loading} title="Recorded module information" error={detail.error}/>) }
          {detail && drawer === "sources" && (
            <SourceTrail
              data={detail.data}
              onRegister={() => openOverlay("evidence")}
            />
          )}
        </Drawer>
      )}
      {searchOpen && (
        <GlobalSearch
          modules={modules}
          loading={loading}
          errors={loadErrors}
          onRetry={(key) => retries.current[key]?.()}
          onClose={() => setSearchOpen(false)}
          onAction={id => {
            setSearchOpen(false);
            if (['display','help','profile','evidence'].includes(id)) setDrawer(id);
            else navigate(id);
          }}
          onModule={(code) => {
            setSearchOpen(false);
            navigate("plan");
            openModule(code);
          }}
        />
      )}
    </div>
  );
}
