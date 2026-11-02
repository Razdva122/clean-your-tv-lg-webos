# Design: Clean Your TV website

Shared website system for the Hallmark redesign. TV application styling is independent.

## System
- Genre: editorial consumer software.
- Home shape: Workbench. The real launcher leads at first-screen scale.
- Guide shape: Long Document with persistent desktop index and compact mobile chrome.
- Theme: approved B1 brand, warm charcoal, cream, small orange signal.
- Existing copy, all twelve languages, canonical routes, links and demo behavior stay.

## Tokens
`website/src/tokens.css` is the source of truth. The approved brand values come from `assets/brand/README.md`.
- Paper: #241D19, raised surfaces #302722 and #3B3028.
- Ink: #FFF8EB, secondary #DFD3C6, muted #C7BDB3.
- Rule: #66564A. Accent: #FF4C20. Focus: #FFF8EB.
- Display: local Outfit, system fallback for scripts outside its coverage.
- Body: system sans, preserving the site's multilingual coverage.
- Code: system monospace, used only for code.
- One 1440px container, 64px desktop gutters, 32px column gap.
- Spacing/type/easing scales live in tokens.css; no inline brand values.

## Controls
- Primary: cream fill, dark ink, 48px minimum height, 8px radius.
- Secondary: outline with the same height/radius.
- Plain navigation and native details menus; focus appears instantly.
- Every existing destination remains available without JavaScript.

## Product imagery
- Existing real Classic, Alpine and Ribbon screenshots stay unretouched.
- No invented device frame, photographs, testimonials or usage metrics.
- Actual demo stays under /demo/ with Root/No-root and inline themes.

## Motion
Still by default. Small control feedback only; reduced motion cancels transitions.

## Exports
`website/src/tokens.css`, `base.css`, `styles.css` and `article.css`.
