import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

function harness({ motion = 'expressive', hidden = false } = {}) {
  const messages = [], courses = [], calls = [];
  let cleanup, observer, disconnected = false;
  const main = { querySelectorAll: selector => selector.startsWith('.message') ? messages : courses };
  const context = {
    useEffect: effect => { cleanup = effect(); },
    document: { hidden, getElementById: () => main, addEventListener() {}, removeEventListener() {} },
    MutationObserver: class { constructor(callback) { observer = callback; } observe() {} disconnect() { disconnected = true; } },
  };
  const source = readFileSync(new URL('./useContentMotion.js', import.meta.url), 'utf8')
    .replace("import { useEffect } from 'react';", '').replace('export function', 'function');
  vm.runInNewContext(source + '\nthis.run = useContentMotion;', context);
  const element = id => ({ dataset: { courseMotionId: id }, animate(frames, options) {
    const call = { frames, options, cancelled: false };
    calls.push(call);
    return { finished: new Promise(() => {}), cancel() { call.cancelled = true; } };
  } });
  return { messages, courses, calls, element, start: () => context.run('advisor', motion),
    scan: () => observer?.(), stop: () => cleanup?.(), disconnected: () => disconnected };
}

test('existing messages stay still; appended messages animate once', () => {
  const h = harness(); h.messages.push(h.element('old')); h.start();
  assert.equal(h.calls.length, 0);
  h.messages.push(h.element('new')); h.scan(); h.scan();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].options.duration, 160);
});
test('course stagger is bounded and returning course IDs do not replay', () => {
  const h = harness(); h.courses.push(...Array.from({ length: 8 }, (_, i) => h.element(String(i)))); h.start();
  assert.deepEqual(h.calls.map(c => c.options.delay), [0, 40, 80, 120]);
  h.courses.splice(0, 8, h.element('0')); h.scan();
  assert.equal(h.calls.length, 4);
});
test('off mode and hidden tabs never start effects', () => {
  for (const options of [{ motion: 'off' }, { hidden: true }]) {
    const h = harness(options); h.courses.push(h.element('a')); h.start();
    h.messages.push(h.element('b')); h.scan(); assert.equal(h.calls.length, 0);
  }
});
test('cleanup disconnects observation and cancels active animation', () => {
  const h = harness(); h.start(); h.messages.push(h.element('new')); h.scan(); h.stop();
  assert.equal(h.disconnected(), true); assert.equal(h.calls[0].cancelled, true);
});
test('subtle mode fades without movement', () => {
  const h = harness({ motion: 'subtle' }); h.start(); h.messages.push(h.element('new')); h.scan();
  assert.equal(h.calls[0].frames[0].translate, '0 0');
});
