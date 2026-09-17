# Design

> Maintained by frontend-god-mode.
> Source of truth for typography, color, layout, and component tokens of the ChatQT desktop client.
> Read this BEFORE touching the UI in any subsequent session. Tokens live in `chatqt/theme.py`.

## Aesthetic direction

Editorial utility on paper — a warm off-white writing surface with hairline rules, one terracotta accent, and strictly square corners. It should feel like a well-set technical document, not an AI dashboard.

## Dials

- DESIGN_VARIANCE: 3 / 10 (calm, grid-aligned; personality comes from type + one accent)
- MOTION_INTENSITY: 1 / 10 (native desktop app, no decorative animation)
- VISUAL_DENSITY: 5 / 10 (comfortable reading, compact sidebar)

## Type stack

- Display / body: Geist (bundled TTFs in `chatqt/assets/fonts`, weights 400–600)
- CJK fallback: Noto Sans CJK SC → PingFang SC → Microsoft YaHei
- Mono: Geist Mono → JetBrains Mono → Consolas (code blocks, timestamps, model labels, status bar)
- Sizes: body 14px / line-height 1.6; captions 11–12px; conversation title 17px; dialog title 20px, tracking −0.4px
- All-caps only for micro-labels (model tag, code-block language), letter-spacing +0.4–0.6px

Banned in this project: Inter, Roboto, Arial, system-ui as primary, serif anywhere.

## Color tokens

Stone (warm) neutral family, one accent. Hex values are what Qt consumes.

| Token          | Hex       | Use                                              |
|----------------|-----------|--------------------------------------------------|
| BG             | `#FAFAF9` | window / chat canvas                             |
| SURFACE        | `#F5F5F4` | sidebar, user bubble, code block, table header   |
| SURFACE_2      | `#EDEBE8` | hover rows, inline code, disabled controls       |
| FG             | `#1C1917` | body text                                        |
| FG_SOFT        | `#44403C` | blockquotes, secondary text                      |
| MUTED          | `#78716C` | captions, placeholders                           |
| MUTED_2        | `#A8A29E` | timestamps, disabled icons                       |
| BORDER         | `#E7E5E4` | hairline rules                                   |
| BORDER_STRONG  | `#D6D3D1` | inputs, tables, code-block outline               |
| ACCENT         | `#C45A3A` | primary button, focus ring, selected row bar, links |
| ACCENT_HOVER   | `#A84A2F` | primary hover                                    |
| ACCENT_PRESSED | `#8F3F28` | primary pressed                                  |
| ACCENT_SOFT    | `#F6E7E0` | text selection, selected conversation row        |
| ERROR          | `#BE3554` | inline API errors                                |
| ERROR_SOFT     | `#F8E4E9` | error box background                             |
| SUCCESS        | `#059669` | "connection ok" feedback                         |
| ON_ACCENT      | `#FCF7F4` | text on accent                                   |

Banned: pure `#000` / `#FFF`, gradients of any kind, a second accent hue, drop shadows (depth is expressed with borders only).

## Shape

- `border-radius: 0` on every widget, dialog, button, input, thumbnail, scrollbar, tooltip. No exceptions — this is a hard requirement from the product owner.
- Depth = 1px borders. Selected sidebar row uses a 2px accent bar on the left edge, not a filled background.
- No nested cards: assistant messages sit directly on the canvas; only user messages get a surface box.

## Layout

- Window min 1024×680, default 1240×800. Sidebar fixed 272px (`Settings.sidebar_width`), chat column capped at 780px and centered.
- Sidebar: wordmark → primary "新对话" → search → conversation list → (bottom-left) 接口设置 / 数据文件夹.
- Header: editable title · created time · model combo · refresh / pin / export / delete icon buttons.
- Composer: bordered frame, auto-growing input (max ~10 lines), attachment strip above, tool row (attach · hint · send/stop).
- Status bar: host on the left, message/token count on the right, mono 11px.

## Component inventory (all custom, `chatqt/widgets.py`, `chatqt/dialogs.py`)

- `ConversationRow` — title / relative time / preview, accent left bar when selected.
- `MessageWidget` — role label + time + hover actions (copy · regenerate · delete), thumbnails, `MessageBody` (QTextBrowser with Markdown → HTML).
- `Composer`, `AttachmentStrip`, `AttachmentTile` — paste / drop / pick images; thumbnails with remove button.
- `EmptyState` — headline + three prompt suggestions as bordered buttons (not cards).
- `ApiSettingsDialog`, `DataFolderDialog` — form grid, mono value display, primary action bottom-right.
- Icons: hand-drawn 24px line SVGs in `chatqt/icons.py` (stroke 1.75), tinted per state. No emoji.

## States

- Loading: streaming text appears token-by-token; header shows "生成中…"; send button becomes stop.
- Empty: designed `EmptyState` with suggestions; sidebar shows "还没有对话" copy.
- Error: inline `#ErrorBox` under the failed turn with the HTTP/API message + "重试".
- Success: status bar updates with token usage; connection test shows latency in green.

## Brand voice (copy)

Chinese UI copy, direct and short. Verbs on buttons ("保存", "测试连接", "更换文件夹…"). No marketing adjectives.

## Accessibility floor

- Body text `#1C1917` on `#FAFAF9` ≈ 15.7:1; muted `#78716C` on `#FAFAF9` ≈ 4.6:1 (AA).
- Every interactive control has a 1px accent focus border; all actions reachable by keyboard (see README shortcuts).
- Minimum click target 32×32 for icon buttons, 36px tall for text buttons.

## Last updated

2026-09-17 — initial system for the PySide6 client.
