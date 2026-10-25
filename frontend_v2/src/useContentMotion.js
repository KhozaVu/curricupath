import { useEffect } from 'react';

// Observe additions, not text changes: streaming answers and existing history stay still.
export function useContentMotion(page, motion) {
  useEffect(() => {
    const main = document.getElementById('main-content');
    if (!main || motion === 'off') return;
    const seen = new Set();
    const knownMessages = new WeakSet(main.querySelectorAll('.message-log > *'));
    const active = new Set();
    const animate = (element, delay = 0) => {
      if (!element.animate || document.hidden) return;
      const animation = element.animate([
        { opacity: 0.55, translate: motion === 'expressive' ? '0 8px' : '0 0' },
        { opacity: 1, translate: '0 0' },
      ], { duration: 160, delay, easing: 'ease-out' });
      active.add(animation);
      animation.finished.then(() => active.delete(animation), () => active.delete(animation));
    };
    const scan = () => {
      main.querySelectorAll('.message-log > *').forEach(element => {
        if (knownMessages.has(element)) return;
        knownMessages.add(element);
        animate(element);
      });
      main.querySelectorAll('.explore-list > [data-course-motion-id]').forEach((element, index) => {
        const id = element.dataset.courseMotionId;
        if (seen.has(id)) return;
        seen.add(id);
        if (index < 4) animate(element, index * 40);
      });
    };
    scan();
    const observer = new MutationObserver(scan);
    observer.observe(main, { childList: true, subtree: true });
    const stop = () => { if (document.hidden) active.forEach(animation => animation.cancel()); };
    document.addEventListener('visibilitychange', stop);
    return () => {
      observer.disconnect();
      document.removeEventListener('visibilitychange', stop);
      active.forEach(animation => animation.cancel());
    };
  }, [page, motion]);
}
