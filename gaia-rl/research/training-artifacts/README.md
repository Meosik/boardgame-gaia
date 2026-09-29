# AI 학습·평가 산출물 보관

2026-09-29 시점의 로컬 학습·평가 산출물은 GitHub Release
[`training-snapshot-2026-09-29`](https://github.com/Meosik/boardgame-gaia/releases/tag/training-snapshot-2026-09-29)에
보관한다. 일반 Git에는 큰 체크포인트를 넣지 않는다.

아카이브에는 `gaia-rl/runs/`의 실험·평가 기록과 모델 체크포인트,
`gaia-rl/datasets/`의 파생 학습 데이터, `gaia-rl/research/bgs-records/`의
수집 기록이 들어 있다. 총 19,187개 파일, 원본 파일 크기 합계
5,407,001,957바이트다. 각 원본 파일의 SHA-256은 Release의
`gaia-training-20260929-files.sha256`에 있다.

브라우저 프로필과 쿠키, 빌드·소스 복사본, 영상, 절대 경로 심볼릭 링크,
잠금 파일과 기타 임시 실행 상태는 포함하지 않았다. 이 파일들은 학습
체크포인트나 평가 원본이 아니며, 특히 브라우저 프로필은 공개하면 안 된다.
기존 `runs/`, `datasets/`, `research/bgs-records/`의 Git 무시 규칙은 유지한다.

Release에서 두 `gaia-training-20260929.tar.zst.part-*` 파일과
`gaia-training-20260929-files.sha256`, `gaia-training-20260929-SHA256SUMS`를
받아 저장소 루트에서 다음처럼 복원한다.

```sh
sha256sum -c gaia-training-20260929-SHA256SUMS
cat gaia-training-20260929.tar.zst.part-* | zstd -d -c | tar -xf -
sha256sum -c gaia-training-20260929-files.sha256
```

체크포인트에는 Python pickle/RLlib 파일이 있으므로 신뢰하는 환경에서만
불러온다. 이 보관본은 기존 결과의 스냅샷이며 새 학습을 실행하지 않았다.
