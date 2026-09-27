#!/usr/bin/env python3
"""Keep the pthread scheduler alive while the browser pauses emulation."""
from pathlib import Path
import sys


def patch(source: str) -> str:
    replacements = (
        ("bool EJS_MAINLOOP_PAUSED = false;\n", ""),
        ("""   if (EJS_PAUSED && !EJS_MAINLOOP_PAUSED) {
      emscripten_pause_main_loop();
      EJS_MAINLOOP_PAUSED = true;
      return;
   }""", """   /* The browser invokes toggleMainLoop, but this loop belongs to a
    * pthread. Keep its scheduler alive: resuming an Emscripten loop on
    * the browser thread cannot restart the pthread's stopped scheduler.
    * Paused ticks do no emulation, audio or frame accounting. */
   if (EJS_PAUSED)
      return;"""),
        ("""    if (running == 1 && EJS_MAINLOOP_PAUSED) {
        emscripten_resume_main_loop();
        EJS_MAINLOOP_PAUSED = false;
    }
""", ""),
    )
    for before, after in replacements:
        if source.count(before) != 1:
            raise ValueError("EMULATORJS_THREADED_PAUSE_PATCH_MISMATCH")
        source = source.replace(before, after, 1)
    return source


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("/work/retroarch")
    path = root / "retroarch.c"
    path.write_text(patch(path.read_text()))
