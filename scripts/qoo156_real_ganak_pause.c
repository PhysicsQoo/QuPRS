/* QOO-156 TEST ONLY: deterministic pause after genuine Ganak ELF exec.
 * Does not edit Ganak or any Rust core source or change solver arguments.
 * No effect on Ganak --version preflight or unrelated processes.
 */
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

__attribute__((constructor))
static void quprs_test_pause_ganak_count_only(void) {
    if (getenv("QOO156_PAUSE_REAL_GANAK") == NULL) return;
    int fd = open("/proc/self/cmdline", O_RDONLY);
    if (fd < 0) return;
    char buf[4096];
    ssize_t n = read(fd, buf, sizeof(buf));
    close(fd);
    if (n <= 0) return;
    for (ssize_t i = 0; i < n;) {
        size_t remaining = (size_t)(n-i);
        size_t length = strnlen(buf+i, remaining);
        if (length == remaining) return;
        if (length == 8 && memcmp(buf+i, "--mode=6", 8) == 0) {
            raise(SIGSTOP);
            return;
        }
        i += (ssize_t)length + 1;
    }
}
