# P2-platform — mounting hardware

![Doc Type](https://img.shields.io/badge/doc-mechanical%20CAD-blue)
![Platform](https://img.shields.io/badge/platform-Propeller%202-blue)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

Mechanical CAD for the adapter plate that drops a **Propeller 2 Edge Module +
breakout board** into the spot where the Raspberry Pi normally sits on the
Robot Dog connection board. See [`../P2_MIGRATION_WIRING.md`](../P2_MIGRATION_WIRING.md)
for the electrical side of the swap, and [`../HARDWARE_SETUP.md`](../HARDWARE_SETUP.md)
for the full build walk-through.

## The model

The plate is modeled in Shapr3D to match the Pi's mounting footprint, with raised standoff
bosses positioned to carry the P2 Edge breakout board:

<p align="center">
  <img src="../Picture/p2-platform.png" width="75%" alt="Shapr3D CAD model of the P2 mount plate"/>
</p>

## Print progression

Getting the standoff height and hole alignment right took a few iterations. The trick is to
print **thin, quick test plates first** — just enough plate to verify the mounting-hole
positions and the board footprint line up — before committing the time and filament to the
full-height (taller-standoff) plate. Here are three of those test plates, ending in the V2
design:

<p align="center">
  <img src="../Picture/test-3d-prints.png" width="55%" alt="Three 3D-printed test plates showing the design progression"/>
</p>

## Files

| File | Format | What it is |
|------|--------|------------|
| `pi_p2_mount_plate.dxf` | DXF (2D CAD) | Outline/drilling drawing of the mount plate — Pi-footprint mounting holes mapped to the P2 board. Open in any CAD tool or for laser/CNC. |
| `RoboDogP2PlateV2.3mf` | 3MF (3D model) | Printable V2 mount plate for the P2 platform. Slice and 3D-print. |

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
