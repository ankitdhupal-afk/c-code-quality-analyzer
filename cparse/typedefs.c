#include "typedefs.h"
#include <string.h>
#include <stdlib.h>

#define MAX_TYPEDEFS 1024

static char *table[MAX_TYPEDEFS];
static int count = 0;

void typedefs_init(void) {
    for (int i = 0; i < count; i++) {
        free(table[i]);
        table[i] = NULL;
    }
    count = 0;
}

void typedefs_add(const char *name) {
    if (count < MAX_TYPEDEFS) {
        if (!typedefs_is_type(name)) {
            table[count++] = strdup(name);
        }
    }
}

int typedefs_is_type(const char *name) {
    for (int i = 0; i < count; i++) {
        if (strcmp(table[i], name) == 0) return 1;
    }
    return 0;
}
