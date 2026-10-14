#include <stdio.h>
#include <string.h>
#include "parser.h"
#include "ast.h"
#include "errors.h"
#include "directives.h"
#include "json.h"
#include "typedefs.h"

extern int yyparse(void);
extern int yylex(void);
extern FILE *yyin;
extern char *yytext;

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s [--tokens] <file.c>\n", argv[0]);
        return 1;
    }
    
    int tokens_mode = 0;
    const char *filename = argv[1];
    if (strcmp(argv[1], "--tokens") == 0) {
        tokens_mode = 1;
        if (argc < 3) return 1;
        filename = argv[2];
    }
    
    yyin = fopen(filename, "r");
    if (!yyin) {
        perror("fopen");
        return 1;
    }
    
    typedefs_init();

    if (tokens_mode) {
        printf("[\n");
        int tok, first = 1;
        while ((tok = yylex())) {
            if (!first) printf(",\n");
            first = 0;
            printf("  {\"loc\": {\"line\": %d, \"col\": %d}, ", yylloc.first_line, yylloc.first_column);
            
            const char *kind = "UNKNOWN";
            if (tok < 256) {
                char buf[2] = {(char)tok, 0};
                printf("\"kind\": \"%s\", \"text\": \"%s\"}", buf, yytext);
                continue;
            }
            switch(tok) {
                case IDENT: kind = "IDENT"; break;
                case TYPE_NAME: kind = "TYPE_NAME"; break;
                case INT_LITERAL: kind = "INT_LITERAL"; break;
                case FLOAT_LITERAL: kind = "FLOAT_LITERAL"; break;
                case CHAR_LITERAL: kind = "CHAR_LITERAL"; break;
                case STRING_LITERAL: kind = "STRING_LITERAL"; break;
                case PTR_OP: kind = "PTR_OP"; break;
                case INC_OP: kind = "INC_OP"; break;
                case DEC_OP: kind = "DEC_OP"; break;
                case LEFT_OP: kind = "LEFT_OP"; break;
                case RIGHT_OP: kind = "RIGHT_OP"; break;
                case LE_OP: kind = "LE_OP"; break;
                case GE_OP: kind = "GE_OP"; break;
                case EQ_OP: kind = "EQ_OP"; break;
                case NE_OP: kind = "NE_OP"; break;
                case AND_OP: kind = "AND_OP"; break;
                case OR_OP: kind = "OR_OP"; break;
                case MUL_ASSIGN: kind = "MUL_ASSIGN"; break;
                case DIV_ASSIGN: kind = "DIV_ASSIGN"; break;
                case MOD_ASSIGN: kind = "MOD_ASSIGN"; break;
                case ADD_ASSIGN: kind = "ADD_ASSIGN"; break;
                case SUB_ASSIGN: kind = "SUB_ASSIGN"; break;
                case LEFT_ASSIGN: kind = "LEFT_ASSIGN"; break;
                case RIGHT_ASSIGN: kind = "RIGHT_ASSIGN"; break;
                case AND_ASSIGN: kind = "AND_ASSIGN"; break;
                case XOR_ASSIGN: kind = "XOR_ASSIGN"; break;
                case OR_ASSIGN: kind = "OR_ASSIGN"; break;
                case VOID: kind = "VOID"; break;
                case CHAR: kind = "CHAR"; break;
                case SHORT: kind = "SHORT"; break;
                case INT: kind = "INT"; break;
                case LONG: kind = "LONG"; break;
                case FLOAT: kind = "FLOAT"; break;
                case DOUBLE: kind = "DOUBLE"; break;
                case SIGNED: kind = "SIGNED"; break;
                case UNSIGNED: kind = "UNSIGNED"; break;
                case CONST: kind = "CONST"; break;
                case STATIC: kind = "STATIC"; break;
                case EXTERN: kind = "EXTERN"; break;
                case STRUCT: kind = "STRUCT"; break;
                case TYPEDEF: kind = "TYPEDEF"; break;
                case IF: kind = "IF"; break;
                case ELSE: kind = "ELSE"; break;
                case WHILE: kind = "WHILE"; break;
                case DO: kind = "DO"; break;
                case FOR: kind = "FOR"; break;
                case SWITCH: kind = "SWITCH"; break;
                case CASE: kind = "CASE"; break;
                case DEFAULT: kind = "DEFAULT"; break;
                case BREAK: kind = "BREAK"; break;
                case CONTINUE: kind = "CONTINUE"; break;
                case RETURN: kind = "RETURN"; break;
                case SIZEOF: kind = "SIZEOF"; break;
            }
            printf("\"kind\": \"%s\", \"text\": \"%s\"}", kind, yytext);
        }
        printf("\n]\n");
    } else {
        int res = yyparse();
        print_json(filename);
        arena_free_all();
        return res == 0 && get_error_count() == 0 ? 0 : 1;
    }
    
    return 0;
}
