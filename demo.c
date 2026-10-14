int BadName = 1;

static int unused_func() {
    return 0;
}

int no_return() {
    int a = 1;
}

int main(int unused_param) {
    int unused = 0;
    
    // Magic number and dead store
    int x = 42;
    x = 10;
    
    // Uninitialized variable
    int y;
    int z = y + 1;
    
    // Const index out of bounds
    int arr[5];
    arr[10] = 1;
    
    // Unsafe function
    char buf[100];
    gets(buf);
    
    return z;
    
    // Unreachable code
    int b = 1;
}
