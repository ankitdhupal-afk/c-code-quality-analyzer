#ifndef DIRECTIVES_H
#define DIRECTIVES_H

void add_include(const char *text, int line, int col);
void add_define(const char *name, const char *value, int line, int col);
void print_directives_json(void);

#endif
