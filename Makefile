CC = gcc
CFLAGS = -Wall -Wextra -std=gnu11 -O2 -I cparse -I build
LDFLAGS =

# ASan options
ASAN_FLAGS = -fsanitize=address,undefined -g -O0

SRCS = cparse/main.c cparse/ast.c cparse/json.c cparse/errors.c cparse/directives.c cparse/typedefs.c build/lexer.c build/parser.c
OBJS = $(SRCS:%.c=%.o)
ASAN_OBJS = $(SRCS:%.c=%_asan.o)

.PHONY: all build test asan clean

all: build

build: build/cparse

build/cparse: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

build/lexer.c: cparse/lexer.l build/parser.h
	mkdir -p build
	flex -o $@ $<

build/parser.c build/parser.h: cparse/parser.y
	mkdir -p build
	bison -d -o build/parser.c $<

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

%_asan.o: %.c
	$(CC) $(CFLAGS) $(ASAN_FLAGS) -c $< -o $@

asan: build/cparse-asan

build/cparse-asan: $(ASAN_OBJS)
	$(CC) $(CFLAGS) $(ASAN_FLAGS) $(LDFLAGS) -o $@ $^

test: build
	python3 -m pytest tests/

clean:
	rm -rf build
	find cparse -name "*.o" -type f -delete

$(OBJS) $(ASAN_OBJS): build/parser.h
