export type Photo = {
  src: string;
  srcSet?: string;
  credit: string;
  source: string;
  alt: string;
};

const pexels = (id: number, w = 1800) =>
  `https://images.pexels.com/photos/${id}/pexels-photo-${id}.jpeg?auto=compress&cs=tinysrgb&w=${w}`;

export const photos = {
  cinemaEmpty: {
    src: pexels(7991486, 2400),
    credit: "Tima Miroshnichenko",
    source: "https://www.pexels.com/photo/an-empty-cinema-7991486/",
    alt: "An empty independent cinema with rows of seats facing a dark screen, lit by a projector.",
  },
  cinemaSeats: {
    src: pexels(7991489, 1600),
    credit: "Tima Miroshnichenko",
    source: "https://www.pexels.com/photo/ann-array-of-red-chairs-in-a-movie-theater-7991489/",
    alt: "Rows of empty red cinema seats in a darkened auditorium.",
  },
  cinemaAisle: {
    src: pexels(7991112, 1600),
    credit: "Tima Miroshnichenko",
    source: "https://www.pexels.com/photo/empty-seats-of-a-movie-theater-7991112/",
    alt: "Empty movie theater interior with rows of red and black seats.",
  },
  cinemaAudience: {
    src: pexels(7991437, 1600),
    credit: "Tima Miroshnichenko",
    source: "https://www.pexels.com/photo/audience-in-a-movie-theater-7991437/",
    alt: "Audience seated in a dark cinema, watching a screening.",
  },
  cinemaCurtain: {
    src: pexels(14725587, 1800),
    credit: "Enes Bayraktar",
    source: "https://www.pexels.com/photo/looking-through-the-curtain-of-a-cinema-14725587/",
    alt: "Looking through red cinema curtains into a screening room.",
  },
  projectorLens: {
    src: pexels(5515483, 1600),
    credit: "Ann H",
    source: "https://www.pexels.com/photo/lens-of-movie-projector-5515483/",
    alt: "Close-up of a cinema projector lens emitting a square of light.",
  },
  vintageProjectors: {
    src: pexels(19374140, 1800),
    credit: "Sami TÜRK",
    source: "https://www.pexels.com/photo/sofas-and-vintage-film-projectors-in-a-room-19374140/",
    alt: "Vintage film projectors in a quiet screening room with sofas.",
  },
  redPortrait: {
    src: pexels(21316136, 1200),
    credit: "Fakhri Baghirov",
    source: "https://www.pexels.com/photo/woman-face-illuminated-by-red-light-21316136/",
    alt: "A face illuminated by cinematic red light. Atmospheric photographic reference, not a film still.",
  },
  urbanPuddle: {
    src: pexels(16158304, 1200),
    credit: "Shuvo Haque",
    source: "https://www.pexels.com/photo/puddles-on-empty-street-in-city-16158304/",
    alt: "Puddles on an empty city street at night. Atmospheric photographic reference.",
  },
  columns: {
    src: pexels(35551877, 1200),
    credit: "Poetarojo",
    source: "https://www.pexels.com/photo/classical-columns-in-museum-interior-setting-35551877/",
    alt: "Classical columns in a museum interior. Atmospheric photographic reference.",
  },
  soho: {
    src: pexels(15510029, 1200),
    credit: "Alexander Nadrilyanski",
    source: "https://www.pexels.com/photo/string-lights-above-the-cobblestone-street-in-soho-london-england-15510029/",
    alt: "String lights above a cobblestone street in Soho. Atmospheric photographic reference.",
  },
  nightAlley: {
    src: pexels(13657333, 1200),
    credit: "Muhammed Zahid Bulut",
    source: "https://www.pexels.com/photo/puddles-in-an-alley-at-night-13657333/",
    alt: "Moody night alley with neon reflections on wet cobblestones.",
  },
  lanternStreet: {
    src: pexels(34290547, 1200),
    credit: "Matheus Freitas",
    source: "https://www.pexels.com/photo/cobblestone-street-with-reflective-lantern-glow-34290547/",
    alt: "A lantern glow reflected on a wet cobblestone path.",
  },
  editingTable: {
    src: pexels(9439248, 1800),
    credit: "Faruk Tokluoğlu",
    source: "https://www.pexels.com/photo/closeup-of-old-film-production-cutting-table-9439248/",
    alt: "Close-up of vintage film editing equipment with knobs and reels.",
  },
  filmstrips: {
    src: pexels(35355237, 1600),
    credit: "Clément Proust",
    source: "https://www.pexels.com/photo/vintage-filmstrips-featuring-western-scenes-35355237/",
    alt: "Vintage filmstrips laid out as archival material. Not an official still from any featured film.",
  },
  analogDesk: {
    src: pexels(37157243, 1600),
    credit: "Jakub Zerdzicki",
    source: "https://www.pexels.com/photo/analog-film-digitization-setup-in-studio-37157243/",
    alt: "Analog film digitization setup on a studio desk.",
  },
  reelTape: {
    src: pexels(6764882, 1400),
    credit: "Dmitry Demidov",
    source: "https://www.pexels.com/photo/a-rocording-tape-on-a-black-background-6764882/",
    alt: "Close-up of a vintage reel on a black background.",
  },
  screenplay: {
    src: pexels(8085932, 1600),
    credit: "Ron Lach",
    source: "https://www.pexels.com/photo/person-reading-document-8085932/",
    alt: "Hands reading a document at a writing desk. Atmospheric photographic reference.",
  },
  writing: {
    src: pexels(8085267, 1600),
    credit: "Ron Lach",
    source: "https://www.pexels.com/photo/a-person-writing-on-a-notebook-8085267/",
    alt: "Hands writing notes in a notebook indoors.",
  },
  dramaticTheater: {
    src: pexels(39587241, 2000),
    credit: "Uday Veeru",
    source: "https://www.pexels.com/photo/empty-movie-theater-with-dramatic-lighting-39587241/",
    alt: "Empty movie theater with dramatic seat lighting.",
  },
} as const satisfies Record<string, Photo>;

export const filmStrip = [
  photos.cinemaEmpty,
  photos.cinemaSeats,
  photos.projectorLens,
  photos.editingTable,
  photos.filmstrips,
  photos.soho,
] as const;
