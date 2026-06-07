# dbg-display-theory — building P2 DEBUG-window displays

![Doc Type](https://img.shields.io/badge/doc-technique-blue)
![Platform](https://img.shields.io/badge/platform-Propeller%202-blue)
![Maintainer](https://img.shields.io/badge/maintainer-stephen%40ironsheep.biz-blue?labelColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

How we build the on-screen **DEBUG `PLOT`** panels this project uses for bench work — the
clickable move panel (`src/test_dog_panel.spin2`) and the diagnostic readouts. These pages
capture the **crop-and-overlay** sprite technique, the Python (Pillow) asset pipeline, and
the gotchas, so the next display is a copy-and-adjust job rather than a rediscovery.

- **[`THEORY-OF-OPERATION-crop-overlay.md`](THEORY-OF-OPERATION-crop-overlay.md)** — the
  authoritative semantics of the three primitives (`LAYER`, `CROP`, `UPDATE`) that blit
  pre-rendered bitmaps into a DEBUG window. Read this first.
- **[`DISPLAY-PATTERNS-builders-guide.md`](DISPLAY-PATTERNS-builders-guide.md)** — the
  builder's guide: the common display skeleton, the four reference displays, and the
  commands you actually use day to day.
- **[`HOWTO-build-debug-displays-with-claude.md`](HOWTO-build-debug-displays-with-claude.md)** —
  the end-to-end workflow: generating the artwork with Pillow, the Spin2 side, and the
  "I can't see your screen" round-trip discipline with `pnut-term-ts`.

---

## License

MIT License - See [LICENSE](../../LICENSE) for details.

---

*Part of the Iron Sheep Productions Propeller 2 Projects Collection*

---
