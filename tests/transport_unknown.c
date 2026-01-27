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

START_TEST(test_init_null_transport)
{
    ck_assert_msg(drava_init() == DRAVA_SUCCESS,
                  "drava_init() should use Socket by default");
}
END_TEST

START_TEST(test_init_invalid_transport_fails)
{
    setenv("DRAVA_TRANSPORT", "this_transport_does_not_exist", 1);
    ck_assert_msg(drava_init() != DRAVA_SUCCESS,
                  "invalid transport must fail");
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