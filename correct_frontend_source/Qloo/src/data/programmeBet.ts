import type { ProgrammeBet } from "./types";

export const programmeBet: ProgrammeBet = {
  title: "Cinema × Contemporary Classical",
  candidate: "Bryce Dessner",
  format: "Film screening + live performance / discussion",
  partnerType: "Composer / contemporary ensemble / cultural venue",
  location: "Central London",
  summary: "Your recent programme repeatedly sits near contemporary music, experimental sound and auteur culture. A composer-led screening or live-score event creates a culturally adjacent programming experiment without asking the cinema to abandon its existing identity.",
  hypothesis: "A composer-led event can extend the cinema's existing arthouse programme into adjacent live-music culture.",
  evidence: [
    {
      id: "adjacency",
      source: "DEMO CULTURAL GRAPH",
      type: "CULTURAL_AFFINITY",
      description: "Repeated links connect film composition, experimental sound, composers and contemporary classical practice.",
      status: "HIGH / QUALITATIVE SIGNAL",
    },
    {
      id: "compatibility",
      source: "PROGRAMME SAMPLE",
      type: "PROGRAMME_COMPATIBILITY",
      description: "Recent titles show a coherent interest in auteur-led work, designed worlds and sound as part of the film experience.",
      status: "HIGH / EDITORIAL READ",
    },
    {
      id: "geography",
      source: "LONDON VENUE FIELD",
      type: "GEOGRAPHIC_CONTEXT",
      description: "Concert halls, performance spaces and arts institutions are present across central London; proximity is context, not proof of demand.",
      status: "PRESENT / PLACE CONTEXT",
    },
    {
      id: "gap",
      source: "PROGRAMME GAP REVIEW",
      type: "TERRITORY_GAP",
      description: "The sampled programme is film-first. Live, composer-led contemporary music is a neighbouring territory not yet expressed in this sample.",
      status: "GAP IDENTIFIED / SAMPLE-BASED",
    },
  ],
};