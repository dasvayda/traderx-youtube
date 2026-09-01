# Chart Images Module

**File:** `modules/chart_generator.py`

## 방침

차트는 자동 생성하지 않습니다. 사용자가 TradingView, Yahoo Finance 등에서
직접 캡처한 이미지를 UI에서 씬별로 첨부합니다.

## 역할

사용자가 업로드한 차트 이미지 경로를 씬 ID와 매핑하는 인메모리 레지스트리입니다.
Pipeline의 `_step_assets`에서 `get_chart(scene_id)`를 호출하여 경로를 조회합니다.

## API

```python
from modules.chart_generator import register_chart, get_chart, clear_registry

# 이미지 등록 (app.py에서 업로드 시 자동 호출)
register_chart(scene_id=1, image_path=Path("assets/charts/scene_01_tsla.png"))

# 파이프라인에서 조회
path = get_chart(scene_id=1)   # Path 또는 None

# 새 Job 시작 전 초기화
clear_registry()
```

## UI 동작 (app.py → Tab 3)

1. 씬 목록에서 각 씬의 expander를 엽니다.
2. "シーン画像をアップロード" 파일 업로더에서 PNG/JPG를 선택합니다.
3. 이미지가 `assets/charts/scene_{id}_{filename}` 에 저장되고 레지스트리에 등록됩니다.
4. 이미 등록된 이미지는 미리보기로 표시됩니다.

## 이미지 미등록 시 동작

파이프라인에서 해당 씬에 이미지가 없으면 `title_card`(텍스트 카드)로 폴백됩니다.
경고 메시지가 로그에 출력됩니다.

## 권장 이미지 사양

| 항목 | 권장 값 |
|------|---------|
| 해상도 | 1080px 이상 (가로) |
| 종횡비 | 16:9 또는 4:3 (자동 크롭됨) |
| 형식 | PNG, JPG, WebP |
| 배경 | 다크 테마 권장 (TradingView 기본값) |
