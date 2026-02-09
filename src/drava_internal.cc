#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <drava/drava.h>

static const char *env_get(const char *k)
{
    const char *v = getenv(k);
    return (v && v[0] != '\0') ? v : nullptr;
}

int drava_parse_transport_from_env(drava_transport_t *out)
{
    if (!out)
        return DRAVA_EINVAL;

    const char *t = env_get("DRAVA_TRANSPORT");
    if (!t || strcmp(t, "auto") == 0) {
        *out = DRAVA_TRANSPORT_SOCKET;
        return DRAVA_SUCCESS;
    }

    if (strcmp(t, "socket") == 0) {
        *out = DRAVA_TRANSPORT_SOCKET;
        return DRAVA_SUCCESS;
    }

    if (strcmp(t, "nats") == 0) {
#ifdef DRAVA_HAS_NATS
        *out = DRAVA_TRANSPORT_NATS;
        return DRAVA_SUCCESS;
#else
        return DRAVA_ENOTSUP;
#endif
    }

    return DRAVA_EINVAL;
}

int drava_env_get_int_default(const char *key, int default_value)
{
    const char *s = env_get(key);
    if (!s)
        return default_value;
    errno = 0;
    char *end = nullptr;
    long v = std::strtol(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0')
        return default_value;
    return (int)v;
}

void drava_parse_line(drava_t *drava,
                device_global_id_t device_global_id,
                const std::string &line)
{
    (void)device_global_id;
    if (drava && drava->routine) {
        drava->routine(line.c_str());
    }
}
