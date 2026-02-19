/*******************************************************************************
 * Copyright 2025 UChicago Argonne, LLC.
 * (c.f. AUTHORS, LICENSE)
 *
 * This file is part of the drava project.
 * For more info, see https://github.com/anlsys/drava
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *****************************************************************************/

#include <assert.h>
#include <drava/drava_c.h>
#include <stdio.h>

static void *handler(const drava_frame_batch_t *batch, void *user_data)
{
    (void)user_data;
    if (!batch)
        return NULL;

    printf("C app: count=%u\n", batch->count);
    for (uint32_t i = 0; i < batch->count; ++i) {
        const drava_frame_t *f = &batch->frames[i];
        printf("  bytes=%zu\n", f->data_len);
    }
    return NULL;
}

int main()
{
    assert(drava_init() == DRAVA_SUCCESS);
    assert(drava_register_frame_routine(handler, NULL) == DRAVA_SUCCESS);
    assert(drava_listen() == DRAVA_SUCCESS);
    assert(drava_deinit() == DRAVA_SUCCESS);
    return 0;
}
