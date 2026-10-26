/**
 * Class-name join used by the ported Project Nightfall components.
 *
 * The source ZIP used clsx + tailwind-merge. This application deliberately
 * avoids adding a dependency for two trivial utilities: the ported components
 * never pass conflicting utilities for the same property, so a filtered join is
 * sufficient and keeps the bundle unchanged.
 */
export function cn(...inputs: Array<string | false | null | undefined>): string {
  return inputs.filter(Boolean).join(" ");
}
