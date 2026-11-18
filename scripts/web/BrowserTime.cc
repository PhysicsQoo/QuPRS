// MIT licensed PathsumWMC portability shim.
// Browsers expose no OS CPU/RSS counters. Use worker-local monotonic elapsed
// time for solver resource budgets, and allocated linear memory as a heap
// high-water proxy. These are NOT OS CPU time or resident-set measurements.
#ifdef __EMSCRIPTEN__
#include <sys/resource.h>
#include <emscripten.h>
#include <emscripten/heap.h>
#include <cerrno>
#include <cmath>
#include <cstring>
extern "C" int getrusage(int who, struct rusage* usage) {
    if (!usage) { errno=EFAULT;return -1; }
    std::memset(usage,0,sizeof(*usage));
    if (who==RUSAGE_CHILDREN) return 0; // A dedicated solver worker has no child processes.
    if (who!=RUSAGE_SELF
#ifdef RUSAGE_THREAD
        && who!=RUSAGE_THREAD
#endif
    ) { errno=EINVAL;return -1; }
    static const double origin=emscripten_get_now();
    const double elapsed=(emscripten_get_now()-origin)/1000.0;
    const double seconds=std::floor(elapsed);
    usage->ru_utime.tv_sec=static_cast<decltype(usage->ru_utime.tv_sec)>(seconds);
    usage->ru_utime.tv_usec=static_cast<decltype(usage->ru_utime.tv_usec)>((elapsed-seconds)*1000000.0);
    usage->ru_maxrss=static_cast<decltype(usage->ru_maxrss)>(emscripten_get_heap_size()/1024);
    return 0;
}
#endif
