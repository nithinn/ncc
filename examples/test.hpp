#ifndef SYMBOL
#define SYMBOL

class Test
{
public:
    Test(){};
    virtual ~Test(){};

private:
    /* data */
    int t;

    void func();
};

typedef struct _test_t
{
    int _aaa;
} test_t;

#endif
