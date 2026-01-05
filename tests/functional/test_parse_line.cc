#include <check.h>
#include <cstring>

// Compile prod code into this test binary
#include "../../src/drava.cc"

static int g_called = 0;
static const char *g_last = nullptr;

static void routine_spy(const char *s)
{
    g_called++;
    g_last = s;
}

START_TEST(test_parse_line_calls_routine_when_set)
{
    drava_t d;
    d.routine = routine_spy;

    g_called = 0;
    g_last = nullptr;

    parse_line(&d, (device_global_id_t)1, std::string("hello"));

    ck_assert_int_eq(g_called, 1);
    ck_assert_ptr_nonnull(g_last);
    ck_assert_str_eq(g_last, "hello");
}
END_TEST

START_TEST(test_parse_line_noop_when_routine_null)
{
    drava_t d;
    d.routine = nullptr;

    g_called = 0;
    g_last = nullptr;

    // Should not crash, should not call anything
    parse_line(&d, (device_global_id_t)0, std::string("ignored"));

    ck_assert_int_eq(g_called, 0);
    ck_assert_ptr_null(g_last);
}
END_TEST

START_TEST(test_parse_line_noop_when_drava_null)
{
    g_called = 0;
    g_last = nullptr;

    // Should not crash
    parse_line(nullptr, (device_global_id_t)0, std::string("ignored"));

    ck_assert_int_eq(g_called, 0);
    ck_assert_ptr_null(g_last);
}
END_TEST

static Suite *parse_line_suite(void)
{
    Suite *s = suite_create("parse_line");
    TCase *tc = tcase_create("core");

    tcase_add_test(tc, test_parse_line_calls_routine_when_set);
    tcase_add_test(tc, test_parse_line_noop_when_routine_null);
    tcase_add_test(tc, test_parse_line_noop_when_drava_null);

    suite_add_tcase(s, tc);
    return s;
}

int main(void)
{
    Suite *s = parse_line_suite();
    SRunner *sr = srunner_create(s);

    srunner_run_all(sr, CK_NORMAL);

    int nf = srunner_ntests_failed(sr);
    srunner_free(sr);
    return (nf == 0) ? 0 : 1;
}
