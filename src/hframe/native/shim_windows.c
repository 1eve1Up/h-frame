/*
 * Windows workspace launcher: spawn Python on the membrane zipapp.
 * Must match resolve_membrane_pyz / _posix_launcher_source in hframe/shim_install.py.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define PYZ_NAME L"hframe-membrane.pyz"
#define HFRAME_DIR L".hframe"
#define DEVCONTAINER_MOUNT L"hframe-root"
#define PATH_MAX_W 4096

static int is_in_or_out(const wchar_t *arg) {
    return wcscmp(arg, L"in") == 0 || wcscmp(arg, L"out") == 0;
}

static int path_is_file(const wchar_t *path) {
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

static int path_full(const wchar_t *in, wchar_t *out, size_t out_chars) {
    DWORD n = GetFullPathNameW(in, (DWORD)out_chars, out, NULL);
    return n > 0 && n < out_chars;
}

static void path_dirname(wchar_t *path) {
    wchar_t *last = wcsrchr(path, L'\\');
    if (last != NULL) {
        *last = L'\0';
    }
}

static int try_candidate(const wchar_t *candidate, wchar_t *resolved, size_t resolved_chars) {
    if (!path_full(candidate, resolved, resolved_chars)) {
        return 0;
    }
    return path_is_file(resolved);
}

static int resolve_pyz(const wchar_t *workspace_dir, wchar_t *pyz_out, size_t pyz_chars) {
    wchar_t parent[PATH_MAX_W];
    wchar_t direct[PATH_MAX_W];
    wchar_t devc[PATH_MAX_W];

    wcsncpy_s(parent, PATH_MAX_W, workspace_dir, _TRUNCATE);
    path_dirname(parent);

    swprintf_s(direct, PATH_MAX_W, L"%s\\%s\\%s", parent, HFRAME_DIR, PYZ_NAME);
    if (try_candidate(direct, pyz_out, pyz_chars)) {
        return 1;
    }

    swprintf_s(devc, PATH_MAX_W, L"%s\\%s\\%s\\%s", parent, DEVCONTAINER_MOUNT, HFRAME_DIR, PYZ_NAME);
    if (try_candidate(devc, pyz_out, pyz_chars)) {
        return 1;
    }

    wchar_t pattern[PATH_MAX_W];
    swprintf_s(pattern, PATH_MAX_W, L"%s\\*", parent);

    WIN32_FIND_DATAW entry;
    HANDLE handle = FindFirstFileW(pattern, &entry);
    if (handle == INVALID_HANDLE_VALUE) {
        return 0;
    }

    wchar_t hits[2][PATH_MAX_W];
    int hit_count = 0;

    do {
        if (entry.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (wcscmp(entry.cFileName, L".") == 0 || wcscmp(entry.cFileName, L"..") == 0) {
                continue;
            }
            wchar_t child[PATH_MAX_W];
            swprintf_s(child, PATH_MAX_W, L"%s\\%s", parent, entry.cFileName);
            if (_wcsicmp(child, workspace_dir) == 0) {
                continue;
            }
            wchar_t candidate[PATH_MAX_W];
            swprintf_s(candidate, PATH_MAX_W, L"%s\\%s\\%s", child, HFRAME_DIR, PYZ_NAME);
            wchar_t resolved[PATH_MAX_W];
            if (try_candidate(candidate, resolved, PATH_MAX_W)) {
                if (hit_count < 2) {
                    wcsncpy_s(hits[hit_count], PATH_MAX_W, resolved, _TRUNCATE);
                }
                hit_count++;
            }
        }
    } while (FindNextFileW(handle, &entry));

    FindClose(handle);

    if (hit_count == 1) {
        wcsncpy_s(pyz_out, pyz_chars, hits[0], _TRUNCATE);
        return 1;
    }
    if (hit_count > 1) {
        fwprintf(stderr,
                 L"hframe: multiple sibling .hframe/ bundles under %s; keep only one or use "
                 L"%s\\%s\\%s.\n",
                 parent, parent, DEVCONTAINER_MOUNT, HFRAME_DIR);
    }
    return 0;
}

static int spawn_python(const wchar_t *interpreter, const wchar_t *pyz, const wchar_t *subcmd) {
    const wchar_t *argv[] = {interpreter, pyz, subcmd, NULL};
    return _wspawnvp(_P_OVERLAY, interpreter, argv);
}

static int run_python_on_pyz(const wchar_t *pyz, const wchar_t *subcmd) {
    int rc = spawn_python(L"python", pyz, subcmd);
    if (rc != -1) {
        return rc;
    }
    rc = spawn_python(L"python3", pyz, subcmd);
    if (rc != -1) {
        return rc;
    }
    fwprintf(stderr, L"hframe: could not spawn python or python3 on %s\n", pyz);
    return 127;
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 2 || !is_in_or_out(argv[1])) {
        fwprintf(stderr, L"usage: hframe in\n       hframe out\n");
        return 2;
    }

    wchar_t exe_path[PATH_MAX_W];
    if (GetModuleFileNameW(NULL, exe_path, PATH_MAX_W) == 0) {
        fwprintf(stderr, L"hframe: GetModuleFileNameW failed\n");
        return 2;
    }

    wchar_t workspace_dir[PATH_MAX_W];
    wcsncpy_s(workspace_dir, PATH_MAX_W, exe_path, _TRUNCATE);
    path_dirname(workspace_dir);

    wchar_t pyz[PATH_MAX_W];
    if (!resolve_pyz(workspace_dir, pyz, PATH_MAX_W)) {
        wchar_t parent[PATH_MAX_W];
        wcsncpy_s(parent, PATH_MAX_W, workspace_dir, _TRUNCATE);
        path_dirname(parent);

        wchar_t tried_direct[PATH_MAX_W];
        wchar_t tried_devc[PATH_MAX_W];
        swprintf_s(tried_direct, PATH_MAX_W, L"%s\\%s\\%s", parent, HFRAME_DIR, PYZ_NAME);
        swprintf_s(tried_devc, PATH_MAX_W, L"%s\\%s\\%s\\%s", parent, DEVCONTAINER_MOUNT, HFRAME_DIR, PYZ_NAME);

        fwprintf(stderr,
                 L"hframe: missing membrane bundle. Tried:\n  %s\n  %s\n"
                 L"If those files are missing, add Dev Container bind mounts (see README "
                 L"Devcontainers).\n"
                 L"To refresh this launcher, install the hframe package (pip install -e /path/to/h-frame) "
                 L"then run the install_workspace_shim one-liner from README Devcontainers.\n",
                 tried_direct, tried_devc);
        return 2;
    }

    return run_python_on_pyz(pyz, argv[1]);
}
