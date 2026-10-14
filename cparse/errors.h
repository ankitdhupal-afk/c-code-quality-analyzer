#ifndef ERRORS_H
#define ERRORS_H

void report_error(int line, int col, const char *msg);
void print_errors_json(void);
int get_error_count(void);

#endif
