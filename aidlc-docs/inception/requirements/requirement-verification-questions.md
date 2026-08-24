# 가이아 프로젝트 온라인 구현 — 요구사항 확인 질문

아래 질문들에 각 [Answer]: 태그 다음에 알파벳 선택지를 입력해 주세요.
선택지에 맞는 것이 없다면 X) Other를 선택하고 설명을 작성해 주세요.

---

## Question 1
구현하려는 플랫폼은 무엇인가요?

A) 웹 브라우저 (React, Vue 등 프론트엔드)

B) 데스크탑 앱 (Electron 등)

C) 웹 + 모바일 모두

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
멀티플레이어 기능을 포함하나요?

A) 온라인 실시간 멀티플레이어 (여러 명이 동시에 플레이)

B) 로컬 멀티플레이어 (같은 화면에서 여러 명)

C) 싱글플레이어만 (AI 상대)

D) 멀티플레이어 + AI 상대 모두 지원

E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 3
초기 구현 범위는 어떻게 설정하나요?

A) 완전한 가이아 프로젝트 (14개 팩션, 전체 규칙 포함)

B) 핵심 규칙만 먼저 구현 (기본 팩션 몇 가지 + 주요 메커니즘)

C) MVP (최소 기능 - 게임 진행 흐름과 기본 규칙만)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
선호하는 백엔드 기술 스택은 무엇인가요?

A) Node.js / TypeScript (Express, Fastify)

B) Java / Spring Boot

C) Python (FastAPI, Django)

D) Go

E) Other (please describe after [Answer]: tag below)

[Answer]: E
RUST

---

## Question 5
선호하는 프론트엔드 기술 스택은 무엇인가요?

A) React + TypeScript

B) Vue.js + TypeScript

C) Svelte / SvelteKit

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
게임 상태 저장 방식은 어떻게 할까요?

A) 데이터베이스에 영구 저장 (게임 재접속 가능)

B) 메모리 내 저장 (세션 종료 시 삭제)

C) 로컬 파일 저장

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 7
사용자 인증/계정 시스템이 필요한가요?

A) 예 — 회원가입/로그인 시스템 포함

B) 아니오 — 게스트 플레이만 (닉네임으로 입장)

C) 간단한 인증 (구글/깃허브 소셜 로그인)

D) Other (please describe after [Answer]: tag below)

[Answer]: B
Phase 1: LLM 기반 코칭 (RAG, MACO Qwen 14B 활용)
Phase 2: MCTS 기반 실제 대전 AI
---

## Question 8
헥사곤 게임 보드 렌더링 방식은 무엇을 선호하나요?

A) Canvas / WebGL (고성능, 커스텀 렌더링)

B) SVG (벡터, 쉬운 인터랙션)

C) CSS + HTML (간단하지만 제한적)

D) 기존 헥사곤 라이브러리 활용 (예: honeycomb.js, react-hex-grid)

E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 9
AI 상대 기능이 필요한 경우, 어느 수준의 AI를 원하나요?

A) 랜덤 행동 (매우 단순)

B) 룰 기반 휴리스틱 AI (기본 전략)

C) AI 상대는 이 프로젝트에서 불필요

D) Other (please describe after [Answer]: tag below)

[Answer]: D
LLM 기반 코칭 + MCTS 기반 실제 대전 AI

---

## Question 10
배포 환경은 어디를 목표로 하나요?

A) 로컬 개발 환경만 (배포 불필요)

B) 클라우드 배포 (AWS, GCP, Azure)

C) 자체 서버 (VPS, 온프레미스)

D) Vercel, Railway, Render 등 PaaS

E) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question: Security Extensions
이 프로젝트에 보안 확장 규칙을 적용할까요?

A) Yes — 모든 보안 규칙을 필수 제약으로 적용 (프로덕션 수준 권장)

B) No — 보안 규칙 생략 (PoC, 프로토타입, 실험적 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question: Property-Based Testing Extension
이 프로젝트에 속성 기반 테스트(PBT) 규칙을 적용할까요?

A) Yes — 모든 PBT 규칙을 필수 제약으로 적용 (비즈니스 로직, 데이터 변환, 직렬화가 있는 프로젝트에 권장)

B) Partial — 순수 함수와 직렬화 라운드트립에만 PBT 규칙 적용

C) No — PBT 규칙 생략 (단순 CRUD, UI 전용, 또는 얇은 통합 레이어 프로젝트)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
