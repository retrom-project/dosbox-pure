#!/usr/bin/env python3
"""Exercise the pinned linker pause path from its browser and loop threads."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

# Minimal excerpts from EmulatorJS/RetroArch at the commit in retrom-fork.json.
UPSTREAM = """bool EJS_PAUSED = false;
bool EJS_MAINLOOP_PAUSED = false;
void emscripten_mainloop(void) {
   if (EJS_PAUSED && !EJS_MAINLOOP_PAUSED) {
      emscripten_pause_main_loop();
      EJS_MAINLOOP_PAUSED = true;
      return;
   }
   frames++;
}
void toggleMainLoop(int running) {
    if (running == 1 && EJS_MAINLOOP_PAUSED) {
        emscripten_resume_main_loop();
        EJS_MAINLOOP_PAUSED = false;
    }
    EJS_PAUSED = (running == 0);
}
"""
HARNESS = """#include <stdbool.h>
static int thread, frames;
static bool scheduled[2] = {false, true};
void emscripten_pause_main_loop(void) { scheduled[thread] = false; }
void emscripten_resume_main_loop(void) { scheduled[thread] = true; }
%s
static void tick(void) { thread = 1; if (scheduled[thread]) emscripten_mainloop(); }
int main(void) {
   tick();
   if (frames != 1) return 1;
   for (int i = 0; i < 3; ++i) {
      thread = 0; toggleMainLoop(0);
      tick(); tick();
      if (frames != i + 1) return 2;
      thread = 0; toggleMainLoop(1);
      tick();
      if (frames != i + 2) return 3;
   }
   return 0;
}
"""


def run_loop(source):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        (path / "pause.c").write_text(HARNESS % source)
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        str(path / "pause.c"), "-o", str(path / "pause")], check=True)
        return subprocess.run([str(path / "pause")], check=False).returncode


class ThreadedPauseTests(unittest.TestCase):
    def test_browser_resume_keeps_worker_loop_alive(self):
        script = Path(__file__).with_name("patch-retroarch-threaded-pause.py")
        spec = importlib.util.spec_from_file_location("threaded_pause", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.patch(UPSTREAM)
        self.assertEqual(run_loop(source), 0, "worker loop must resume after each browser pause")
        with self.assertRaisesRegex(ValueError, "PATCH_MISMATCH"):
            module.patch(source)
        with self.assertRaisesRegex(ValueError, "PATCH_MISMATCH"):
            module.patch(UPSTREAM.replace("if (EJS_PAUSED &&", "if (false &&"))

    def test_pinned_upstream_reproduces_wrong_thread_resume(self):
        self.assertEqual(run_loop(UPSTREAM), 3)


if __name__ == "__main__":
    unittest.main()
