import { useEffect, useRef } from 'react';

// Presentation only: never remount the workspace or delay navigation.
export function useWorkspaceMotion(page, motion) {
  const previous = useRef(page);
  useEffect(() => {
    const from = previous.current;
    previous.current = page;
    if (from === page || motion === 'off' || document.hidden) return;
    const order = ['home', 'plan', 'advisor', 'explore'];
    const direction = order.indexOf(page) >= order.indexOf(from) ? 1 : -1;
    const animations = [];
    for (const element of document.getElementById('main-content')?.children || []) {
      if (!element.matches('.page-content, .advisor-page, .setup-empty') || !element.animate) continue;
      animations.push(element.animate([
        { opacity: 0.25, transform: motion === 'expressive' ? `translateX(${direction * 16}px)` : 'none' },
        { opacity: 1, transform: 'none' },
      ], { duration: motion === 'expressive' ? 300 : 180, easing: 'cubic-bezier(.22,1,.36,1)' }));
    }
    const stop = () => { if (document.hidden) animations.forEach(animation => animation.cancel()); };
    document.addEventListener('visibilitychange', stop);
    return () => {
      document.removeEventListener('visibilitychange', stop);
      animations.forEach(animation => animation.cancel());
    };
  }, [page, motion]);
}
