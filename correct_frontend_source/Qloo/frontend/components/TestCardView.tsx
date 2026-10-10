"use client";

interface TestCardData {
  title: string;
  programme_context: string;
  audience_hypothesis: string;
  cultural_bridge: string;
  geographic_signal: string;
  programming_direction: string;
  primary_evidence: string;
  runner_up: string;
  falsification_condition: string;
  provenance: Record<string, string | null>;
  data_status: string;
}

interface Props {
  testCard: TestCardData;
}

export default function TestCardView({ testCard }: Props) {
  const fields = [
    { label: "Programme", value: testCard.programme_context },
    { label: "Audience Hypothesis", value: testCard.audience_hypothesis },
    { label: "Cultural Bridge", value: testCard.cultural_bridge },
    { label: "Geographic Signal", value: testCard.geographic_signal },
    { label: "Programming Direction", value: testCard.programming_direction },
    { label: "Primary Evidence", value: testCard.primary_evidence },
    { label: "Runner-Up", value: testCard.runner_up },
    { label: "Falsification", value: testCard.falsification_condition },
  ];

  return (
    <div className="rounded-xl border border-violet-700/50 bg-violet-900/10 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-violet-400 uppercase tracking-wide">
          🧪 Test Card
        </h3>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            testCard.data_status === "measured"
              ? "bg-emerald-900/50 text-emerald-300"
              : "bg-amber-900/50 text-amber-300"
          }`}
        >
          {testCard.data_status === "measured" ? "Measured Qloo" : testCard.data_status === "fixture" ? "Fixture demo (not live)" : testCard.data_status}
        </span>
      </div>

      <h4 className="text-lg font-semibold text-violet-200 mb-4">
        {testCard.title}
      </h4>

      <div className="space-y-3">
        {fields.map((field) => (
          <div key={field.label}>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">
              {field.label}
            </div>
            <p className="text-sm text-gray-300 leading-relaxed">
              {field.value}
            </p>
          </div>
        ))}
      </div>

      {/* Provenance */}
      <div className="mt-4 pt-3 border-t border-gray-700/50">
        <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
          Provenance
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs text-gray-400">
          {Object.entries(testCard.provenance).map(([key, value]) => (
            <div key={key}>
              <span className="text-gray-500">{key}:</span>{" "}
              <span className="font-mono">{value ?? "n/a"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}