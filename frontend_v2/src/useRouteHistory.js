import { useCallback, useEffect, useRef } from 'react';

// Each history entry owns its scroll position. Filters still live in the URL.
export function useRouteHistory() {
  const positions = useRef(new Map());
  const active = useRef(null);
  const pending = useRef(null);
  const serial = useRef(0);
  const ensure = useCallback(() => {
    let key = window.history.state?.curricupathEntry;
    if (!key) {
      key = `cp-${Date.now()}-${++serial.current}`;
      window.history.replaceState({ ...window.history.state, curricupathEntry:key }, '', window.location.href);
    }
    return key;
  },[]);
  useEffect(() => {
    active.current = ensure();
    const previous = window.history.scrollRestoration;
    window.history.scrollRestoration = 'manual';
    const remember = () => { if(active.current && pending.current === null) positions.current.set(active.current,window.scrollY); };
    window.addEventListener('scroll',remember,{passive:true});
    return () => {window.removeEventListener('scroll',remember);window.history.scrollRestoration=previous;};
  },[ensure]);
  const push = useCallback((hash, replace=false) => {
    if(active.current)positions.current.set(active.current,window.scrollY);
    pending.current=null;
    if(replace) window.history.replaceState(window.history.state,'',hash);
    else {
      const key=`cp-${Date.now()}-${++serial.current}`;
      positions.current.set(key,window.scrollY);
      window.history.pushState({ curricupathEntry:key },'',hash);
      active.current=key;
    }
  },[]);
  const arrived = useCallback(() => {
    active.current=ensure();
    pending.current=positions.current.get(active.current) || 0;
  },[ensure]);
  const restore = useCallback((settled=false) => {
    if(pending.current === null)return;
    window.scrollTo({top:pending.current,behavior:'instant'});
    if(settled) pending.current=null;
  },[]);
  return {push,arrived,restore};
}
