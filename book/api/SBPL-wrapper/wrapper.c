#include <sandbox.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/*
 * SBPL wrapper: apply an SBPL profile to the current process and exec a command.
 *
 * Mode A (implemented): SBPL text via sandbox_init.
 * Mode B (TODO): compiled blob via sandbox_apply on .sb.bin.
 *
 * Usage:
 *   wrapper --sbpl <profile.sb> -- <cmd> [args...]
 */

static void usage(const char *prog) {
    fprintf(stderr, "Usage: %s --sbpl <profile.sb> -- <cmd> [args...]\n", prog);
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        usage(argv[0]);
        return 64; /* EX_USAGE */
    }

    /* parse args */
    const char *mode = NULL;
    const char *profile_path = NULL;
    int sep = -1;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--") == 0) {
            sep = i;
            break;
        }
        if (strcmp(argv[i], "--sbpl") == 0 && i + 1 < argc) {
            mode = "sbpl";
            profile_path = argv[++i];
        }
    }
    if (!mode || !profile_path || sep < 0 || sep == argc - 1) {
        usage(argv[0]);
        return 64;
    }

    if (strcmp(mode, "sbpl") == 0) {
        /* load SBPL text */
        FILE *fp = fopen(profile_path, "r");
        if (!fp) {
            perror("open profile");
            return 66; /* EX_NOINPUT */
        }
        fseek(fp, 0, SEEK_END);
        long len = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        char *buf = (char *)malloc((size_t)len + 1);
        if (!buf) {
            fprintf(stderr, "oom\n");
            fclose(fp);
            return 70; /* EX_SOFTWARE */
        }
        size_t nread = fread(buf, 1, (size_t)len, fp);
        fclose(fp);
        buf[nread] = '\0';

        char *err = NULL;
        int rc = sandbox_init(buf, 0, &err);
        free(buf);
        if (rc != 0) {
            fprintf(stderr, "sandbox_init failed: %s\n", err ? err : "unknown");
            if (err) sandbox_free_error(err);
            return 1;
        }
    } else {
        usage(argv[0]);
        return 64;
    }

    /* exec command */
    char **cmd = &argv[sep + 1];
    execvp(cmd[0], cmd);
    perror("execvp");
    return 127;
}
