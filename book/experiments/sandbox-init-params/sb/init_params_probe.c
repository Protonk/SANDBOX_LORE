#include <dlfcn.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef void *(*sandbox_compile_string_fn)(const char *profile, void *params, char **errorbuf);
typedef int (*sandbox_apply_fn)(void *compiled, const char *container);
typedef void (*sandbox_free_profile_fn)(void *compiled);

static void dump_qwords(const char *label, const uint64_t *ptr, size_t count) {
    printf("%s @ %p:", label, (const void *)ptr);
    for (size_t i = 0; i < count; i++) {
        printf(" [%zu]=0x%016" PRIx64, i, ptr[i]);
    }
    printf("\n");
}

int main(void) {
    const char *profile = "(version 1)\n(allow default)";
    char *err = NULL;

    void *lib = dlopen("/usr/lib/libsandbox.1.dylib", RTLD_LAZY);
    if (!lib) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    sandbox_compile_string_fn compile_fn = (sandbox_compile_string_fn)dlsym(lib, "sandbox_compile_string");
    sandbox_apply_fn apply_fn = (sandbox_apply_fn)dlsym(lib, "sandbox_apply");
    sandbox_free_profile_fn free_fn = (sandbox_free_profile_fn)dlsym(lib, "sandbox_free_profile");
    if (!compile_fn || !apply_fn) {
        fprintf(stderr, "dlsym failed (compile_fn=%p apply_fn=%p): %s\n", (void *)compile_fn, (void *)apply_fn, dlerror());
        return 1;
    }

    void *handle = compile_fn(profile, NULL, &err);
    if (!handle) {
        fprintf(stderr, "sandbox_compile_string returned NULL\n");
        if (err) {
            fprintf(stderr, "error: %s\n", err);
            free(err);
        }
        return 1;
    }

    uint64_t *handle_q = (uint64_t *)handle;
    dump_qwords("handle", handle_q, 3);

    const void *blob_ptr = NULL;
    size_t blob_len = 0;

    if (handle_q[0]) {
        uint64_t *buf = (uint64_t *)handle_q[0];
        dump_qwords("sb_buffer", buf, 4);
        blob_ptr = (const void *)buf[0];
        blob_len = (size_t)buf[1];
    } else {
        blob_ptr = (const void *)handle_q[1];
        blob_len = (size_t)handle_q[2];
    }

    printf("compiled blob ptr=%p len=%zu\n", blob_ptr, blob_len);

    const char *out_path = getenv("INIT_PARAMS_PROBE_OUT");
    if (blob_ptr && blob_len && out_path && out_path[0]) {
        FILE *f = fopen(out_path, "wb");
        if (!f) {
            perror("fopen");
        } else {
            size_t written = fwrite(blob_ptr, 1, blob_len, f);
            fclose(f);
            printf("wrote %zu bytes to %s\n", written, out_path);
        }
    }

    int apply_rv = apply_fn(handle, NULL);
    printf("sandbox_apply returned %d\n", apply_rv);

    if (free_fn) {
        free_fn(handle);
    }
    if (err) {
        free(err);
    }
    dlclose(lib);
    return 0;
}
