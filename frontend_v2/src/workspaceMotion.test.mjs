import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

function harness() {
  const previous = { current: 'home' }, calls = [];
  let cleanup, listener;
  const element = matches => ({ matches: () => matches, animate(frames, options) {
    const call = { frames, options, cancelled: false }; calls.push(call);
    return { cancel() { call.cancelled = true; } };
  } });
  const document = { hidden: false,
    getElementById: () => ({ children: [element(false), element(true)] }),
    addEventListener: (_, fn) => { listener = fn; }, removeEventListener: () => { listener = null; },
  };
  const context = { document, useRef: () => previous, useEffect: effect => { cleanup?.(); cleanup = effect(); } };
  const source = readFileSync(new URL('./useWorkspaceMotion.js', import.meta.url), 'utf8')
    .replace("import { useEffect, useRef } from 'react';", '').replace('export function', 'function');
  vm.runInNewContext(source + '\nthis.run = useWorkspaceMotion;', context);
  return { calls, document, run: context.run, hide() { document.hidden = true; listener?.(); } };
}
test('same-route changes do not animate; navigation skips the shell', () => {
  const h = harness(); h.run('home', 'expressive'); assert.equal(h.calls.length, 0);
  h.run('plan', 'expressive'); assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].frames[0].transform, 'translateX(16px)');
});
test('reverse navigation cancels prior effect and reverses direction', () => {
  const h = harness(); h.run('plan', 'expressive'); h.run('home', 'expressive');
  assert.equal(h.calls[0].cancelled, true);
  assert.equal(h.calls[1].frames[0].transform, 'translateX(-16px)');
});
test('Off and hidden routes never animate', () => {
  const h = harness(); h.run('plan', 'off'); h.document.hidden = true;
  h.run('advisor', 'expressive'); assert.equal(h.calls.length, 0);
});
test('Subtle fades and hiding a tab cancels active animation', () => {
  const h = harness(); h.run('plan', 'subtle');
  assert.equal(h.calls[0].frames[0].transform, 'none'); h.hide();
  assert.equal(h.calls[0].cancelled, true);
});
