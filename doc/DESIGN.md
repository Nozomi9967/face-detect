# TouchFlow Design System
## Overview
TouchFlow is a gesture-native, thumb-friendly design system crafted for iOS and Android general-purpose app design. It prioritizes comfortable one-handed use with generous touch targets, rounded surfaces, and spatial cues that guide natural finger movement. The clean white foundation paired with blue, coral, and mint accents creates a fresh, approachable interface. Every component is optimized for mobile viewport constraints and touch interaction patterns.
---
## Colors
- **Primary** (
#3B82F6
): Blue -- main actions, navigation active
- **Secondary** (
#F97171
): Coral -- accent highlights, notifications
- **Tertiary** (
#34D399
): Mint -- success, confirmations
- **Background** (
#FFFFFF
): Page background
- **Surface** (
#F9FAFB
): Cards, sheet backgrounds
- **Success** (
#34D399
): Completed actions, valid input
- **Warning** (
#FBBF24
): Cautionary alerts, pending
- **Error** (
#EF4444
): Form errors, destructive state
- **Info** (
#3B82F6
): Informational banners, tips
## Typography
- **Headline Font**: Figtree
- **Body Font**: DM Sans
- **Mono Font**: Roboto Mono
- **Display**: Figtree 32px bold, 40px line height
- **Headline**: Figtree 24px bold, 32px line height
- **Subhead**: Figtree 20px semibold, 28px line height
- **Body Large**: DM Sans 17px regular, 26px line height
- **Body**: DM Sans 15px regular, 24px line height
- **Body Small**: DM Sans 13px regular, 20px line height
- **Caption**: DM Sans 12px medium, 18px line height
- **Overline**: DM Sans 11px semibold, 16px line height
- **Code**: Roboto Mono 13px regular, 20px line height
---
## Spacing
- **Base unit:** 6px (mobile-optimized)
- **Scale:** 6 / 12 / 18 / 24 / 30 / 36 / 48 / 60 / 72
- **Component padding:** 12px (compact) | 18px (default) | 24px (relaxed)
- **Section spacing:** 36px between major sections, 18px between related groups
- **Safe areas:** Respect system safe area insets; minimum 18px horizontal page margin
## Border Radius
- **None** (0px): Full-width dividers, edge-to-edge
- **Small** (8px): Chips, small badges
- **Medium** (12px): Inputs, small cards
- **Large** (16px): Cards, sheets, modals
- **XL** (24px): Bottom sheets, large containers
- **Full** (9999px): FAB buttons, pill shapes, avatars
## Elevation
- **Subtle**: Gentle 1px vertical, 3px blur, black at 6% opacity. Cards at rest.
- **Medium**: Moderate 4px vertical, 12px blur, black at 8% opacity. Elevated cards, FABs.
- **Large**: Pronounced 8px vertical, 24px blur, black at 12% opacity. Bottom sheets, modals.
- **Overlay**: Deep 16px vertical, 48px blur, black at 18% opacity. Full-screen overlays.
## Components
### Buttons
- **Primary**: Blue (
#3B82F6
) fill, white (
#FFFFFF
) text, no border. Press darkens to 
#2563EB
.
- **Secondary**: Light gray (
#F3F4F6
) fill, blue (
#3B82F6
) text, no border. Press darkens to 
#E5E7EB
.
- **Ghost**: Transparent fill, gray (
#6B7280
) text, no border. Press fills with 
#F9FAFB
.
- **Destructive**: Red (
#EF4444
) fill, white (
#FFFFFF
) text, no border. Press darkens to 
#DC2626
.
- **FAB**: 56px circular, primary blue background, full-radius, medium shadow.
Available in small (36px tall, 14px padding), medium (48px tall, 18px padding), and large (56px tall, 24px padding). Disabled buttons drop to 0.4 opacity with no press feedback. All interactive elements maintain a minimum 44px touch target.
### Cards
- **Default**: Light surface (
#F9FAFB
) background, no border, 16px rounded corners, 18px padding, subtle shadow at rest.
- **Elevated**: White (
#FFFFFF
) background, no border, 16px rounded corners, 18px padding, medium shadow. Cards support left/right swipe gestures with revealed action areas behind the card.
### Inputs
Inputs have a minimum height of 48px for comfortable touch.
In the default state the border is 
#E5E7EB
 on a light (
#F9FAFB
) background with no shadow. On hover the border strengthens to 
#D1D5DB
. On focus the border turns blue (
#3B82F6
) over a white (
#FFFFFF
) background with a 3px blue ring at 12% opacity. In the error state the border turns red (
#EF4444
) over a light red (
#FEF2F2
) background with a 3px red ring at 10% opacity. When disabled the border fades to 
#F3F4F6
 on a light (
#F9FAFB
) background.
Labels are 13px medium (500) in text-primary with 6px spacing below. Helper text is 12px in text-secondary; error helper uses the error color.
### Chips
- **Filter**: Light blue (
#EFF6FF
) fill, blue (
#3B82F6
) text, pill-shaped, 6px 14px padding, toggleable.
- **Status**: Semantic color at 12% opacity fill, semantic-colored text, pill-shaped, 6px 14px padding. Minimum touch height is 36px.
### Lists
Each row is at least 52px tall with 12px 18px padding, separated by a 1px 
#F3F4F6
 divider inset by 18px. Press feedback fills the background with 
#F3F4F6
 after 100ms. Active/selected rows show a light blue (
#EFF6FF
) background with a 3px blue (
#3B82F6
) left accent. Swipe actions reveal delete (red) or archive (blue) zones behind rows.
### Checkboxes
22px square with 6px rounded corners. Unchecked state has a 2px 
#D1D5DB
 border on a transparent background. When checked the box fills blue (
#3B82F6
) with a white checkmark and a scale animation. Focus adds a 3px blue ring at 15% opacity. Touch target is 44px. Disabled drops to 0.35 opacity.
### Radio Buttons
22px circular. Unselected state has a 2px 
#D1D5DB
 border on a transparent background. When selected the border turns 2px blue (
#3B82F6
) with a 10px blue inner dot. Focus adds a 3px blue ring at 15% opacity. Touch target is 44px. Disabled drops to 0.35 opacity.
### Tooltips
Dark (
#111827
) background with white (
#FFFFFF
) text in DM Sans 13px regular (400), 12px rounded corners, 8px 14px padding, and a 6px arrow matching the background. Maximum width is 220px. Appears on long-press (mobile) or after 300ms hover (tablet).
---
## Do's and Don'ts
1. **Do** ensure all interactive elements have a minimum 44px touch target for accessibility.
2. **Do** place primary actions in the thumb zone (bottom third of the screen).
3. **Don't** rely on hover states -- design for press/tap feedback on mobile.
4. **Do** use haptic feedback cues for destructive actions and confirmations.
5. **Don't** use small text below 12px -- legibility on mobile screens is critical.
6. **Do** support swipe gestures on cards and list items for quick contextual actions.
7. **Don't** place critical actions behind long-press menus without a visible alternative.
8. **Do** respect system safe areas and notch/Dynamic Island clearance.
9. **Don't** use shadows heavier than Medium on resting components -- keep the interface light.
10. **Do** provide smooth spring animations (250-350ms) for all navigation transitions.