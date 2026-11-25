# Prologue Prototype — Mission 1: The First Assault

This update adds the first playable slice of **The Fall of Lumerian**.

## Start

Install the dependencies from the project root:

```bash
python -m pip install -r requirements.txt
python main.py
```

Choose **New Game** and advance through the short opening text. The game then loads `assets/maps/prologue_first_assault.tmx` with Leonhard as the player character.

## Controls

- `W A S D` — move
- Left mouse button — sword attack
- Right mouse button — switch between melee and the existing ranged projectile mode
- `E` — interact when an NPC is nearby
- `R` — retry after Leonhard falls
- `Esc` — return to the menu from the defeat screen

## What is included

- Leonhard loads from `assets/imgs/sprites/leonhard/`.
- Leonhard has a larger health pool and stronger damage than the default player stats.
- The first mission map uses the project's 16×16 Town02 A2 and B tilesets.
- The map has a player spawn, four `EnemySpawn` markers, tree trunk collisions, and map boundaries.
- The four enemy markers load the existing Orc animation sheets as temporary demon raiders.
- Enemies chase Leonhard inside their aggro range and attack at close range.
- Leonhard's melee attack damages enemies; enemies can damage Leonhard.
- The HUD shows Leonhard's health and the number of remaining enemies.
- Defeating all four raiders displays `AREA SECURED`.

## Files changed

- `player.py` — optional character sprite selection, Leonhard stats, enemy collision/attack support, and player damage handling.
- `enemy.py` — chase behaviour, close-range attacks, and death handling.
- `game.py` — starts the first prologue map, loads and updates enemies, draws the HUD, and handles defeat/retry.
- `data/entities/enemies.json` — adds the `demon_raider` configuration while retaining the existing `skeleton` entry.
- `data/story/prologue.json` — replaces the generic opening text with the Lumerian/Vorlithra setup.
- `assets/maps/prologue_first_assault.tmx` — new first-mission map.
- `assets/maps/fsm_Town02_B.tsx` — external tileset reference used by the new map.

The existing playground maps (`level0.tmx`, `level1.tmx`, `level2.tmx`, `forest.tmx`, and `map.tmx`) were left unchanged.

## Current scope and test status

This is the first playable mission slice, not all five missions. It intentionally reuses the existing combat and sprite systems rather than adding a new skill framework or mission manager. The Orc sprite is a temporary stand-in for an invading raider until dedicated demon art is selected.

Static validation passed for Python syntax, JSON parsing, TMX XML, tile-layer cell counts, tileset GID ranges, and the player/enemy spawn markers. The packaging environment did not have Pygame or PyTMX installed, so the game window and live combat could not be launched here. Please run it locally and send the first traceback or screenshot if anything behaves unexpectedly.
