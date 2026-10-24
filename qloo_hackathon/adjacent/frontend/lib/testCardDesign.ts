import type { TestCardTextSection } from "./testCardExport";

export type TestDesignField = "comparison_protocol" | "primary_measure" | "decision_rule" | "observation_window";
export type TestDesign = Record<TestDesignField, string>;
export type TestDesignDefaults = Partial<TestDesign> | null | undefined;

const FIELD_LABELS: Record<TestDesignField, string> = {
  comparison_protocol: "Comparison protocol",
  primary_measure: "Primary measure",
  decision_rule: "Decision rule",
  observation_window: "Observation window",
};

/** Copy generated prompts into editable UI state without sharing the API object. */
export function createTestDesign(defaults: TestDesignDefaults): TestDesign {
  return {
    comparison_protocol: defaults?.comparison_protocol ?? "",
    primary_measure: defaults?.primary_measure ?? "",
    decision_rule: defaults?.decision_rule ?? "",
    observation_window: defaults?.observation_window ?? "",
  };
}

/** Update one field while preserving sibling edits and filling older-card defaults. */
export function updateTestDesign(
  current: TestDesign | null,
  defaults: TestDesignDefaults,
  field: TestDesignField,
  value: string,
): TestDesign {
  return { ...createTestDesign(defaults), ...current, [field]: value };
}

/** Sections shared by both UI exports, so edits cannot diverge from the file. */
export function testDesignExportSections(design: TestDesign): TestCardTextSection[] {
  return (Object.keys(FIELD_LABELS) as TestDesignField[]).map((field) => ({
    label: FIELD_LABELS[field],
    value: design[field],
  }));
}

/** Read saved fields from current or legacy snapshots without mutating either. */
export function readSavedTestDesign(
  sourceBet: unknown,
  legacyObservationWindow?: unknown,
): Record<TestDesignField, string | null> {
  const bet = sourceBet && typeof sourceBet === "object" && !Array.isArray(sourceBet)
    ? sourceBet as Record<string, unknown>
    : {};
  const raw = bet.experiment_design && typeof bet.experiment_design === "object" && !Array.isArray(bet.experiment_design)
    ? bet.experiment_design as Record<string, unknown>
    : {};
  return {
    comparison_protocol: typeof raw.comparison_protocol === "string" ? raw.comparison_protocol : null,
    primary_measure: typeof raw.primary_measure === "string" ? raw.primary_measure : null,
    decision_rule: typeof raw.decision_rule === "string" ? raw.decision_rule : null,
    observation_window: typeof raw.observation_window === "string"
      ? raw.observation_window
      : typeof legacyObservationWindow === "string"
        ? legacyObservationWindow
        : null,
  };
}
