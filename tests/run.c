/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

# include <assert.h>
# include <drava/drava_c.h>
# include <stdio.h>

static void *
handler(void)
{
    puts("Handler raised");
    return NULL;
}

int
main(void)
{
    assert(drava_init()                     == DRAVA_SUCCESS);
    assert(drava_register_routine(handler)  == DRAVA_SUCCESS);
    assert(drava_listen()                   == DRAVA_SUCCESS);
    assert(drava_deinit()                   == DRAVA_SUCCESS);
    return 0;
}
