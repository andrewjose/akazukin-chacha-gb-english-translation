# MANDATORY - Akazukin Chacha (GB) translation style

Every translator/agent working on this script must follow this file and glossary.md.
Where they conflict with your instincts, they win.

## Reference hierarchy

1. Official English: the 1998 Cartoon Network Asia dub (episode titles only survive; see glossary.md).
2. Where no official form exists: the established fan/Wikipedia romanization (Riiya, Shiine, ...).
3. Only then free translation, logged as "unofficial: reason" in glossary.md.
New terms you coin go into glossary.md before use, so every batch stays consistent.

## Tone

A gag-heavy magical-girl comedy for kids. Short, punchy, playful lines. Slapstick, puns, and
exaggerated reactions are the point; keep jokes working in English rather than literal.
Rewrite a pun into an English pun and flag it in your batch notes.

## Character voices

(From en.wikipedia/ja.wikipedia character descriptions; finer speech habits are not documented
in any official English source, so these are working notes.)

- **ChaCha**: cheerful, kind, clumsy apprentice magician. Her spells usually misfire. Upbeat,
  girlish, quick to panic and quick to recover. Big exasperated shouts ("What is going ON?!").
  Soft spot for Riiya. Calls her teacher "Master Seravi".
- **Riiya**: energetic, simple, hungry, super-strong werewolf boy. Short excited sentences,
  talks about food, adores ChaCha, hates being called a dog ("I'm a wolf!"). Rough boyish speech
  but never mean.
- **Shiine**: the sensible, prim, polite boy wizard of the trio. Neat, proper vocabulary,
  a little fussy and easily flustered; loyal to "Lady Dorothy"; in love with ChaCha; bickers
  with Riiya.
- **Seravi**: world's greatest wizard, eccentric and calm, goofy, theatrical. Often "speaks"
  through his doll Elizabeth (ventriloquism) - keep Elizabeth's lines sassier and childish.
- **Dorothy**: vain, short-tempered, scheming witch who wants to be the best; ham villain energy,
  shouts, gloats. Soft underneath (Seravi).
- **Yakko**: snooty, jealous rival in the black hood; potion expert; swoons over Seravi.
- **Marin**: spoiled, cutesy, selfish mermaid ("burikko"); fake-sweet when Riiya is around.
- **Suzu (Orin)**: small, honest ninja girl; polite, earnest, voice of reason; shy about Shiine.
- **Principal Urara**: airheaded, sweet, rambling.
- Teachers: plain adult speech, each with one comic trait.

## Honorifics

No official subtitles exist to copy, and the English dub localized names (Orin -> Suzu), so:
- Drop -chan/-kun/-san/-sama. Do not keep any Japanese honorific.
- sensei after a name -> "Master X" for Seravi from his pupils; "Mr./Ms. X" for school teachers.
- doroshii sama -> "Lady Dorothy". seravii sama (Yakko) -> "Dear Seravi" / "Lord Seravi" as the line fits.
- shiinechan used as a tease -> "little Shiine"; otherwise just "Shiine".

## Formatting rules

- ASCII only. No curly quotes, no em/en dashes, no Japanese punctuation, no full-width characters.
  Use straight ' and ". Use "..." (three periods) for ellipsis. Use "-" only as a hyphen;
  for an interruption use "..." or rephrase.
- Write unwrapped text: one logical line per message/box sequence as the script format
  specifies. The inserter wraps. Do not insert manual line breaks unless the source has a
  hard page/box break control code at that spot.
- Keep every control code / tag exactly as it appears (order, spelling, brackets, arguments).
  Never translate, drop, merge or reorder them. If a control code inserts a name, do not also
  type the name.
- Stutters / screams: "W-wait!", "Eeek!" are fine. No ALL-CAPS whole lines; caps on one word
  for emphasis is fine.
- Flag in batch notes any line you shortened or rewrote heavily.

## LIMITS

TBD by RE agent: box width (tiles/chars per line), lines per box, font (fixed 8x8 vs VWF,
upper/lowercase availability), name-field lengths (characters, items, spells, menu labels),
max string lengths for menus/battle text.
