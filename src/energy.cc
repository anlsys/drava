/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

/*
 * Energy sampling.
 *
 * GPU energy comes from NVML's nvmlDeviceGetTotalEnergyConsumption, a monotonic
 * millijoule counter (Volta+). We read it once at the start of the stream and
 * once at end-of-stream and subtract -- no power sampling, no integration.
 * Compiled only when DRAVA_HAS_NVML is defined.
 *
 * CPU energy comes from the Linux RAPL powercap sysfs
 * (/sys/class/powercap/intel-rapl:*​/energy_uj), read the same way with
 * wraparound handling via max_energy_range_uj. Available on Linux regardless of
 * NVML.
 *
 * A sampler with neither source available is valid; it simply produces no
 * readings, and the JSON metrics record omits the corresponding fields.
 */

#include <cstdint>
#include <cstdio>
#include <new>
#include <string>
#include <vector>

#include <drava/drava.h>

#ifdef __linux__
#include <dirent.h>
#endif

#ifdef DRAVA_HAS_NVML
#include <nvml.h>
#endif

namespace {

#ifdef __linux__
/* One RAPL domain (package/dram/...) tracked across the stream window. */
struct rapl_domain_t {
    std::string energy_path;      /* .../energy_uj */
    uint64_t max_range_uj = 0;    /* 0 if unknown (wraparound not corrected) */
    uint64_t baseline_uj = 0;
    bool baseline_valid = false;
};

static bool read_uint64_file(const std::string &path, uint64_t *out)
{
    FILE *f = std::fopen(path.c_str(), "r");
    if (f == nullptr)
        return false;
    unsigned long long v = 0;
    int n = std::fscanf(f, "%llu", &v);
    std::fclose(f);
    if (n != 1)
        return false;
    *out = (uint64_t)v;
    return true;
}

/* Discover top-level RAPL domains under /sys/class/powercap/intel-rapl:*. We
 * intentionally skip subdomains (intel-rapl:0:0) to avoid double counting;
 * package-level domains already include their subdomains. */
static std::vector<rapl_domain_t> discover_rapl_domains()
{
    std::vector<rapl_domain_t> domains;
    const char *base = "/sys/class/powercap";
    DIR *dir = opendir(base);
    if (dir == nullptr)
        return domains;

    struct dirent *ent;
    while ((ent = readdir(dir)) != nullptr) {
        const std::string name = ent->d_name;
        /* Top-level domains look like "intel-rapl:0"; subdomains contain a
         * second colon ("intel-rapl:0:0") -- match exactly one ':' after the
         * "intel-rapl" prefix. */
        if (name.rfind("intel-rapl:", 0) != 0)
            continue;
        if (name.find(':', 11) != std::string::npos)
            continue;

        rapl_domain_t d;
        d.energy_path = std::string(base) + "/" + name + "/energy_uj";
        uint64_t probe = 0;
        if (!read_uint64_file(d.energy_path, &probe))
            continue; /* not readable (permissions) -> skip this domain */
        uint64_t max_range = 0;
        if (read_uint64_file(std::string(base) + "/" + name +
                                     "/max_energy_range_uj",
                             &max_range))
            d.max_range_uj = max_range;
        domains.push_back(std::move(d));
    }
    closedir(dir);
    return domains;
}
#endif /* __linux__ */

} /* namespace */

struct drava_energy_sampler_t {
    bool baseline_captured = false;

#ifdef DRAVA_HAS_NVML
    bool nvml_ready = false;
    nvmlDevice_t nvml_device{};
    unsigned long long gpu_baseline_mj = 0;
    bool gpu_baseline_valid = false;
#endif

#ifdef __linux__
    std::vector<rapl_domain_t> rapl_domains;
#endif
};

drava_energy_sampler_t *drava_energy_create(void)
{
    drava_energy_sampler_t *s = new (std::nothrow) drava_energy_sampler_t();
    if (s == nullptr)
        return nullptr;

#ifdef DRAVA_HAS_NVML
    nvmlReturn_t rc = nvmlInit_v2();
    if (rc == NVML_SUCCESS) {
        /* Device 0: drava binds a single GPU team per stage today. */
        if (nvmlDeviceGetHandleByIndex_v2(0, &s->nvml_device) == NVML_SUCCESS) {
            /* Probe the energy counter so we only advertise GPU energy when the
             * device actually supports it (Volta+). */
            unsigned long long probe = 0;
            if (nvmlDeviceGetTotalEnergyConsumption(s->nvml_device, &probe) ==
                NVML_SUCCESS) {
                s->nvml_ready = true;
            } else {
                LOGGER_WARN("NVML present but GPU energy counter unsupported "
                            "(requires Volta+); GPU energy disabled");
            }
        }
        if (!s->nvml_ready)
            nvmlShutdown();
    } else {
        LOGGER_WARN("nvmlInit failed (%d); GPU energy disabled", (int)rc);
    }
#endif

#ifdef __linux__
    s->rapl_domains = discover_rapl_domains();
    if (s->rapl_domains.empty())
        LOGGER_INFO("No readable RAPL domains found; CPU energy disabled");
#endif

    return s;
}

void drava_energy_capture_baseline(drava_energy_sampler_t *sampler)
{
    if (sampler == nullptr || sampler->baseline_captured)
        return;
    sampler->baseline_captured = true;

#ifdef DRAVA_HAS_NVML
    if (sampler->nvml_ready) {
        unsigned long long mj = 0;
        if (nvmlDeviceGetTotalEnergyConsumption(sampler->nvml_device, &mj) ==
            NVML_SUCCESS) {
            sampler->gpu_baseline_mj = mj;
            sampler->gpu_baseline_valid = true;
        }
    }
#endif

#ifdef __linux__
    for (rapl_domain_t &d : sampler->rapl_domains) {
        uint64_t uj = 0;
        if (read_uint64_file(d.energy_path, &uj)) {
            d.baseline_uj = uj;
            d.baseline_valid = true;
        }
    }
#endif
}

bool drava_energy_read(drava_energy_sampler_t *sampler,
                       drava_energy_reading_t *out)
{
    if (sampler == nullptr || out == nullptr || !sampler->baseline_captured)
        return false;

    *out = drava_energy_reading_t{};

#ifdef DRAVA_HAS_NVML
    if (sampler->nvml_ready && sampler->gpu_baseline_valid) {
        unsigned long long mj = 0;
        if (nvmlDeviceGetTotalEnergyConsumption(sampler->nvml_device, &mj) ==
                    NVML_SUCCESS &&
            mj >= sampler->gpu_baseline_mj) {
            out->gpu_joules =
                    (double)(mj - sampler->gpu_baseline_mj) / 1000.0; /* mJ->J */
            out->gpu_valid = true;
        }
    }
#endif

#ifdef __linux__
    double cpu_uj_total = 0.0;
    bool cpu_any = false;
    for (const rapl_domain_t &d : sampler->rapl_domains) {
        if (!d.baseline_valid)
            continue;
        uint64_t uj = 0;
        if (!read_uint64_file(d.energy_path, &uj))
            continue;
        uint64_t delta;
        if (uj >= d.baseline_uj) {
            delta = uj - d.baseline_uj;
        } else if (d.max_range_uj > 0) {
            /* Counter wrapped: (max - baseline) + current. */
            delta = (d.max_range_uj - d.baseline_uj) + uj;
        } else {
            continue; /* wrapped but range unknown -> cannot correct */
        }
        cpu_uj_total += (double)delta;
        cpu_any = true;
    }
    if (cpu_any) {
        out->cpu_joules = cpu_uj_total / 1.0e6; /* uJ -> J */
        out->cpu_valid = true;
    }
#endif

    return out->gpu_valid || out->cpu_valid;
}

void drava_energy_destroy(drava_energy_sampler_t *sampler)
{
    if (sampler == nullptr)
        return;
#ifdef DRAVA_HAS_NVML
    if (sampler->nvml_ready)
        nvmlShutdown();
#endif
    delete sampler;
}
