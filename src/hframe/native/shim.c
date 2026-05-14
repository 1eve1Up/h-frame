/*
 * Native workspace launcher: exec python3 on the membrane zipapp.
 * Must match MEMBRANE_PYZ_NAME in hframe/config.py (reference / optional native build).
 */
#define HF_PYZ_REL "/../.hframe/hframe-membrane.pyz"
enum { HF_PATH_MAX = 4096 };

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2 || (strcmp(argv[1], "in") != 0 && strcmp(argv[1], "out") != 0)) {
        const char *u = "usage: ./hframe in\n       ./hframe out\n";
        fwrite(u, 1, strlen(u), stderr);
        return 2;
    }

    char exe[HF_PATH_MAX];
    if (!realpath(argv[0], exe)) {
        fprintf(stderr, "hframe: realpath(%s): %s\n", argv[0], strerror(errno));
        return 2;
    }

    char *slash = strrchr(exe, '/');
    if (!slash) {
        fputs("hframe: could not locate workspace directory\n", stderr);
        return 2;
    }
    *slash = '\0';

    char pyz_rel[HF_PATH_MAX];
    int n = snprintf(pyz_rel, sizeof(pyz_rel), "%s%s", exe, HF_PYZ_REL);
    if (n < 0 || (size_t)n >= sizeof(pyz_rel)) {
        fputs("hframe: path too long\n", stderr);
        return 2;
    }

    char pyz[HF_PATH_MAX];
    if (!realpath(pyz_rel, pyz)) {
        fprintf(stderr, "hframe: cannot resolve membrane bundle (%s): %s\n", pyz_rel, strerror(errno));
        return 2;
    }

    char *av[] = {"python3", pyz, argv[1], NULL};
    execvp("python3", av);
    fprintf(stderr, "hframe: exec python3: %s\n", strerror(errno));
    return 127;
}
