# OptionBadge Feature Plan

## Goal
- Add an `OptionBadge` displayed on the selected strike(s) with color and placement rules:
  - Buy Call → top of strikes ruler, green
  - Sell Call → bottom of strikes ruler, green
  - Buy Put → top of strikes ruler, red
  - Sell Put → bottom of strikes ruler, red

## Current UI Context
- `OptionBadge` widget exists and draws a bottom-pointing badge `delta_spread/ui/option_badge.py:8` and `delta_spread/ui/option_badge.py:16`.
- Strikes ruler draws the horizontal axis and tick labels `delta_spread/ui/strike_ruler.py:8` and `delta_spread/ui/strike_ruler.py:35`.
- Legs are added from the Add menu and chart updates propagate selected strike lines `delta_spread/ui/main_window.py:325` and `delta_spread/ui/main_window.py:410`.
- Selected strikes flow to the ruler via `set_selected_strikes` `delta_spread/ui/main_window.py:430` and `delta_spread/ui/strike_ruler.py:18`.

## Behavior Rules
- One badge per leg placed at the leg’s strike.
- Color maps by option type:
  - Call → green (use app’s existing green for consistency)
  - Put → red (reuse ruler’s selected red `#DC2626` for consistency)
- Placement maps by side:
  - Buy → top of ruler (pointer downward)
  - Sell → bottom of ruler (pointer upward)
- Badge text displays the leg summary, e.g., "BUY CALL", "SELL PUT".

## Design Overview
- Compute the x-position for a strike using the same mapping as the ruler ticks: `x = (s - mn) / (mx - mn) * width` `delta_spread/ui/strike_ruler.py:38`.
- Anchor badges as child widgets of the strikes ruler, positioned via `move(x - badge_width/2, y_top_or_bottom)`.
- Determine y-position by placement:
  - Top: above ruler center line and above tick labels
  - Bottom: below ruler center line
- Handle window resize by re-computing positions in the ruler’s `resizeEvent` or on `paintEvent`.
- Avoid overlapping badges at the same strike by offsetting subsequent badges slightly horizontally.

## Color Palette Extraction
- Centralize color constants in `delta_spread/ui/styles.py` for consistent usage across widgets and QSS strings.
- Proposed constants and sources:
  - `COLOR_BG_WHITE = #FFFFFF` from `delta_spread/ui/styles.py:1`
  - `COLOR_TEXT_PRIMARY = #333333` from `delta_spread/ui/styles.py:1`
  - `COLOR_PRIMARY = #3B82F6` from `delta_spread/ui/styles.py:5`
  - `COLOR_PRIMARY_HOVER = #2563EB` from `delta_spread/ui/styles.py:11`
  - `COLOR_ACCENT_BLUE = #5CACEE` from `delta_spread/ui/styles.py:29` and `delta_spread/ui/styles.py:55`–`delta_spread/ui/styles.py:56`
  - `COLOR_SUCCESS_GREEN = #22C55E` from `delta_spread/ui/styles.py:22`
  - `COLOR_DANGER_RED = #DC2626` from selected strike color `delta_spread/ui/strike_ruler.py:40`
  - `COLOR_GRAY_100 = #EAEAEA` from `delta_spread/ui/styles.py:14`
  - `COLOR_GRAY_200 = #DDD` from `delta_spread/ui/styles.py:49` and `delta_spread/ui/styles.py:54`
  - `COLOR_GRAY_300 = #CCC` from `delta_spread/ui/styles.py:19` and `delta_spread/ui/styles.py:41`
  - `COLOR_GRAY_400 = #BBB` from `delta_spread/ui/styles.py:15`
  - `COLOR_GRAY_500 = #AAA` from `delta_spread/ui/styles.py:24`
  - `COLOR_GRAY_600 = #888` from `delta_spread/ui/styles.py:23` and `delta_spread/ui/styles.py:50`
  - `COLOR_GRAY_700 = #777` from `delta_spread/ui/styles.py:44`
  - `COLOR_GRAY_800 = #666` from `delta_spread/ui/styles.py:32` and `delta_spread/ui/styles.py:34`
  - `COLOR_GRAY_900 = #555` from `delta_spread/ui/styles.py:16`, `delta_spread/ui/styles.py:24`, and `delta_spread/ui/styles.py:46`
- Refactor approach:
  - Define palette constants at the top of `styles.py`.
  - Convert QSS style strings to f-strings or builder functions that embed palette constants.
  - Update `OptionBadge` to use `COLOR_SUCCESS_GREEN` (calls) and `COLOR_DANGER_RED` (puts) rather than literals.
- Benefits:
  - Single source of truth for colors and easy theme adjustments.
  - Consistency across ruler, badges, metrics, and menus.

## Integration Points
- `MainWindow.update_chart` collects legs and drives visual updates `delta_spread/ui/main_window.py:410`.
- Extend the flow to compute badges from `Strategy.legs` and invoke `StrikeRuler.set_badges(badges)`.
- `StrikeRuler` maintains and positions child `OptionBadge` widgets alongside existing tick rendering `delta_spread/ui/strike_ruler.py:37`.
- `OptionBadge` gains a placement option (top/bottom) and color schema selection `delta_spread/ui/option_badge.py:9`.

## Edge Cases
- No strikes or a degenerate range (mx == mn): skip badge placement `delta_spread/ui/strike_ruler.py:33`.
- Multiple legs sharing the same strike: apply small horizontal offsets to avoid overlap.
- Changing expiries resets badges; clear and re-render after strikes load `delta_spread/ui/main_window.py:246`.

## Acceptance Criteria
- When a leg is added via the Add menu, a badge appears at the leg’s strike with correct color and placement.
- Resizing the window preserves correct badge alignment to strikes.
- Multiple legs produce multiple badges aligned appropriately without unreadable overlap.
- Removing or changing legs updates badges accordingly.
- All colors used by badges and ruler derive from centralized palette constants in `styles.py`.

## Test Plan
- Unit: compute x-position mapping and ensure consistency with ruler math.
- Unit: placement logic mapping from `(side, type)` → `(top/bottom, color)`.
- Integration: add legs and verify badges appear at expected pixel positions relative to strikes.
- Visual/manual: confirm colors, text, pointer direction, and behavior during resize.

## Task List
- Create OptionBadge feature plan document under docs.
- Define OptionBadge UI behavior and placement rules.
- Map legs to badge color and orientation.
- Design badge anchoring on StrikeRuler with resizing.
- Plan badge updates on legs and strikes change.
- Specify overlap handling for multiple badges per strike.
- Define acceptance criteria and test plan.
- Outline integration points in MainWindow and StrikeRuler.
- Extract color palette constants in `styles.py` and refactor style strings to use them.
