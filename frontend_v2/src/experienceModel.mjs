export const MOTION_LEVELS = [
  { id: 'off', label: 'Off', text: 'A composed still frame. No decorative movement.' },
  { id: 'subtle', label: 'Subtle', text: 'Gentle light trails and short transitions.' },
  { id: 'expressive', label: 'Expressive', text: 'Brighter campus light, ambient depth and movement.' },
];

export function motionLevel(value) {
  if (value === 'reduced') return 'off';
  if (value === 'auto') return 'expressive';
  return MOTION_LEVELS.some(level => level.id === value) ? value : 'subtle';
}

export function effectiveMotion(value, systemReduced) {
  return systemReduced ? 'off' : motionLevel(value);
}

export function historySummary(profile) {
  const completed = profile.completed?.length || 0;
  const current = profile.current?.length || 0;
  const declared = completed + current;
  if (profile.historyConfirmed)
    return { label: declared ? 'History confirmed' : 'No history declared · confirmed', tone:'green', text: declared ? 'Your completed and current module declarations are confirmed.' : 'You explicitly confirmed no completed or current modules.' };
  return { label: declared ? 'Partial history · unconfirmed' : 'History unknown', tone:'gold', text: declared ? 'Some modules are declared. Unselected history remains unknown until you confirm it.' : 'No completed or current history has been confirmed. This does not mean you have completed no modules.' };
}

export const SPACE_ACTIONS = [
  { id:'home', title:'Go to Home', detail:'Your campus and next step', terms:'home campus start' },
  { id:'plan', title:'Open your plan', detail:'Curriculum and requirements', terms:'plan modules curriculum map timeline' },
  { id:'advisor', title:'Ask the Advisor', detail:'Questions and grounded guidance', terms:'advisor advice question eligibility' },
  { id:'explore', title:'Explore Wits modules', detail:'Your Wits curriculum', terms:'explore wits modules electives curriculum' },
  { id:'profile', title:'Review your degree profile', detail:'Programme and declared history', terms:'profile programme history degree' },
  { id:'evidence', title:'Inspect evidence and sources', detail:'Recorded rules and provenance', terms:'evidence sources rules handbook' },
  { id:'display', title:'Appearance and accessibility', detail:'Theme, motion and keyboard help', terms:'appearance settings theme motion accessibility keyboard shortcuts' },
  { id:'help', title:'How CurricuPath works', detail:'Planning, guidance and uncertainty', terms:'help orientation how introduction' },
];

export function searchMatches(text, query) {
  const normalize = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  const haystack = normalize(text);
  const compact = haystack.replaceAll(' ', '');
  return normalize(query).split(' ').filter(Boolean).every(word => haystack.includes(word) || compact.includes(word));
}

export function searchEntries(query, modules, courses) {
  const actions = SPACE_ACTIONS.filter(a => !query.trim() || searchMatches(`${a.title} ${a.terms}`, query));
  const curriculum = query.trim() ? modules.filter(m => searchMatches(`${m.course_code} ${m.course_name}`,query)).slice(0,8) : [];

  return [
    ...actions.map(a => ({ ...a, type:'action' })),
    ...curriculum.map(m => ({ id:m.course_code, title:m.course_name, detail:m.course_code, type:'module' })),

  ];
}
