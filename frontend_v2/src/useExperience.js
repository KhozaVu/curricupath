import { useEffect, useState } from 'react';

export function usePageVisibility() {
  const [visible,setVisible] = useState(!document.hidden);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange',update);
    return () => document.removeEventListener('visibilitychange',update);
  },[]);
  return visible;
}

export function useInView(ref) {
  const [visible,setVisible] = useState(true);
  useEffect(() => {
    if (!ref.current || !window.IntersectionObserver) return;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { rootMargin:'80px' });
    observer.observe(ref.current);
    return () => observer.disconnect();
  },[ref]);
  return visible;
}
