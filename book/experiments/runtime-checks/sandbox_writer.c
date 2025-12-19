#include <sandbox.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

/*
 * sandbox_writer: apply SBPL profile from file via sandbox_init, then append
 * a line to the target path. Avoids execing external binaries.
 *
 * Usage: sandbox_writer <profile.sb> <path>
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

static void emit_stage_apply(const char *api, int rc, int err, const char *errbuf, const char *profile_path) {
    FILE *out = stderr;
    int first = 1;
    fputc('{', out);
    json_emit_kv_string(out, &first, "tool", "sbpl-apply");
    json_emit_kv_string(out, &first, "stage", "apply");
    json_emit_kv_string(out, &first, "mode", "sbpl");
    json_emit_kv_string(out, &first, "api", api);
    json_emit_kv_int(out, &first, "rc", rc);
    json_emit_kv_int(out, &first, "errno", err);
    json_emit_kv_string(out, &first, "errbuf", errbuf);
    json_emit_kv_string(out, &first, "profile", profile_path);
    json_emit_kv_int(out, &first, "pid", (long)getpid());
    fputs("}\n", out);
    fflush(out);
}

static void emit_stage_applied(const char *api, const char *profile_path) {
    FILE *out = stderr;
    int first = 1;
    fputc('{', out);
    json_emit_kv_string(out, &first, "tool", "sbpl-apply");
    json_emit_kv_string(out, &first, "stage", "applied");
    json_emit_kv_string(out, &first, "mode", "sbpl");
    json_emit_kv_string(out, &first, "api", api);
    json_emit_kv_int(out, &first, "rc", 0);
    json_emit_kv_string(out, &first, "profile", profile_path);
    json_emit_kv_int(out, &first, "pid", (long)getpid());
    fputs("}\n", out);
    fflush(out);
}

static void usage(const char *prog) {
    fprintf(stderr, "Usage: %s <profile.sb> <path>\n", prog);
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        usage(argv[0]);
        return 64; /* EX_USAGE */
    }
    const char *profile_path = argv[1];
    const char *target = argv[2];

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
    free(buf);
    emit_stage_apply("sandbox_init", rc, saved_errno, err, profile_path);
    if (rc != 0) {
        fprintf(stderr, "sandbox_init failed: %s\n", err ? err : "unknown");
        if (err) sandbox_free_error(err);
        return 1;
    }
    emit_stage_applied("sandbox_init", profile_path);

    int fd = open(target, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd < 0) {
        perror("open target");
        return 2;
    }
    const char *line = "runtime-check\n";
    ssize_t nw = write(fd, line, strlen(line));
    if (nw < 0) {
        perror("write");
        close(fd);
        return 3;
    }
    close(fd);
    return 0;
}
