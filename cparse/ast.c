#include "ast.h"
#include <stdlib.h>
#include <string.h>

#define ARENA_CHUNK 65536

typedef struct ArenaChunk {
    char data[ARENA_CHUNK];
    size_t offset;
    struct ArenaChunk *next;
} ArenaChunk;

static ArenaChunk *arena_head = NULL;

void *arena_alloc(size_t size) {
    if (size == 0) return NULL;
    // Align to 8 bytes
    size = (size + 7) & ~7;
    if (!arena_head || arena_head->offset + size > ARENA_CHUNK) {
        ArenaChunk *c = calloc(1, sizeof(ArenaChunk));
        c->next = arena_head;
        arena_head = c;
    }
    void *ptr = arena_head->data + arena_head->offset;
    arena_head->offset += size;
    return ptr;
}

char *arena_strdup(const char *s) {
    if (!s) return NULL;
    size_t len = strlen(s) + 1;
    char *dup = arena_alloc(len);
    memcpy(dup, s, len);
    return dup;
}

void arena_free_all(void) {
    ArenaChunk *c = arena_head;
    while (c) {
        ArenaChunk *next = c->next;
        free(c);
        c = next;
    }
    arena_head = NULL;
}

typedef struct {
    int cap;
    int len;
    void **data;
} ListHeader;

static void **list_make(void) {
    ListHeader *h = arena_alloc(sizeof(ListHeader));
    h->cap = 4;
    h->len = 0;
    h->data = arena_alloc(sizeof(void*) * h->cap);
    h->data[0] = NULL;
    return h->data;
}

static void **list_append(void **list, void *item) {
    if (!list) list = list_make();
    // To find the header, we might just store it. Wait, the arena memory isn't reallocable.
    // Better: store len and cap before the array.
    // Let's implement lists properly inside arena:
    return NULL; // Wait, will redefine list below
}

// Simple list: since it's arena, we can just copy.
// Let's do a simple array that is copied on grow.
static void **grow_list(void **list, void *item) {
    int len = 0;
    if (list) {
        while (list[len]) len++;
    }
    void **new_list = arena_alloc(sizeof(void*) * (len + 2));
    for (int i = 0; i < len; i++) new_list[i] = list[i];
    new_list[len] = item;
    new_list[len + 1] = NULL;
    return new_list;
}

Node **node_list_make(void) { return NULL; }
Node **node_list_append(Node **list, Node *node) { return (Node**)grow_list((void**)list, node); }

Type **type_list_make(void) { return NULL; }
Type **type_list_append(Type **list, Type *type) { return (Type**)grow_list((void**)list, type); }

int node_list_len(Node **list) {
    if (!list) return 0;
    int i = 0;
    while (list[i]) i++;
    return i;
}

Node *make_node(NodeKind kind, Loc loc) {
    Node *n = arena_alloc(sizeof(Node));
    n->kind = kind;
    n->loc = loc;
    return n;
}

Type *make_type(TypeKind tk) {
    Type *t = arena_alloc(sizeof(Type));
    t->tk = tk;
    return t;
}

static Node **top_level_items = NULL;

void add_top_level(Node *node) {
    top_level_items = node_list_append(top_level_items, node);
}

Node **get_top_level(void) {
    return top_level_items;
}

// Type building helper
Type *build_type(DeclSpec *spec, Declarator *decl, const char **out_name, Node ***out_params, int strip_func) {
    Type *base = make_type(TK_BASE);
    base->is_const = spec->has_const;
    if (spec->struct_type) {
        // Struct could be just a reference or a def. The type pointer handles it.
        base = spec->struct_type;
    } else if (spec->typedef_name) {
        base->tk = TK_TYPEDEF;
        base->name = spec->typedef_name;
    } else {
        // construct name like "unsigned int"
        char buf[128] = {0};
        if (spec->has_unsigned) strcat(buf, "unsigned ");
        if (spec->has_signed) strcat(buf, "signed ");
        if (spec->has_void) strcat(buf, "void ");
        if (spec->has_char) strcat(buf, "char ");
        if (spec->has_short) strcat(buf, "short ");
        if (spec->has_int) strcat(buf, "int ");
        if (spec->has_long && spec->has_long_long) strcat(buf, "long long ");
        else if (spec->has_long) strcat(buf, "long ");
        if (spec->has_float) strcat(buf, "float ");
        if (spec->has_double) strcat(buf, "double ");
        
        if (strlen(buf) > 0 && buf[strlen(buf)-1] == ' ') buf[strlen(buf)-1] = '\0';
        if (strlen(buf) == 0) strcpy(buf, "int"); // implicit int
        base->name = arena_strdup(buf);
    }

    if (!decl) {
        if (out_name) *out_name = NULL;
        if (out_params) *out_params = NULL;
        return base;
    }

    // Traverse declarator chain: it is built from inside out.
    // e.g., *a[10] -> decl=ARRAY(10), decl->base=POINTER, decl->base->base=IDENT(a)
    // Actually, bison parses it inside out. 
    // `pointer direct_declarator` makes POINTER wrap the inner.
    // So the tree of Declarator has IDENT at the bottom.
    // But type needs to wrap base.
    
    // We need to invert the chain to build the Type.
    Declarator *d = decl;
    Declarator *chain[100];
    int count = 0;
    while (d && d->kind != DECL_IDENT) {
        chain[count++] = d;
        d = d->base;
    }
    
    if (d && out_name) *out_name = d->name;
    if (out_params) *out_params = NULL;
    
    Type *curr = base;
    for (int i = 0; i < count; i++) {
        Declarator *c = chain[i];
        if (c->kind == DECL_FUNC && out_params) *out_params = c->func_params;
        
        if (strip_func && i == count - 1 && c->kind == DECL_FUNC) {
            continue; // Skip the outermost FUNC wrapper
        }
        
        if (c->kind == DECL_POINTER) {
            Type *ptr = make_type(TK_POINTER);
            ptr->to = curr;
            ptr->is_const = c->is_const;
            curr = ptr;
        } else if (c->kind == DECL_ARRAY) {
            Type *arr = make_type(TK_ARRAY);
            arr->to = curr; // 'of' maps to 'to' structurally
            arr->size = c->array_size;
            curr = arr;
        } else if (c->kind == DECL_FUNC) {
            Type *fun = make_type(TK_FUNCTION);
            fun->returns = curr;
            fun->params = c->func_params;
            curr = fun;
        }
    }
    return curr;
}

Node *build_var_decl(DeclSpec *spec, Declarator *decl, Node *init, int is_global, Loc loc) {
    const char *name = NULL;
    Type *t = build_type(spec, decl, &name, NULL, 0);
    Node *n = make_node(ND_VAR_DECL, loc);
    n->name = name;
    n->type = t;
    n->init = init;
    n->is_global = is_global;
    if (spec->storage_static) n->storage = "static";
    else if (spec->storage_extern) n->storage = "extern";
    return n;
}
