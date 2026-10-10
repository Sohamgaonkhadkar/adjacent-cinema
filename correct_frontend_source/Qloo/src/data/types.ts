export interface EditorialImage {
  src: string;
  source: string;
  photographer: string;
  license: string;
  attributionUrl: string;
  alt: string;
}

export interface Cinema {
  name: string;
  city: string;
  country: string;
  address: string;
  description: string;
  imageKey: string;
}

export interface Film {
  id: string;
  title: string;
  year: number;
  genre: string;
  director: string;
  imageKey: string;
  programmeNote: string;
}

export type EntityKind = "DOMAIN" | "FILM" | "COMPOSER" | "PRACTICE" | "VENUE" | "CANDIDATE";

export interface CulturalEntity {
  id: string;
  name: string;
  domain: string;
  kind: EntityKind;
  relationship: string;
  description: string;
  adjacency: "HIGH" | "SIGNIFICANT" | "EMERGING" | "FOUNDATIONAL";
  x: number;
  y: number;
}

export interface CulturalConnection {
  id: string;
  from: string;
  to: string;
  relationship: string;
  signal: "REPEATED" | "ADJACENT" | "EMERGING";
}

export interface Venue {
  id: string;
  name: string;
  category: "CINEMA" | "MUSIC" | "ART" | "CULTURAL SPACE";
  type: string;
  area: string;
  latitude: number;
  longitude: number;
  relationship: string;
}

export interface Evidence {
  id: string;
  source: string;
  type: string;
  description: string;
  status: string;
}

export interface ProgrammeBet {
  title: string;
  candidate: string;
  format: string;
  partnerType: string;
  location: string;
  summary: string;
  hypothesis: string;
  evidence: Evidence[];
}

export interface TestCard {
  bet: string;
  candidate: string;
  format: string;
  partnerType: string;
  location: string;
  hypothesis: string;
  successSignals: string[];
  failureConditions: string[];
}