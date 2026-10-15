---
name: ECO Ansible dashboard
description: A Red Hat team workspace for repository health and issue triage.
colors:
  brand-red: "#ee0000"
  selected-dark: "#ff542e"
  interactive-light: "#0066cc"
  interactive-dark: "#92c5f9"
  interactive-hover-light: "#004080"
  interactive-hover-dark: "#b9dafb"
  neutral-white: "#ffffff"
  neutral-canvas-light: "#f2f2f2"
  neutral-charcoal: "#151515"
  neutral-panel-dark: "#1f1f1f"
  neutral-raised-dark: "#292929"
  neutral-secondary-light: "#4d4d4d"
  neutral-border-light: "#c7c7c7"
  neutral-border-dark: "#707070"
  neutral-field-dark: "#a3a3a3"
  neutral-hover-light: "#fafafa"
  neutral-hover-dark: "#262626"
  masthead-hover: "#383838"
  success-light: "#3d7317"
  success-dark: "#87bb62"
  warning-light: "#795600"
  warning-dark: "#ffcc17"
  failure-light: "#b1380b"
  failure-dark: "#f8a080"
  info-light: "#5e40be"
  info-dark: "#b6a6e9"
typography:
  headline:
    fontFamily: "Red Hat Display, sans-serif"
    fontSize: "36px"
    fontWeight: 500
    lineHeight: 1.2
  headline-mobile:
    fontFamily: "Red Hat Display, sans-serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: 1.2
  brand:
    fontFamily: "Red Hat Display, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.15
  brand-parent:
    fontFamily: "Red Hat Display, sans-serif"
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1.15
  metric:
    fontFamily: "Red Hat Display, sans-serif"
    fontSize: "24px"
    fontWeight: 500
    lineHeight: 1.3
  detail-title:
    fontFamily: "Red Hat Display, sans-serif"
    fontSize: "18px"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "Red Hat Text, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Red Hat Text, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.5
  small:
    fontFamily: "Red Hat Text, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sharp: "0px"
  default: "3px"
spacing:
  step-8: "8px"
  step-12: "12px"
  step-16: "16px"
  step-20: "20px"
  step-24: "24px"
  step-32: "32px"
  step-48: "48px"
components:
  button-neutral:
    backgroundColor: "{colors.neutral-white}"
    textColor: "{colors.neutral-charcoal}"
    rounded: "{rounded.default}"
    padding: "9px 14px"
  button-masthead:
    backgroundColor: "transparent"
    textColor: "{colors.neutral-white}"
    rounded: "{rounded.default}"
    padding: "9px 14px"
  filter-field:
    backgroundColor: "{colors.neutral-white}"
    textColor: "{colors.neutral-charcoal}"
    rounded: "{rounded.sharp}"
    padding: "8px 12px"
    height: "48px"
  view-navigation:
    backgroundColor: "transparent"
    textColor: "{colors.neutral-secondary-light}"
    rounded: "{rounded.sharp}"
    padding: "16px 24px"
  workspace-row:
    backgroundColor: "{colors.neutral-white}"
    textColor: "{colors.neutral-charcoal}"
    rounded: "{rounded.sharp}"
  issue-label:
    backgroundColor: "{colors.neutral-canvas-light}"
    textColor: "{colors.neutral-charcoal}"
    rounded: "{rounded.default}"
    padding: "4px 10px"
  status-label:
    textColor: "{colors.success-light}"
    typography: "{typography.label}"
  repository-details:
    textColor: "{colors.interactive-light}"
    typography: "{typography.small}"
---
# Design System: ECO Ansible dashboard

## Overview

**Creative North Star: "Red Hat team workspace"**

A precise, approachable team workspace grounded in the user-selected Red Hat design language. The black masthead, neutral content surfaces, Red Hat typefaces, red selected-view accent, and blue interactions give dense repository information a consistent visual hierarchy.

This is a local implementation in native HTML, CSS, and JavaScript, rather than an installation of the RHDS component runtime. The shipped stylesheet is the authority for implementation details; official RHDS references explain the selected language. Light and dark themes use the same structure and adapt their neutral, interaction, and status colors.

**Key Characteristics:**

- Black masthead with neutral light and dark work surfaces.
- Red Hat Display for prominent headings and metrics; Red Hat Text for body copy and controls.
- Red selected-view underline, blue interactions, and explicit icon-and-label statuses.
- Flat, square information panels with subtly rounded action controls.

The direction is established by [PRODUCT.md](PRODUCT.md) and the user's pinned [Red Hat design system](https://ux.redhat.com/). This record describes the completed build in [site/styles.css](site/styles.css), [site/index.html](site/index.html), and [site/app.js](site/app.js); the dashboard composition remains in [.impeccable/dashboard-brief.md](.impeccable/dashboard-brief.md).

## Colors

The palette uses neutral surfaces, a concentrated red selection cue, blue interactions, and semantic status colors. Frontmatter records the exact shipped values; theme pairs are explicit tokens rather than inferred ramps.

### Primary

- **Brand red / selected dark:** underline the active view. The light and dark values follow [RHDS tabs style](https://ux.redhat.com/elements/tabs/style/).

### Secondary

- **Interactive light / dark:** links, caret, and keyboard focus. Hover colors deepen blue on light surfaces and lighten it on dark surfaces. The [RHDS button style](https://ux.redhat.com/elements/button/style/) establishes blue interactions; the local stylesheet defines these native control variants.

### Neutral

- **Neutral white / canvas light:** content surface and surrounding page, with the canvas also used for inset details and domain headings.
- **Neutral charcoal / panel dark / raised dark:** persistent masthead, dark canvas, dark panel, and inset surface hierarchy.
- **Neutral secondary / border / field:** secondary copy, one-pixel separators, and stronger input outlines. The [RHDS border tokens](https://ux.redhat.com/tokens/border/) inform the border and focus language.
- **Neutral hover / masthead hover:** row and masthead-action hover feedback.

### Semantic status

- **Success:** Passing.
- **Failure:** Failing.
- **Info:** Running.
- **Warning:** Unknown, Data error, collection notices, and triage signals.
- **Secondary neutral:** No Actions.

**The Selection and Action Rule.** Reserve UI red for the selected view; the official Red Hat logo retains its brand red. Use blue for links and focus indicators.

**The Status Has Words Rule.** Keep the status icon and readable label together; color is an additional signal.

## Typography

Prominent headings, the brand, overview metrics, and detail titles use Red Hat Display. Body copy, controls, repository links, metadata, and domain headings use Red Hat Text. This pairing follows the [RHDS font-family guidance](https://ux.redhat.com/foundations/typography/font-family/); the local hierarchy is recorded above without claiming every heading matches an RHDS runtime default.

The six unmodified WOFF2 files cover regular, medium, and bold weights in both families. They are self-hosted with `font-display: swap`; [site/fonts/README.md](site/fonts/README.md) records the upstream commit, and `site/fonts/OFL.txt` plus `site/fonts/LICENSE` retain the included SIL Open Font License and notices.

- **Headline:** medium Display for the page title; the mobile role applies at the small breakpoint.
- **Brand:** regular Display for “Red Hat” above bold Display for the dashboard name, separated from the hat by a white vertical rule; both lines reduce to (18px) on small screens.
- **Metric:** medium Display with tabular numbers; reduces to (23px) on small screens.
- **Detail title:** medium Display for expanded repository sections.
- **Body:** regular Text with a (1.5) line height. The page description is capped at (70ch), and reading guidance at (75ch).
- **Label / small:** medium or regular Text for field labels, statuses, secondary copy, and metadata. Column labels use bold Text at (14px).

Controls inherit the body font before local size and weight adjustments. Issue titles use medium Text at (18px), keeping them within the reading hierarchy. The code does not load Red Hat Mono; inline code retains the browser's monospace family.

## Layout

The main container has a maximum width of (1440px) with (32px) padding. The masthead uses (32px) minimum horizontal padding and aligns to the content at larger widths. Reused spacing follows the frontmatter's measured steps; the implementation also uses small contextual gaps for icon-label pairs and metadata.

The filter toolbar starts with a flexible search column and three filter columns. At (1150px), search spans the toolbar above three equal filters. At (1000px), repository column headers disappear, repository rows become a two-column arrangement, compatibility and release fields span the width, visible mobile labels provide context, and detail sections stack. At (600px), page heading and issue rows stack, the summary becomes a two-column grid, toolbar filters use two columns, and main padding becomes (26px 16px). Long repository names, issue titles, and source values wrap.

## Elevation & Depth

The dashboard has no box shadows. Depth comes from the black masthead, page-versus-panel contrast, raised neutral domain headers and expanded details, one-pixel separators, and subtle row hover surfaces. A visible focus outline uses (3px) width and (3px) offset; the masthead uses its light blue focus color in both themes.

**The Flat Workspace Rule.** Separate information with neutral surface changes and one-pixel dividers; do not add ornamental shadows.

## Shapes

Action buttons and issue-label controls use the subtly softened default radius. Workspace panels, view controls, and filter inputs/selects are square. The view's selected underline is (4px); structural borders and dividers are (1px). Preserve this distinction between controls and information containers.

## Components

### Masthead logo

Match the supplied Red Hat design-system lockup: official fedora, white vertical divider, then “Red Hat” on the first line and the bold dashboard name on the second. The image occupies (64px) square on desktop and (40px) square below the small breakpoint, with clear space from the two-line title. Keep its original aspect ratio and colors in both themes; the masthead remains dark. The header wraps its actions when needed on narrow screens. The accessible home link includes Red Hat and ECO Ansible. Asset source and trademark attribution are in `site/assets/README.md`.

### Buttons

Native neutral action buttons use a surface fill, a field-strength outline, medium Text, and the default corner radius. Their minimum height is (44px); hover uses the raised surface. Disabled reload controls use reduced opacity and a waiting cursor. The masthead theme action is transparent with a light outline and fills with the masthead hover color on hover. There is no shipped filled primary action button.

### Inputs / Fields

Search and native selects have visible labels, square corners, a strong one-pixel outline, and a (48px) height. Their label gap is the smallest frontmatter spacing step. Hover changes the bottom border to the interactive color; focus uses the global outline. Native select behavior remains intact.

### Navigation

The view switcher is a navigation region containing native pressed-state buttons. It uses a one-pixel baseline, unselected secondary text, and a bold active label with the red selected underline. Hover adds a raised surface and a neutral underline, while a selected control retains its red accent. The desktop padding is (16px 24px); small screens use (12px 16px). This is a view switcher styled in the RHDS tabs language, not an ARIA tab widget. Its border transition is (160ms ease-out) only when reduced motion is not requested.

### Cards / Containers

The workspace is one square bordered content surface. Domain headers and expanded details use the raised neutral surface. Repository and issue rows separate with one-pixel rules and use the subtle row-hover token. The desktop toolbar and detail body use the shared (24px) inset; small screens reduce local padding. Do not add standalone rounded repository cards to this system.

### Chips / Labels

Issue labels are native filter buttons with raised neutral fill, a subtle outline, regular Text, and the default radius. Desktop minimum height is (34px); at the small breakpoint it becomes (44px). Clicking a label applies the corresponding issue-label filter.

### Status labels

Status labels are compact inline icon-and-word pairs. The inline SVG is (16px), outlined with rounded joins and caps; its stroke follows the semantic text color. Passing uses a check in a circle; Failing a cross in a circle; Running a clock; Unknown and Data error a warning triangle; No Actions a horizontal mark in a circle. Status labels have no filled pill container.

### Repository details and data context

Native disclosure summaries use blue text and an underline on hover; expansion reveals a raised grid of source-linked sections. Preserve the distinction between supported Core metadata, configured CI-tested versions, and Actions outcomes. Error/stale notices and unknown counts remain explicit; presentation must not imply that incomplete data is success. Source links and the reading guide are part of the information hierarchy.

## Do's and Don'ts

### Do:

- Do inherit Red Hat Text on buttons, inputs, and selects.
- Do use the theme variables for surfaces, text, borders, links, and statuses.
- Do keep selected-view styling and the pressed state synchronized.
- Do retain visible labels, keyboard focus, source links, and the distinction between declared support, configured CI coverage, and Actions outcomes.

### Don't:

- Don't replace the black masthead or Red Hat typefaces with a new visual identity.
- Don't turn workspace panels or filter fields into rounded cards or pill controls.
- Don't communicate status through color alone or present configured CI coverage as a successful test run.
- Don't claim that the local native controls are the RHDS component runtime.
