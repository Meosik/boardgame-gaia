import loader from '../../public/previews/moweyds-ring/shuttle-preview.js?raw';
import { afterEach, describe, expect, it } from 'vitest';
import { waitFor } from '@testing-library/react';

afterEach(() => {
  window.dispatchEvent(new Event('pagehide'));
  document.body.innerHTML = '';
  window.history.replaceState({}, '', '/');
});

describe('isolated Moweyds ring preview', () => {
  it('does not add anything to the normal game', () => {
    document.body.innerHTML = '<div id="root"><main class="shuttle-preview"><h1>Preview</h1></main></div>';
    window.eval(loader);
    expect(document.querySelector('iframe')).toBeNull();
  });

  it('adds one preview after the shuttle heading, even if loaded twice', () => {
    window.history.replaceState({}, '', '/?shuttlePreview=1');
    document.body.innerHTML = '<div id="root"><main class="shuttle-preview"><h1>Preview</h1></main></div>';
    window.eval(loader);
    window.eval(loader);
    expect(document.querySelectorAll('iframe')).toHaveLength(1);
    expect(document.querySelector('h1')?.nextElementSibling).toHaveAttribute('src', '/previews/moweyds-ring/index.html');
  });

  it('waits for the existing React preview to mount', async () => {
    window.history.replaceState({}, '', '/?shuttlePreview=1');
    document.body.innerHTML = '<div id="root"></div>';
    window.eval(loader);
    document.getElementById('root')!.innerHTML = '<main class="shuttle-preview"><h1>Preview</h1></main>';
    await waitFor(() => expect(document.querySelector('iframe')).not.toBeNull());
  });
});
