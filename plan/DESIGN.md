# Design System Document

## 1. Overview & Creative North Star: "The Architectural Authority"

This design system moves beyond the generic "government form" aesthetic, adopting a Creative North Star of **The Architectural Authority**. We treat the building permit process not as a bureaucratic hurdle, but as a high-end editorial journey. The experience is defined by spaciousness, structural integrity, and tonal depth.

To break the "template" look, we utilize **Intentional Asymmetry**. Instead of centering every element, we use heavy left-aligned typography anchored by expansive negative space. We reject the "boxed-in" feel of traditional web apps; instead, we use overlapping layers and shifting background tones to guide the user’s eye, creating a digital environment that feels as considered as a blueprint.

---

## 2. Colors & Surface Logic

Our palette is rooted in trust-inducing blues and clean, structural grays. However, the application of these colors must be sophisticated.

### Tonal Hierarchy
- **Primary (`#0051ae`)**: Reserved for high-intent actions.
- **Secondary (`#006e2b`)**: Represents "Approved" status and growth.
- **Tertiary (`#50555b`)**: Used for metadata and de-emphasized structural elements.

### The "No-Line" Rule
**Explicit Instruction:** 1px solid borders are strictly prohibited for sectioning or containment. Boundaries must be defined solely through background color shifts. 
- Use `surface-container-low` (`#f2f4f6`) for main content areas.
- Use `surface-container-highest` (`#e0e3e5`) to highlight a specific active card or focal point.
- Contrast is created through the transition of these tokens, never through a line.

### The "Glass & Gradient" Rule
To inject a "signature" feel into the permit process:
- **Floating Progress Trackers:** Use a backdrop-blur effect (20px) on `surface-container-lowest` (`#ffffff`) at 80% opacity.
- **Primary CTAs:** Use a subtle linear gradient from `primary` (`#0051ae`) to `primary_container` (`#0969da`) at a 135-degree angle to provide a "machined" professional finish.

---

## 3. Typography: Editorial Clarity

We utilize **Inter** to achieve a functional, high-density information display that feels premium.

- **Display & Headlines (`headline-lg` to `display-sm`)**: Use these for page titles and permit numbers. The scale is intentionally dramatic (e.g., `3.5rem` for display) to establish immediate hierarchy.
- **Title & Body (`title-md` to `body-lg`)**: Use `title-md` (`1.125rem`) for form section headers. This creates a clear distinction between the "Label" and the "Data."
- **Monospace Accents**: Use `ui-monospace` for Permit IDs and Technical Codes to provide a subtle nod to architectural documentation and technical precision.

**Pro Tip:** Increase the letter-spacing of `label-sm` by 0.05rem and use uppercase for metadata headers to give it a "blueprint" architectural feel.

---

## 4. Elevation & Depth: Tonal Layering

Traditional shadows are often a crutch for poor layout. In this design system, depth is achieved through **Tonal Layering**.

- **The Layering Principle**: Place a `surface-container-lowest` card on top of a `surface-container-low` background. This creates a "soft lift" that feels integrated into the environment.
- **Ambient Shadows**: If an element must float (e.g., a mobile bottom sheet or a modal), use an ultra-diffused shadow: `box-shadow: 0 20px 40px rgba(25, 28, 30, 0.06)`. The shadow color is a tinted version of `on-surface` (`#191c1e`) to mimic natural light.
- **The "Ghost Border"**: For accessibility in input fields, use `outline_variant` (`#c2c6d6`) at **15% opacity**. It should feel like a suggestion of a container, not a cage.

---

## 5. Components

### Cards (Permit Summaries)
*   **The Rule**: No borders, no dividers.
*   **Structure**: Use a `surface-container-lowest` background. Use vertical spacing (`spacing-6`) to separate internal content blocks.
*   **Status Indicators**: Instead of a small dot, use a vertical "Status Bar" on the far left edge (4px wide) using the `secondary` (green) or `error` (red) tokens.

### Progress Trackers
*   **Visual Style**: Use a horizontal stepped layout with `primary_fixed` (`#d8e2ff`) as the inactive track and `primary` (`#0051ae`) as the active path.
*   **Mobile-First**: On mobile, collapse this into a "Step X of Y" textual headline with a high-contrast `surface_tint` progress bar.

### Input Fields
*   **State**: Active fields use a 2px bottom-only highlight of `primary`.
*   **Labels**: Place labels inside the "Ghost Border" container using `label-md` to save vertical space and maintain a compact, professional look.

### Buttons
*   **Primary**: Gradient fill (as per the Glass & Gradient rule) with `xl` (0.75rem) roundedness.
*   **Secondary**: `surface-container-high` background with `on-surface` text. No border.
*   **Tertiary**: Text-only, using `primary` color, with a slight background shift on hover.

---

## 6. Do's and Don'ts

### Do
*   **Do** use `spacing-8` (2rem) and `spacing-10` (2.5rem) generously between sections to allow the eye to rest.
*   **Do** use background tonal shifts to group related form fields (e.g., "Applicant Info" vs. "Property Specs").
*   **Do** leverage `surface-bright` for the main canvas to ensure the application feels modern and energetic.

### Don't
*   **Don't** use black (`#000000`) for text. Use `on-surface` (`#191c1e`) to maintain a sophisticated, soft-contrast look.
*   **Don't** use 100% opaque lines to separate list items. Use a `spacing-4` gap or a subtle shift from `surface` to `surface-container-low`.
*   **Don't** use standard "drop shadows." If it doesn't look like it's naturally catching ambient light, remove the shadow.
