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

## How I developed the model

So I'm a heavy Claude Code user, and I decided to try an experiment. The geometry and pin mounting points for the P2 Edge modules are well-known and publicly documented, as are the Raspberry Pi mounting holes. I asked Perplexity, in this case, to study and gather the mounting information (mounting hole sizes and locations), and then to overlay the two with the same orientation. I described how I wanted the platform to look, and then I had Perplexity give me the constraints for drawing it. Perplexity can't produce files, so it gave me the specification for the model file that I'd want. I copied that specification into Claude Code, and I said, "OK, now write the 2D design file that Shapr3D can read." It did that beautifully, and in fact, it did it in one pass. The first one was correct. I was able to use it.

The next thing I did was import the file into Shapr3D and apply the standard extrusion techniques to create a 3D model. I printed some lightweight tests so I could prove that all the geometry was correct, and pleasantly so, the geometry was perfectly correct. I never had to move a hole placement. The only thing that might have been better is if the inner diameter of the standoffs had been narrower, so the screw could have threaded itself. As a result of not paying attention to that, I had to use nuts to hold the screws in place for the P2 Edge standoffs.  

The final thing is, you'll see the very first print I produced was perfectly rectangular. When I laid it down, I realized that the pins on the board underneath, where I would have to connect that header to the P2, were too close to this board. The last thing I had to do then was create an inset so the header would have more clearance around it, allowing me to plug in the cables. That was the final modification, which is why the first one in the following print regression is rectangular, while the second and third have the inset.  Anyway, I thought this would be interesting for you to know. -Stephen

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
