#include "errors.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ERRORS 20

typedef struct {
    int line;
    int col;
    char *message;
} Error;

static Error errors[MAX_ERRORS];
static int error_count = 0;

void report_error(int line, int col, const char *msg) {
    if (error_count >= MAX_ERRORS) return;
    errors[error_count].line = line;
    errors[error_count].col = col;
    errors[error_count].message = strdup(msg);
    error_count++;
}

void print_errors_json(void) {
    printf("  \"errors\": [");
    for (int i = 0; i < error_count; i++) {
        printf("{\"line\": %d, \"col\": %d, \"message\": \"%s\"}%s", 
               errors[i].line, errors[i].col, errors[i].message,
               (i < error_count - 1) ? ", " : "");
    }
    printf("],\n");
}

int get_error_count(void) {
    return error_count;
}
