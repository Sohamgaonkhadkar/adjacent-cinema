/**
 * View types for the Project Nightfall frontend port.
 * These describe *derived view models* (fingerprint nodes, stage states), not
 * API payloads. Every instance is built from a real backend run; nothing here
 * is a fixture.
 */

export type ClaimKind = "FACT" | "INTERPRETATION" | "HYPOTHESIS" | "UNKNOWN";

export type FingerprintNode = {
  id: string;
  label: string;
  kind: "film" | "cohort" | "entity" | "tag";
  domain?: string;
  affinity?: number | null;
  band?: string | null;
  members?: string[];
  sourceCallId?: string | null;
  claim: ClaimKind;
  note: string;
  related: string[];
  rejected?: boolean;
  rejectReason?: string;
};

export type StageState = "done" | "now" | "wait" | "skipped";

export type StageView = {
  id: string;
  label: string;
  detail: string;
  state: StageState;
};
