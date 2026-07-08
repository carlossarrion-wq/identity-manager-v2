# PDS Dashboard Mock-Up

## Overview

This deliverable is a **static HTML mock-up** of the PDS (Platform Dashboard System) main dashboard interface for stakeholder review. This is not a full application requiring backend services, authentication, or live data.

The mock-up demonstrates user interface design, information hierarchy, and role-aware widget presentation with two distinct persona variants.

## Files Included

### `index_us_user.html`
Dashboard variant for the **Standard User (US_USER)** persona. Emphasizes personal context, self-service actions, and guidance-oriented content with lower information density. Shows personal subscription status, account balance, usage summary, alerts, and recommended next steps.

### `index_us_cc.html`
Dashboard variant for the **Customer Care (US_CC)** persona. Emphasizes operational context, queue visibility, and system-wide monitoring with higher information density. Shows open tickets, SLA compliance, escalations, operational alerts, and team activity.

## How to Review

1. Open either `index_us_user.html` or `index_us_cc.html` in a modern web browser such as Chrome, Firefox, Safari, or Edge.
2. The files render immediately without requiring any server, installation, or configuration.
3. Compare the two persona variants to observe differences in content emphasis, information density, and tone.

## What to Expect

- **Static content**: All data, metrics, and alerts are embedded placeholder content for demonstration purposes.
- **No interactivity**: Links and buttons are styled but do not navigate to functional pages.
- **Visual fidelity**: Design reflects UFD/Naturgy brand guidelines, WCAG 2.2 AA-compliant color contrast, semantic HTML structure, and responsive layout.

## Technical Notes

The mock-up is fully self-contained within each HTML file with embedded CSS. Responsive breakpoints adapt the layout for desktop (1440px+), tablet (1024px), and mobile (768px) viewports.

## Supporting Documentation

Comprehensive design and compliance documentation is available in the `docs/` directory:

- **`/repos/identity-manager-v2/docs/dashboard_mockup_overview.md`**: Detailed design decisions, persona differences, traceability to requirements, and widget category descriptions.
- **`/repos/identity-manager-v2/docs/accessibility_notes.md`**: WCAG 2.2 AA conformance details and accessibility testing guidance.

---

**For questions or feedback on this deliverable, please contact the project team.**
