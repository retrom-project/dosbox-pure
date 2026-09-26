#!/usr/bin/env python3
"""Expose the pinned EmulatorJS RetroArch savestate task result to the browser."""

from pathlib import Path
import sys


def replace_once(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise SystemExit("EMULATORJS_STATE_STATUS_PATCH_MISMATCH")
    return source.replace(before, after, 1)


root = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("/work/retroarch")
path = root / "tasks/task_save.c"
source = path.read_text()
source = replace_once(source, "/**\n * content_load_state_cb:", """#ifdef EMULATORJS
static int retrom_state_load_result;

int retrom_state_load_status(void)
{
   return retrom_state_load_result;
}
#endif

/**
 * content_load_state_cb:""")
start = source.index("static void content_load_state_cb(")
end = source.index("/**\n * save_state_cb:", start)
callback = source[start:end]
callback = replace_once(callback, "   if (!ret)\n      goto error;\n\n   free(buf);", """   if (!ret)
      goto error;

#ifdef EMULATORJS
   retrom_state_load_result = 1;
#endif
   free(buf);""")
callback = replace_once(callback, 'error:\n   RARCH_ERR("[State]: %s \\"%s\\".\\n",',
    '''error:
#ifdef EMULATORJS
   retrom_state_load_result = -1;
#endif
   RARCH_ERR("[State]: %s \\"%s\\".\\n",''')
source = source[:start] + callback + source[end:]
start = source.index("bool content_load_state(const char *path,")
end = source.index("bool content_rename_state(", start)
loader = source[start:end]
loader = replace_once(loader, "   if (!core_info_current_supports_savestate())", """#ifdef EMULATORJS
   retrom_state_load_result = 0;
#endif
   if (!core_info_current_supports_savestate())""")
loader = replace_once(loader, "error:\n   if (state)", """error:
#ifdef EMULATORJS
   retrom_state_load_result = -1;
#endif
   if (state)""")
source = source[:start] + loader + source[end:]
path.write_text(source)

path = root / "Makefile.emulatorjs"
source = path.read_text()
source = replace_once(source, "EXPORTED_FUNCTIONS = _main,_malloc,_free,_load_state, \\\n",
    "EXPORTED_FUNCTIONS = _main,_malloc,_free,_load_state,_retrom_state_load_status, \\\n")
path.write_text(source)
