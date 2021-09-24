/*
g++ appLayer/in*App/try.cpp -o appLayer/in*App/try
appLayer/in*App/try
*/

#include <iostream>
#include <list>
using namespace std;
#define A 1
#define ppp(a) cout<<A<<' '<<a<<endl;
void aaa(){
    ppp("aaa");
}
#define A 2
void bbb(){
    ppp("bbb");
}

int main(){
    ppp("hh");
    aaa();
    bbb();
}