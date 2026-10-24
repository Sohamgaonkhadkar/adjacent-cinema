export type StrategyId = "anchor" | "bridge" | "frontier";


export const MULTIVERSE_BANNER =
  "CONCEPT PREVIEW — ILLUSTRATIVE DATA — NOT A LIVE QLOO ANALYSIS";

export type Strategy = {
  id: StrategyId;
  name: string;
  kicker: string;
  headline: string;
  lede: string;
  body: string;
  visual: string;
  worlds: { a: string; b: string };
  evidence: { label: string; kind: string; note: string }[];
  risks: string[];
  dossier: {
    title: string;
    stance: string;
    imageCrop: string;
    typeTone: string;
  };
};

export const strategies: Strategy[] = [
  {
    id: "anchor",
    name: "Anchor",
    kicker: "01  ·  strongest supported direction",
    headline: "Stay with the world the evidence already holds.",
    lede: "Anchor is the most defensible cultural position: analog inheritance, not a broader coming-of-age claim.",
    body: "The composition is stable, centred, and editorial. It privileges resolved comparables — Aftersun, The Souvenir — and refuses to inflate a weaker field for the sake of novelty. Use Anchor when the filmmaker needs a sentence that can survive inspection.",
    visual: "Restrained, precise, confident. A still composition. Paper against ink. One photograph, fully seen.",
    worlds: { a: "Analog inheritance dramas", b: "Intimate realism" },
    evidence: [
      {
        label: "Analog inheritance dramas",
        kind: "FACT · fixture",
        note: "Highest-ranked cohort in the illustrative set. Similarity signal only.",
      },
      {
        label: "Resolved seeds Aftersun, Wendy and Lucy",
        kind: "FACT · fixture",
        note: "Identity-checked references. Not an audience overlap claim.",
      },
      {
        label: "Prestige awards circuit",
        kind: "UNKNOWN",
        note: "Rejected for insufficient members. Remains unknown.",
      },
    ],
    risks: [
      "May feel too quiet for sales materials that want a bigger category.",
      "Does not invent a youth-market story the evidence does not support.",
    ],
    dossier: {
      title: "Decision dossier · Anchor",
      stance: "Primary bet: analog inheritance.",
      imageCrop: "Full frame, level horizon, credits at the foot.",
      typeTone: "Instrument Serif, centred, one idea per line.",
    },
  },
  {
    id: "bridge",
    name: "Bridge",
    kicker: "02  ·  a credible connection between worlds",
    headline: "Hold two cultural rooms in the same frame.",
    lede: "Bridge keeps the analog-inheritance core and lets coastal labour sit beside it — a join, not a blend.",
    body: "The composition splits. Two photographic fields share a hairline. Copy speaks in pairs: the reel and the harbour, the daughter and the off-season town. Bridge is for filmmakers who can defend a connection without collapsing it into a slogan.",
    visual: "Overlapping editorial fields. Connecting rules. Juxtaposed crops. Two captions, one decision.",
    worlds: { a: "Analog inheritance", b: "Coastal working-class life" },
    evidence: [
      {
        label: "Coastal coming-of-age cohort",
        kind: "FACT · fixture",
        note: "Second-ranked. Strong enough to sit beside the primary, not replace it.",
      },
      {
        label: "Place tags · off-season resorts",
        kind: "INTERPRETATION · fixture",
        note: "Geographic colour. Not a booking map.",
      },
      {
        label: "Shared intimate-realism grammar",
        kind: "INTERPRETATION",
        note: "A reading of two facts. Labelled as such.",
      },
    ],
    risks: [
      "A bridge that cannot be evidenced becomes a mash-up.",
      "Materials must show both worlds; one photograph will not carry it.",
    ],
    dossier: {
      title: "Decision dossier · Bridge",
      stance: "Primary + secondary: inheritance × coastal labour.",
      imageCrop: "Diptych. Left analog, right street. A joining rule.",
      typeTone: "Paired sentences. Two columns that meet in the gutter.",
    },
  },
  {
    id: "frontier",
    name: "Frontier",
    kicker: "03  ·  exploratory, still bound to evidence",
    headline: "Test the edge that still has a source.",
    lede: "Frontier follows the field-recording / analog-media adjacency — a thinner signal, offered as an experiment, never as a fact.",
    body: "The crop is off-centre. Type sits where it should not. The photograph is a projector lens, not a face. Frontier is allowed only because a real (illustrative) music-domain cohort exists; it is not a licence to invent a scene. If the signal fails, the bet is withdrawn.",
    visual: "Unusual crop. Discovery tone. More air, more risk, same honesty about unknowns.",
    worlds: { a: "Analog media as heirloom", b: "Field-recording scores" },
    evidence: [
      {
        label: "Field-recording scores",
        kind: "INTERPRETATION · fixture",
        note: "Weaker affinity. Cross-domain. Suitable for a bounded experiment only.",
      },
      {
        label: "No live music-entity resolution in this preview",
        kind: "UNKNOWN",
        note: "Unknown remains unknown. No invented artists.",
      },
      {
        label: "Requires a falsification rule",
        kind: "HYPOTHESIS",
        note: "Frontier without a Test Card is decoration.",
      },
    ],
    risks: [
      "Easy to over-claim a thin signal.",
      "Must remain labelled exploratory in every public sentence.",
    ],
    dossier: {
      title: "Decision dossier · Frontier",
      stance: "Exploratory bet: analog media × room-tone music.",
      imageCrop: "Off-centre lens. Grain. Negative space to the left.",
      typeTone: "Smaller display. Asymmetry. A question, not a verdict.",
    },
  },
];

export const priorityMarks = [
  { id: "evidence", label: "Evidence strictness", hint: "How hard the bet must be to inspect." },
  { id: "distinct", label: "Distinctiveness", hint: "How far from a generic category." },
  { id: "range", label: "Exploratory range", hint: "Willingness to use a thinner signal." },
] as const;

export type Priorities = { evidence: number; distinct: number; range: number };

/**
 * Illustrative preview index for the concept preview only.
 * Weights are published in the UI. This is NOT a ranking model and is not used
 * anywhere in the real product. Replace with the strategy-engine payload later.
 */
export function previewIndex(p: Priorities): Record<StrategyId, number> {
  const E = p.evidence;
  const D = p.distinct;
  const R = p.range;
  return {
    anchor: Math.round(0.5 * E + 0.3 * (100 - R) + 0.2 * (100 - D)),
    bridge: Math.round(0.4 * D + 0.4 * E + 0.2 * R),
    frontier: Math.round(0.5 * R + 0.3 * D + 0.2 * (100 - E)),
  };
}

export type Suggestion = {
  id: StrategyId;
  score: number;
  reason: string;
  weights: string;
};

export function suggestStrategy(p: Priorities): Suggestion {
  const idx = previewIndex(p);
  const order: StrategyId[] = ["anchor", "bridge", "frontier"];
  const id = order.reduce((best, next) => (idx[next] > idx[best] ? next : best), "anchor" as StrategyId);

  const explanations: Record<StrategyId, string> = {
    anchor:
      p.evidence >= p.range
        ? "Evidence strictness outweighs exploratory range, so the strongest supported direction leads."
        : "Exploratory range is still below evidence strictness, so the supported direction leads.",
    bridge:
      p.distinct >= p.evidence
        ? "Distinctiveness leads while evidence stays strict, so a connection between two supported worlds ranks first."
        : "Evidence and distinctiveness are close, so the connective strategy outranks the single anchor.",
    frontier:
      p.range >= p.evidence
        ? "Exploratory range outruns evidence strictness, so the bounded but exploratory direction ranks first."
        : "Range is high while distinctiveness is moderate, so the exploratory direction edges ahead.",
  };

  const weights =
    "anchor = 0.5·E + 0.3·(100−R) + 0.2·(100−D) · bridge = 0.4·D + 0.4·E + 0.2·R · frontier = 0.5·R + 0.3·D + 0.2·(100−E)";

  return { id, score: idx[id], reason: explanations[id], weights };
}
