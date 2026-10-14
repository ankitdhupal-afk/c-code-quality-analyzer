#ifndef AST_H
#define AST_H

#include <stddef.h>

typedef struct {
    int first_line;
    int first_column;
    int last_line;
    int last_column;
} Loc;

typedef struct Type Type;
typedef struct Node Node;

typedef enum {
    TK_BASE, TK_POINTER, TK_ARRAY, TK_STRUCT, TK_TYPEDEF, TK_FUNCTION
} TypeKind;

struct Type {
    TypeKind tk;
    const char *name;
    int is_const;
    Type *to;
    Node *size;
    Node **fields; 
    Type *returns;
    Node **params;
};

typedef enum {
    ND_FUNCTION_DEF, ND_PROTOTYPE, ND_VAR_DECL, ND_TYPEDEF_DECL, ND_STRUCT_DEF, ND_PARAM,
    ND_BLOCK, ND_DECL_STMT, ND_EXPR_STMT, ND_EMPTY_STMT, ND_IF, ND_WHILE, ND_DO_WHILE,
    ND_FOR, ND_SWITCH, ND_CASE, ND_DEFAULT, ND_BREAK, ND_CONTINUE, ND_RETURN,
    ND_IDENTIFIER, ND_INT_LITERAL, ND_FLOAT_LITERAL, ND_CHAR_LITERAL, ND_STRING_LITERAL,
    ND_UNARY, ND_POSTFIX, ND_BINARY, ND_ASSIGN, ND_TERNARY, ND_CALL, ND_INDEX,
    ND_MEMBER, ND_CAST, ND_SIZEOF, ND_INIT_LIST
} NodeKind;

struct Node {
    NodeKind kind;
    Loc loc;
    
    const char *name; 
    const char *text; 
    const char *storage; 
    Type *type; 
    
    Node *init; 
    int is_global; 
    int arrow; 
    const char *op; 
    
    Node **items; 
    Node *expr; 
    Node *cond; 
    Node *then_branch; 
    Node *else_branch; 
    Node *body; 
    Node *step; 
    Node *left; 
    Node *right; 
    Node *target; 
    Node *value; 
    Node *operand; 
    Node *callee; 
    Node *base; 
    Node *index; 
    
    Type *return_type; 
    Node **params; 
    Node **fields; 
};

void *arena_alloc(size_t size);
char *arena_strdup(const char *s);
void arena_free_all(void);

Node **node_list_make(void);
Node **node_list_append(Node **list, Node *node);
int node_list_len(Node **list);

Type **type_list_make(void);
Type **type_list_append(Type **list, Type *type);

Node *make_node(NodeKind kind, Loc loc);
Type *make_type(TypeKind tk);

void add_top_level(Node *node);
Node **get_top_level(void);

// Declarator structures for parser
typedef struct {
    int has_void, has_char, has_short, has_int, has_long, has_long_long;
    int has_float, has_double, has_signed, has_unsigned;
    int has_const;
    int storage_static, storage_extern, storage_typedef;
    const char *typedef_name;
    Type *struct_type;
} DeclSpec;

typedef struct Declarator {
    enum { DECL_IDENT, DECL_POINTER, DECL_ARRAY, DECL_FUNC } kind;
    const char *name;
    struct Declarator *base;
    int is_const;
    Node *array_size;
    Node **func_params;
    Loc loc;
} Declarator;

Type *build_type(DeclSpec *spec, Declarator *decl, const char **out_name, Node ***out_params, int strip_func);
Node *build_var_decl(DeclSpec *spec, Declarator *decl, Node *init, int is_global, Loc loc);

#endif
