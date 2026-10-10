import type { CulturalConnection } from "./types";

export const culturalConnections: CulturalConnection[] = [
  { id: "cinema-film", from: "cinema", to: "film", relationship: "Existing programme", signal: "REPEATED" },
  { id: "cinema-music", from: "cinema", to: "music", relationship: "Cross-domain adjacency", signal: "REPEATED" },
  { id: "cinema-art", from: "cinema", to: "art", relationship: "Shared auteur culture", signal: "ADJACENT" },
  { id: "cinema-books", from: "cinema", to: "books", relationship: "Narrative culture", signal: "EMERGING" },
  { id: "cinema-design", from: "cinema", to: "design", relationship: "Visual authorship", signal: "ADJACENT" },
  { id: "cinema-venues", from: "cinema", to: "venues", relationship: "Local cultural field", signal: "REPEATED" },
  { id: "cinema-performers", from: "cinema", to: "performers", relationship: "Event format adjacency", signal: "ADJACENT" },
  { id: "cinema-composers", from: "cinema", to: "composers", relationship: "Creative bridge", signal: "REPEATED" },
  { id: "film-past-lives", from: "film", to: "past-lives", relationship: "Recent programme title", signal: "REPEATED" },
  { id: "film-zone", from: "film", to: "zone-of-interest", relationship: "Sound-led programme title", signal: "REPEATED" },
  { id: "film-poor-things", from: "film", to: "poor-things", relationship: "Visual-world programme title", signal: "REPEATED" },
  { id: "zone-mica", from: "zone-of-interest", to: "mica-levi", relationship: "Film composition", signal: "ADJACENT" },
  { id: "mica-experimental", from: "mica-levi", to: "experimental-sound", relationship: "Compositional practice", signal: "REPEATED" },
  { id: "music-composers", from: "music", to: "composers", relationship: "Creative discipline", signal: "REPEATED" },
  { id: "composers-dessner", from: "composers", to: "bryce-dessner", relationship: "Illustrative candidate", signal: "ADJACENT" },
  { id: "dessner-contemporary", from: "bryce-dessner", to: "contemporary-classical", relationship: "Contemporary composition", signal: "REPEATED" },
  { id: "contemporary-live", from: "contemporary-classical", to: "live-performance", relationship: "Live presentation", signal: "REPEATED" },
  { id: "venues-halls", from: "venues", to: "concert-halls", relationship: "London partner landscape", signal: "REPEATED" },
  { id: "halls-live", from: "concert-halls", to: "live-performance", relationship: "Shared live context", signal: "ADJACENT" },
];