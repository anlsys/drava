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

static void set_socket_stage_config(void)
{
    setenv("DRAVA_STAGE_CONFIG", DRAVA_TEST_SRCDIR "/transport_socket.yaml", 1);
    setenv("DRAVA_STAGE_NAME", "test_stage", 1);
    unsetenv("DRAVA_TRANSPORT");
}

static void set_invalid_stage_config(void)
{
    setenv("DRAVA_STAGE_CONFIG", DRAVA_TEST_SRCDIR "/transport_invalid.yaml",
           1);
    setenv("DRAVA_STAGE_NAME", "test_stage", 1);
    unsetenv("DRAVA_TRANSPORT");
}

START_TEST(test_init_null_transport)
{
    set_socket_stage_config();
    ck_assert_msg(drava_init() == DRAVA_SUCCESS,
                  "drava_init() should use Socket by default");
}
END_TEST

START_TEST(test_init_invalid_transport_fails)
{
    set_invalid_stage_config();
    ck_assert_msg(drava_init() == DRAVA_SUCCESS,
                  "invalid YAML transport should fall back to socket");
}
END_TEST

static Suite *suite_api_errors(void)
{
    Suite *s = suite_create("drava_api_errors");
    TCase *tc = tcase_create("core");
    tcase_add_test(tc, test_init_null_transport);
    tcase_add_test(tc, test_init_invalid_transport_fails);
    suite_add_tcase(s, tc);
    return s;
}

int main(void)
{
    SRunner *sr = srunner_create(suite_api_errors());
    srunner_run_all(sr, CK_NORMAL);
    int failed = srunner_ntests_failed(sr);
    srunner_free(sr);
    return failed == 0 ? 0 : 1;
}
