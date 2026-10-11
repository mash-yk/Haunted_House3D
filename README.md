# Haunted House 3D

A 3D action game set in a haunted house, built in **Python** with **PyOpenGL** and GLUT. Explore connected rooms, fight off ghosts, collect treasure, and unlock the boss room for a final fight.

Built for **CSE423: Computer Graphics** at BRAC University (Summer 2025).

## Gameplay

- **Explore** several rooms connected by hallways. Walls block movement, so you have to find the doorways.
- **Survive** 12 ghosts that chase you (any ghost you destroy respawns somewhere else in the house), plus traps that slide back and forth. Touching either costs a life; you start with 10.
- **Collect** all 5 treasure chests scattered through the rooms.
- **Unlock the boss**: with all 5 treasures, walk up to the gate of the boss room. The lights go dark and the boss starts hunting you.
- **Win** by bringing the boss's 200 HP down to zero.

Teleport pads around the map send you to another pad, which helps when you're cornered.

## Combat

You carry two weapons and can switch at any time:

- **Laser gun:** fires lasers in the direction you face. It holds 15 shots, then needs a reload.
- **Sword:** a wide, short-range swing that hits everything in an arc in front of you.

## Controls

| Key | Action |
|---|---|
| W, A, S, D | Move |
| Space | Jump |
| Left click | Fire laser / swing sword |
| Right click | Toggle first-person and third-person view |
| X | Switch weapon |
| L | Reload the gun |
| Arrow keys | Rotate and raise or lower the camera |
| V | Toggle highlight outlines |
| C | Toggle cheat mode (no damage) |
| R | Restart the game |

## How it's built

- **Rendering:** everything is drawn with OpenGL primitives (cubes, spheres, cylinders), with a third-person follow camera and an optional first-person view.
- **Collision:** each wall is an axis-aligned bounding box, and movement is resolved against them so the player slides along walls instead of passing through.
- **Hit detection:** the sword checks whether a target falls inside a cone in front of the player; lasers are moved every frame and tested against ghosts and the boss.
- **Game loop:** GLUT's idle callback updates ghosts, traps, the boss, reload timers and damage cooldowns, then redraws the scene.

## Running it

1. Install Python 3 and the OpenGL bindings:
   ```bash
   pip install PyOpenGL PyOpenGL_accelerate
   ```
   On Windows, if GLUT fails to load, install a build of PyOpenGL that includes `freeglut`.
2. Run the game:
   ```bash
   python haunted_house.py
   ```
