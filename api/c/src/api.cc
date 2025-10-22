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
# include <drava/drava.h>

/* the C api uses an ugly global singleton, whatever */
static drava_t drava;

extern "C"
int
drava_init(void)
{
    return drava.init();
}

extern "C"
int
drava_listen(drava_routine_t routine)
{
    return drava.listen(routine);
}

extern "C"
int
drava_deinit(void)
{
    return drava.deinit();
}
