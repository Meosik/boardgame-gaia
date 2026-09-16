import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Explicit cleanup also works when test files share one worker/module cache.
afterEach(cleanup);
