import { describe, expect, it } from 'vitest';
import { ApiError, apiError } from '../api/errors';

describe('apiError', () => {
  it('turns a server error code into something a player can act on', () => {
    const error = apiError(403, JSON.stringify({ error: 'INVALID_ROOM_PASSWORD', message: 'room password does not match' }));

    expect(error.message).toBe('비밀번호가 맞지 않습니다.');
    expect(error.code).toBe('INVALID_ROOM_PASSWORD');
    expect(error.status).toBe(403);
    // The lobby renders `e.message` off a plain Error, so it must stay one.
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
  });

  it('never leaks the raw body into the message', () => {
    const body = JSON.stringify({ error: 'ROOM_FULL', message: 'room is full' });
    const error = apiError(409, body);

    expect(error.message).not.toContain('HTTP');
    expect(error.message).not.toContain('{');
    expect(error.message).not.toContain('ROOM_FULL');
    expect(error.detail).toBe(body);
  });

  it('falls back to the status when the body is not the usual JSON', () => {
    expect(apiError(502, '<html>Bad Gateway</html>').message).toBe('서버에 문제가 생겼습니다. 잠시 후 다시 시도해주세요.');
    expect(apiError(404, '').message).toBe('찾을 수 없습니다.');
    expect(apiError(418, '').message).toBe('요청을 처리하지 못했습니다 (HTTP 418).');
    expect(apiError(502, '<html>').code).toBeNull();
  });

  it('falls back to the status for a code this build has not caught up with', () => {
    const error = apiError(403, JSON.stringify({ error: 'SOME_NEW_CODE' }));

    expect(error.code).toBe('SOME_NEW_CODE');
    expect(error.message).toBe('권한이 없어 요청이 거절되었습니다.');
  });
});
