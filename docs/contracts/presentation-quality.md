# Presentation quality contract

- **Contract ID:** `presentation-quality`
- **Status:** Active
- **Issue:** [#77](https://github.com/yaqub0r/sabiqah/issues/77)

## Purpose

This contract governs the visible quality of Sabiqah's user-facing web
surfaces. Source, type, unit, and build checks do not prove that a rendered
page is readable. Every visual change must therefore combine deterministic
browser checks with human inspection of the actual presentation.

## Required viewport matrix

Test every affected page at these minimum Chromium viewports:

| Surface      | Viewport   |
| ------------ | ---------- |
| Mobile       | `390x844`  |
| Tablet       | `1024x768` |
| Wide desktop | `1440x900` |

Additional widths are required when the changed design introduces another
breakpoint or when content, direction, or interaction state is known to stress
the layout.

## Automated presentation gate

The browser smoke suite must use deterministic public fixtures and fail when an
affected critical surface exhibits:

- horizontal page overflow;
- overlapping cards or controls;
- text or interactive content clipped by its component;
- a responsive column count that disagrees with the intended breakpoint; or
- missing selected, expanded, disabled, or other material accessibility state.

Tests must exercise real application components and production styles. They
must emit a screenshot on failure and identify the violated geometric or state
invariant. Broad full-page pixel snapshots are not the default: they are
brittle across rendering environments and do not replace explicit layout
assertions.

## Human visual review

For every user-facing change, inspect the affected state at the required
viewports and record evidence in the pull request. Review typography,
hierarchy, whitespace, wrapping, density, reading order, Arabic and English
legibility, and the relevant loading, empty, error, focus, selected, and hover
states. A reviewer must be able to connect the evidence to the tested commit.

A genuinely non-visual change may state that visual review is not applicable,
but it must explain why. A source diff or successful build is not visual
evidence.

## Development deployment verification

After merge and successful development deployment, inspect the canonical
development URL at every required viewport. Record the deployed commit, URL,
viewports, and result. A visible regression blocks completion even when CI is
green; fix it through the normal issue and pull-request workflow rather than
accepting it as a follow-up.

## Release condition

A user-facing change is not complete until its automated browser gate passes,
its pull request contains reviewable visual evidence, and the development
deployment has been inspected. Production promotion retains its separate
approval and protection requirements.
