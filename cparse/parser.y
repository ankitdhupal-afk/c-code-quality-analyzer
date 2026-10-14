%code requires {
    #include "ast.h"
    #include "typedefs.h"
}

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ast.h"
#include "errors.h"
#include "typedefs.h"

int yylex(void);
void yyerror(const char *s);
%}

%code {
static Loc to_loc(YYLTYPE l) {
    Loc r = {l.first_line, l.first_column, l.last_line, l.last_column};
    return r;
}

static Loc join_loc(Loc a, Loc b) {
    Loc r = {a.first_line, a.first_column, b.last_line, b.last_column};
    return r;
}

static void register_typedef(DeclSpec *spec, Declarator *decl) {
    if (spec && spec->storage_typedef && decl) {
        Declarator *d = decl;
        while (d && d->kind != DECL_IDENT) d = d->base;
        if (d && d->name) typedefs_add(d->name);
    }
}
}


%locations
%define parse.error verbose

%union {
    char *s;
    Node *node;
    Node **node_list;
    Type *type;
    DeclSpec *decl_spec;
    Declarator *declarator;
}

%token <s> IDENT INT_LITERAL FLOAT_LITERAL CHAR_LITERAL STRING_LITERAL TYPE_NAME
%token PTR_OP INC_OP DEC_OP LEFT_OP RIGHT_OP LE_OP GE_OP EQ_OP NE_OP
%token AND_OP OR_OP MUL_ASSIGN DIV_ASSIGN MOD_ASSIGN ADD_ASSIGN
%token SUB_ASSIGN LEFT_ASSIGN RIGHT_ASSIGN AND_ASSIGN
%token XOR_ASSIGN OR_ASSIGN
%token VOID CHAR SHORT INT LONG FLOAT DOUBLE SIGNED UNSIGNED CONST STATIC EXTERN STRUCT TYPEDEF
%token IF ELSE WHILE DO FOR SWITCH CASE DEFAULT BREAK CONTINUE RETURN SIZEOF

%type <node> external_declaration function_definition declaration
%type <node> statement compound_statement expression_statement selection_statement
%type <node> iteration_statement jump_statement block_item
%type <node_list> block_item_list init_declarator_list
%type <node_list> argument_expression_list initializer_list
%type <node> init_declarator initializer expr assignment_expression
%type <node> conditional_expression logical_or_expression logical_and_expression
%type <node> inclusive_or_expression exclusive_or_expression and_expression
%type <node> equality_expression relational_expression shift_expression
%type <node> additive_expression multiplicative_expression cast_expression
%type <node> unary_expression postfix_expression primary_expression constant_expr constant_expr_opt
%type <type> type_name struct_specifier
%type <node> struct_declaration struct_declarator
%type <node_list> struct_declaration_list struct_declarator_list
%type <decl_spec> declaration_specifiers specifier_qualifier_list
%type <declarator> declarator direct_declarator pointer
%type <node> parameter_declaration
%type <node_list> parameter_list parameter_type_list

// Precedence decisions:
// We resolve the "dangling else" shift/reduce conflict using %nonassoc precedence.
// We declare LOWER_THAN_ELSE with lower precedence than ELSE.
// By default, the `if (expr) stmt` rule is assigned LOWER_THAN_ELSE precedence via `%prec LOWER_THAN_ELSE`.
// When Bison sees an `ELSE` token, it compares the precedence of the shift (ELSE) with the reduce (the IF rule).
// Since ELSE has higher precedence, Bison shifts the ELSE token and associates it with the closest IF.
// This successfully eliminates the shift/reduce conflict and behaves identically to standard C.
%nonassoc LOWER_THAN_ELSE
%nonassoc ELSE

%%

translation_unit:
    /* empty */ { }
    | translation_unit external_declaration { if ($2) add_top_level($2); }
    | translation_unit error ';' { }
    ;

external_declaration:
    function_definition { $$ = $1; }
    | declaration { $$ = $1; }
    ;

function_definition:
    declaration_specifiers declarator compound_statement {
        Node *n = make_node(ND_FUNCTION_DEF, join_loc(to_loc(@1), to_loc(@3)));
        Node **params = NULL;
        const char *name = NULL;
        n->return_type = build_type($1, $2, &name, &params, 1);
        n->name = name;
        n->params = params;
        n->body = $3;
        if ($1->storage_static) n->storage = "static";
        else if ($1->storage_extern) n->storage = "extern";
        $$ = n;
    }
    ;

declaration:
    declaration_specifiers ';' {
        Node *n = make_node(ND_DECL_STMT, join_loc(to_loc(@1), to_loc(@2)));
        // If it's a struct def without vars:
        if ($1->struct_type && $1->struct_type->name && $1->struct_type->fields) {
            Node *sdef = make_node(ND_STRUCT_DEF, to_loc(@1));
            sdef->name = $1->struct_type->name;
            sdef->fields = $1->struct_type->fields;
            n->items = node_list_append(NULL, sdef);
        } else {
            n->items = NULL;
        }
        $$ = n;
    }
    | declaration_specifiers init_declarator_list ';' {
        Node *n = make_node(ND_DECL_STMT, join_loc(to_loc(@1), to_loc(@3)));
        n->items = NULL;
        for (int i=0; $2 && $2[i]; i++) {
            Node *id = $2[i]; // init_declarator returns an ND_VAR_DECL or ND_TYPEDEF_DECL
            // actually $2 is list of pair of (declarator, initializer) we can pack in dummy nodes, or just VarDecls.
            // Let's make init_declarator return a VarDecl or TypedefDecl directly using $1!
            // Wait, we can't pass $1 down to init_declarator easily without mid-rule actions.
            // Let's use mid-rule actions or construct VarDecls here.
            // If $2 contains dummy nodes: kind=ND_VAR_DECL, init=initializer, operand=declarator(stored as Node*)?
            // Safer: use a mid-rule action to pass $1? No, just iterate and build correctly.
            // Let init_declarator return a dummy ND_VAR_DECL where `expr` = (Node*)declarator, `init` = initializer.
            Declarator *decl = (Declarator*)id->expr;
            if ($1->storage_typedef) {
                register_typedef($1, decl);
                Node *td = make_node(ND_TYPEDEF_DECL, id->loc);
                const char *name = NULL;
                td->type = build_type($1, decl, &name, NULL, 0);
                td->name = name;
                n->items = node_list_append(n->items, td);
            } else {
                Node *vd = build_var_decl($1, decl, id->init, 0, id->loc);
                n->items = node_list_append(n->items, vd);
            }
        }
        $$ = n;
    }
    ;

declaration_specifiers:
    VOID { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_void = 1; }
    | CHAR { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_char = 1; }
    | SHORT { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_short = 1; }
    | INT { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_int = 1; }
    | LONG { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_long = 1; }
    | FLOAT { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_float = 1; }
    | DOUBLE { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_double = 1; }
    | SIGNED { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_signed = 1; }
    | UNSIGNED { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_unsigned = 1; }
    | CONST { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_const = 1; }
    | STATIC { $$ = arena_alloc(sizeof(DeclSpec)); $$->storage_static = 1; }
    | EXTERN { $$ = arena_alloc(sizeof(DeclSpec)); $$->storage_extern = 1; }
    | TYPEDEF { $$ = arena_alloc(sizeof(DeclSpec)); $$->storage_typedef = 1; }
    | TYPE_NAME { $$ = arena_alloc(sizeof(DeclSpec)); $$->typedef_name = $1; }
    | struct_specifier { $$ = arena_alloc(sizeof(DeclSpec)); $$->struct_type = $1; }
    | declaration_specifiers VOID { $$ = $1; $$->has_void = 1; }
    | declaration_specifiers CHAR { $$ = $1; $$->has_char = 1; }
    | declaration_specifiers SHORT { $$ = $1; $$->has_short = 1; }
    | declaration_specifiers INT { $$ = $1; $$->has_int = 1; }
    | declaration_specifiers LONG { $$ = $1; if($$->has_long) $$->has_long_long=1; else $$->has_long=1; }
    | declaration_specifiers FLOAT { $$ = $1; $$->has_float = 1; }
    | declaration_specifiers DOUBLE { $$ = $1; $$->has_double = 1; }
    | declaration_specifiers SIGNED { $$ = $1; $$->has_signed = 1; }
    | declaration_specifiers UNSIGNED { $$ = $1; $$->has_unsigned = 1; }
    | declaration_specifiers CONST { $$ = $1; $$->has_const = 1; }
    | declaration_specifiers STATIC { $$ = $1; $$->storage_static = 1; }
    | declaration_specifiers EXTERN { $$ = $1; $$->storage_extern = 1; }
    | declaration_specifiers TYPEDEF { $$ = $1; $$->storage_typedef = 1; }
    | declaration_specifiers TYPE_NAME { $$ = $1; $$->typedef_name = $2; }
    | declaration_specifiers struct_specifier { $$ = $1; $$->struct_type = $2; }
    ;

init_declarator_list:
    init_declarator { $$ = node_list_append(NULL, $1); }
    | init_declarator_list ',' init_declarator { $$ = node_list_append($1, $3); }
    ;

init_declarator:
    declarator { 
        $$ = make_node(ND_VAR_DECL, to_loc(@1));
        $$->expr = (Node*)$1; 
        $$->init = NULL;
    }
    | declarator '=' initializer {
        $$ = make_node(ND_VAR_DECL, join_loc(to_loc(@1), to_loc(@3)));
        $$->expr = (Node*)$1;
        $$->init = $3;
    }
    ;

struct_specifier:
    STRUCT IDENT '{' struct_declaration_list '}' {
        Type *t = make_type(TK_STRUCT);
        t->name = $2;
        t->fields = $4;
        $$ = t;
    }
    | STRUCT '{' struct_declaration_list '}' {
        Type *t = make_type(TK_STRUCT);
        t->name = NULL;
        t->fields = $3;
        $$ = t;
    }
    | STRUCT IDENT {
        Type *t = make_type(TK_STRUCT);
        t->name = $2;
        t->fields = NULL;
        $$ = t;
    }
    ;

struct_declaration_list:
    struct_declaration { $$ = node_list_append(NULL, $1); }
    | struct_declaration_list struct_declaration { $$ = node_list_append($1, $2); }
    ;

struct_declaration:
    specifier_qualifier_list struct_declarator_list ';' {
        // We'll just return a dummy node wrapping the list of VarDecls. 
        // Wait, struct_declaration_list needs a flat list of VarDecls.
        // Let's just assume one declarator for simplicity, or we can flatten it.
        // To flatten, struct_declaration_list can just append all items.
        Node *n = make_node(ND_DECL_STMT, join_loc(to_loc(@1), to_loc(@3)));
        n->items = NULL;
        for (int i=0; $2 && $2[i]; i++) {
            Node *id = $2[i]; // dummy from struct_declarator
            Declarator *decl = (Declarator*)id->expr;
            Node *vd = build_var_decl($1, decl, NULL, 0, id->loc);
            n->items = node_list_append(n->items, vd);
        }
        $$ = n; // Return the DeclStmt.
    }
    ;

specifier_qualifier_list:
    VOID { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_void = 1; }
    | CHAR { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_char = 1; }
    | SHORT { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_short = 1; }
    | INT { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_int = 1; }
    | LONG { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_long = 1; }
    | FLOAT { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_float = 1; }
    | DOUBLE { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_double = 1; }
    | SIGNED { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_signed = 1; }
    | UNSIGNED { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_unsigned = 1; }
    | CONST { $$ = arena_alloc(sizeof(DeclSpec)); $$->has_const = 1; }
    | TYPE_NAME { $$ = arena_alloc(sizeof(DeclSpec)); $$->typedef_name = $1; }
    | struct_specifier { $$ = arena_alloc(sizeof(DeclSpec)); $$->struct_type = $1; }
    | specifier_qualifier_list VOID { $$ = $1; $$->has_void = 1; }
    | specifier_qualifier_list CHAR { $$ = $1; $$->has_char = 1; }
    | specifier_qualifier_list SHORT { $$ = $1; $$->has_short = 1; }
    | specifier_qualifier_list INT { $$ = $1; $$->has_int = 1; }
    | specifier_qualifier_list LONG { $$ = $1; if($$->has_long) $$->has_long_long=1; else $$->has_long=1; }
    | specifier_qualifier_list FLOAT { $$ = $1; $$->has_float = 1; }
    | specifier_qualifier_list DOUBLE { $$ = $1; $$->has_double = 1; }
    | specifier_qualifier_list SIGNED { $$ = $1; $$->has_signed = 1; }
    | specifier_qualifier_list UNSIGNED { $$ = $1; $$->has_unsigned = 1; }
    | specifier_qualifier_list CONST { $$ = $1; $$->has_const = 1; }
    | specifier_qualifier_list TYPE_NAME { $$ = $1; $$->typedef_name = $2; }
    | specifier_qualifier_list struct_specifier { $$ = $1; $$->struct_type = $2; }
    ;

struct_declarator_list:
    struct_declarator { $$ = node_list_append(NULL, $1); }
    | struct_declarator_list ',' struct_declarator { $$ = node_list_append($1, $3); }
    ;

struct_declarator:
    declarator { 
        $$ = make_node(ND_VAR_DECL, to_loc(@1));
        $$->expr = (Node*)$1;
    }
    ;

declarator:
    pointer direct_declarator {
        Declarator *p = $1;
        while (p->base != NULL) p = p->base;
        p->base = $2;
        $$ = $1;
    }
    | direct_declarator { $$ = $1; }
    ;

direct_declarator:
    IDENT {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_IDENT;
        d->name = $1;
        d->loc = to_loc(@1);
        $$ = d;
    }
    | '(' declarator ')' { $$ = $2; }
    | direct_declarator '[' constant_expr_opt ']' {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_ARRAY;
        d->base = $1;
        d->array_size = $3;
        d->loc = join_loc(to_loc(@1), to_loc(@4));
        $$ = d;
    }
    | direct_declarator '(' parameter_type_list ')' {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_FUNC;
        d->base = $1;
        d->func_params = $3;
        d->loc = join_loc(to_loc(@1), to_loc(@4));
        $$ = d;
    }
    | direct_declarator '(' ')' {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_FUNC;
        d->base = $1;
        d->func_params = NULL;
        d->loc = join_loc(to_loc(@1), to_loc(@3));
        $$ = d;
    }
    ;

pointer:
    '*' {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_POINTER;
        d->loc = to_loc(@1);
        $$ = d;
    }
    | '*' CONST {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_POINTER;
        d->is_const = 1;
        d->loc = join_loc(to_loc(@1), to_loc(@2));
        $$ = d;
    }
    | '*' pointer {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_POINTER;
        d->base = $2;
        d->loc = join_loc(to_loc(@1), to_loc(@2));
        $$ = d;
    }
    | '*' CONST pointer {
        Declarator *d = arena_alloc(sizeof(Declarator));
        d->kind = DECL_POINTER;
        d->is_const = 1;
        d->base = $3;
        d->loc = join_loc(to_loc(@1), to_loc(@3));
        $$ = d;
    }
    ;

parameter_type_list:
    parameter_list { $$ = $1; }
    ;

parameter_list:
    parameter_declaration { $$ = node_list_append(NULL, $1); }
    | parameter_list ',' parameter_declaration { $$ = node_list_append($1, $3); }
    ;

parameter_declaration:
    declaration_specifiers declarator {
        Node *n = make_node(ND_PARAM, join_loc(to_loc(@1), to_loc(@2)));
        const char *name = NULL;
        n->type = build_type($1, $2, &name, NULL, 0);
        n->name = name;
        $$ = n;
    }
    | declaration_specifiers {
        Node *n = make_node(ND_PARAM, to_loc(@1));
        n->type = build_type($1, NULL, NULL, NULL, 0);
        n->name = NULL;
        $$ = n;
    }
    ;

type_name:
    specifier_qualifier_list { $$ = build_type($1, NULL, NULL, NULL, 0); }
    | specifier_qualifier_list pointer {
        // Need to wrap pointer with base type
        Declarator *p = $2;
        $$ = build_type($1, p, NULL, NULL, 0);
    }
    ;

initializer:
    assignment_expression { $$ = $1; }
    | '{' initializer_list '}' {
        Node *n = make_node(ND_INIT_LIST, join_loc(to_loc(@1), to_loc(@3)));
        n->items = $2;
        $$ = n;
    }
    | '{' initializer_list ',' '}' {
        Node *n = make_node(ND_INIT_LIST, join_loc(to_loc(@1), to_loc(@4)));
        n->items = $2;
        $$ = n;
    }
    ;

initializer_list:
    initializer { $$ = node_list_append(NULL, $1); }
    | initializer_list ',' initializer { $$ = node_list_append($1, $3); }
    ;

statement:
    compound_statement { $$ = $1; }
    | expression_statement { $$ = $1; }
    | selection_statement { $$ = $1; }
    | iteration_statement { $$ = $1; }
    | jump_statement { $$ = $1; }
    | error ';' { $$ = NULL; }
    ;

compound_statement:
    '{' '}' {
        Node *n = make_node(ND_BLOCK, join_loc(to_loc(@1), to_loc(@2)));
        n->items = NULL;
        $$ = n;
    }
    | '{' block_item_list '}' {
        Node *n = make_node(ND_BLOCK, join_loc(to_loc(@1), to_loc(@3)));
        n->items = $2;
        $$ = n;
    }
    ;

block_item_list:
    block_item { $$ = $1 ? node_list_append(NULL, $1) : NULL; }
    | block_item_list block_item { 
        if ($2) $$ = node_list_append($1, $2);
        else $$ = $1;
    }
    ;

block_item:
    declaration { $$ = $1; }
    | statement { $$ = $1; }
    | CASE constant_expr ':' { 
        Node *n = make_node(ND_CASE, join_loc(to_loc(@1), to_loc(@3)));
        n->value = $2;
        $$ = n;
    }
    | DEFAULT ':' {
        Node *n = make_node(ND_DEFAULT, join_loc(to_loc(@1), to_loc(@2)));
        $$ = n;
    }
    ;

expression_statement:
    ';' { $$ = make_node(ND_EMPTY_STMT, to_loc(@1)); }
    | expr ';' {
        Node *n = make_node(ND_EXPR_STMT, join_loc(to_loc(@1), to_loc(@2)));
        n->expr = $1;
        $$ = n;
    }
    ;

selection_statement:
    IF '(' expr ')' statement %prec LOWER_THAN_ELSE {
        Node *n = make_node(ND_IF, join_loc(to_loc(@1), to_loc(@5)));
        n->cond = $3;
        n->then_branch = $5;
        n->else_branch = NULL;
        $$ = n;
    }
    | IF '(' expr ')' statement ELSE statement {
        Node *n = make_node(ND_IF, join_loc(to_loc(@1), to_loc(@7)));
        n->cond = $3;
        n->then_branch = $5;
        n->else_branch = $7;
        $$ = n;
    }
    | SWITCH '(' expr ')' statement {
        Node *n = make_node(ND_SWITCH, join_loc(to_loc(@1), to_loc(@5)));
        n->expr = $3;
        n->body = $5;
        $$ = n;
    }
    ;

iteration_statement:
    WHILE '(' expr ')' statement {
        Node *n = make_node(ND_WHILE, join_loc(to_loc(@1), to_loc(@5)));
        n->cond = $3;
        n->body = $5;
        $$ = n;
    }
    | DO statement WHILE '(' expr ')' ';' {
        Node *n = make_node(ND_DO_WHILE, join_loc(to_loc(@1), to_loc(@7)));
        n->body = $2;
        n->cond = $5;
        $$ = n;
    }
    | FOR '(' expression_statement expression_statement ')' statement {
        Node *n = make_node(ND_FOR, join_loc(to_loc(@1), to_loc(@6)));
        n->init = $3;
        n->cond = $4->kind == ND_EXPR_STMT ? $4->expr : NULL;
        n->step = NULL;
        n->body = $6;
        $$ = n;
    }
    | FOR '(' expression_statement expression_statement expr ')' statement {
        Node *n = make_node(ND_FOR, join_loc(to_loc(@1), to_loc(@7)));
        n->init = $3;
        n->cond = $4->kind == ND_EXPR_STMT ? $4->expr : NULL;
        n->step = $5;
        n->body = $7;
        $$ = n;
    }
    | FOR '(' declaration expression_statement ')' statement {
        Node *n = make_node(ND_FOR, join_loc(to_loc(@1), to_loc(@6)));
        n->init = $3;
        n->cond = $4->kind == ND_EXPR_STMT ? $4->expr : NULL;
        n->step = NULL;
        n->body = $6;
        $$ = n;
    }
    | FOR '(' declaration expression_statement expr ')' statement {
        Node *n = make_node(ND_FOR, join_loc(to_loc(@1), to_loc(@7)));
        n->init = $3;
        n->cond = $4->kind == ND_EXPR_STMT ? $4->expr : NULL;
        n->step = $5;
        n->body = $7;
        $$ = n;
    }
    ;

jump_statement:
    BREAK ';' { $$ = make_node(ND_BREAK, join_loc(to_loc(@1), to_loc(@2))); }
    | CONTINUE ';' { $$ = make_node(ND_CONTINUE, join_loc(to_loc(@1), to_loc(@2))); }
    | RETURN ';' {
        Node *n = make_node(ND_RETURN, join_loc(to_loc(@1), to_loc(@2)));
        n->value = NULL;
        $$ = n;
    }
    | RETURN expr ';' {
        Node *n = make_node(ND_RETURN, join_loc(to_loc(@1), to_loc(@3)));
        n->value = $2;
        $$ = n;
    }
    ;

expr:
    assignment_expression { $$ = $1; }
    | expr ',' assignment_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = ",";
        n->left = $1;
        n->right = $3;
        $$ = n;
    }
    ;

assignment_expression:
    conditional_expression { $$ = $1; }
    | unary_expression '=' assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression MUL_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "*="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression DIV_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "/="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression MOD_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "%="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression ADD_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "+="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression SUB_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "-="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression LEFT_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "<<="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression RIGHT_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = ">>="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression AND_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "&="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression XOR_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "^="; n->target = $1; n->value = $3; $$ = n;
    }
    | unary_expression OR_ASSIGN assignment_expression {
        Node *n = make_node(ND_ASSIGN, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "|="; n->target = $1; n->value = $3; $$ = n;
    }
    ;

conditional_expression:
    logical_or_expression { $$ = $1; }
    | logical_or_expression '?' expr ':' conditional_expression {
        Node *n = make_node(ND_TERNARY, join_loc(to_loc(@1), to_loc(@5)));
        n->cond = $1;
        n->then_branch = $3;
        n->else_branch = $5;
        $$ = n;
    }
    ;

constant_expr_opt:
    /* empty */ { $$ = NULL; }
    | constant_expr { $$ = $1; }
    ;

constant_expr:
    conditional_expression { $$ = $1; }
    ;

logical_or_expression:
    logical_and_expression { $$ = $1; }
    | logical_or_expression OR_OP logical_and_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "||"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

logical_and_expression:
    inclusive_or_expression { $$ = $1; }
    | logical_and_expression AND_OP inclusive_or_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "&&"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

inclusive_or_expression:
    exclusive_or_expression { $$ = $1; }
    | inclusive_or_expression '|' exclusive_or_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "|"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

exclusive_or_expression:
    and_expression { $$ = $1; }
    | exclusive_or_expression '^' and_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "^"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

and_expression:
    equality_expression { $$ = $1; }
    | and_expression '&' equality_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "&"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

equality_expression:
    relational_expression { $$ = $1; }
    | equality_expression EQ_OP relational_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "=="; n->left = $1; n->right = $3; $$ = n;
    }
    | equality_expression NE_OP relational_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "!="; n->left = $1; n->right = $3; $$ = n;
    }
    ;

relational_expression:
    shift_expression { $$ = $1; }
    | relational_expression '<' shift_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "<"; n->left = $1; n->right = $3; $$ = n;
    }
    | relational_expression '>' shift_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = ">"; n->left = $1; n->right = $3; $$ = n;
    }
    | relational_expression LE_OP shift_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "<="; n->left = $1; n->right = $3; $$ = n;
    }
    | relational_expression GE_OP shift_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = ">="; n->left = $1; n->right = $3; $$ = n;
    }
    ;

shift_expression:
    additive_expression { $$ = $1; }
    | shift_expression LEFT_OP additive_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "<<"; n->left = $1; n->right = $3; $$ = n;
    }
    | shift_expression RIGHT_OP additive_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = ">>"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

additive_expression:
    multiplicative_expression { $$ = $1; }
    | additive_expression '+' multiplicative_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "+"; n->left = $1; n->right = $3; $$ = n;
    }
    | additive_expression '-' multiplicative_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "-"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

multiplicative_expression:
    cast_expression { $$ = $1; }
    | multiplicative_expression '*' cast_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "*"; n->left = $1; n->right = $3; $$ = n;
    }
    | multiplicative_expression '/' cast_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "/"; n->left = $1; n->right = $3; $$ = n;
    }
    | multiplicative_expression '%' cast_expression {
        Node *n = make_node(ND_BINARY, join_loc(to_loc(@1), to_loc(@3)));
        n->op = "%"; n->left = $1; n->right = $3; $$ = n;
    }
    ;

cast_expression:
    unary_expression { $$ = $1; }
    | '(' type_name ')' cast_expression {
        Node *n = make_node(ND_CAST, join_loc(to_loc(@1), to_loc(@4)));
        n->type = $2; n->operand = $4; $$ = n;
    }
    ;

unary_expression:
    postfix_expression { $$ = $1; }
    | INC_OP unary_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "++"; n->operand = $2; $$ = n;
    }
    | DEC_OP unary_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "--"; n->operand = $2; $$ = n;
    }
    | '&' cast_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "&"; n->operand = $2; $$ = n;
    }
    | '*' cast_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "*"; n->operand = $2; $$ = n;
    }
    | '+' cast_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "+"; n->operand = $2; $$ = n;
    }
    | '-' cast_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "-"; n->operand = $2; $$ = n;
    }
    | '~' cast_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "~"; n->operand = $2; $$ = n;
    }
    | '!' cast_expression {
        Node *n = make_node(ND_UNARY, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "!"; n->operand = $2; $$ = n;
    }
    | SIZEOF unary_expression {
        Node *n = make_node(ND_SIZEOF, join_loc(to_loc(@1), to_loc(@2)));
        n->operand = $2; n->type = NULL; $$ = n;
    }
    | SIZEOF '(' type_name ')' {
        Node *n = make_node(ND_SIZEOF, join_loc(to_loc(@1), to_loc(@4)));
        n->operand = NULL; n->type = $3; $$ = n;
    }
    ;

postfix_expression:
    primary_expression { $$ = $1; }
    | postfix_expression '[' expr ']' {
        Node *n = make_node(ND_INDEX, join_loc(to_loc(@1), to_loc(@4)));
        n->base = $1; n->index = $3; $$ = n;
    }
    | postfix_expression '(' ')' {
        Node *n = make_node(ND_CALL, join_loc(to_loc(@1), to_loc(@3)));
        n->callee = $1; n->items = NULL; $$ = n;
    }
    | postfix_expression '(' argument_expression_list ')' {
        Node *n = make_node(ND_CALL, join_loc(to_loc(@1), to_loc(@4)));
        n->callee = $1; n->items = $3; $$ = n;
    }
    | postfix_expression '.' IDENT {
        Node *n = make_node(ND_MEMBER, join_loc(to_loc(@1), to_loc(@3)));
        n->base = $1; n->name = $3; n->arrow = 0; $$ = n;
    }
    | postfix_expression PTR_OP IDENT {
        Node *n = make_node(ND_MEMBER, join_loc(to_loc(@1), to_loc(@3)));
        n->base = $1; n->name = $3; n->arrow = 1; $$ = n;
    }
    | postfix_expression INC_OP {
        Node *n = make_node(ND_POSTFIX, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "++"; n->operand = $1; $$ = n;
    }
    | postfix_expression DEC_OP {
        Node *n = make_node(ND_POSTFIX, join_loc(to_loc(@1), to_loc(@2)));
        n->op = "--"; n->operand = $1; $$ = n;
    }
    ;

primary_expression:
    IDENT {
        Node *n = make_node(ND_IDENTIFIER, to_loc(@1));
        n->name = $1; $$ = n;
    }
    | INT_LITERAL {
        Node *n = make_node(ND_INT_LITERAL, to_loc(@1));
        n->text = $1; $$ = n;
    }
    | FLOAT_LITERAL {
        Node *n = make_node(ND_FLOAT_LITERAL, to_loc(@1));
        n->text = $1; $$ = n;
    }
    | CHAR_LITERAL {
        Node *n = make_node(ND_CHAR_LITERAL, to_loc(@1));
        n->text = $1; $$ = n;
    }
    | STRING_LITERAL {
        Node *n = make_node(ND_STRING_LITERAL, to_loc(@1));
        n->text = $1; $$ = n;
    }
    | '(' expr ')' { $$ = $2; }
    ;

argument_expression_list:
    assignment_expression { $$ = node_list_append(NULL, $1); }
    | argument_expression_list ',' assignment_expression { $$ = node_list_append($1, $3); }
    ;

%%

void yyerror(const char *s) {
    report_error(yylloc.first_line, yylloc.first_column, s);
}
