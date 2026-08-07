# pocket-monsters

**Pocket Monsters: Verdant** — a Game Boy style monster-catching RPG that runs in a phone browser,
on-screen console buttons and all. One HTML file, no build step, no external assets, no network calls.

Everything you see is generated at runtime: the 4-shade LCD palette, the tile art, the walking
sprites, the monsters, the 5x7 bitmap font, and the chiptune music are all drawn or synthesised in
JavaScript. That is why the whole game is a single ~100 KB file you can email to yourself.

## Play it

**On a phone:** open `index.html` in the browser. On iOS, tap **Share → Add to Home Screen** and it
launches fullscreen with no browser chrome, like an installed app. It works offline once loaded.

**On a computer:** double-click `index.html`, or serve the folder:

```bash
cd pocket-monsters
python3 -m http.server 8000   # then open http://localhost:8000
```

## Controls

| Action | Touch | Keyboard |
| --- | --- | --- |
| Move | D-pad (slide your thumb between directions) | Arrow keys / WASD |
| Confirm, talk, read, pick up | A | Z / J / Space |
| Cancel, back, speed up text | B | X / K |
| Menu (team, bag, dex, save, sound) | START | Enter |

Sound starts on the first button press, because browsers require a gesture before playing audio.
Toggle it under START → SOUND.

## The game

- **Verdant Town → Route 1 → Whisper Woods → Stone Summit.** Get a starter from Prof. Holly,
  catch a team in the tall grass, beat the four trainers on the way, and take the Summit Ace.
- **12 species** across 7 types (Normal, Fire, Water, Grass, Electric, Rock, Bug), with a type chart,
  STAB, critical hits, burn / paralysis / sleep, and level-up evolutions at 16.
- **Turn-based battles** with FIGHT / BAG / MON / RUN, PP, catching, switching, and experience.
- **A free healing centre and a shop** in town; items and hidden pickups out on the routes.
- **Trainers spot you** if you walk through their line of sight, same as the games this borrows from.
- **Saving** writes to `localStorage`, so a save lives in the browser you played it in.

## How it is put together

Single file, sectioned top to bottom:

| Section | What it does |
| --- | --- |
| screen / font | 160x144 canvas, 4-shade palette, hand-drawn 5x7 bitmap font |
| input | keyboard map plus pointer handling for the d-pad and buttons |
| audio | two square-wave voices and a noise channel driving short looping songs |
| procedural art | tiles, four-direction walk cycles, and a parametric monster-sprite renderer |
| game data | types, moves, species, items, and the seven maps as character grids |
| script runner | generators yield small tasks (`say`, `ask`, `wait`, `anim`), so dialogue and battle sequences read top to bottom |
| overworld | grid movement, warps, encounters, NPCs, line of sight |
| battle | turn resolution, damage, status, catching, experience, evolution |

The monster sprites are not hand-drawn pixel art. Each species declares a silhouette — body and head
size, ear style, tail style, leg count, wings, markings — and `creatureSprite()` rasterises that into
a shaded 48x48 sprite. Adding a species is a data entry, not an art job.

### Adding a species

```js
NEWMON: {
  no: 13, type: 'WATER', base: { hp: 50, atk: 55, def: 45, spd: 60 }, catch: 120, xp: 70,
  learn: [[1, 'TACKLE'], [8, 'BUBBLE'], [16, 'AQUAJET']],
  evo: { lv: 20, to: 'SOMETHINGELSE' },        // optional
  look: { bw: 10, bh: 8, bcy: 27, hr: 9, hcy: 15, ears: 'fin', tail: 'fin', legs: 2, pattern: 'belly' }
}
```

Then add it to a map's `encounters.table` as `['NEWMON', minLevel, maxLevel]`.

## Verified with

Headless Chromium (Playwright) drives a full playthrough — new game, walking, warps, picking a
starter, wild battles, throwing balls, menus, the shop, a trainer battle, saving and reloading —
and asserts no console or page errors along the way.
