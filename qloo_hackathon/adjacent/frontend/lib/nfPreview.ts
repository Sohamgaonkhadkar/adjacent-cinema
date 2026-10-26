/**
 * Illustrative content for the home-page Cultural Multiverse *design preview*.
 *
 * This is ported from the source ZIP (src/data/multiverse.ts) and is explicitly
 * NOT analyst output: it is not produced by Qloo, not produced by the strategy
 * engine, and it never touches a run, a saved experiment or the archive.
 * The real, evidence-backed Multiverse lives in Creator Studio and is computed
 * from a completed run by `lib/positioningArena`.
 */

export const MULTIVERSE_BANNER =
  "CONCEPT PREVIEW — ILLUSTRATIVE DATA — NOT A LIVE QLOO ANALYSIS";

export type PreviewStrategyId = "anchor" | "bridge" | "frontier";

export type PreviewStrategy = {
  id: PreviewStrategyId;
  name: string;
  kicker: string;
  headline: string;
  lede: string;
  body: string;
  visual: string;
  worlds: { a: string; b: string };
  evidence: { label: string; kind: string; note: string }[];
  risks: string[];
  dossier: { title: string; stance: string; imageCrop: string; typeTone: string };
};

export const previewStrategies: PreviewStrategy[] = [
  {
    id: "anchor",
    name: "Anchor",
    kicker: "01 · strongest supported direction",
    headline: "Stay with the world the evidence already holds.",
    lede: "Anchor keeps the film inside the world its strongest returned cohort supports — not a broader category chosen for reach.",
    body: "The composition is stable, centred and editorial. It privileges resolved comparables and refuses to inflate a weaker field for the sake of novelty. Use Anchor when the sentence has to survive inspection.",
    visual: "Restrained, precise, confident. A still composition. One photograph, fully seen.",
    worlds: { a: "Strongest returned cohort", b: "Second-ranked world, held in reserve" },
    evidence: [
      {
        label: "Highest-ranked cohort",
        kind: "FACT · sample",
        note: "Illustrative only. In the real arena this row is a cohort returned by your run, with its call id.",
      },
      {
        label: "Identity-checked seeds",
        kind: "FACT · sample",
        note: "Illustrative only. References that fail resolution are shown as unresolved, not guessed.",
      },
      {
        label: "Rejected world",
        kind: "UNKNOWN",
        note: "Illustrative only. Insufficient worlds stay visible with their reason instead of disappearing.",
      },
    ],
    risks: [
      "May feel too quiet for materials that want a bigger category.",
      "Does not invent a youth-market story the evidence does not support.",
    ],
    dossier: {
      title: "Decision dossier · Anchor",
      stance: "One supported direction.",
      imageCrop: "Full frame, level horizon, credits at the foot.",
      typeTone: "Display serif, centred, one idea per line.",
    },
  },
  {
    id: "bridge",
    name: "Bridge",
    kicker: "02 · a connection the evidence can carry",
    headline: "Hold two cultural rooms in the same frame.",
    lede: "Bridge keeps the strongest world and lets a second, genuinely related world sit beside it — a join, not a blend.",
    body: "The composition splits. Two photographic fields share a hairline. Copy speaks in pairs. In the real arena a Bridge requires a returned relationship or shared attribution between the two worlds; without it the strategy is unavailable.",
    visual: "Overlapping editorial fields. Connecting rules. Juxtaposed crops. Two captions, one decision.",
    worlds: { a: "Primary returned cohort", b: "Second world with returned support" },
    evidence: [
      {
        label: "Second-ranked cohort",
        kind: "FACT · sample",
        note: "Illustrative only. Strong enough to sit beside the primary, not replace it.",
      },
      {
        label: "Shared provider tag",
        kind: "INTERPRETATION · sample",
        note: "Illustrative only. A shared tag is a join candidate, not proof of audience overlap.",
      },
      {
        label: "Shared seed attribution",
        kind: "INTERPRETATION",
        note: "Illustrative only. Provider-attributed contribution is the only permitted basis for a join.",
      },
    ],
    risks: [
      "A bridge that cannot be evidenced becomes a mash-up.",
      "Materials must show both worlds; one photograph will not carry it.",
    ],
    dossier: {
      title: "Decision dossier · Bridge",
      stance: "Primary + second world, joined visibly.",
      imageCrop: "Diptych. Left world, right world. A joining rule.",
      typeTone: "Paired sentences. Two columns that meet in the gutter.",
    },
  },
  {
    id: "frontier",
    name: "Frontier",
    kicker: "03 · exploratory, still bound to evidence",
    headline: "Test the edge that still has a source.",
    lede: "Frontier follows a thinner cross-domain signal — offered as an bounded experiment, never as a fact.",
    body: "The crop is off-centre. Type sits where it should not. Frontier is allowed only when a real cohort in the same scoring context clears the novelty gate; if the signal fails, the bet is withdrawn rather than dressed up.",
    visual: "Unusual crop. Discovery tone. More air, more risk, same honesty about unknowns.",
    worlds: { a: "Primary returned cohort", b: "Thinner cross-domain cohort" },
    evidence: [
      {
        label: "Cross-domain cohort",
        kind: "INTERPRETATION · sample",
        note: "Illustrative only. Weaker affinity, suitable for a bounded experiment at most.",
      },
      {
        label: "Unresolved references",
        kind: "UNKNOWN",
        note: "Illustrative only. Unknown remains unknown; no invented artists or titles.",
      },
      {
        label: "Falsification rule",
        kind: "HYPOTHESIS",
        note: "Illustrative only. A frontier without a falsification rule is decoration.",
      },
    ],
    risks: [
      "Easy to over-claim a thin signal.",
      "Must remain labelled exploratory in every public sentence.",
    ],
    dossier: {
      title: "Decision dossier · Frontier",
      stance: "Exploratory bet, bounded by evidence.",
      imageCrop: "Off-centre frame. Grain. Negative space to the left.",
      typeTone: "Smaller display. Asymmetry. A question, not a verdict.",
    },
  },
];

export type Priorities = { evidence: number; distinct: number; range: number };

/**
 * Illustrative index for the *design preview* only. Weights are published in
 * the UI. This is not a ranking model and is never used by Creator Studio.
 */
export function previewIndex(priorities: Priorities): Record<PreviewStrategyId, number> {
  const { evidence: E, distinct: D, range: R } = priorities;
  return {
    anchor: Math.round(0.5 * E + 0.3 * (100 - R) + 0.2 * (100 - D)),
    bridge: Math.round(0.4 * D + 0.4 * E + 0.2 * R),
    frontier: Math.round(0.5 * R + 0.3 * D + 0.2 * (100 - E)),
  };
}

export type PreviewSuggestion = {
  id: PreviewStrategyId;
  score: number;
  reason: string;
  weights: string;
};

export function suggestPreviewStrategy(priorities: Priorities): PreviewSuggestion {
  const index = previewIndex(priorities);
  const order: PreviewStrategyId[] = ["anchor", "bridge", "frontier"];
  const id = order.reduce((best, next) => (index[next] > index[best] ? next : best), "anchor");

  const explanations: Record<PreviewStrategyId, string> = {
    anchor:
      priorities.evidence >= priorities.range
        ? "Evidence strictness outweighs exploratory range in this demonstration, so the strongest supported direction leads."
        : "Exploratory range is still below evidence strictness here, so the supported direction leads.",
    bridge:
      priorities.distinct >= priorities.evidence
        ? "Distinctiveness leads while evidence stays strict, so a connection between two supported worlds ranks first."
        : "Evidence and distinctiveness are close, so the connective strategy outranks the single anchor.",
    frontier:
      priorities.range >= priorities.evidence
        ? "Exploratory range outruns evidence strictness here, so the bounded exploratory direction ranks first."
        : "Range is high while distinctiveness is moderate, so the exploratory direction edges ahead.",
  };

  const weights =
    "anchor = 0.5·E + 0.3·(100−R) + 0.2·(100−D) · bridge = 0.4·D + 0.4·E + 0.2·R · frontier = 0.5·R + 0.3·D + 0.2·(100−E)";

  return { id, score: index[id], reason: explanations[id], weights };
}
