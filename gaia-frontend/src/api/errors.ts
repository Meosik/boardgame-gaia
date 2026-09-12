/**
 * Turns a REST failure into something a player can act on.
 *
 * The server answers every error with `{ "error": CODE, "message": ... }` (see
 * `gaia-server/src/error.rs`); showing that JSON to someone who mistyped a room password is
 * how "HTTP 403: {"error":"INVALID_ROOM_PASSWORD"...}" used to reach the lobby. Callers keep
 * rendering `e.message` — an `ApiError` is a plain `Error` whose message is already Korean —
 * and can read `code`/`status` when they want to branch on a specific failure.
 */

/** Every code `ServerError::into_response` can emit, in the words a player can act on. */
const SERVER_ERROR_MESSAGES: Record<string, string> = {
  ROOM_NOT_FOUND: '그런 방이 없습니다. 룸 코드를 다시 확인해주세요.',
  ROOM_FULL: '방이 가득 찼습니다.',
  ALREADY_STARTED: '이미 시작한 게임이라 참가할 수 없습니다.',
  PLAYER_NOT_FOUND: '그 방에서 내 자리를 찾지 못했습니다.',
  NOT_YOUR_TURN: '지금은 내 차례가 아닙니다.',
  INVALID_ACTION: '지금은 할 수 없는 행동입니다.',
  UNAUTHORISED: '권한이 없습니다.',
  INVALID_SESSION: '접속이 만료되었습니다. 첫 화면에서 다시 참가해주세요.',
  INVALID_NICKNAME: '닉네임을 입력해주세요.',
  INVALID_ROOM_PASSWORD: '비밀번호가 맞지 않습니다.',
  INVALID_SEED: '시드값이 올바르지 않습니다.',
  DB_ERROR: '서버에 문제가 생겼습니다. 잠시 후 다시 시도해주세요.',
  SERIALISE_ERROR: '서버에 문제가 생겼습니다. 잠시 후 다시 시도해주세요.',
  INTERNAL_ERROR: '서버에 문제가 생겼습니다. 잠시 후 다시 시도해주세요.',
};

/** Used when the body carries no code we know — a proxy's HTML page, or a code added server-side
 *  that this table hasn't caught up with yet. */
function messageForStatus(status: number): string {
  if (status === 401 || status === 403) return '권한이 없어 요청이 거절되었습니다.';
  if (status === 404) return '찾을 수 없습니다.';
  if (status === 409) return '지금 상태에서는 처리할 수 없습니다.';
  if (status >= 500) return '서버에 문제가 생겼습니다. 잠시 후 다시 시도해주세요.';
  return `요청을 처리하지 못했습니다 (HTTP ${status}).`;
}

export class ApiError extends Error {
  readonly status: number;
  /** The server's error code, or `null` when the body wasn't the usual JSON shape. */
  readonly code: string | null;
  /** The raw response body, kept for logs — never shown to the player. */
  readonly detail: string;

  constructor(status: number, code: string | null, message: string, detail: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

export function apiError(status: number, body: string): ApiError {
  let code: string | null = null;
  try {
    const parsed: unknown = JSON.parse(body);
    if (parsed && typeof parsed === 'object' && typeof (parsed as { error?: unknown }).error === 'string') {
      code = (parsed as { error: string }).error;
    }
  } catch {
    // Not JSON (a proxy error page, an empty body) — the status still tells the player enough.
  }
  const message = (code && SERVER_ERROR_MESSAGES[code]) || messageForStatus(status);
  return new ApiError(status, code, message, body);
}
