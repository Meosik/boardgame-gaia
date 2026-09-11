//! Site-wide shared-password gate.
//!
//! The server sits behind a public Cloudflare Tunnel hostname with no other
//! access control — anyone who has the link can hit it. This adds one shared
//! passphrase (distributed out-of-band to invited players) that has to be
//! entered once per browser before any route, static asset, REST call, or
//! websocket connection is served. It intentionally isn't per-user auth:
//! knowing the password is proof enough, same as a locked door with one key.
//!
//! Disabled (pass-through) when `GAIA_SITE_PASSWORD` isn't set, so local dev
//! and `docker-compose` setups without it configured keep working unchanged.

use axum::{
    body::Bytes,
    extract::Request,
    http::{header, HeaderMap, StatusCode},
    middleware::Next,
    response::{Html, IntoResponse, Redirect, Response},
    routing::get,
    Router,
};
use serde::Deserialize;
use sha2::{Digest, Sha256};

const COOKIE_NAME: &str = "gaia_gate";
// One year — this is a shared secret, not a per-user session, so there's
// nothing to expire; re-entering it on every device is the actual friction.
const COOKIE_MAX_AGE: &str = "31536000";

#[derive(Clone)]
pub struct SiteGate {
    /// hex-encoded sha256 of the shared password. `None` disables the gate.
    expected: Option<String>,
}

impl SiteGate {
    pub fn from_env() -> Self {
        let password = std::env::var("GAIA_SITE_PASSWORD").ok();
        let gate = Self::with_password(password.as_deref());
        if gate.expected.is_none() {
            log::warn!("GAIA_SITE_PASSWORD not set — site gate disabled, server is open to anyone with the link");
        }
        gate
    }

    fn with_password(password: Option<&str>) -> Self {
        let expected = password
            .filter(|password| !password.is_empty())
            .map(hash);
        Self { expected }
    }

    fn satisfied_by(&self, request: &Request) -> bool {
        let Some(expected) = &self.expected else {
            return true;
        };
        request
            .headers()
            .get(header::COOKIE)
            .and_then(|value| value.to_str().ok())
            .and_then(|raw| cookie_value(raw, COOKIE_NAME))
            .is_some_and(|value| value == *expected)
    }
}

// Case-insensitive: friends retyping the shared passphrase from a Kakao/Discord
// message shouldn't get locked out over Shift being on.
fn hash(password: &str) -> String {
    format!("{:x}", Sha256::digest(password.trim().to_lowercase().as_bytes()))
}

fn cookie_value(raw: &str, name: &str) -> Option<String> {
    raw.split(';').find_map(|part| {
        let (key, value) = part.trim().split_once('=')?;
        (key == name).then(|| value.to_string())
    })
}

pub async fn require_password(gate: SiteGate, request: Request, next: Next) -> Response {
    let path = request.uri().path();
    // Health checks (hit in-container, no browser/cookie involved) and the
    // gate page itself always have to stay reachable.
    if path == "/health" || path == "/gate" {
        return next.run(request).await;
    }
    let satisfied = gate.satisfied_by(&request);
    log::info!(
        "gate check {} {path} ua={:?} satisfied={satisfied}",
        request.method(),
        request
            .headers()
            .get(header::USER_AGENT)
            .and_then(|v| v.to_str().ok())
            .unwrap_or("<none>"),
    );
    if satisfied {
        return next.run(request).await;
    }
    if path.starts_with("/api") || path.starts_with("/ws") {
        return StatusCode::UNAUTHORIZED.into_response();
    }
    Redirect::to("/gate").into_response()
}

#[derive(Deserialize)]
pub struct GateForm {
    #[serde(default)]
    password: String,
}

/// `/gate` GET+POST pair, generic over the app's state `S` since the gate
/// closes over its own `SiteGate` rather than pulling it through `State<_>` —
/// that lets it merge straight into `Router<AppState>` without needing its
/// own state type.
pub fn routes<S>(gate: SiteGate) -> Router<S>
where
    S: Clone + Send + Sync + 'static,
{
    Router::new().route(
        "/gate",
        get(show_form).post(move |headers: HeaderMap, body: Bytes| {
            let gate = gate.clone();
            async move { submit(gate, headers, body).await }
        }),
    )
}

pub async fn show_form() -> Html<String> {
    Html(render_form(None))
}

// Parses the body manually (rather than the `Form` extractor) so a
// content-type/encoding quirk from an unusual client — an in-app browser's
// WebView, say — logs the actual bytes it sent instead of axum silently
// answering with its default, bodyless 400 before this code ever runs.
async fn submit(gate: SiteGate, headers: HeaderMap, body: Bytes) -> Response {
    let user_agent = headers
        .get(header::USER_AGENT)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("<none>")
        .to_string();

    let form: GateForm = match serde_urlencoded::from_bytes(&body) {
        Ok(form) => form,
        Err(err) => {
            log::warn!(
                "/gate POST body unparseable (ua={user_agent}, content-type={:?}, len={}): {err}",
                headers
                    .get(header::CONTENT_TYPE)
                    .and_then(|v| v.to_str().ok()),
                body.len(),
            );
            return Html(render_form(Some(
                "입력을 확인하지 못했습니다. 다시 시도해주세요.",
            )))
            .into_response();
        }
    };

    let Some(expected) = &gate.expected else {
        return Redirect::to("/").into_response();
    };
    let submitted = hash(&form.password);
    log::info!(
        "/gate POST ua={user_agent} matched={}",
        submitted == *expected
    );
    if submitted != *expected {
        return Html(render_form(Some("비밀번호가 틀렸습니다."))).into_response();
    }

    let cookie = format!(
        "{COOKIE_NAME}={submitted}; Path=/; Max-Age={COOKIE_MAX_AGE}; HttpOnly; Secure; SameSite=Lax"
    );
    ([(header::SET_COOKIE, cookie)], Redirect::to("/")).into_response()
}

fn render_form(error: Option<&str>) -> String {
    let error_html = error
        .map(|message| format!(r#"<p class="error">{message}</p>"#))
        .unwrap_or_default();
    format!(
        r#"<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gaia Project</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #0b1120; color: #e2e8f0;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
  form {{ background: #1e293b; padding: 2rem; border-radius: 8px; width: 90%; max-width: 320px; }}
  h1 {{ font-size: 1.1rem; margin: 0 0 1rem; }}
  input {{ width: 100%; box-sizing: border-box; padding: 0.6rem; border-radius: 4px;
           border: 1px solid #334155; background: #0f172a; color: #e2e8f0; margin-bottom: 0.75rem; }}
  button {{ width: 100%; padding: 0.6rem; border-radius: 4px; border: none;
            background: #6366f1; color: white; font-weight: 600; cursor: pointer; }}
  .error {{ color: #f87171; margin: 0 0 0.75rem; font-size: 0.9rem; }}
  .external {{ display: none; margin-top: 0.75rem; text-align: center; font-size: 0.85rem; }}
  .external a {{ color: #a5b4fc; }}
</style>
</head>
<body>
<form method="post" action="/gate">
  <h1>Gaia Project 입장 비밀번호</h1>
  {error_html}
  <input type="password" name="password" placeholder="비밀번호" autofocus>
  <button type="submit">입장</button>
  <p class="external" id="external-link">
    카카오톡 안에서는 로그인이 유지되지 않아요.
    <a href="" id="open-external">여기를 눌러 외부 브라우저로 열기</a>
  </p>
</form>
<script>
  // KakaoTalk's in-app WebView doesn't reliably persist the cookie this page
  // sets after a correct password, so the same in-app tab loops right back
  // here — hand off to the device's real browser instead, where it works.
  if (/KAKAOTALK/i.test(navigator.userAgent)) {{
    var target = "kakaotalk://web/openExternal?url=" + encodeURIComponent(location.href);
    document.getElementById("external-link").style.display = "block";
    document.getElementById("open-external").href = target;
    location.href = target;
  }}
</script>
</body>
</html>"#
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{header, StatusCode},
        middleware::from_fn,
        routing::get as axum_get,
    };
    use axum_test::TestServer;

    fn app(gate: SiteGate) -> TestServer {
        let router: Router<()> = routes(gate.clone())
            .route("/", axum_get(|| async { "home" }))
            .route("/api/rooms", axum_get(|| async { "rooms" }))
            .layer(from_fn(move |req: Request<Body>, next| {
                let gate = gate.clone();
                async move { require_password(gate, req, next).await }
            }));
        TestServer::new(router).expect("test server")
    }

    #[tokio::test]
    async fn disabled_gate_passes_everything_through() {
        let server = app(SiteGate::with_password(None));
        let res = server.get("/").await;
        res.assert_status_ok();
    }

    #[tokio::test]
    async fn root_without_cookie_redirects_to_gate() {
        let server = app(SiteGate::with_password(Some("secret")));
        let res = server.get("/").await;
        res.assert_status(StatusCode::SEE_OTHER);
        assert_eq!(res.header(header::LOCATION), "/gate");
    }

    #[tokio::test]
    async fn api_without_cookie_is_unauthorized_not_redirected() {
        let server = app(SiteGate::with_password(Some("secret")));
        let res = server.get("/api/rooms").await;
        res.assert_status(StatusCode::UNAUTHORIZED);
    }

    #[tokio::test]
    async fn wrong_password_shows_error_without_setting_cookie() {
        let server = app(SiteGate::with_password(Some("secret")));
        let res = server.post("/gate").form(&[("password", "nope")]).await;
        res.assert_status_ok();
        assert!(res.maybe_header(header::SET_COOKIE).is_none());
        res.assert_text_contains("비밀번호가 틀렸습니다");
    }

    #[tokio::test]
    async fn password_check_is_case_insensitive() {
        let server = app(SiteGate::with_password(Some("KHU-2osvz9")));
        let res = server.post("/gate").form(&[("password", "khu-2OSVZ9")]).await;
        res.assert_status(StatusCode::SEE_OTHER);
    }

    #[tokio::test]
    async fn correct_password_grants_access_via_cookie() {
        let server = app(SiteGate::with_password(Some("secret")));
        let res = server.post("/gate").form(&[("password", "secret")]).await;
        res.assert_status(StatusCode::SEE_OTHER);
        let cookie = res
            .header(header::SET_COOKIE)
            .to_str()
            .unwrap_or_else(|error| panic!("response cookie should be valid text: {error}"))
            .to_string();
        assert!(cookie.contains("HttpOnly"));
        assert!(cookie.contains("Secure"));

        let res = server.get("/").add_header(header::COOKIE, cookie).await;
        res.assert_status_ok();
        res.assert_text("home");
    }
}
