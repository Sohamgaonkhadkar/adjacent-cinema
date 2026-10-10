"use client";

import { useState } from "react";
import { DEMO_PROGRAMME, type ProgrammeItemInput } from "@/lib/api";

function DemoBadge() {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
      Sample programme
    </span>
  );
}

interface Props {
  onSubmit: (
    city: string,
    venue: string,
    programme: ProgrammeItemInput[]
  ) => void;
  loading: boolean;
}

export default function IntakeForm({ onSubmit, loading }: Props) {
  const [city, setCity] = useState("London, UK");
  const [venue, setVenue] = useState("Demo Cinema");
  const [programme, setProgramme] = useState<ProgrammeItemInput[]>([
    { title: "", year: undefined, imdb_id: "" },
  ]);
  const [isDemo, setIsDemo] = useState(false);

  function loadDemo() {
    setProgramme(DEMO_PROGRAMME);
    setIsDemo(true);
  }

  function addFilm() {
    setProgramme([...programme, { title: "", year: undefined, imdb_id: "" }]);
  }

  function removeFilm(index: number) {
    setProgramme(programme.filter((_, i) => i !== index));
    setIsDemo(false);
  }

  function updateFilm(
    index: number,
    field: keyof ProgrammeItemInput,
    value: string
  ) {
    const updated = [...programme];
    if (field === "year") {
      updated[index] = {
        ...updated[index],
        [field]: value ? parseInt(value) : undefined,
      };
    } else {
      updated[index] = {
        ...updated[index],
        [field]: value || undefined,
      };
    }
    setProgramme(updated);
    setIsDemo(false);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const valid = programme.filter((p) => p.title.trim());
    if (valid.length === 0) return;
    onSubmit(city, venue, valid);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Venue & City */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Venue
          </label>
          <input
            type="text"
            value={venue}
            onChange={(e) => setVenue(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Cinema name"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            City
          </label>
          <input
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="London, UK"
            required
          />
        </div>
      </div>

      {/* Programme */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="block text-sm font-medium text-gray-700">
            Programme
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={loadDemo}
              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Load verified demo programme
            </button>
            <button
              type="button"
              onClick={addFilm}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              + Add film
            </button>
          </div>
        </div>

        {isDemo && (
          <div className="mb-3">
            <DemoBadge />
            <span className="ml-2 text-xs text-gray-500">
              6 starter titles; resolution and evidence are checked during this run
            </span>
          </div>
        )}

        <div className="space-y-2">
          {programme.map((item, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                type="text"
                value={item.title}
                onChange={(e) => updateFilm(i, "title", e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm"
                placeholder="Film title"
                required
              />
              <input
                type="number"
                value={item.year ?? ""}
                onChange={(e) => updateFilm(i, "year", e.target.value)}
                className="w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm"
                placeholder="Year"
              />
              <input
                type="text"
                value={item.imdb_id ?? ""}
                onChange={(e) => updateFilm(i, "imdb_id", e.target.value)}
                className="w-32 px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm"
                placeholder="IMDb ID"
              />
              {programme.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeFilm(i)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={
          loading || programme.filter((p) => p.title.trim()).length === 0
        }
        className="w-full py-3 px-4 bg-indigo-600 text-white font-medium rounded-md shadow-sm hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Starting analysis…" : "Analyse programme"}
      </button>
    </form>
  );
}