#include <sandbox.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/*
 * SBPL wrapper: apply an SBPL profile to the current process and exec a command.
 *
 * Mode A: SBPL text via sandbox_init.
 * Mode B: compiled blob via sandbox_apply on .sb.bin (uses libsandbox.1.dylib).
 *
 * Usage:
 *   wrapper --sbpl <profile.sb> -- <cmd> [args...]
 *   wrapper --blob <profile.sb.bin> -- <cmd> [args...]
 */

static void json_write_string(FILE *out, const char *s) {
    fputc('"', out);
    for (const unsigned char *p = (const unsigned char *)s; p && *p; p++) {
        switch (*p) {
        case '\\':
            fputs("\\\\", out);
            break;
        case '"':
            fputs("\\\"", out);
            break;
        case '\b':
            fputs("\\b", out);
            break;
        case '\f':
            fputs("\\f", out);
            break;
        case '\n':
            fputs("\\n", out);
            break;
        case '\r':
            fputs("\\r", out);
            break;
        case '\t':
            fputs("\\t", out);
            break;
        default:
            if (*p < 0x20) {
                fprintf(out, "\\u%04x", (unsigned int)*p);
            } else {
                fputc(*p, out);
            }
        }
    }
    fputc('"', out);
}

static void json_emit_kv_string(FILE *out, int *first, const char *key, const char *value) {
    if (!value) return;
    if (!*first) fputc(',', out);
    *first = 0;
    json_write_string(out, key);
    fputc(':', out);
    json_write_string(out, value);
}

static void json_emit_kv_int(FILE *out, int *first, const char *key, long value) {
    if (!*first) fputc(',', out);
    *first = 0;
    json_write_string(out, key);
    fprintf(out, ":%ld", value);
}

static void emit_stage_apply(const char *mode, const char *api, int rc, int err, const char *errbuf, const char *profile_path) {
    FILE *out = stderr;
    int first = 1;
    fputc('{', out);
    json_emit_kv_string(out, &first, "tool", "sbpl-apply");
    json_emit_kv_string(out, &first, "stage", "apply");
    json_emit_kv_string(out, &first, "mode", mode);
    json_emit_kv_string(out, &first, "api", api);
    json_emit_kv_int(out, &first, "rc", rc);
    json_emit_kv_int(out, &first, "errno", err);
    json_emit_kv_string(out, &first, "errbuf", errbuf);
    json_emit_kv_string(out, &first, "profile", profile_path);
    json_emit_kv_int(out, &first, "pid", (long)getpid());
    fputs("}\n", out);
    fflush(out);
}

static void emit_stage_applied(const char *mode, const char *api, const char *profile_path) {
    FILE *out = stderr;
    int first = 1;
    fputc('{', out);
    json_emit_kv_string(out, &first, "tool", "sbpl-apply");
    json_emit_kv_string(out, &first, "stage", "applied");
    json_emit_kv_string(out, &first, "mode", mode);
    json_emit_kv_string(out, &first, "api", api);
    json_emit_kv_int(out, &first, "rc", 0);
    json_emit_kv_string(out, &first, "profile", profile_path);
    json_emit_kv_int(out, &first, "pid", (long)getpid());
    fputs("}\n", out);
    fflush(out);
}

static void emit_stage_exec(int rc, int err, const char *argv0) {
    FILE *out = stderr;
    int first = 1;
    fputc('{', out);
    json_emit_kv_string(out, &first, "tool", "sbpl-apply");
    json_emit_kv_string(out, &first, "stage", "exec");
    json_emit_kv_int(out, &first, "rc", rc);
    json_emit_kv_int(out, &first, "errno", err);
    json_emit_kv_string(out, &first, "argv0", argv0);
    json_emit_kv_int(out, &first, "pid", (long)getpid());
    fputs("}\n", out);
    fflush(out);
}

static void usage(const char *prog) {
    fprintf(stderr, "Usage: %s (--sbpl <profile.sb> | --blob <profile.sb.bin>) -- <cmd> [args...]\n", prog);
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
        if (strcmp(argv[i], "--blob") == 0 && i + 1 < argc) {
            mode = "blob";
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
        errno = 0;
        int rc = sandbox_init(buf, 0, &err);
        int saved_errno = errno;
        emit_stage_apply("sbpl", "sandbox_init", rc, saved_errno, err, profile_path);
        free(buf);
        if (rc != 0) {
            fprintf(stderr, "sandbox_init failed: %s\n", err ? err : "unknown");
            if (err) sandbox_free_error(err);
            return 1;
        }
        emit_stage_applied("sbpl", "sandbox_init", profile_path);
    } else if (strcmp(mode, "blob") == 0) {
        /* load blob */
        FILE *fp = fopen(profile_path, "rb");
        if (!fp) {
            perror("open blob");
            return 66;
        }
        fseek(fp, 0, SEEK_END);
        long len = ftell(fp);
        fseek(fp, 0, SEEK_SET);
        unsigned char *blob = (unsigned char *)malloc((size_t)len);
        if (!blob) {
            fprintf(stderr, "oom\n");
            fclose(fp);
            return 70;
        }
        size_t nread = fread(blob, 1, (size_t)len, fp);
        fclose(fp);
        if (nread != (size_t)len) {
            fprintf(stderr, "short read on blob\n");
            free(blob);
            return 66;
        }

        void *h = dlopen("/usr/lib/libsandbox.1.dylib", RTLD_NOW | RTLD_LOCAL);
        if (!h) {
            fprintf(stderr, "dlopen libsandbox.1.dylib failed: %s\n", dlerror());
            free(blob);
            return 1;
        }

        typedef struct sandbox_profile {
            char *builtin;
            const unsigned char *data;
            size_t size;
        } sandbox_profile_t;

        int (*p_sandbox_apply)(sandbox_profile_t *) =
            (int (*)(sandbox_profile_t *))dlsym(h, "sandbox_apply");
        if (!p_sandbox_apply) {
            fprintf(stderr, "dlsym sandbox_apply failed: %s\n", dlerror());
            dlclose(h);
            free(blob);
            return 1;
        }

        sandbox_profile_t profile = {0};
        profile.builtin = NULL;
        profile.data = blob;
        profile.size = (size_t)len;

        errno = 0;
        int rc = p_sandbox_apply(&profile);
        int saved_errno = errno;
        emit_stage_apply("blob", "sandbox_apply", rc, saved_errno, saved_errno ? strerror(saved_errno) : NULL, profile_path);
        free(blob);
        if (rc != 0) {
            perror("sandbox_apply");
            dlclose(h);
            return 1;
        }
        dlclose(h);
        emit_stage_applied("blob", "sandbox_apply", profile_path);
    } else {
        usage(argv[0]);
        return 64;
    }

    /* exec command */
    char **cmd = &argv[sep + 1];
    execvp(cmd[0], cmd);
    int saved_errno = errno;
    emit_stage_exec(-1, saved_errno, cmd[0]);
    perror("execvp");
    return 127;
}
