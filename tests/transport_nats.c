/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#include <check.h>
#include <drava/drava_c.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


static void *handler(const char *s)
{
    printf("drava(nats): Received %s\n", s ? s : "(null)");
    return NULL;
}

START_TEST(test_nats_init_register_deinit)
{
    const char *use_nats = getenv("USE_NATS");

    if (!use_nats || strcmp(use_nats, "1") != 0) {
        fprintf(stderr, "SKIP: set USE_NATS=1 to run Jetstream check tests\n");
        return;
    }
    setenv("DRAVA_TRANSPORT", "nats", 1);
    ck_assert_int_eq(drava_init(), DRAVA_SUCCESS);
    ck_assert_int_eq(drava_register_routine(handler), DRAVA_SUCCESS);
    ck_assert_int_eq(drava_deinit(), DRAVA_SUCCESS);
}
END_TEST

static Suite *suite_drava_nats(void)
{
    Suite *s = suite_create("drava_nats");
    TCase *tc = tcase_create("core");
    tcase_set_timeout(tc, 5);
    tcase_add_test(tc, test_nats_init_register_deinit);
    suite_add_tcase(s, tc);
    return s;
}

int main(void)
{
    SRunner *sr = srunner_create(suite_drava_nats());
    srunner_run_all(sr, CK_NORMAL);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return failed == 0 ? 0 : 1;
}