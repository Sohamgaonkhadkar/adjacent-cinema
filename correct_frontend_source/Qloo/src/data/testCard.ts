import type { TestCard } from "./types";

export const testCard: TestCard = {
  bet: "Cinema × Contemporary Classical",
  candidate: "Bryce Dessner",
  format: "Film screening + live performance / discussion",
  partnerType: "Composer / contemporary ensemble / cultural venue",
  location: "Central London",
  hypothesis: "A composer-led event can extend the cinema's existing arthouse programme into adjacent live-music culture.",
  successSignals: [
    "A credible composer or ensemble partner is interested in shaping the event.",
    "The event concept is easy to explain alongside the cinema's existing programme.",
    "The screening and performance feel like one coherent cultural experience.",
    "The team can identify a repeatable partner or format for a second test.",
  ],
  failureConditions: [
    "Low partner interest or no workable rights / production route.",
    "Poor advance demand after a clear, well-timed announcement.",
    "The format feels bolted on rather than connected to the film.",
    "No repeatable cultural fit emerges in the post-event review.",
  ],
};