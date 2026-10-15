# VMzero

*A concept and project foundation by Runaque*

**© 2026 Runaque. First published 15 October 2026.**
Licensed under [Creative Commons Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)](https://creativecommons.org/licenses/by-nd/4.0/).
You may share this document in full, in any medium, provided you credit Runaque as the author and do not alter it. The concept described here was first published on the date above.

---

## TL;DR

The M5Stack Cardputer Zero is a pocket Linux handheld (Raspberry Pi CM0, quad-core Cortex-A53, running real Linux). The existing Cardputer/StickS3/Atom ecosystem is huge and active, but all of it is built for ESP32 microcontrollers, not for a Linux ARM device.

**VMzero** is a single launcher app for the Zero that runs those existing M5 apps through one interface, choosing the lightest viable execution method per app:

- **MicroPython apps** run *natively* on the Zero's own Python, through a thin hardware-compatibility shim. No emulation.
- **Compiled (C/C++) ESP32 apps** run through an *Xtensa board emulator* with a selectable device profile (e.g. "Cardputer ADV", "StickS3"), so the original firmware runs unmodified.
- A **library/launcher front-end** (think Steam for your firmware) houses many `.bin`/`.py` apps and launches them from one place, keeping them out of the desktop/menu.
- Eventually, an **online catalogue link** (like the Cardputer Loader firmware's download page) so users can browse and run the ecosystem, not just their local collection.

The key design principle: **tiered execution behind one button.** Run natively where you can, emulate only where you must. Each layer ships value on its own, so v1 is useful before any emulation exists.

---

## The problem

The Cardputer line has moved up a tier. The original Cardputer and the Cardputer ADV are ESP32-S3 microcontroller boards. The Cardputer Zero swaps that for a Raspberry Pi Compute Module Zero — a real ARM Linux computer in the same pocket form factor.

That's a big capability jump, but it creates a discontinuity: years of community firmware, launchers, tools and emulators were written for the ESP32. None of it runs directly on an ARM Linux host. A new Zero owner inherits the hardware leap but not the back-catalogue.

VMzero's goal is to bridge that gap so the Zero can make use of the ecosystem that already exists around its own family of devices.

---

## Why the Zero is the right host for this

- It runs full Linux, so it has a real filesystem, a package manager, multitasking and CPython out of the box.
- It keeps the Cardputer form factor: pocket-sized, keyboard, screen, battery.
- The community and skills already transfer. M5Stack's UiFlow platform is built on MicroPython, so the language and much of the code carry straight over to the Zero's full-Linux Python environment.

This positions the Zero as the "glue tier" between ESP32 boards and full x86/amd64 machines: capture-and-sit-there jobs stay on ESP32, think-and-drive jobs run on the Zero, heavy compute gets handed off upstream.

---

## The core idea: tiered execution

Not every M5 app needs the same treatment. The workload and the firmware type decide the execution path. VMzero inspects each app and routes it to the lightest method that works.

### Tier 1 — Native MicroPython (easy, highest value)

A MicroPython `.bin` is the MicroPython VM plus the author's `.py` scripts baked into a firmware image. The valuable part — the actual code — is Python. The Zero already runs CPython.

So for MicroPython apps, VMzero does **not** emulate anything. It runs the Python code natively and substitutes the M5/hardware calls (display, keyboard, GPIO, etc.) with Zero equivalents through a compatibility shim. This is the lightest path and covers a large share of community apps, including anything built in UiFlow.

### Tier 2 — Xtensa emulation (harder, for compiled apps)

A compiled Arduino/C++ `.bin` is native ESP32-S3 (Xtensa) machine code — you can't just extract source from it. For these, VMzero loads an ESP32 board emulator and runs the firmware unmodified.

The user experience is the interesting part: instead of picking cores/RAM/storage like a normal VM, you pick a **device profile** — "Cardputer ADV", "StickS3", etc. Each profile is a board-definition file describing the SoC, flash/PSRAM, display controller, keyboard map, IR pin and other peripherals. The emulator presents that virtual board and the firmware installs/runs as if on real hardware. This is conceptually what Wokwi and the Espressif QEMU fork already do; VMzero's contribution is the profile-driven launcher around it.

Because profiles are just data, the community can contribute new board definitions without touching the emulator core.

### Routing

The launcher chooses the tier automatically. The user presses one button; whether the app runs natively or emulated is invisible to them.

---

## Honest constraints (so the scope is clear)

- **Emulation cost.** Tier 2 is Xtensa-on-ARM CPU emulation. On a 1 GHz A53 with 512 MB RAM it will handle many apps but won't be effortless, especially timing-sensitive code. This is why native (Tier 1) is preferred wherever possible.
- **Radio fidelity.** Emulating the *logic* of a device is tractable; faithfully emulating Wi-Fi/BT/Sub-GHz RF behaviour is the hardest part. Many apps (UI, tools, offline logic) don't need it; radio-heavy hacking features do.
- **Workload matters more than the emulator.** Passive/IO tasks like wardriving are light and may run *better* natively on the Zero's own Linux Wi-Fi stack than emulated. Heavy cracking (WPA/hash brute force) is pure compute and shouldn't run on the device at all — capture on the handheld, crack on an upstream x86/GPU box.
- **Naming honesty.** v1 is a launcher + native MicroPython runtime, not a "VM" in the emulation sense. Describe VMzero as "runs M5 apps on the Zero — natively where it can, emulated where it must" so the name never oversells the early builds.

---

## Proposed architecture

```
                     ┌─────────────────────────────┐
                     │        VMzero launcher       │
                     │  (library UI — "Steam-like") │
                     └──────────────┬──────────────┘
                                    │  inspect app
                 ┌──────────────────┴──────────────────┐
                 │                                      │
        MicroPython app                        Compiled C/C++ app
                 │                                      │
                 ▼                                      ▼
      ┌────────────────────┐              ┌──────────────────────────┐
      │ Native CPython run  │              │  Xtensa board emulator    │
      │ + hardware shim     │              │  + selected device profile│
      │ (display, keys,     │              │  (Cardputer ADV / StickS3 │
      │  GPIO, IR, …)       │              │   / community profiles)   │
      └─────────┬──────────┘              └────────────┬─────────────┘
                │                                       │
                └──────────────┬────────────────────────┘
                               ▼
                   Cardputer Zero hardware
              (display, keyboard, GPIO, radios)

   Optional later layer:
   ┌──────────────────────────────────────────────┐
   │ Online catalogue link (Loader-style download) │
   │ browse + fetch .bin/.py apps into the library  │
   └──────────────────────────────────────────────┘
```

---

## Build roadmap (each layer ships value independently)

**v1 — Launcher + native MicroPython runtime + hardware shim.**
Fully useful on its own. Proves the "run my apps on the Zero" story. Needs no emulator. This is the first target and the first thing worth demonstrating publicly.

**v2 — Xtensa emulation path with device profiles.**
Additive. Covers compiled apps you don't have source for. Gated behind "if it can be made to run well enough." Starts with one or two profiles (Cardputer ADV, StickS3).

**v3 — Online catalogue / Loader link.**
Turns a local collection into a browse-and-run front-end for the wider ecosystem. The "comprehensive solution" layer.

Each version is independently shippable, so the hard emulation work never blocks a useful release.

---

## Why this is worth doing

- **For users:** one place to run the M5 app ecosystem on the Zero, keeping existing software investment alive on the new hardware.
- **For the community:** a profile system and a shim are both community-extendable. New board profiles are data files; new shim mappings are small Python contributions. The Cardputer scene is already large and active, which is the right soil for this.
- **For M5Stack (commercially):** an official or community "run your existing M5 ecosystem on the Zero" story makes the Zero a soft-landing upgrade for every existing Cardputer/Stick/Atom owner, protects their community's software investment, and is a marketing angle competitors can't match. A natural fit for M5Stack's channels, forum, or Global Innovation Contest.

---

## Proof-of-concept plan

Performance is explicitly **secondary** at PoC stage. The PoC answers one binary question: *is this possible?* Optimisation comes after feasibility is proven, and has several fallback paths (JIT/dynamic recompilation, network offload, narrowing profile scope, or dropping to the shim for apps that don't need full emulation).

Two separate experiments, in order:

1. **MicroPython path (do first, doable before the Zero even ships).**
   Take one existing `.py` app, run it on a Pi under CPython with a small hardware shim stubbing display/keyboard/GPIO. Proves the native-port story cheaply. A Pi Zero 2W or similar is close enough ARM hardware to be indicative.

2. **Emulator path (harder, only needed for compiled apps).**
   Get a simple ESP32-S3 firmware booting in an ESP32 emulator on a PC first (feasibility, host-independent). Then try it on real ARM Linux. Then define a first Cardputer board profile.

**Open question gating the emulator path:** current state of ESP32-S3 support in the Espressif QEMU fork and in Wokwi — whether it covers the S3 (the ADV/Stick chip) specifically, not just the original ESP32. That one fact decides whether the emulator path is a start-now job or a wait-for-better-support job.

---

## Starting points / prior art to build on

- **Wokwi** — in-browser ESP32 board emulation; the reference for "firmware believes it's on real hardware."
- **Espressif's QEMU fork** — system-level ESP32 emulation; the likely basis for Tier 2.
- **Cardputer Loader firmware** — the existing online `.bin` catalogue model that v3 would mirror/link.
- **UiFlow2 / MicroPython** — the reason Tier 1 is viable: shared language between the ecosystem and the Zero.

---

## Status

Concept stage, authored ahead of the Cardputer Zero (Lite) arriving. Next step is to scaffold the v1 launcher structure and the shim's hardware-abstraction surface, which can be stubbed before any emulation work begins.

*Project and concept by Runaque. Open to collaboration and contribution.*
