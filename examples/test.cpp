#include <iostream>

struct A
{
    int a;
};

typedef A aTypeDef;

typedef struct C
{
    int a;
    int m_b;
} ccc;

class B
{
public:
    B() {};
    virtual ~B() {};

    void function_name()
    {
        /* code */
    }
private:
    /* data */
    int b;
};

int g_abc = 0;
int abc = 0;

static int s_abc = 0;

int main(int argc, const char *argv[])
{
    int b = 0;

    if (true)
    {
        int a = 10;
    }

    return 0;
}
